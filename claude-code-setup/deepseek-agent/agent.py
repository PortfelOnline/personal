
def _api_call_with_tools_stream(messages, tools=None, temperature=0.7, max_tokens=8192, model=None):
    """Streaming call with tool support."""
    from deepseek_api import _api_key, DEFAULT_MODEL, FAST_MODEL, BASE_URL, route_model

    # Route if no explicit model
    if model is None:
        _prompt = ""
        _system = ""
        for m in messages:
            if m.get("role") == "system" and m.get("content"):
                _system = m["content"]
            elif m.get("role") == "user" and m.get("content"):
                _prompt = m["content"]
        model = route_model(prompt=_prompt, system=_system)
        import sys
        print(f"[Router] Tools stream routed to {model}", file=sys.stderr, flush=True)

    actual_model = model or DEFAULT_MODEL
    models_to_try = [actual_model]
    if actual_model == DEFAULT_MODEL:
        models_to_try.append(FAST_MODEL)

    last_error = None
    for attempt_model in models_to_try:
        for attempt in range(3):
            try:
                body = {
                    "model": attempt_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True,
                }
                if response_format:
                    body["response_format"] = response_format
                if tools:
                    body["tools"] = tools

                req_body = json.dumps(body).encode("utf-8")
                req = urllib.request.Request(
                    f"{BASE_URL}/chat/completions",
                    data=req_body,
                    headers={
                        "Authorization": f"Bearer {_api_key()}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    partial_tc = {}
                    full_content = []
                    reasoning = None
                    finish = None

                    for raw in resp:
                        line = raw.decode("utf-8").strip()
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        choices = chunk.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})

                        text = delta.get("content", "")
                        if text:
                            full_content.append(text)
                            yield text, None, None, None, None

                        rc = delta.get("reasoning_content")
                        if rc:
                            reasoning = rc

                        fr = choices[0].get("finish_reason")
                        if fr:
                            finish = fr

                        tc_delta = delta.get("tool_calls", [])
                        for tc in tc_delta:
                            idx = tc.get("index", 0)
                            if idx not in partial_tc:
                                partial_tc[idx] = {
                                    "id": tc.get("id", ""),
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                }
                            if tc.get("id"):
                                partial_tc[idx]["id"] = tc["id"]
                            fn = tc.get("function", {})
                            if fn.get("name"):
                                partial_tc[idx]["function"]["name"] += fn["name"]
                            if fn.get("arguments"):
                                partial_tc[idx]["function"]["arguments"] += fn["arguments"]

                    if partial_tc:
                        yield "", list(partial_tc.values()), reasoning, "".join(full_content), finish
                    else:
                        yield "", None, reasoning, "".join(full_content), finish
                    return  # success — exit both loops

            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")[:500]
                last_error = f"HTTP {e.code}: {err_body}"
                log(f"DeepSeek stream error: model={attempt_model} {last_error}")
                if e.code not in (429, 500, 502, 503, 504):
                    raise  # non-retryable — bail out
                if attempt < 2:
                    import time
                    time.sleep((2 ** attempt) * 1.0)
                    continue
                # Max retries for this model — try fallback
            except (urllib.error.URLError, OSError) as e:
                last_error = str(e)
                log(f"DeepSeek stream error: model={attempt_model} {last_error}")
                if attempt < 2:
                    import time
                    time.sleep((2 ** attempt) * 0.5)
                    continue
                break  # max retries for this model

        if attempt_model == models_to_try[-1]:
            break
        # Fallback to next model
        log(f"[Router] Stream fallback: {attempt_model} -> next")

    log(f"[Router] Stream failed: last={last_error}")
    raise RuntimeError(f"DeepSeek stream failed: {last_error}")

#!/usr/bin/env python3
"""
DeepSeek Agent — 24/7 AI tasks + Claude Code parity tools.

Tier 17: Model Router + Stack Health
Tier 18: Filesystem/git tools + /chat REPL

Endpoints:
  GET  /health              — status + uptime + tasks
  GET  /services            — health of all containers
  GET  /tasks               — scheduled tasks
  POST /run/<name>          — trigger task manually

  POST /tools/read          — read file
  POST /tools/write         — write file
  POST /tools/edit          — edit file (string replace)
  POST /tools/ls            — list directory
  POST /tools/grep          — search files (grep -rn)
  POST /tools/glob          — glob pattern
  GET  /tools/git-status    — git status
  GET  /tools/git-diff      — git diff
  POST /tools/git-commit    — git commit
  POST /tools/git-push      — git push
  GET  /tools/git-log       — git log

  POST /chat                — multi-turn with tool calling
  GET  /sessions            — list sessions
  DELETE /sessions/<id>     — delete session
"""

import sys, os, json, signal, time, subprocess, shlex, shutil, socket, fnmatch, glob as glob_mod, urllib.request, urllib.error, requests
import threading, queue as _queue
from datetime import datetime, timezone
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
from threading import Thread
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from deepseek_api import chat, stream_chat, FAST_MODEL, DEFAULT_MODEL, route_model
from safe_access import is_allowed, safe_join, check_dangerous_cmd, check_dangerous_write, check_hostile, check_file_size, check_write_size, check_network_access, check_web_rate_limit, check_web_url
from background_tasks import BackgroundTaskManager
from session_manager import SessionManager
from mcp_client import init_mcp_servers, MCPClient
from plugin_loader import init_plugins
from cron_manager import init_cron, create_task, list_tasks, delete_task
from hook_loader import init_hooks, run_hooks, list_hooks

START_TIME = datetime.now(timezone.utc)
sessions = SessionManager()
_session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")
os.makedirs(_session_dir, exist_ok=True)
SESSION_FILE = os.path.join(_session_dir, "sessions.json")
_session_loaded_cnt = sessions.load(SESSION_FILE)
if _session_loaded_cnt:
    print(f"Restored {_session_loaded_cnt} session(s) from disk")
_last = sessions.get_last_active()
if _last:
    _CURRENT_SESSION_ID = _last.id
    _last_name = getattr(_last, "name", "") or _last.id
    print(f"Auto-restored session: {_last_name} ({len(_last.messages)} messages, last active {_last.updated})")
else:
    print("No previous session found — starting fresh")

# ── Task store ──
TASKS_FILE = os.path.join(_session_dir, "tasks.json")
_tasks = {}
if os.path.exists(TASKS_FILE):
    import json as _j
    with open(TASKS_FILE) as _f:
        _tasks = _j.load(_f)
    print(f"Loaded {len(_tasks)} task(s) from disk")

# ── Memory store ──
MEMORY_FILE = os.path.join(_session_dir, "memory.json")
_memory = {}
if os.path.exists(MEMORY_FILE):
    import json as _j2
    with open(MEMORY_FILE) as _f2:
        _memory = _j2.load(_f2)
    print(f"Loaded {len(_memory)} memory item(s) from disk")

# ── Sub-agent state ──
_subagents = {}
_subagents_lock = threading.Lock()
_bg_tasks = BackgroundTaskManager()
SUBAGENT_TIMEOUT = 300

# ── Sub-agent auto-routing profiles ──
_AGENT_PROFILES = {
    "code_review": {
        "label": "Code Review",
        "system": "You are a senior code reviewer. Analyze code for: bugs, security issues, performance problems, style violations, and architectural concerns. Be specific — cite exact lines and suggest fixes. Output a structured report with severity levels (CRITICAL/HIGH/MEDIUM/LOW).",
        "model": "deepseek-v4-flash",
    },
    "debug": {
        "label": "Debugger",
        "system": "You are a debugger. Analyze error messages, stack traces, and code context. Identify root cause, not just symptoms. Suggest exact fixes with code snippets. If you need more info, say what specifically is missing.",
        "model": "deepseek-v4-flash",
    },
    "refactor": {
        "label": "Refactoring Expert",
        "system": "You are a refactoring expert. Analyze code structure and suggest improvements: reduce duplication, improve naming, simplify logic, split large functions, improve testability. Output specific before/after code snippets. Preserve behavior.",
        "model": "deepseek-v4-flash",
    },
    "research": {
        "label": "Researcher",
        "system": "You are a technical researcher. Search for information, compare approaches, analyze trade-offs. Output structured findings with pros/cons and recommendations. Cite sources when possible.",
        "model": "deepseek-v4-flash",
    },
    "write_code": {
        "label": "Coding Agent",
        "system": "You are a coding agent. Write clean, correct, well-structured code. Follow existing codebase patterns. Output ONLY the code with minimal explanation unless asked otherwise.",
        "model": "deepseek-v4-flash",
    },
    "ops": {
        "label": "DevOps Engineer",
        "system": "You are a DevOps engineer. Diagnose infrastructure issues, analyze logs, troubleshoot deployments. Be specific with commands, config changes, and debugging steps. Consider security and idempotency.",
        "model": "deepseek-v4-flash",
    },
}

# ── Auto-routing state ──
_auto_route_enabled = True  # can toggle with /auto-route endpoint

# ── Plan mode state ──
_plans = {}
_plans_lock = threading.Lock()
_plan_mode_active = False

ALLOWED_BASES = ["/app", "/root", "/tmp"]
NOTIFY_TELEGRAM_BOT_TOKEN = os.environ.get("NOTIFY_TELEGRAM_BOT_TOKEN", "")
NOTIFY_TELEGRAM_CHAT_ID = os.environ.get("NOTIFY_TELEGRAM_CHAT_ID", "")
TOOL_CALL_MAX_ITER = 6
BUDGET_DEFAULT_MAX_USD = 0.05  # $0.05/session safety net (opt-out: 0.0 = unlimited)
_session_budget = {}  # session_id -> {"total_cost": float, "api_calls": int}
_session_budget_lock = threading.Lock()
_msg_save_counter = 0  # periodic auto-save counter

# Effort → max tool call iterations
EFFORT_MAP = {"low": 3, "medium": 6, "high": 12}

MCP_CLIENTS = []  # list of (name, MCPClient)  # safety limit for tool calling loop

# ── Auto-memory ─────────────────────────────────────────
# Auto-save trigger: after every N LLM responses without explicit memory_set,
# key facts are extracted and persisted automatically.
_AUTO_MEMORY_ENABLED = True

# ── Web cache ──
_web_cache = {}
_web_cache_ttl = 300  # 5 min cache TTL

# ── Monitor state ──
_monitors = {}
_monitors_lock = threading.Lock()

# ── Permission gates state ─────────────────────────────────────

PENDING_DANGEROUS = {}  # session_id -> {"type": "bash"|"write"|"edit", "key": str, "params": dict, "warning": str}
_CURRENT_SESSION_ID = None

CONFIRM_KEYWORDS = [
    "да", "подтверждаю", "разрешаю", "выполняй", "делай",
    "давай", "ок", "ok", "yes", "confirm", "go ahead",
    "согласен", "можно", "выполнить",
]

def _pending_key(val):
    """Hash-based key to identify a pending dangerous operation."""
    import hashlib
    return hashlib.md5(val.encode()).hexdigest()[:16]

def _is_confirmation(text):
    """Check if user message is a confirmation for a pending dangerous operation."""
    t = text.strip().lower().rstrip(".!?")
    return t in CONFIRM_KEYWORDS or any(t == kw for kw in CONFIRM_KEYWORDS)
  # list of (name, MCPClient)  # safety limit for tool calling loop

SERVICES = {
    "deepseek-agent":        {"port": 8766, "group": "ai"},
    "kad":                   {"port": 8082, "group": "web"},
    "bot_dashboard":         {"port": 4000, "group": "bots"},
    "proxy_checker":         {"port": 8765, "group": "bots"},
    "aiwaiter":              {"port": 4100, "group": "web"},
    "yandex_bot":            {"port": None,  "group": "bots"},
    "n8n-docker-n8n-1":     {"port": 5678, "group": "infra"},
    "n8n-docker-redis-1":   {"port": 6380, "group": "infra"},
    "n8n-docker-browserless-1": {"port": 3001, "group": "infra"},
    "n8n-docker-qdrant-1":  {"port": 6335, "group": "infra"},
    "n8n-docker-db-1":      {"port": 5432, "group": "infra"},
    "mariadb-wordpress":    {"port": 3306, "group": "infra"},
    "buildx_buildkit_n8n-bx0": {"port": None,  "group": "infra"},
}

# ── Tool definitions (OpenAI function calling format) ──────────────

