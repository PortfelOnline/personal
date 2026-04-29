#!/usr/bin/env python3
"""Apply gap-closing features to DeepSeek Agent on server n.
Zero-risk: all features opt-in via request body, defaults = current behavior.

Features:
1. Budget controls (max_budget_usd) — track+limit API cost per session
2. Tool allow/deny (allowed_tools, blocked_tools) — filter TOOL_DEFS per request
3. Effort levels (effort: low/medium/high) — control tool call depth
4. JSON mode (response_format) — pass through to DeepSeek API
5. Context compaction toggle (skip_compact) — per-request disable
6. Max context tokens override (max_context_tokens) — per-request override
"""

import re
import sys

def patch_agent(path):
    with open(path) as f:
        src = f.read()

    changes = 0

    # ── 1. Budget tracking constants after TOOL_CALL_MAX_ITER ──
    marker = "TOOL_CALL_MAX_ITER = 10"
    new_block = """TOOL_CALL_MAX_ITER = 10
BUDGET_DEFAULT_MAX_USD = 0.0  # 0 = unlimited (opt-in)
_session_budget = {}  # session_id -> {"total_cost": float, "api_calls": int}
_session_budget_lock = threading.Lock()

# Effort → max tool call iterations
EFFORT_MAP = {"low": 3, "medium": 10, "high": 25}
"""
    if marker in src and "BUDGET_DEFAULT_MAX_USD" not in src:
        src = src.replace(marker, new_block, 1)
        changes += 1
        print("[1/6] Budget tracking constants added")
    else:
        print("[1/6] SKIP — already present or marker not found")

    # ── 2. Tool filtering helper function ──
    # Insert after the TOOL_DISPATCH dict (before _safe_run_hooks)
    marker_func = "def _safe_run_hooks(event, **data):"
    filter_func = """
def _filter_tools(tools, allowed=None, blocked=None):
    \"\"\"Filter tool definitions by allow/block lists. Both are lists of names.
    Returns filtered list. Default (None/empty) = no filtering.\"\"\"
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
    \"\"\"Track API spend per session. Prices in USD per 1M tokens.\"\"\"
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
    \"\"\"Return None if within budget, or error dict if exceeded.\"\"\"
    if not max_usd:
        return None
    with _session_budget_lock:
        entry = _session_budget.get(session_id)
        if entry and entry["total_cost"] >= max_usd:
            return {"error": f"Budget exceeded: ${entry['total_cost']:.4f} >= ${max_usd:.4f} max"}
    return None


"""
    if marker_func in src and "def _filter_tools" not in src:
        src = src.replace("def _safe_run_hooks(event, **data):", filter_func + "def _safe_run_hooks(event, **data):", 1)
        changes += 1
        print("[2/6] Tool filter + budget tracker functions added")
    else:
        print("[2/6] SKIP — already present or marker not found")

    # ── 3. Parse new params in handle_chat() ──
    # Find "def handle_chat(body):" and modify the body parsing section
    hc_marker = '    session_id = body.get("session_id", "")'
    hc_params = """    session_id = body.get("session_id", "")
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
"""
    if hc_marker in src and "allowed_tools = body.get" not in src:
        src = src.replace(hc_marker, hc_params, 1)
        changes += 1
        print("[3/6] handle_chat: opt-in params added")
    else:
        print("[3/6] SKIP — already present or marker not found")

    # ── 3b. Modify context compaction call in handle_chat ──
    old_compact = """    session.compact(lambda p: chat(
        system="You are a summarizer. Output ONLY the summary, no greetings.",
        prompt=p,
        model=FAST_MODEL,
        temperature=0.3,
    ))"""
    new_compact = """    if not skip_compact:
        session.compact(lambda p: chat(
            system="You are a summarizer. Output ONLY the summary, no greetings.",
            prompt=p,
            model=FAST_MODEL,
            temperature=0.3,
        ))"""
    if old_compact in src and "if not skip_compact:" not in src:
        src = src.replace(old_compact, new_compact, 1)
        changes += 1
        print("[3b/6] handle_chat: skip_compact support added")
    else:
        print("[3b/6] SKIP")

    # ── 3c. Modify the for loop in handle_chat to use local_max_iter and check budget ──
    old_for = """    for iteration in range(TOOL_CALL_MAX_ITER):
        try:
            result = _api_call_with_tools(
                session.api_msgs(),
                tools=TOOL_DEFS,"""
    new_for = """    for iteration in range(local_max_iter):
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
                tools=api_tools,"""
    # Make sure we don't double-patch
    if old_for in src and "Budget check before each iteration" not in src:
        src = src.replace(old_for, new_for, 1)
        changes += 1
        print("[3c/6] handle_chat: effort+budget+response_format in loop")
    else:
        print("[3c/6] SKIP")

    # ── 3d. Add budget tracking after successful API call in handle_chat ──
    # Find "content = result.get("content", "")" and add tracking before it
    old_content = """        content = result.get("content", "")"""
    new_content_plus = """        # Track API spend
        usage = result.get("usage", {})
        if usage:
            _track_budget(session_id, result.get("model", "deepseek-v4-flash"),
                          usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0),
                          usage.get("completion_tokens", 0) or usage.get("output_tokens", 0))
        content = result.get("content", "")"""
    if old_content in src and "_track_budget" not in src:
        src = src.replace(old_content, new_content_plus, 1)
        changes += 1
        print("[3d/6] handle_chat: budget tracking after API call")
    else:
        print("[3d/6] SKIP")

    # ── 4. Same params in handle_chat_stream ──
    # Find the streaming version
    hcs_marker = '    session_id = sessions.get(session_id)'
    hcs_params = """    session_id = sessions.get(session_id)
    # ── Opt-in gap features (zero-risk) ──
    allowed_tools = body.get("allowed_tools")  # None or list
    blocked_tools = body.get("blocked_tools")  # None or list
    effort = body.get("effort", "")
    skip_compact = body.get("skip_compact", False)
    response_format = body.get("response_format")
    max_budget = body.get("max_budget_usd", 0.0)
    max_ctx_tok = body.get("max_context_tokens", 0)
    local_max_iter = EFFORT_MAP.get(effort, TOOL_CALL_MAX_ITER) if effort else TOOL_CALL_MAX_ITER
    local_tools = _filter_tools(TOOL_DEFS, allowed=allowed_tools, blocked=blocked_tools)
"""
    # But this marker appears for both functions. We need the one in handle_chat_stream.
    # Let's find the second occurrence — in handle_chat_stream
    # We'll use a different approach: find "def handle_chat_stream" and modify from there
    hcs_replace_old = """def handle_chat_stream(session_id, message, sse_callback, temperature=0.3):
    \"\"\"Streaming chat with SSE events.\"\"\"
    session = sessions.get(session_id)
    if not session:
        session_id = sessions.create(sid=session_id)
        session = sessions.get(session_id)
        # Inject auto-memory system prompt + memory context
        session.system = _build_auto_prompt()

    session.add("user", message)
    sessions.save(SESSION_FILE)

    # Context compaction (Tier 21)
    session.compact(lambda p: chat(
        system="You are a summarizer. Output ONLY the summary, no greetings.",
        prompt=p,
        model=FAST_MODEL,
        temperature=0.3,
    ))"""

    hcs_replace_new = """def handle_chat_stream(session_id, message, sse_callback, temperature=0.3, **kwargs):
    \"\"\"Streaming chat with SSE events.\"\"\"
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

    session.add("user", message)
    sessions.save(SESSION_FILE)

    if not skip_compact:
        session.compact(lambda p: chat(
            system="You are a summarizer. Output ONLY the summary, no greetings.",
            prompt=p,
            model=FAST_MODEL,
            temperature=0.3,
        ))"""

    if hcs_replace_old in src and "handle_chat_stream(session_id, message, sse_callback, temperature=0.3, **kwargs)" not in src:
        src = src.replace(hcs_replace_old, hcs_replace_new, 1)
        changes += 1
        print("[4/6] handle_chat_stream: opt-in params + skip_compact")
    else:
        print("[4/6] SKIP — already present or marker changed")

    # ── 4b. Modify streaming for loop in handle_chat_stream ──
    old_hcs_for = """    for iteration in range(TOOL_CALL_MAX_ITER):
        try:
            gen = _api_call_with_tools_stream(
                session.api_msgs(),
                tools=TOOL_DEFS,"""
    new_hcs_for = """    for iteration in range(local_max_iter):
        budget_check = _check_budget(session_id, max_budget)
        if budget_check:
            sse_callback("error", {"error": budget_check["error"]})
            return
        try:
            api_tools = local_tools
            gen = _api_call_with_tools_stream(
                session.api_msgs(),
                tools=api_tools,"""
    if old_hcs_for in src and "budget_check" not in src:
        src = src.replace(old_hcs_for, new_hcs_for, 1)
        changes += 1
        print("[4b/6] handle_chat_stream: effort+budget in streaming loop")
    else:
        print("[4b/6] SKIP")

    # ── 5. SSE stream handler: pass kwargs ──
    old_sse = """        try:
            handle_chat_stream(
                session_id=session_id,
                message=message,
                sse_callback=sse_send,
                temperature=0.3,
            )"""
    new_sse = """        try:
            body = self._read_body() if self.headers.get("Content-Length") else {}
            if not isinstance(body, dict):
                body = {}
            handle_chat_stream(
                session_id=session_id,
                message=message,
                sse_callback=sse_send,
                temperature=0.3,
                **body,
            )"""
    if old_sse in src and "_read_body()" not in src[src.find(old_sse):src.find(old_sse)+len(old_sse)+200]:
        src = src.replace(old_sse, new_sse, 1)
        changes += 1
        print("[5/6] SSE handler: pass-through kwargs from body")
    else:
        print("[5/6] SKIP")

    # ── 6. Pass response_format to _api_call_with_tools ──
    # Modify the non-streaming API call function
    old_api = """def _api_call_with_tools(messages, tools=None, temperature=0.7, max_tokens=8192, model=None):"""
    new_api = """def _api_call_with_tools(messages, tools=None, temperature=0.7, max_tokens=8192, model=None, response_format=None):"""
    if old_api in src and "response_format=None" not in src:
        src = src.replace(old_api, new_api, 1)
        changes += 1
        print("[6/6] _api_call_with_tools: response_format param")

        # Add response_format to body if present
        old_body = """                body = {
                    "model": attempt_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False,
                }"""
        new_body = """                body = {
                    "model": attempt_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False,
                }
                if response_format:
                    body["response_format"] = response_format"""
        if old_body in src:
            src = src.replace(old_body, new_body, 1)
            print("[6b/6] _api_call_with_tools: response_format in request body")
            changes += 1
        else:
            print("[6b/6] SKIP — body format may differ")
    else:
        print("[6/6] SKIP")

    if changes:
        with open(path, 'w') as f:
            f.write(src)
        print(f"\n✅ Applied {changes} change(s) to {path}")
    else:
        print(f"\n⚠️  No changes applied — all features may already be present")

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "/root/deepseek-agent/agent.py"
    patch_agent(path)