TOOL_DEFS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from disk",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to file"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to file"},
                    "content": {"type": "string", "description": "File content"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace text in a file by string match",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to file"},
                    "old_string": {"type": "string", "description": "Text to replace"},
                    "new_string": {"type": "string", "description": "Replacement text"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ls_dir",
            "description": "List directory contents",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to directory"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep_files",
            "description": "Search for pattern in files",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern"},
                    "path": {"type": "string", "description": "Directory to search"},
                    "glob": {"type": "string", "description": "File glob filter (e.g. *.ts, *.py)"},
                },
                "required": ["pattern", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "glob_files",
            "description": "Find files matching a glob",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern (e.g. **/*.py)"},
                    "path": {"type": "string", "description": "Root directory"},
                },
                "required": ["pattern", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Execute a shell command",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Git status",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Git repo path"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "Git diff",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Git repo path"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_log",
            "description": "Git log",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Git repo path"},
                    "n": {"type": "integer", "description": "Number of commits"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch and process a URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL to fetch (http/https only)"},
                    "selector": {"type": "string", "description": "Optional CSS selector to extract specific content"}
                },
                "required": ["url"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Max results (1-10, default 5)"},
                    "allowed_domains": {"type": "array", "items": {"type": "string"}, "description": "Only return results from these domains (e.g., [\"github.com\", \"react.dev\"])"},
                    "blocked_domains": {"type": "array", "items": {"type": "string"}, "description": "Exclude results from these domains (e.g., [\"wikipedia.org\", \"reddit.com\"])"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task_create",
            "description": "Create a background task",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "description": "Short task title"},
                    "description": {"type": "string", "description": "Detailed description"}
                },
                "required": ["subject"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task_update",
            "description": "Update task status",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID to update"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed"], "description": "New status"},
                    "description": {"type": "string", "description": "Updated description"},
                    "subject": {"type": "string", "description": "Updated subject"}
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task_list",
            "description": "List background tasks",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["all", "pending", "in_progress", "completed"], "description": "Filter by status"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task_delete",
            "description": "Delete a task by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID to delete"}
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_set",
            "description": "Store a value in memory",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Memory key (e.g. 'project/myapp/language', 'user/preference')"},
                    "value": {"type": "string", "description": "Value to store"}
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_get",
            "description": "Read a value from memory by key",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Memory key to retrieve"}
                },
                "required": ["key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_search",
            "description": "Search memory by key prefix",
            "parameters": {
                "type": "object",
                "properties": {
                    "prefix": {"type": "string", "description": "Key prefix to match (e.g. 'project/' returns all project memories)"}
                },
                "required": ["prefix"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_delete",
            "description": "Delete a memory by key.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Memory key to delete"}
                },
                "required": ["key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notify",
            "description": "Send a notification",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Notification message text"},
                    "level": {"type": "string", "enum": ["info", "success", "warning", "error"], "description": "Notification level (default: info)"}
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "subagent_spawn",
            "description": "Spawn a sub-agent",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "The task/instruction for the sub-agent"},
                    "system": {"type": "string", "description": "Optional system prompt for the sub-agent"},
                    "model": {"type": "string", "enum": ["deepseek-v4-flash", "deepseek-v4-pro"], "description": "Model override (default: auto-routed)"}
                },
                "required": ["task"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "subagent_list",
            "description": "List sub-agents",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["running", "completed", "failed", "killed"], "description": "Filter by status"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "subagent_result",
            "description": "Get sub-agent result by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Sub-agent task ID to retrieve result for"}
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "subagent_kill",
            "description": "Kill a running sub-agent by task ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Sub-agent task ID to kill"}
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plan_create",
            "description": "Create a new plan",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Plan title"},
                    "description": {"type": "string", "description": "Optional plan summary"}
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plan_section",
            "description": "Add a section to a plan",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "Plan ID from plan_create"},
                    "name": {"type": "string", "description": "Section name (e.g. architecture, components, data_flow, implementation_steps)"},
                    "content": {"type": "string", "description": "Section content/analysis"}
                },
                "required": ["plan_id", "name", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plan_present",
            "description": "Mark plan ready for review",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "Plan ID to present for review"}
                },
                "required": ["plan_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plan_approve",
            "description": "Mark plan as approved",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "Plan ID to approve"}
                },
                "required": ["plan_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plan_list",
            "description": "List plans",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["draft", "review", "approved", "implemented"], "description": "Filter by plan status"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "monitor_start",
            "description": "Start a background monitor",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run in the background"},
                    "timeout": {"type": "integer", "description": "Optional timeout in seconds (default: no timeout)"}
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "monitor_result",
            "description": "Get monitor output",
            "parameters": {
                "type": "object",
                "properties": {
                    "monitor_id": {"type": "string", "description": "Monitor ID to retrieve result for"}
                },
                "required": ["monitor_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "monitor_stop",
            "description": "Stop a running monitor",
            "parameters": {
                "type": "object",
                "properties": {
                    "monitor_id": {"type": "string", "description": "Monitor ID to stop"}
                },
                "required": ["monitor_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "monitor_list",
            "description": "List all monitors",
            "parameters": {
                "type": "object",
                "properties": {}
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cron_create",
            "description": "Create a recurring cron task",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Standard 5-field cron expression (e.g. '0 9 * * *', '*/30 * * * *')"},
                    "action": {"type": "string", "description": "Chat message to send when the cron fires"},
                    "description": {"type": "string", "description": "Optional human-readable description"}
                },
                "required": ["expression", "action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cron_list",
            "description": "List cron tasks",
            "parameters": {
                "type": "object",
                "properties": {}
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cron_delete",
            "description": "Delete a cron task",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID of the cron to delete"}
                },
                "required": ["task_id"],
            },
        },
    },
]


# ── Tool implementations ──────────────────────────────────────────

def _path_from_params(params):
    path = params.get("path", "")
    if path.startswith("/"):
        # Check if absolute path is allowed
        return path if is_allowed(path) else None
    # Relative — try each base
    for base in ALLOWED_BASES:
        joined = safe_join(base, path)
        if joined:
            return joined
    return None


def tool_read_file(params):
    path = _path_from_params(params)
    if not path:
        return json.dumps({"error": "path not allowed or not found"})
    if not os.path.isfile(path):
        return json.dumps({"error": f"not a file: {path}"})
    warn = check_file_size(path)
    if warn:
        return json.dumps({"permission_required": True, "warning": warn, "path": path})
    try:
        with open(path, "r", errors="replace") as f:
            content = f.read()
        # Truncate very large files
        if len(content) > 50000:
            content = content[:50000] + "\n... [truncated 50000 chars]"
        return content
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_write_file(params):
    path = _path_from_params(params)
    if not path:
        return json.dumps({"error": "path not allowed"})
    content = params.get("content", "")
    warn = check_write_size(content)
    if warn:
        return json.dumps({"permission_required": True, "warning": warn, "path": path})
    is_dw, dw_warn = check_dangerous_write(path)
    if is_dw:
        sid = _CURRENT_SESSION_ID
        key = _pending_key(path)
        if sid and PENDING_DANGEROUS.get(sid, {}).get("key") == key:
            if sid in PENDING_DANGEROUS:
                del PENDING_DANGEROUS[sid]
        else:
            PENDING_DANGEROUS[sid] = {"type": "write", "key": key, "params": {"path": path, "content_len": len(content)}, "warning": dw_warn}
            return json.dumps({"permission_required": True, "warning": dw_warn, "path": path})
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(params.get("content", ""))
        return json.dumps({"ok": True, "path": path, "bytes": len(params.get("content", ""))})
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_edit_file(params):
    path = _path_from_params(params)
    if not path or not os.path.isfile(path):
        return json.dumps({"error": "path not allowed or not found"})
    is_dw, dw_warn = check_dangerous_write(path)
    if is_dw:
        sid = _CURRENT_SESSION_ID
        key = _pending_key(path)
        if sid and PENDING_DANGEROUS.get(sid, {}).get("key") == key:
            if sid in PENDING_DANGEROUS:
                del PENDING_DANGEROUS[sid]
        else:
            PENDING_DANGEROUS[sid] = {"type": "edit", "key": key, "params": {"path": path}, "warning": dw_warn}
            return json.dumps({"permission_required": True, "warning": dw_warn, "path": path})
    old, new = params.get("old_string", ""), params.get("new_string", "")
    if not old:
        return json.dumps({"error": "old_string required"})
    try:
        with open(path, "r") as f:
            content = f.read()
        if old not in content:
            return json.dumps({"error": "old_string not found in file"})
        content = content.replace(old, new, 1)
        with open(path, "w") as f:
            f.write(content)
        _edit_ret = json.dumps({"ok": True, "replaced": old.count(old) > 0})
        _safe_run_hooks("PostEdit", path=path, old_len=len(old), new_len=len(new), status="ok", session_id=_CURRENT_SESSION_ID)
        return _edit_ret
    except Exception as e:
        _edit_err = json.dumps({"error": str(e)})
        _safe_run_hooks("PostEdit", path=path, old_len=len(old), new_len=len(new), status="error", session_id=_CURRENT_SESSION_ID)
        return _edit_err


def tool_ls_dir(params):
    path = _path_from_params(params)
    if not path:
        return json.dumps({"error": "path not allowed"})
    if not os.path.isdir(path):
        return json.dumps({"error": f"not a directory: {path}"})
    try:
        entries = os.listdir(path)
        result = []
        for e in sorted(entries):
            full = os.path.join(path, e)
            t = "d" if os.path.isdir(full) else "f"
            size = os.path.getsize(full) if os.path.isfile(full) else 0
            result.append(f"{t} {size:>10} {e}")
        return "\n".join(result[:500])  # cap at 500 entries
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_grep_files(params):
    base = _path_from_params({"path": params.get("path", "/app")})
    if not base:
        return json.dumps({"error": "path not allowed"})
    pattern = params.get("pattern", "")
    file_pat = params.get("glob", "")
    try:
        cmd = f"grep -rn --binary-files=without-match {shlex.quote(pattern)} {shlex.quote(base)}"
        if file_pat:
            cmd = f"grep -rn --include={shlex.quote(file_pat)} {shlex.quote(pattern)} {shlex.quote(base)}"
        result = subprocess.check_output(cmd, shell=True, timeout=30, stderr=subprocess.DEVNULL)
        output = result.decode("utf-8", errors="replace")[:10000]
        if len(output) >= 10000:
            output += "\n... [truncated]"
        return output or "(no matches)"
    except subprocess.CalledProcessError as e:
        return "(no matches)" if e.returncode == 1 else json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_glob_files(params):
    base = _path_from_params({"path": params.get("path", "/app")})
    if not base:
        return json.dumps({"error": "path not allowed"})
    pattern = params.get("pattern", "**/*")
    full_pattern = os.path.join(base, pattern)
    try:
        matches = glob_mod.glob(full_pattern, recursive=True)[:200]
        return "\n".join(m for m in sorted(matches) if is_allowed(m)) or "(no matches)"
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_bash(params):
    cmd = params.get("command", "")
    timeout = min(params.get("timeout", 30), 120)
    if not cmd:
        return json.dumps({"error": "command required"})

    # PreBash hook
    _pre_ret = _safe_run_hooks("PreBash", command=cmd, session_id=_CURRENT_SESSION_ID)
    if _pre_ret and "error" in _pre_ret:
        return json.dumps({"blocked": True, "error": _pre_ret["error"]})
    is_dangerous, warning = check_dangerous_cmd(cmd)
    if is_dangerous:
        sid = _CURRENT_SESSION_ID
        key = _pending_key(cmd)
        if sid and PENDING_DANGEROUS.get(sid, {}).get("key") == key:
            # Authorized — remove pending and execute
            if sid in PENDING_DANGEROUS:
                del PENDING_DANGEROUS[sid]
        else:
            # Store pending and ask
            PENDING_DANGEROUS[sid] = {"type": "bash", "key": key, "params": {"command": cmd}, "warning": warning}
            return json.dumps({"permission_required": True, "warning": warning, "command": cmd})
    hostile_blocked, hostile_warning = check_hostile(cmd)
    if hostile_blocked:
        return json.dumps({"error": hostile_warning, "command": cmd, "blocked": True})
    try:
        result = subprocess.check_output(
            cmd, shell=True, timeout=timeout, stderr=subprocess.STDOUT
        )
        output = result.decode("utf-8", errors="replace")[:15000]
        if len(output) >= 15000:
            output += "\n... [truncated]"
        return output or "(empty output)"
    except subprocess.CalledProcessError as e:
        return e.output.decode("utf-8", errors="replace")[:5000] if e.output else f"exit code {e.returncode}"
    except subprocess.TimeoutExpired:
        return json.dumps({"error": f"timeout after {timeout}s"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_git_status(params):
    path = _path_from_params(params)
    if not path:
        return json.dumps({"error": "path not allowed"})
    try:
        r = subprocess.check_output(
            f"cd {shlex.quote(path)} && git status",
            shell=True, timeout=15, stderr=subprocess.STDOUT
        )
        return r.decode("utf-8", errors="replace")
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_git_diff(params):
    path = _path_from_params(params)
    if not path:
        return json.dumps({"error": "path not allowed"})
    try:
        r = subprocess.check_output(
            f"cd {shlex.quote(path)} && git diff",
            shell=True, timeout=15, stderr=subprocess.STDOUT
        )
        d = r.decode("utf-8", errors="replace")[:30000]
        return d or "(clean)"
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_git_log(params):
    path = _path_from_params(params)
    n = min(params.get("n", 10), 50)
    if not path:
        return json.dumps({"error": "path not allowed"})
    try:
        r = subprocess.check_output(
            f"cd {shlex.quote(path)} && git log --oneline -{n}",
            shell=True, timeout=15, stderr=subprocess.STDOUT
        )
        return r.decode("utf-8", errors="replace")
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_git_commit(params):
    repo = params.get("repo_path", "")
    msg = params.get("message", "")
    if not repo or not msg:
        return json.dumps({"error": "repo_path and message required"})
    if not os.path.isdir(os.path.join(repo, ".git")):
        return json.dumps({"error": "not a git repository"})
    try:
        r = subprocess.check_output(
            f"cd {shlex.quote(repo)} && git add -A && git commit -m {shlex.quote(msg)}",
            shell=True, timeout=30, stderr=subprocess.STDOUT
        )
        return r.decode("utf-8", errors="replace")
    except subprocess.CalledProcessError as e:
        out = e.output.decode("utf-8", errors="replace") if e.output else str(e)
        return json.dumps({"error": out})
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_git_push(params):
    repo = params.get("repo_path", "")
    remote = params.get("remote", "origin")
    branch = params.get("branch", "")
    if not repo:
        return json.dumps({"error": "repo_path required"})
    if not os.path.isdir(os.path.join(repo, ".git")):
        return json.dumps({"error": "not a git repository"})
    try:
        cmd = f"cd {shlex.quote(repo)} && git push {shlex.quote(remote)}"
        if branch:
            cmd += f" {shlex.quote(branch)}"
        r = subprocess.check_output(cmd, shell=True, timeout=60, stderr=subprocess.STDOUT)
        return r.decode("utf-8", errors="replace")
    except subprocess.CalledProcessError as e:
        out = e.output.decode("utf-8", errors="replace") if e.output else str(e)
        return json.dumps({"error": out})
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_web_fetch(params):
    url = params.get("url", "")
    selector = params.get("selector", "")
    if not url:
        return json.dumps({"error": "url required"})

    # Security: validate URL
    blocked, reason = check_web_url(url)
    if blocked:
        return json.dumps({"error": reason, "url": url, "blocked": True})
    blocked, reason = check_web_rate_limit()
    if blocked:
        return json.dumps({"error": reason})

    try:
        resp = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; DeepSeekAgent/1.0)"},
            allow_redirects=True,
        )
        resp.raise_for_status()

        # Limit response size
        raw = resp.text[:25600]  # 25KB

        if selector:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(raw, "html.parser")
            elements = soup.select(selector)
            if not elements:
                return "No elements matched selector: " + selector
            text = "\n\n".join(el.get_text(strip=True) for el in elements)
        else:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(raw, "html.parser")
            # Remove script/style elements
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)

        # Truncate to 50KB
        text = text[:25600]
        if len(text) >= 25600:
            text += "\n... [truncated to 50KB]"

        if not text.strip():
            return "(empty page)"
        return text

    except requests.exceptions.Timeout:
        return json.dumps({"error": "request timed out after 15s"})
    except requests.exceptions.ConnectionError as e:
        return json.dumps({"error": "connection failed: " + str(e)})
    except requests.exceptions.HTTPError as e:
        return json.dumps({"error": "HTTP " + str(e.response.status_code) if hasattr(e, "response") else str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Task Management ──

def _tasks_save():
    import json
    tmp = TASKS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(_tasks, f, ensure_ascii=False, indent=2)
    os.replace(tmp, TASKS_FILE)

def tool_task_create(params):
    subject = params.get("subject", "untitled")
    desc = params.get("description", "")
    tid = "t" + str(int(__import__("time").time() * 10))[-8:]
    _tasks[tid] = {"id": tid, "subject": subject, "description": desc, "status": "pending"}
    _tasks_save()
    return json.dumps({"task_id": tid, "subject": subject, "status": "pending"})

def tool_task_update(params):
    tid = params.get("task_id", "")
    if tid not in _tasks:
        return json.dumps({"error": f"task not found: {tid}"})
    if "status" in params:
        _tasks[tid]["status"] = params["status"]
    if "subject" in params:
        _tasks[tid]["subject"] = params["subject"]
    if "description" in params:
        _tasks[tid]["description"] = params["description"]
    _tasks_save()
    return json.dumps({"task_id": tid, "status": _tasks[tid]["status"]})

def tool_task_list(params):
    status_filter = params.get("status", "all")
    items = list(_tasks.values())
    if status_filter != "all":
        items = [t for t in items if t["status"] == status_filter]
    items.sort(key=lambda t: t["id"])
    summary = {s: sum(1 for t in _tasks.values() if t["status"] == s) for s in ("pending","in_progress","completed")}
    return json.dumps({"total": len(_tasks), "summary": summary, "tasks": items}, ensure_ascii=False)

def tool_task_delete(params):
    tid = params.get("task_id", "")
    if tid not in _tasks:
        return json.dumps({"error": f"task not found: {tid}"})
    subj = _tasks[tid]["subject"]
    del _tasks[tid]
    _tasks_save()
    return json.dumps({"deleted": tid, "subject": subj})


# ── Memory Management ──

def _memory_save():
    import json
    tmp = MEMORY_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(_memory, f, ensure_ascii=False, indent=2)
    os.replace(tmp, MEMORY_FILE)

def tool_memory_set(params):
    key = params.get("key", "")
    value = params.get("value", "")
    if not key:
        return json.dumps({"error": "key is required"})
    _memory[key] = value
    _memory_save()
    return json.dumps({"key": key, "stored": True})

def tool_memory_get(params):
    key = params.get("key", "")
    if key not in _memory:
        return json.dumps({"found": False, "key": key})
    return json.dumps({"found": True, "key": key, "value": _memory[key]}, ensure_ascii=False)

def tool_memory_search(params):
    prefix = params.get("prefix", "")
    items = [(k, v) for k, v in sorted(_memory.items()) if k.startswith(prefix)]
    return json.dumps({"prefix": prefix, "count": len(items), "results": [{"key": k, "value": v} for k, v in items]}, ensure_ascii=False)

def tool_memory_delete(params):
    key = params.get("key", "")
    if key not in _memory:
        return json.dumps({"error": f"memory key not found: {key}"})
    val = _memory.pop(key)
    _memory_save()
    return json.dumps({"deleted": key, "was": val}, ensure_ascii=False)


# ── Notifications ──

def _notify_telegram(message, level):
    bot_token = NOTIFY_TELEGRAM_BOT_TOKEN
    chat_id = NOTIFY_TELEGRAM_CHAT_ID
    if not bot_token or not chat_id:
        return False
    icon = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "🚨"}
    text = f"{icon.get(level, '')} DeepSeek Agent: {message}"
    import urllib.request
    import json as _json
    try:
        payload = _json.dumps({"chat_id": chat_id, "text": text}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception:
        return False

def tool_notify(params):
    message = params.get("message", "")
    level = params.get("level", "info")
    if level not in ("info", "success", "warning", "error"):
        level = "info"
    log(f"[NOTIFY:{level}] {message}")
    tg_ok = _notify_telegram(message, level)
    return json.dumps({"sent": True, "telegram": tg_ok, "level": level, "message": message}, ensure_ascii=False)



# ── Sub-agents ──────────────────────────────────────────

# ── Task classifier for auto-routing ──
_TASK_PATTERNS = [
    ("code_review", ["review", "code review", "check my code", "найди ошибки", "code review", "audit code", "найди баги", "проверь код"]),
    ("debug", ["debug", "ошибка", "error", "bug", "не работает", "crash", "traceback", "exception", "не запускается", "fix bug"]),
    ("refactor", ["refactor", "рефакторинг", "переписать", "улучшить код", "clean up", "упростить", "duplication"]),
    ("research", ["research", "исследуй", "найди информацию", "compare", "сравни", "analyze", "проанализируй", "alternatives", "альтернативы"]),
    ("write_code", ["напиши", "write", "implement", "реализуй", "create function", "создай", "add feature", "add endpoint"]),
    ("ops", ["server", "сервер", "deploy", "деплой", "docker", "nginx", "конфиг", "config", "logs", "лог", "ssh", "fail2ban", "systemd"]),
]

def _classify_task(message):
    """Classify user message into task type. Returns (category, confidence, reason)."""
    msg_lower = message.lower()
    best_cat = None
    best_score = 0
    best_reason = ""
    
    for cat, patterns in _TASK_PATTERNS:
        score = 0
        matched = []
        for p in patterns:
            if p in msg_lower:
                score += 1
                matched.append(p)
        if score > best_score:
            best_score = score
            best_cat = cat
            best_reason = ", ".join(matched[:3])
    
    if best_score >= 2:
        return best_cat, "high", best_reason
    elif best_score == 1:
        return best_cat, "medium", best_reason
    return None, "none", ""

def _auto_route(message, session_id):
    """If message matches a task profile, spawn sub-agent. Returns (routed, result_dict)."""
    global _auto_route_enabled
    if not _auto_route_enabled:
        return False, None
    
    cat, confidence, reason = _classify_task(message)
    if not cat or confidence == "none":
        return False, None
    
    profile = _AGENT_PROFILES.get(cat)
    if not profile:
        return False, None
    
    log(f"Auto-route: [{cat}] {reason} (confidence={confidence})")
    
    import time
    from deepseek_api import chat as _ds_chat
    
    # Build context from session
    session = sessions.get(session_id)
    context = ""
    if session and session.messages:
        recent = session.messages[-4:]  # last 4 messages for context
        parts = []
        for m in recent:
            role = m.get("role", "")
            content = (m.get("content") or "")[:300]
            if content:
                parts.append(f"{role}: {content}")
            elif m.get("tool_calls"):
                names = ", ".join(tc["function"]["name"] for tc in m["tool_calls"])
                parts.append(f"{role}: [tools: {names}]")
        if parts:
            context = "Recent conversation context:\n" + "\n".join(parts) + "\n\n"
    
    full_task = context + message
    
    try:
        result = _ds_chat(full_task, system=profile["system"], model=profile["model"])
        log(f"Auto-route [{cat}] completed ({len(result)} chars)")
        
        # Store in subagents list for tracking
        tid = "ar" + str(int(time.time() * 10))[-8:]
        entry = {
            "task_id": tid, "task": message[:100], "category": cat,
            "status": "completed", "result": result,
            "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "finished_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "auto_routed": True,
        }
        with _subagents_lock:
            _subagents[tid] = entry
        
        return True, {"category": cat, "result": result, "task_id": tid}
    except Exception as e:
        log(f"Auto-route [{cat}] FAILED: {e}")
        return False, None


def _subagent_worker(task_id, task_text, system_text, model):
    # Run sub-agent in a thread: call DeepSeek API, store result
    from deepseek_api import chat as _ds_chat
    try:
        result = _ds_chat(task_text, system=system_text, model=model or None)
        with _subagents_lock:
            if task_id in _subagents and _subagents[task_id]["status"] == "running":
                _subagents[task_id]["status"] = "completed"
                _subagents[task_id]["result"] = result
                _subagents[task_id]["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                log(f"Sub-agent [{task_id}] completed ({len(result)} chars)")
    except Exception as e:
        with _subagents_lock:
            if task_id in _subagents:
                _subagents[task_id]["status"] = "failed"
                _subagents[task_id]["result"] = str(e)
                _subagents[task_id]["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                log(f"Sub-agent [{task_id}] FAILED: {e}")

def tool_subagent_spawn(params):
    task = params.get("task", "")
    if not task:
        return json.dumps({"error": "task is required"})
    system = params.get("system", "")
    model = params.get("model", "")
    tid = "sa" + str(int(time.time() * 10))[-8:]
    entry = {
        "task_id": tid, "task": task, "system": system, "model": model,
        "status": "running", "result": "",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "finished_at": "",
    }
    with _subagents_lock:
        _subagents[tid] = entry
    t = threading.Thread(target=_subagent_worker, args=(tid, task, system, model), daemon=True)
    t.start()
    return json.dumps({"task_id": tid, "status": "running", "task": task[:100]})

def tool_subagent_list(params):
    status_filter = params.get("status", "")
    items = list(_subagents.values())
    if status_filter:
        items = [sa for sa in items if sa["status"] == status_filter]
    items.sort(key=lambda sa: sa["created_at"], reverse=True)
    summary = {s: sum(1 for sa in _subagents.values() if sa["status"] == s) for s in ("running", "completed", "failed", "killed")}
    return json.dumps({"total": len(_subagents), "summary": summary, "subagents": items}, ensure_ascii=False)

def tool_subagent_result(params):
    tid = params.get("task_id", "")
    if tid not in _subagents:
        return json.dumps({"error": f"sub-agent not found: {tid}"})
    return json.dumps(_subagents[tid], ensure_ascii=False)

def tool_subagent_kill(params):
    tid = params.get("task_id", "")
    if tid not in _subagents:
        return json.dumps({"error": f"sub-agent not found: {tid}"})
    entry = _subagents[tid]
    if entry["status"] != "running":
        return json.dumps({"error": f"sub-agent [{tid}] is not running (status: {entry['status']})"})
    entry["status"] = "killed"
    entry["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry["result"] = "(killed by user)"
    log(f"Sub-agent [{tid}] killed")
    return json.dumps({"task_id": tid, "status": "killed"})


# ── Plan mode ────────────────────────────────────────────

def _plan_format_sections(plan):
    lines = [f"# Plan: {plan['title']}", f"Status: {plan['status']}", f"Created: {plan['created_at']}"]
    if plan['description']:
        lines.append(f"\nDescription: {plan['description']}")
    for sec in plan.get("sections", []):
        lines.append(f"\n## {sec['name'].replace('_', ' ').title()}")
        lines.append(sec["content"])
    if plan["status"] == "approved":
        lines.append(f"\nApproved: {plan['approved_at']}")
    return "\n".join(lines)

def tool_plan_create(params):
    title = params.get("title", "")
    if not title:
        return json.dumps({"error": "title is required"})
    pid = "pl" + str(int(time.time() * 10))[-6:]
    entry = {
        "plan_id": pid, "title": title, "description": params.get("description", ""),
        "sections": [], "status": "draft",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "approved_at": "",
    }
    with _plans_lock:
        _plans[pid] = entry
    return json.dumps({"plan_id": pid, "title": title, "status": "draft", "sections": []})

def tool_plan_section(params):
    pid = params.get("plan_id", "")
    if pid not in _plans:
        return json.dumps({"error": f"plan not found: {pid}"})
    name = params.get("name", "")
    content = params.get("content", "")
    if not name or not content:
        return json.dumps({"error": "name and content are required"})
    with _plans_lock:
        plan = _plans[pid]
        for i, sec in enumerate(plan["sections"]):
            if sec["name"] == name:
                plan["sections"][i]["content"] = content
                return json.dumps({"plan_id": pid, "section": name, "updated": True})
        plan["sections"].append({"name": name, "content": content})
    return json.dumps({"plan_id": pid, "section": name, "added": True})

def tool_plan_present(params):
    pid = params.get("plan_id", "")
    if pid not in _plans:
        return json.dumps({"error": f"plan not found: {pid}"})
    with _plans_lock:
        plan = _plans[pid]
        plan["status"] = "review"
    formatted = _plan_format_sections(plan)
    return json.dumps({"plan_id": pid, "status": "review", "formatted": formatted}, ensure_ascii=False)

def tool_plan_approve(params):
    pid = params.get("plan_id", "")
    if pid not in _plans:
        return json.dumps({"error": f"plan not found: {pid}"})
    with _plans_lock:
        plan = _plans[pid]
        if plan["status"] == "approved":
            return json.dumps({"plan_id": pid, "status": "approved", "message": "already approved"})
        plan["status"] = "approved"
        plan["approved_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log(f"Plan [{pid}] approved: {plan['title']}")
    return json.dumps({"plan_id": pid, "title": plan["title"], "status": "approved"})

def tool_plan_list(params):
    status_filter = params.get("status", "")
    items = list(_plans.values())
    if status_filter:
        items = [p for p in items if p["status"] == status_filter]
    items.sort(key=lambda p: p["created_at"], reverse=True)
    summary = {}
    for p in _plans.values():
        summary[p["status"]] = summary.get(p["status"], 0) + 1
    return json.dumps({"total": len(_plans), "summary": summary, "plans": items}, ensure_ascii=False)

# ── Auto-memory ──────────────────────────────────────────

def _auto_memory_extract(text, session_id):
    """Extract key facts from an assistant response and auto-save to memory.
    Extracts: URLs as reference/<domain>, decisions marked with key phrases."""
    if not _AUTO_MEMORY_ENABLED:
        return 0

    saved = 0
    text_lower = text.lower()

    # Extract URLs → reference/<domain>
    import re as _re
    urls = _re.findall(r'https?://([a-zA-Z0-9.-]+)', text)
    for domain in set(urls):
        domain = domain.removeprefix("www.")
        if not domain:
            continue
        key = f"reference/{domain}"
        if key not in _memory:
            _memory[key] = {"url": domain, "source": "auto", "session": session_id}
            saved += 1

    # Extract decisions marked with → or "using"/"decided to"/"lets use"
    decision_patterns = _re.findall(
        r'(?:using|decided to|lets use|going with|opted for|chose)\s+([A-Za-z0-9_-]+)',
        text_lower,
    )
    for item in set(decision_patterns):
        if len(item) < 2:
            continue
        key = f"decision/{item}"
        if key not in _memory:
            _memory[key] = {"value": item, "source": "auto", "session": session_id}
            saved += 1

    if saved:
        _memory_save()
        log(f"Auto-memory: saved {saved} fact(s) from session [{session_id}]")
    return saved


def _build_auto_prompt():
    """Build system prompt section with auto-memory instructions and current memory context."""
    lines = [
        "You have a persistent memory store callable via memory_set / memory_get / memory_search / memory_delete.",
        "When you learn:",
        "- Personal information about the user (name, role, preferences, location, timezone)",
        "- Project decisions, architecture choices, important URLs or references",
        "- User feedback or corrections",
        "- New facts relevant to the current task",
        "",
        "...automatically call memory_set with key in 'user/', 'project/', 'decision/', 'reference/', or 'feedback/' format.",
        "Do NOT over-save — only facts that would be useful in a future session.",
        "",
    ]

    # Add current memory context (last 20 entries)
    if _memory:
        lines.append("Current memory context (use memory_get for full values):")
        mem_keys = sorted(_memory.keys())
        for k in mem_keys[-20:]:
            v = _memory[k]
            if isinstance(v, dict):
                preview = json.dumps(v, ensure_ascii=False)[:80]
            else:
                preview = str(v)[:80]
            lines.append(f"  {k}: {preview}")
        lines.append("")

    return "\n".join(lines)


# ── Monitor ─────────────────────────────────────────────

def _monitor_worker(monitor_id, command, timeout):
    """Run a shell command in a thread, capture output."""
    import subprocess as _sp
    try:
        proc = _sp.Popen(
            command,
            shell=True,
            stdout=_sp.PIPE,
            stderr=_sp.PIPE,
            text=True,
            preexec_fn=os.setsid if hasattr(os, "setsid") else None,
        )
        with _monitors_lock:
            _monitors[monitor_id]["pid"] = proc.pid

        stdout_lines = []
        stderr_lines = []
        max_output = 5000  # max lines to capture

        # Read output line by line with timeout check
        import select as _sel
        while True:
            # Check stop flag
            with _monitors_lock:
                if _monitors.get(monitor_id, {}).get("status") == "stopping":
                    proc.kill()
                    with _monitors_lock:
                        _monitors[monitor_id]["status"] = "stopped"
                        _monitors[monitor_id]["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                        _monitors[monitor_id]["stdout"] = "\n".join(stdout_lines[-200:])
                        _monitors[monitor_id]["stderr"] = "\n".join(stderr_lines[-200:])
                    log(f"Monitor [{monitor_id}] stopped by user")
                    return

            try:
                outs, errs = proc.communicate(timeout=1)
                if outs:
                    stdout_lines.extend(outs.split("\n"))
                if errs:
                    stderr_lines.extend(errs.split("\n"))
                break
            except _sp.TimeoutExpired:
                continue

        # Process completed
        exit_code = proc.returncode
        with _monitors_lock:
            entry = _monitors.get(monitor_id)
            if entry and entry["status"] not in ("stopping", "stopped"):
                entry["status"] = "completed" if exit_code == 0 else "failed"
                entry["exit_code"] = exit_code
                entry["stdout"] = "\n".join(stdout_lines[-200:])
                entry["stderr"] = "\n".join(stderr_lines[-200:])
                entry["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        log(f"Monitor [{monitor_id}] {_monitors.get(monitor_id,{}).get('status')} (exit={exit_code})")

    except Exception as e:
        with _monitors_lock:
            entry = _monitors.get(monitor_id)
            if entry:
                entry["status"] = "failed"
                entry["exit_code"] = -1
                entry["stderr"] = str(e)
                entry["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        log(f"Monitor [{monitor_id}] FAILED: {e}")


def tool_monitor_start(params):
    command = params.get("command", "")
    if not command:
        return json.dumps({"error": "command is required"})
    timeout = params.get("timeout", 0)
    mid = "mo" + str(int(time.time() * 10))[-6:]
    entry = {
        "monitor_id": mid, "command": command[:200], "timeout": timeout,
        "status": "running", "exit_code": None,
        "pid": None, "stdout": "", "stderr": "",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "finished_at": "",
    }
    with _monitors_lock:
        _monitors[mid] = entry
    t = threading.Thread(target=_monitor_worker, args=(mid, command, timeout), daemon=True)
    t.start()
    return json.dumps({"monitor_id": mid, "status": "running", "command": command[:100]})


def tool_monitor_result(params):
    mid = params.get("monitor_id", "")
    if mid not in _monitors:
        return json.dumps({"error": f"monitor not found: {mid}"})
    entry = dict(_monitors[mid])
    # Truncate output in response
    if len(entry.get("stdout", "")) > 2000:
        entry["stdout"] = entry["stdout"][:2000] + "\n... [truncated]"
    if len(entry.get("stderr", "")) > 2000:
        entry["stderr"] = entry["stderr"][:2000] + "\n... [truncated]"
    return json.dumps(entry, ensure_ascii=False)


def tool_monitor_stop(params):
    mid = params.get("monitor_id", "")
    if mid not in _monitors:
        return json.dumps({"error": f"monitor not found: {mid}"})
    with _monitors_lock:
        entry = _monitors[mid]
        if entry["status"] == "running":
            entry["status"] = "stopping"
            entry["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            return json.dumps({"monitor_id": mid, "status": "stopping", "message": "Stop signal sent"})
        return json.dumps({"monitor_id": mid, "status": entry["status"], "message": f"Monitor is {entry['status']}"})


def tool_monitor_list(params):
    items = list(_monitors.values())
    items.sort(key=lambda m: m["created_at"], reverse=True)
    summary = {}
    for m in _monitors.values():
        summary[m["status"]] = summary.get(m["status"], 0) + 1
    # Compact listing
    compact = []
    for m in items:
        compact.append({
            "monitor_id": m["monitor_id"],
            "command": m["command"][:60],
            "status": m["status"],
            "exit_code": m["exit_code"],
            "created_at": m["created_at"],
        })
    return json.dumps({"total": len(_monitors), "summary": summary, "monitors": compact}, ensure_ascii=False)


# ── Cron ─────────────────────────────────────────────────

def tool_cron_create(params):
    expression = params.get("expression", "")
    action = params.get("action", "")
    if not expression or not action:
        return json.dumps({"error": "expression and action are required"})
    description = params.get("description", "")
    tid, err = create_task(expression, action, description=description)
    if err:
        return json.dumps({"error": err})
    return json.dumps({"task_id": tid, "expression": expression, "action": action[:100], "description": description, "status": "created"})

def tool_cron_list(params):
    tasks = list_tasks()
    return json.dumps({"total": len(tasks), "tasks": tasks}, ensure_ascii=False)

def tool_cron_delete(params):
    tid = params.get("task_id", "")
    if not tid:
        return json.dumps({"error": "task_id is required"})
    ok = delete_task(tid)
    if not ok:
        return json.dumps({"error": f"task not found: {tid}"})
    return json.dumps({"task_id": tid, "status": "deleted"})


def tool_web_search(params):
    query = params.get("query", "")
    max_results = min(params.get("max_results", 5), 10)
    allowed = params.get("allowed_domains", [])
    blocked = params.get("blocked_domains", [])

    if not query:
        return json.dumps({"error": "query required"})

    blkd, reason = check_web_rate_limit()
    if blkd:
        return json.dumps({"error": reason})

    # Check cache
    cache_key = query.lower().strip()
    now = time.time()
    cached = _web_cache.get(cache_key)
    if cached and (now - cached["ts"]) < _web_cache_ttl:
        results = cached["results"]
        results = _filter_domains(results, allowed, blocked)
        results = results[:max_results]
        return json.dumps({"cached": True, "total": len(results), "results": results}, ensure_ascii=False)

    try:
        from bs4 import BeautifulSoup
        resp = requests.get(
            "https://lite.duckduckgo.com/lite/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (compatible; DeepSeekAgent/1.0)"},
            timeout=15,
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        tables = soup.find_all("table")
        if len(tables) < 3:
            return json.dumps({"cached": False, "total": 0, "results": []})

        rows = tables[2].find_all("tr")
        raw_results = []
        i = 0
        while i < len(rows) and len(raw_results) < max_results:
            tds = rows[i].find_all("td")
            if len(tds) >= 2:
                link = tds[1].find("a")
                if link:
                    title = link.get_text(strip=True)
                    href = link.get("href", "")
                    if href.startswith("//"):
                        parsed_url = urlparse("https:" + href)
                        qs = parse_qs(parsed_url.query)
                        real_url = qs.get("uddg", [href])[0]
                    else:
                        real_url = href

                    snippet = ""
                    if i + 1 < len(rows):
                        snip_tds = rows[i + 1].find_all("td")
                        if len(snip_tds) >= 2:
                            snippet = snip_tds[1].get_text(strip=True)

                    raw_results.append({"title": title, "snippet": snippet, "url": real_url})
            i += 4

        # Cache raw results
        _web_cache[cache_key] = {"ts": now, "results": raw_results}
        # Prune old cache entries
        stale_keys = [k for k, v in _web_cache.items() if (now - v["ts"]) > _web_cache_ttl]
        for k in stale_keys:
            _web_cache.pop(k, None)

        # Apply domain filters
        results = _filter_domains(raw_results, allowed, blocked)
        results = results[:max_results]

        return json.dumps({"cached": False, "total": len(results), "results": results}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"cached": False, "error": "search failed: " + str(e), "results": []})


def _filter_domains(results, allowed, blocked):
    """Filter results by allowed/blocked domains."""
    from urllib.parse import urlparse as _up
    filtered = results
    if allowed:
        filtered = [r for r in filtered if any(d in _up(r["url"]).netloc for d in allowed)]
    if blocked:
        filtered = [r for r in filtered if not any(d in _up(r["url"]).netloc for d in blocked)]
    return filtered



# ── Background task tools ───────────────────────────────

def tool_bg_task_start(params):
    """Start a background chat task. Returns immediately with task_id."""
    message = params.get("message", "")
    session_id = params.get("session_id", "bg")
    if not message:
        return json.dumps({"error": "message is required"})
    chat_func = lambda session_id, message: handle_chat({
        "message": message, "session_id": session_id,
    })
    tid = _bg_tasks.start(session_id, message, chat_func)
    return json.dumps({"task_id": tid, "status": "pending"})

def tool_bg_task_status(params):
    """Get status and result of a background task."""
    tid = params.get("task_id", "")
    if not tid:
        return json.dumps({"error": "task_id is required"})
    entry = _bg_tasks.get(tid)
    if not entry:
        return json.dumps({"error": f"task not found: {tid}"})
    return json.dumps(entry, ensure_ascii=False)

def tool_bg_task_list(params):
    """List background tasks, optionally filtered by status."""
    status = params.get("status", "")
    limit = int(params.get("limit", 20))
    items = _bg_tasks.list(status=status, limit=limit)
    all_items = _bg_tasks.list()
    summary = {}
    for t in all_items:
        summary[t["status"]] = summary.get(t["status"], 0) + 1
    return json.dumps({"total": len(all_items), "summary": summary, "tasks": items}, ensure_ascii=False)




# ── Auth management tools (Tier 51) ──
def _create_api_key(body):
    """Create a new API key. Requires existing admin key."""
    name = body.get("name", "unnamed")
    keys = _load_api_keys()
    new_key = _generate_api_key()
    now = str(datetime.now(timezone.utc))
    keys[new_key] = {
        "name": name,
        "created_at": now,
        "last_used_at": now,
        "role": "user",
    }
    _save_api_keys(keys)
    return {"key": new_key, "name": name, "created_at": now}

def _revoke_api_key(body):
    """Revoke an API key by its value."""
    key = body.get("key", "")
    keys = _load_api_keys()
    if key in keys:
        info = keys.pop(key)
        _save_api_keys(keys)
        return {"revoked": key, "name": info.get("name", "")}
    return {"error": "key not found"}

def _list_api_keys(body):
    """List all API keys (without the secret values)."""
    keys = _load_api_keys()
    result = []
    for k, v in keys.items():
        result.append({
            "prefix": k[:12] + "...",
            "name": v.get("name", ""),
            "created_at": v.get("created_at", ""),
            "last_used_at": v.get("last_used_at", ""),
            "role": v.get("role", ""),
        })
    return result

TOOL_DISPATCH = {
    "create-api-key": _create_api_key,
    "revoke-api-key": _revoke_api_key,
    "list-api-keys": _list_api_keys,
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "edit_file": tool_edit_file,
    "ls_dir": tool_ls_dir,
    "grep_files": tool_grep_files,
    "glob_files": tool_glob_files,
    "bash": tool_bash,
    "git_status": tool_git_status,
    "git_diff": tool_git_diff,
    "git_log": tool_git_log,
    "git_commit": tool_git_commit,
    "git_push": tool_git_push,
    "web_fetch": tool_web_fetch,
    "web_search": tool_web_search,
    "task_create": tool_task_create,
    "task_update": tool_task_update,
    "task_list": tool_task_list,
    "task_delete": tool_task_delete,
    "memory_set": tool_memory_set,
    "memory_get": tool_memory_get,
    "memory_search": tool_memory_search,
    "memory_delete": tool_memory_delete,
    "notify": tool_notify,
    "subagent_spawn": tool_subagent_spawn,
    "subagent_list": tool_subagent_list,
    "subagent_result": tool_subagent_result,
    "subagent_kill": tool_subagent_kill,
    "plan_create": tool_plan_create,
    "plan_section": tool_plan_section,
    "plan_present": tool_plan_present,
    "plan_approve": tool_plan_approve,
    "plan_list": tool_plan_list,
    "monitor_start": tool_monitor_start,
    "monitor_result": tool_monitor_result,
    "monitor_stop": tool_monitor_stop,
    "monitor_list": tool_monitor_list,
    "cron_create": tool_cron_create,
    "cron_list": tool_cron_list,
    "cron_delete": tool_cron_delete,
    "bg_task_start": tool_bg_task_start,
    "bg_task_status": tool_bg_task_status,
    "bg_task_list": tool_bg_task_list,
}

MCP_TOOL_NAMES = set()  # populated at init: mcp__<server>__<tool>

HOOK_HANDLERS = {}



def _filter_tools(tools, allowed=None, blocked=None):
    """Filter tool definitions by allow/block lists. Both are lists of names.
    Returns filtered list. Default (None/empty) = no filtering."""
    if not allowed and not blocked:
        return tools
    result = []
    for t in tools:
        name = t.get("function", {}).get("name", "")
        if allowed and name not in allowed:
            continue
        if blocked and name in blocked:
            continue
        result.append(t)
    return result


def _track_budget(session_id, model, input_tokens, output_tokens):

    session = sessions.get(session_id)
    if session:
        session.log_usage(input_tokens, output_tokens)
    """Track API spend per session. Prices in USD per 1M tokens."""
    # DeepSeek pricing (approximate): flash=$0.30/$1.20, pro=$4/$12 per 1M I/O
    price_map = {
        "deepseek-v4-flash": (0.30, 1.20),
        "deepseek-v4-pro": (4.0, 12.0),
        "deepseek-chat": (0.30, 1.20),
    }
    inp_price, out_price = price_map.get(model, (0.30, 1.20))
    cost = (input_tokens / 1_000_000 * inp_price) + (output_tokens / 1_000_000 * out_price)
    with _session_budget_lock:
        entry = _session_budget.setdefault(session_id, {"total_cost": 0.0, "api_calls": 0})
        entry["total_cost"] += cost
        entry["api_calls"] += 1
    return cost


def _check_budget(session_id, max_usd):
    """Return None if within budget, or error dict if exceeded."""
    if not max_usd:
        return None
    with _session_budget_lock:
        entry = _session_budget.get(session_id)
        if entry and entry["total_cost"] >= max_usd:
            return {"error": f"Budget exceeded: ${entry['total_cost']:.4f} >= ${max_usd:.4f} max"}
    return None


def _safe_run_hooks(event, **data):
    try:
        return run_hooks(event, **data)
    except Exception as e:
        log(f"Hook error [{event}]: {e}")
        return None


def tool_mcp(params):
    """Dispatch to MCP server. Handles both prefixed (mcp__<server>__<tool>)
    and unprefixed names (iterates all clients)."""
    full_name = params.get("name", "")
    arguments = params.get("arguments", {})
    if full_name.startswith("mcp__"):
        parts = full_name.split("__", 2)
        if len(parts) != 3:
            return json.dumps({"error": f"invalid mcp tool format: {full_name}"})
        _, server_name, tool_name = parts
        for name, client in MCP_CLIENTS:
            if name == server_name:
                try:
                    result = client.call_tool(tool_name, arguments)
                    if result.get("isError"):
                        return json.dumps({"error": result.get("result", "MCP error")})
                    return result.get("result", "(empty)")
                except Exception as e:
                    return json.dumps({"error": f"MCP {server_name}.{tool_name}: {e}"})
        return json.dumps({"error": f"MCP server not found: {server_name}"})
    # Unprefixed name: search all clients
    for name, client in MCP_CLIENTS:
        if client._tools_cache:
            for t in client._tools_cache:
                if t.get("name") == full_name:
                    try:
                        result = client.call_tool(full_name, arguments)
                        if result.get("isError"):
                            return json.dumps({"error": result.get("result", "MCP error")})
                        return result.get("result", "(empty)")
                    except Exception as e:
                        return json.dumps({"error": f"MCP {name}.{full_name}: {e}"})
    return json.dumps({"error": f"MCP tool not found: {full_name}"})


# URL path → dispatch name (for direct HTTP endpoints)
TOOL_URL_MAP = {
    "read": "read_file",
    "write": "write_file",
    "edit": "edit_file",
    "ls": "ls_dir",
    "grep": "grep_files",
    "glob": "glob_files",
    "web-fetch": "web_fetch",
    "web-search": "web_search",
    "bash": "bash",
    "git-status": "git_status",
    "git-diff": "git_diff",
    "git-commit": "git_commit",
    "git-push": "git_push",
    "git-log": "git_log",
    "task-create": "task_create",
    "task-update": "task_update",
    "task-list": "task_list",
    "task-delete": "task_delete",
    "memory-set": "memory_set",
    "memory-get": "memory_get",
    "memory-search": "memory_search",
    "memory-delete": "memory_delete",
    "notify": "notify",
    "subagent-spawn": "subagent_spawn",
    "subagent-list": "subagent_list",
    "subagent-result": "subagent_result",
    "subagent-kill": "subagent_kill",
    "plan-create": "plan_create",
    "plan-section": "plan_section",
    "plan-present": "plan_present",
    "plan-approve": "plan_approve",
    "plan-list": "plan_list",
    "monitor-start": "monitor_start",
    "monitor-result": "monitor_result",
    "monitor-stop": "monitor_stop",
    "monitor-list": "monitor_list",
    "cron-create": "cron_create",
    "cron-list": "cron_list",
    "cron-delete": "cron_delete",
    "bg-task-start": "bg_task_start",
    "bg-task-status": "bg_task_status",
    "bg-task-list": "bg_task_list",
}


def _api_call_with_tools(messages, tools=None, temperature=0.7, max_tokens=8192, model=None, response_format=None):
    """Call DeepSeek API with tool calling support. Returns full message object."""
    from deepseek_api import _api_key, DEFAULT_MODEL, FAST_MODEL, BASE_URL, route_model

    # Route if no explicit model
    if model is None:
        _prompt = ""
        _system = ""
        for m in messages:
            if m.get("role") == "system" and m.get("content"):
                _system = m["content"]
            elif m.get("role") == "user" and m.get("content"):
                _prompt = m["content"]
        model = route_model(prompt=_prompt, system=_system)
        import sys
        print(f"[Router] Tools stream routed to {model}", file=sys.stderr, flush=True)

    actual_model = model or DEFAULT_MODEL
    models_tried = []
    models_to_try = [actual_model]
    if actual_model == DEFAULT_MODEL:
        models_to_try.append(FAST_MODEL)

    last_error = None
    for attempt_model in models_to_try:
        for attempt in range(3):
            try:
                body = {
                    "model": attempt_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if response_format:
                    body["response_format"] = response_format
                if tools:
                    body["tools"] = tools
                models_tried.append(attempt_model)

                req_body = json.dumps(body).encode("utf-8")
                req = urllib.request.Request(
                    f"{BASE_URL}/chat/completions",
                    data=req_body,
                    headers={
                        "Authorization": f"Bearer {_api_key()}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )

                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read())
                    choice = data["choices"][0]
                    msg = choice["message"]
                    return {
                        "role": msg.get("role", "assistant"),
                        "content": msg.get("content") or "",
                        "tool_calls": msg.get("tool_calls"),
                        "reasoning_content": msg.get("reasoning_content"),
                        "finish_reason": choice.get("finish_reason"),
                        "usage": data.get("usage", {}),
                        "model": attempt_model,
                    }
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")[:500]
                last_error = f"HTTP {e.code}: {err_body}"
                log(f"DeepSeek API error: model={attempt_model} {last_error}")
                if e.code not in (429, 500, 502, 503, 504):
                    break  # non-retryable
                if attempt < 2:
                    import time
                    time.sleep((2 ** attempt) * 1.0)
                    continue
                # Max retries for this model — try next
            except (urllib.error.URLError, OSError) as e:
                last_error = str(e)
                log(f"DeepSeek API error: model={attempt_model} {last_error}")
                if attempt < 2:
                    import time
                    time.sleep((2 ** attempt) * 0.5)
                    continue
                break  # max retries for this model

        if attempt_model == models_to_try[-1]:
            break
        # Fallback to next model
        log(f"[Router] Fallback: {attempt_model} -> {models_to_try[-1] if len(models_to_try) > 1 else 'none'}")
        if len(models_to_try) > 1:
            log(f"[Router] Fallback from {attempt_model} to {models_to_try[models_to_try.index(attempt_model)+1] if models_to_try.index(attempt_model)+1 < len(models_to_try) else 'none'}")

    log(f"[Router] All models failed: {models_tried} last={last_error}")
    raise RuntimeError(f"DeepSeek API failed after {len(models_tried)} attempt(s): {last_error}")




# ── /chat handler ─────────────────────────────────────────────────

THINKER_PROMPT = """You are a senior technical analyst. Your job is to deeply analyze a request before the coding agent implements it.

Follow this analysis structure:
1. REQUIREMENTS — What exactly is being asked? List all explicit and implicit requirements.
2. ARCHITECTURE — What components, files, or systems are involved?
3. FILES/IMPACT — Which files would need to change, and what is the blast radius?
4. PLAN — Step-by-step implementation plan. Be specific.
5. RISKS — What could go wrong? Edge cases? Breaking changes?

Output ONLY the analysis. No greetings, no summaries. Be thorough but concise."""

def handle_chat(body):
    """Multi-turn chat with tool calling loop."""
    _chat_start = time.time()
    session_id = body.get("session_id", "")
    # ── Opt-in gap features (zero-risk: all default to current behavior) ──
    allowed_tools = body.get("allowed_tools")  # None or list of tool names
    blocked_tools = body.get("blocked_tools")  # None or list of tool names
    effort = body.get("effort", "")  # "low", "medium", "high", or ""
    skip_compact = body.get("skip_compact", False)
    response_format = body.get("response_format")  # {"type": "json_object"} etc
    max_budget = body.get("max_budget_usd", 0.0)  # 0 = unlimited
    max_ctx_tok = body.get("max_context_tokens", 0)  # 0 = use default
    # Effort → iterations
    local_max_iter = EFFORT_MAP.get(effort, TOOL_CALL_MAX_ITER) if effort else TOOL_CALL_MAX_ITER
    # Select tool definitions
    local_tools = _filter_tools(TOOL_DEFS, allowed=allowed_tools, blocked=blocked_tools)

    message = body.get("message", "")
    if not message:
        return {"error": "message required"}

    session = sessions.get(session_id)
    if not session:
        session_id = sessions.create(sid=session_id)
        session = sessions.get(session_id)
        active_sessions.set(len(sessions.list()))
        # Inject auto-memory system prompt + memory context
        session.system = _build_auto_prompt()

    # ── Auto-routing: check if task should be delegated to sub-agent ──
    auto_route_result = None
    if body.get("auto_route", True):  # opt-out with auto_route=false
        routed, route_data = _auto_route(message, session_id)
        if routed:
            auto_route_result = route_data
            log(f"Auto-routed: {route_data['category']} — injecting result into context")
            message = message + "\n\n[Auto-routing: delegated to " + route_data["category"] + " agent]\nResult:\n" + route_data["result"]

    # Extended thinking pass (two-pass for complex tasks)
    thinking = body.get("thinking", effort == "high")
    thinking_analysis = ""
    if thinking and not auto_route_result:
        thinker_msg = message
        ctx_parts = []
        if session and session.messages:
            recent = session.messages[-6:]
            for m in recent:
                role = m.get("role", "")
                content = (m.get("content") or "")[:200]
                if content:
                    ctx_parts.append(f"{role}: {content}")
                elif m.get("tool_calls"):
                    names = ", ".join(tc["function"]["name"] for tc in m["tool_calls"])
                    ctx_parts.append(f"{role}: [tools: {names}]")
        if ctx_parts:
            thinker_msg = ("Context of current conversation:\n"
                + "\n".join(ctx_parts)
                + "\n\n---\n\n" + message)
        try:
            thinking_result = chat(
                system=THINKER_PROMPT,
                prompt=thinker_msg,
                model=FAST_MODEL,
                temperature=0.3)
            thinking_analysis = thinking_result.strip()
            sessions.save(SESSION_FILE)
            message = (message
                + "\n\n<thinking-analysis>\n"
                + thinking_analysis
                + "\n</thinking-analysis>")
        except Exception as e:
            log(f"[Thinking] FAILED: {e}")

    session.add("user", message)
    sessions.save(SESSION_FILE)
    global _msg_save_counter
    _msg_save_counter = (_msg_save_counter + 1) % 5

    # Context compaction (Tier 21)
    if not skip_compact:
        session.compact(lambda p: chat(
            system="You are a summarizer. Output ONLY the summary, no greetings.",
            prompt=p,
            model=FAST_MODEL,
            temperature=0.3,
        ))

    # Tool calling loop
    for iteration in range(local_max_iter):
        # Budget check before each iteration
        budget_check = _check_budget(session_id, max_budget)
        if budget_check:
            session.add("assistant", json.dumps(budget_check))
            sessions.save(SESSION_FILE)
            return {"session_id": session_id, "response": budget_check["error"], "error": True}
        try:
            api_tools = local_tools
            api_kw = {}
            if response_format:
                api_kw["response_format"] = response_format
            result = _api_call_with_tools(
                session.api_msgs(),
                tools=api_tools,
                temperature=body.get("temperature", 0.3),
            )
        except Exception as e:
            session.add("assistant", f"API error: {e}")
            observe_request("chat", "", time.time() - _chat_start, error=e)
            return {"session_id": session_id, "response": str(e), "error": True}

        # Track API spend
        usage = result.get("usage", {})
        if usage:
            _track_budget(session_id, result.get("model", "deepseek-v4-flash"),
                          usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0),
                          usage.get("completion_tokens", 0) or usage.get("output_tokens", 0))
        content = result.get("content", "")
        tool_calls = result.get("tool_calls")

        if tool_calls:
            # Add assistant message with tool calls + reasoning
            session.add("assistant", content, tool_calls=tool_calls, reasoning_content=result.get("reasoning_content"))
            sessions.save(SESSION_FILE)

            for tc in tool_calls:
                fn = tc["function"]
                name = fn["name"]
                try:
                    args = json.loads(fn.get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {}

                tool_calls_total.labels(tool=name).inc()

                handler = TOOL_DISPATCH.get(name)

                # Set current session for permission gates
                global _CURRENT_SESSION_ID
                _CURRENT_SESSION_ID = session_id

                # Pre-tool hook
                hook_block = _safe_run_hooks("PreToolUse", name=name, args=args, session_id=session_id, iteration=iteration)
                if hook_block and "error" in hook_block:
                    tool_result = json.dumps({"error": hook_block["error"]})
                elif handler:
                    _start_tool = time.time()
                    if name in MCP_TOOL_NAMES:
                        tool_result = handler({"name": name, "arguments": args})
                    else:
                        tool_result = handler(args)
                    _duration = int((time.time() - _start_tool) * 1000)
                    _safe_run_hooks("PostToolUse", name=name, args=args, result=tool_result, session_id=session_id, iteration=iteration, duration_ms=_duration)
                else:
                    tool_result = json.dumps({"error": f"unknown tool: {name}"})

                # Truncate very long tool results
                if isinstance(tool_result, str) and len(tool_result) > 10000:
                    tool_result = tool_result[:5000] + "\n... [truncated]"

                session.add("tool", str(tool_result), tool_call_id=tc.get("id", ""))

            # Continue the loop — DeepSeek will see tool results
            continue

        # No tool calls — final response
        if content:
            session.add("assistant", content)
            sessions.save(SESSION_FILE)
            _auto_memory_extract(content, session_id)
        _safe_run_hooks("PostTask", result=content, tool_calls_count=iteration+1, session_id=session_id)
        duration = time.time() - _chat_start
        observe_request("chat", result.get("model"), duration)
        track_tokens(result.get("model"),
                (result.get("usage") or {}).get("prompt_tokens", 0) or (result.get("usage") or {}).get("input_tokens", 0),
                (result.get("usage") or {}).get("completion_tokens", 0) or (result.get("usage") or {}).get("output_tokens", 0))
        return {"session_id": session_id, "response": content or "(empty response)"}

    # Hit iteration limit
    _safe_run_hooks("PostTask", result="Tool call limit reached", tool_calls_count=TOOL_CALL_MAX_ITER, session_id=session_id)
    observe_request("chat", "", time.time() - _chat_start)
    return {
        "session_id": session_id,
        "response": "Tool call limit reached. Please simplify your request.",
        "error": True,
    }




# ── Streaming /chat handler ──────────────────────────────────────

def handle_chat_stream(session_id, message, sse_callback, temperature=0.3, **kwargs):
    """Streaming chat with SSE events."""
    # ── Opt-in gap features (zero-risk) ──
    allowed_tools = kwargs.get("allowed_tools")
    blocked_tools = kwargs.get("blocked_tools")
    effort = kwargs.get("effort", "")
    skip_compact = kwargs.get("skip_compact", False)
    response_format = kwargs.get("response_format")
    max_budget = kwargs.get("max_budget_usd", 0.0)
    max_ctx_tok = kwargs.get("max_context_tokens", 0)
    local_max_iter = EFFORT_MAP.get(effort, TOOL_CALL_MAX_ITER) if effort else TOOL_CALL_MAX_ITER
    local_tools = _filter_tools(TOOL_DEFS, allowed=allowed_tools, blocked=blocked_tools)

    session = sessions.get(session_id)
    if not session:
        session_id = sessions.create(sid=session_id)
        session = sessions.get(session_id)
        # Inject auto-memory system prompt + memory context
        session.system = _build_auto_prompt()

    # ── Auto-routing: check if task should be delegated to sub-agent ──
    auto_route_result = None
    if body.get("auto_route", True):  # opt-out with auto_route=false
        routed, route_data = _auto_route(message, session_id)
        if routed:
            auto_route_result = route_data
            log(f"Auto-routed: {route_data['category']} — injecting result into context")
            message = message + "\n\n[Auto-routing: delegated to " + route_data["category"] + " agent]\nResult:\n" + route_data["result"]

    session.add("user", message)
    sessions.save(SESSION_FILE)
    global _msg_save_counter
    _msg_save_counter = (_msg_save_counter + 1) % 5

    if not skip_compact:
        session.compact(lambda p: chat(
            system="You are a summarizer. Output ONLY the summary, no greetings.",
            prompt=p,
            model=FAST_MODEL,
            temperature=0.3,
        ))

    sse_callback("session", {"session_id": session_id})

    for iteration in range(local_max_iter):
        budget_check = _check_budget(session_id, max_budget)
        if budget_check:
            sse_callback("error", {"error": budget_check["error"]})
            return
        try:
            api_tools = local_tools
            gen = _api_call_with_tools_stream(
                session.api_msgs(),
                tools=api_tools,
                temperature=temperature,
            )
        except Exception as e:
            sse_callback("error", {"error": str(e), "iteration": iteration})
            return

        content_parts = []
        tool_calls = None
        reasoning = None
        final_content = None
        finish = None

        for token, tc, rc, fc, fr in gen:
            if token:
                content_parts.append(token)
                sse_callback("token", {"token": token})
            if rc:
                reasoning = rc
            if tc:
                tool_calls = tc
                final_content = fc
                finish = fr
            if fc is not None and not tc:
                final_content = fc
                finish = fr

        if tool_calls:
            full_text = "".join(content_parts)
            session.add("assistant", full_text, tool_calls=tool_calls, reasoning_content=reasoning)
            sessions.save(SESSION_FILE)
            sse_callback("tool_calls", {"tool_calls": tool_calls})

            for tc in tool_calls:
                fn = tc["function"]
                name = fn["name"]
                try:
                    args = json.loads(fn.get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {}

                handler = TOOL_DISPATCH.get(name)

                # Set current session for permission gates
                global _CURRENT_SESSION_ID
                _CURRENT_SESSION_ID = session_id

                # Pre-tool hook
                hook_block = _safe_run_hooks("PreToolUse", name=name, args=args, session_id=session_id, iteration=iteration)
                if hook_block and "error" in hook_block:
                    tool_result = json.dumps({"error": hook_block["error"]})
                elif handler:
                    _start_tool = time.time()
                    if name in MCP_TOOL_NAMES:
                        tool_result = handler({"name": name, "arguments": args})
                    else:
                        tool_result = handler(args)
                    _duration = int((time.time() - _start_tool) * 1000)
                    _safe_run_hooks("PostToolUse", name=name, args=args, result=tool_result, session_id=session_id, iteration=iteration, duration_ms=_duration)
                else:
                    tool_result = json.dumps({"error": f"unknown tool: {name}"})

                if isinstance(tool_result, str) and len(tool_result) > 10000:
                    tool_result = tool_result[:5000] + "\n... [truncated]"

                session.add("tool", str(tool_result), tool_call_id=tc.get("id", ""))
                sse_callback("tool_result", {"name": name, "preview": str(tool_result)[:200]})

            continue

        final_text = final_content or "".join(content_parts) or "(empty response)"
        if final_text:
            session.add("assistant", final_text)
            sessions.save(SESSION_FILE)
        sse_callback("done", {"response": final_text, "session_id": session_id})
        return

    sse_callback("error", {"error": "tool_call_limit", "session_id": session_id})
# ── Docker API ────────────────────────────────────────────────────

def _docker_api(path):
    import socket as sock_module
    s = sock_module.socket(sock_module.AF_UNIX, sock_module.SOCK_STREAM)
    s.settimeout(5)
    try:
        s.connect("/var/run/docker.sock")
        req = "GET {} HTTP/1.0\r\nHost: localhost\r\n\r\n".format(path)
        s.sendall(req.encode())
        resp = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            resp += chunk
    finally:
        s.close()
    body = resp.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in resp else b"[]"
    return json.loads(body)


def check_services():
    try:
        containers = _docker_api("/containers/json?all=true")
        container_status = {}
        for c in containers:
            names = c.get("Names", [])
            name = names[0].lstrip("/") if names else c.get("Id", "?")
            st = c.get("State", "?")
            container_status[name] = "up" if st == "running" else st
    except Exception as e:
        log("docker socket error: {}".format(e))
        container_status = {}

    results = {}
    for name, cfg in SERVICES.items():
        tcp_ok = None
        if cfg["port"]:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3)
                tcp_ok = s.connect_ex(("127.0.0.1", cfg["port"])) == 0
                s.close()
            except Exception:
                tcp_ok = False
        cnt = container_status.get(name, "missing")
        if cnt == "up" and (tcp_ok is None or tcp_ok):
            status = "ok"
        elif cnt == "up" and tcp_ok is False:
            status = "degraded"
        else:
            status = "down"
        results[name] = {"status": status, "container": cnt, "port": cfg["port"], "tcp": tcp_ok, "group": cfg["group"]}
    return results


# ── Scheduled tasks ───────────────────────────────────────────────

def nightly_cleanup():
    log("nightly-cleanup: starting")
    try:
        prune_resp = _docker_api("/build/prune?filters={}".format(
            json.dumps({"until": ["48h"]}).replace(" ", "")
        ))
        reclaimed = prune_resp.get("SpaceReclaimed", 0)
        log("  docker prune: reclaimed {} bytes".format(reclaimed))
    except Exception as e:
        log("  docker prune failed: {}".format(e))
    disk = shutil.disk_usage("/")
    pct = disk.used / disk.total * 100
    log("  disk: {:.1f}% ({}G free)".format(pct, disk.free // 1024**3))
    svc = check_services()
    down_svcs = [n for n, s in svc.items() if s["status"] != "ok"]
    ok_count = len([s for s in svc.values() if s["status"] == "ok"])
    log("  health: {}/{} ok".format(ok_count, len(svc)))
    if down_svcs:
        for name in down_svcs:
            log("    {}: {}".format(name, svc[name]["status"]))
    health_line = ""
    if down_svcs:
        health_line = " ПРОБЛЕМЫ: " + ", ".join("{} {}".format(n, svc[n]["status"]) for n in down_svcs)
    try:
        summary = chat(
            "Кратко (1-2 предложения): сегодняшняя дата — "
            + datetime.now(timezone.utc).strftime("%Y-%m-%d")
            + ". Сервер n: диск {:.1f}%, ".format(pct)
            + "сервисов {}/{} online.".format(ok_count, len(svc))
            + health_line + " Напомни проверить бэкапы. Ответь на русском.",
            model=FAST_MODEL, temperature=0.3,
        )
        log("  AI summary: {}".format(summary.strip()))
    except Exception as e:
        log("  AI summary failed: {}".format(e))
    if pct > 85:
        _alert("Disk usage {:.1f}% on server n".format(pct))
    if down_svcs:
        _alert("Services down: {}".format(", ".join(down_svcs)))
    log("nightly-cleanup: done")


def weekly_refs_update():
    log("weekly-refs-update: starting")
    refs_dir = os.path.expanduser("~/.claude/refs")
    if os.path.isdir(refs_dir):
        for name in os.listdir(refs_dir):
            path = os.path.join(refs_dir, name)
            if os.path.isdir(os.path.join(path, ".git")):
                r = run(f"cd {shlex.quote(path)} && git fetch --prune --quiet origin 2>&1 && git reset --hard origin/HEAD --quiet 2>&1")
                log(f"  refs/{name}: {r.strip() or 'ok'}")
    try:
        summary = chat(
            "Ты — DevOps-ассистент. Сегодня понедельник, время еженедельного обновления. "
            "Напомни проверить: 1) бэкапы сервера n, 2) обновления пакетов, "
            "3) свободное место на диске. Ответь коротко, на русском.",
            model=FAST_MODEL, temperature=0.3,
        )
        log(f"  AI: {summary.strip()}")
    except Exception as e:
        log(f"  AI failed: {e}")
    log("weekly-refs-update: done")


TASKS = {
    "nightly-cleanup": {
        "func": nightly_cleanup,
        "cron": {"hour": 22, "minute": 27},
        "description": "Daily maintenance + AI summary",
    },
    "weekly-refs-update": {
        "func": weekly_refs_update,
        "cron": {"day_of_week": "mon", "hour": 3, "minute": 30},
        "description": "Weekly refs update",
    },
}


# ── Helpers ───────────────────────────────────────────────────────

def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {msg}", flush=True)


def run(cmd: str) -> str:
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=120).decode()
    except subprocess.CalledProcessError as e:
        return e.output.decode() if e.output else str(e)


def _alert(msg: str):
    log(f"ALERT: {msg}")


# ── MCP Init ────────────────────────────────────────────────────

def init_mcp():
    """Initialize MCP servers and merge their tools."""
    global TOOL_DEFS, TOOL_DISPATCH, MCP_TOOL_NAMES, MCP_CLIENTS
    try:
        config_path = "/root/.claude/mcp.json"
        servers = []
        if os.path.isfile(config_path):
            import json as _json
            with open(config_path) as f:
                cfg = _json.load(f)
            _blocked = {"postgres", "postgres-n8n", "playwright"}

            servers = [{"name": k, "command": v.get("command"), "args": v.get("args", []), "env": v.get("env", {})}
                       for k, v in cfg.get("mcpServers", {}).items() if k not in _blocked]
            # Resolve ${VAR} references in env values from process environment
            for s in servers:
                env = s.get("env", {})
                resolved = {}
                for k, v in env.items():
                    if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                        resolved[k] = os.environ.get(v[2:-1], "")
                    else:
                        resolved[k] = v
                s["env"] = resolved
            log(f"MCP config: {len(servers)} server(s) found")
        else:
            log("MCP config not found at ~/.claude/mcp.json — no MCP servers")
            return

        clients, extra_defs = init_mcp_servers(servers)
        MCP_CLIENTS = clients
        MCP_TOOL_NAMES = set()
        for ed in extra_defs:
            name = ed["function"]["name"]
            MCP_TOOL_NAMES.add(name)
            log(f"  MCP tool: {name}")
        if extra_defs:
            existing_names = {d["function"]["name"] for d in TOOL_DEFS}
            seen_in_extra = set()
            filtered = []
            for ed in extra_defs:
                name = ed["function"]["name"]
                if name not in existing_names and name not in seen_in_extra:
                    seen_in_extra.add(name)
                    filtered.append(ed)
            if filtered:
                TOOL_DEFS = TOOL_DEFS + filtered
                for ed in filtered:
                    name = ed["function"]["name"]
                    TOOL_DISPATCH[name] = tool_mcp
            dupes = len(extra_defs) - len(filtered)
            msg = f"MCP: {len(filtered)} tool(s) from {len(clients)} server(s)"
            if dupes:
                msg += f" ({dupes} duplicates skipped)"
            log(msg)
    except Exception as e:
        log(f"MCP init error: {e}")
        import traceback
        log(traceback.format_exc())


# ── Plugin loading ───────────────────────────────

def init_plugins_all():
    global TOOL_DEFS, TOOL_DISPATCH
    try:
        plugin_defs, plugin_dispatch = init_plugins()
        if plugin_defs:
            existing_names = {d["function"]["name"] for d in TOOL_DEFS}
            filtered = [d for d in plugin_defs if d["function"]["name"] not in existing_names]
            if filtered:
                TOOL_DEFS = TOOL_DEFS + filtered
                for d in filtered:
                    name = d["function"]["name"]
                    TOOL_DISPATCH[name] = plugin_dispatch[name]
                log(f"Plugins: {len(filtered)} tool(s) loaded")
            dupes = len(plugin_defs) - len(filtered)
            if dupes:
                log(f"Plugins: {dupes} duplicate(s) skipped")
    except Exception as e:
        log(f"Plugin init error: {e}")
        import traceback
        log(traceback.format_exc())

init_plugins_all()
init_hooks(log=log)

# ── HTTP Handler ─────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        raw = self.rfile.read(length)
        # Strip trailing whitespace that SSH/curl may add
        raw = raw.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            log(f"JSON parse error: {e}, raw_bytes={raw[:100]!r}")
            raise

    def do_GET(self):
        log(f"[HTTP_DEBUG] do_GET: {self.path!r}")
        import traceback
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        # ── System ──
        if path == "/health":
            uptime = str(datetime.now(timezone.utc) - START_TIME).split(".")[0]
            jobs = []
            for job in scheduler.get_jobs():
                jobs.append({
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                })
            self._json({"status": "ok", "uptime": uptime, "tasks": jobs})

        elif path == "/services":
            self._json(check_services())

        elif path == "/hooks":
            self._json({"hooks": list_hooks()})

        elif path == "/cron":
            self._json(list_tasks())

        elif path == "/tasks":
            jobs = []
            for job in scheduler.get_jobs():
                jobs.append({
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                })
            self._json(jobs)

        # ── Sessions ──
        elif path.startswith("/chat/stream"):
            self._handle_sse_stream()

        elif path == "/sessions":
            self._json(sessions.list())

        # ── Agents (sub-agent management) ──
        elif path == "/agents":
            qs = dict(parse_qs(urlparse(self.path).query))
            status_filter = qs.get("status", [""])[0]
            with _subagents_lock:
                items = list(_subagents.values())
            if status_filter:
                items = [sa for sa in items if sa["status"] == status_filter]
            items.sort(key=lambda sa: sa.get("created_at", ""), reverse=True)
            summary = {}
            for s in ("running", "completed", "failed", "killed"):
                summary[s] = sum(1 for sa in _subagents.values() if sa["status"] == s)
            self._json({"total": len(_subagents), "summary": summary, "agents": items[:50]})

        elif path.startswith("/agents/") and len(path) > 8:
            tid = path[8:]
            with _subagents_lock:
                entry = _subagents.get(tid)
            if entry:
                self._json(entry)
            else:
                self._json({"error": "not found"}, 404)

        # ── Auto-route toggle ──
        elif path == "/auto-route":
            self._json({"enabled": _auto_route_enabled, "profiles": list(_AGENT_PROFILES.keys())})

        elif path.startswith("/sessions/") and path.endswith("/export"):
            sid = path[10:-7]  # /sessions/<id>/export
            data = sessions.export_session(sid)
            if data:
                self._json(data)
            else:
                self._json({"error": "not found"}, 404)

        elif path.startswith("/sessions/") and len(path) > 10:
            sid = path[10:]
            s = sessions.get(sid)
            if s:
                self._json(s.stats())
            else:
                self._json({"error": "not found"}, 404)

        # ── Permissions ──
        elif path == "/permissions":
            from safe_access import PERMISSION_POLICIES, DANGEROUS_CMD_PATTERNS, DANGEROUS_WRITE_PATTERNS, LARGE_FILE_WARN_MB, LARGE_WRITE_WARN_KB
            pending = {}
            for sid, op in list(PENDING_DANGEROUS.items()):
                pending[sid] = {k: v for k, v in op.items() if k != "params"}
            self._json({
                "policies": PERMISSION_POLICIES,
                "limits": {
                    "large_file_warn_mb": LARGE_FILE_WARN_MB,
                    "large_write_warn_kb": LARGE_WRITE_WARN_KB,
                },
                "pending": pending,
            })

        # ── Git tools (GET) ──
        elif path == "/tools/git-status":
            body = self._read_body()
            self._json({"result": tool_git_status(body)})

        elif path == "/tools/git-diff":
            body = self._read_body()
            self._json({"result": tool_git_diff(body)})

        elif path == "/tools/git-log":
            query = dict(parse_qs(parsed.query))
            params = {"path": query.get("path", ["/app"])[0]}
            if "n" in query:
                params["n"] = int(query["n"][0])
            self._json({"result": tool_git_log(params)})

        # ── Background tasks ──
        elif path == "/bg-tasks":
            qs = dict(parse_qs(parsed.query))
            status = qs.get("status", [""])[0]
            self._json(_bg_tasks.list(status=status))

        elif path.startswith("/bg-tasks/"):
            tid = path[10:]
            entry = _bg_tasks.get(tid)
            if entry:
                self._json(entry)
            else:
                self._json({"error": "not found"}, 404)

        elif path == "/metrics":
            data = metrics_response()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data.encode("utf-8"))

        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/")
        # API Key auth check
        auth_prefix, auth_err = _check_auth(self.headers)
        if auth_err:
            self._json(auth_err, 401)
            return

        # ── Task triggers ──
        if path.startswith("/run/") and len(path) > 5:
            name = path[5:]
            if name in TASKS:
                log(f"Manual trigger: {name}")
                Thread(target=TASKS[name]["func"], daemon=True).start()
                self._json({"triggered": name})
            else:
                self._json({"error": f"unknown task: {name}"}, 404)

        elif path == "/cron":
            try:
                body = self._read_body()
                expr = body.get("expression")
                action = body.get("action")
                sid = body.get("session_id")
                desc = body.get("description")
                tid, err = create_task(expr, action, sid, desc)
                if err:
                    self._json({"error": err}, 400)
                else:
                    self._json({"id": tid})
            except Exception as e:
                self._json({"error": str(e)}, 500)

        # ── Auto-route toggle ──
        elif path == "/auto-route":
            body = self._read_body()
            global _auto_route_enabled
            _auto_route_enabled = body.get("enabled", not _auto_route_enabled)
            self._json({"enabled": _auto_route_enabled})

        # ── Kill sub-agent ──
        elif path.startswith("/agents/") and path.endswith("/kill"):
            tid = path[8:-5]  # /agents/<id>/kill
            with _subagents_lock:
                entry = _subagents.get(tid)
            if not entry:
                self._json({"error": "not found"}, 404)
            elif entry["status"] != "running":
                self._json({"error": f"not running (status: {entry['status']})"})
            else:
                entry["status"] = "killed"
                self._json({"killed": tid})

        # ── Session management (fork, rename, import) ──
        elif path.startswith("/sessions/") and path.endswith("/fork"):
            sid = path[10:-5]  # /sessions/<id>/fork
            s = sessions.get(sid)
            if not s:
                self._json({"error": "session not found"}, 404)
                return
            new_sid = sessions.fork(sid)
            sessions.save(SESSION_FILE)
            self._json({"forked": new_sid, "stats": sessions.get(new_sid).stats()})

        elif path.startswith("/sessions/") and path.endswith("/rename"):
            sid = path[10:-7]  # /sessions/<id>/rename
            body = self._read_body()
            name = body.get("name", "")
            if not name:
                self._json({"error": "name required"}, 400)
                return
            ok = sessions.rename(sid, name)
            if ok:
                sessions.save(SESSION_FILE)
                self._json({"renamed": sid, "name": name})
            else:
                self._json({"error": "session not found"}, 404)

        elif path == "/sessions/import":
            body = self._read_body()
            sid = sessions.import_session(body)
            if sid:
                sessions.save(SESSION_FILE)
                self._json({"imported": sid, "stats": sessions.get(sid).stats()})
            else:
                self._json({"error": "invalid session data"}, 400)

        elif path == "/chat":
            try:
                body = self._read_body()
                result = handle_chat(body)
                self._json(result)
            except Exception as e:
                self._json({"error": str(e)}, 500)

        # ── Filesystem tools ──
        elif path.startswith("/tools/"):
            tool_name = path[7:]  # remove /tools/
            body = self._read_body()
            dispatch_name = TOOL_URL_MAP.get(tool_name, tool_name)
            handler = TOOL_DISPATCH.get(dispatch_name)
            if handler:
                try:
                    result = handler(body)
                    self._json({"result": result})
                except Exception as e:
                    self._json({"error": str(e)}, 500)
            else:
                self._json({"error": f"unknown tool: {tool_name}"}, 404)

        else:
            self._json({"error": "not found"}, 404)

    def _handle_sse_stream(self):
        """Handle GET /chat/stream via SSE."""
        from urllib.parse import parse_qs
        qs = parse_qs(urlparse(self.path).query)
        session_id = qs.get("session_id", [""])[0]
        message = qs.get("message", [""])[0]
        if not message:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "message required"}).encode())
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        def sse_send(event, data):
            try:
                payload = "event: " + event + "\ndata: " + json.dumps(data) + "\n\n"
                self.wfile.write(payload.encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

        try:
            body = self._read_body() if self.headers.get("Content-Length") else {}
            if not isinstance(body, dict):
                body = {}
            handle_chat_stream(
                session_id=session_id,
                message=message,
                sse_callback=sse_send,
                temperature=0.3,
                **body,
            )
        except Exception as e:
            sse_send("error", {"error": str(e)})
            log("SSE error: " + str(e))


    def do_DELETE(self):
        path = urlparse(self.path).path.rstrip("/")
        # API Key auth check
        auth_prefix, auth_err = _check_auth(self.headers)
        if auth_err:
            self._json(auth_err, 401)
            return

        if path.startswith("/cron/") and len(path) > 6:
            tid = path[6:]
            ok = delete_task(tid)
            self._json({"deleted": ok})

        elif path.startswith("/sessions/") and len(path) > 10:
            sid = path[10:]
            ok = sessions.delete(sid)
            self._json({"deleted": ok})
        else:
            self._json({"error": "not found"}, 404)


# ── Main ─────────────────────────────────────────────────────────

# ── API Key Auth ─────────────────────────────────────────────────
import secrets
from metrics import metrics_response, observe_request, track_tokens, active_sessions, tool_calls_total, errors_total

AUTH_ENABLED = os.environ.get("AGENT_AUTH_ENABLED", "0") == "1"
API_KEYS_FILE = "/app/api_keys.json"

def _load_api_keys():
    """Load API keys from JSON file. Returns dict of key -> info."""
    try:
        with open(API_KEYS_FILE) as f:
            data = json.load(f)
            return data.get("keys", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save_api_keys(keys):
    """Save API keys to JSON file."""
    with open(API_KEYS_FILE, "w") as f:
        json.dump({"keys": keys}, f, indent=2, default=str)
    os.chmod(API_KEYS_FILE, 0o600)

def _generate_api_key():
    """Generate a secure random API key."""
    return "ds_key_" + secrets.token_hex(16)

def _seed_admin_key():
    """Create initial admin key if none exist. Print to stdout."""
    keys = _load_api_keys()
    if not keys:
        new_key = _generate_api_key()
        now = str(datetime.now(timezone.utc))
        keys[new_key] = {
            "name": "admin",
            "created_at": now,
            "last_used_at": now,
            "role": "admin",
        }
        _save_api_keys(keys)
        print(f"\n{'='*60}")
        print(f"  AGENT AUTH: First run — generated admin API key")
        print(f"  KEY: {new_key}")
        print(f"  FILE: {API_KEYS_FILE}")
        print(f"  To protect: AGENT_AUTH_ENABLED=1 and use header:")
        print(f"    Authorization: Bearer {new_key}")
        print(f"{'='*60}\n")
    return keys

def _check_auth(headers):
    """Validate Authorization header. Returns (prefix, error_json_or_None).
    prefix = truncated key hash for session isolation, or '' if no auth."""
    if not AUTH_ENABLED:
        return "", None
    auth = headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, {"error": "unauthorized", "message": "Missing or invalid Authorization header"}
    token = auth[7:]
    keys = _load_api_keys()
    if token not in keys:
        return None, {"error": "unauthorized", "message": "Invalid API key"}
    # Update last_used_at
    keys[token]["last_used_at"] = str(datetime.now(timezone.utc))
    _save_api_keys(keys)
    # Session prefix = first 12 chars of key hash
    prefix = "_" + secrets.token_hex(6)
    return prefix, None

scheduler = BackgroundScheduler(timezone="UTC")
scheduler.start()

for name, cfg in TASKS.items():
    scheduler.add_job(
        cfg["func"],
        CronTrigger(**cfg["cron"], timezone="UTC"),
        name=name,
        replace_existing=True,
    )
    log(f"Scheduled: {name} ({cfg['description']})")

init_mcp()
_seed_admin_key()

def _cron_on_trigger(tid, cfg):
    """When a user cron task fires, call handle_chat."""
    log(f'User cron [{tid}]: ' + cfg['action'][:60])
    import threading
    msg = {'message': cfg['action'], 'session_id': cfg.get('session_id', 'cron')}
    threading.Thread(target=handle_chat, args=(msg,), daemon=True).start()

n_loaded = init_cron(scheduler, _cron_on_trigger)
if n_loaded:
    log(f'User cron: {n_loaded} task(s) loaded')

log("DeepSeek Agent v3 (Tier 48) started")
all_tools = sorted(TOOL_DISPATCH.keys())
log(f"Tools ({len(all_tools)}): {' '.join(all_tools)}")

def _shutdown_handler(*_):
    log("Shutting down...")
    scheduler.shutdown(wait=False)
    sessions.save(SESSION_FILE)
    log("Sessions saved to disk")
    sys.exit(0)

signal.signal(signal.SIGTERM, _shutdown_handler)

server = ThreadingHTTPServer(("0.0.0.0", 8766), Handler)
log("HTTP API on :8766")
server.serve_forever()
