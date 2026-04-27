#!/usr/bin/env python3
"""
Cross-Session Pattern Auto-Indexing (#8)
Extracts patterns from Claude Code session transcripts (JSONL) and indexes into auto-memory.

Usage:
  python3 save-session-memory.py <transcript.jsonl> [--dry-run] [--goodmem]

Output:
  - Writes pattern files to ~/.claude/projects/-Users-evgenijgrudev/memory/
  - Optionally indexes into GoodMem space (if --goodmem and GOODMEM_API_KEY set)

Extracted patterns:
  - Tool usage: which tools used, frequency, parallelism
  - Error patterns: tool failure → fix sequence
  - File clusters: files edited together
  - Session stats: duration, tokens, tasks completed
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter, defaultdict

MEMORY_DIR = Path.home() / ".claude/projects/-Users-evgenijgrudev/memory"

def parse_transcript(path):
    """Parse JSONL transcript into structured events."""
    events = []
    with open(path) as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg = obj.get("message", obj)
            if not isinstance(msg, dict):
                continue

            content = msg.get("content", [])
            if isinstance(content, str):
                continue
            if not isinstance(content, list):
                continue

            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    events.append({
                        "type": "tool_call",
                        "name": block.get("name", "unknown"),
                        "input": block.get("input", {}),
                        "id": block.get("id", ""),
                        "ts": obj.get("timestamp", "")
                    })
                elif block.get("type") == "tool_result":
                    is_error = block.get("is_error", False)
                    content_text = ""
                    if isinstance(block.get("content"), list):
                        content_text = " ".join(
                            c.get("text", "") if isinstance(c, dict) else str(c)
                            for c in block["content"]
                        )[:500]
                    elif isinstance(block.get("content"), str):
                        content_text = block["content"][:500]
                    events.append({
                        "type": "tool_result",
                        "is_error": is_error,
                        "content_preview": content_text,
                        "ts": obj.get("timestamp", "")
                    })
    return events


def extract_patterns(events):
    """Extract learnable patterns from events."""
    patterns = {
        "tool_counts": Counter(),
        "error_tools": Counter(),
        "error_samples": [],
        "file_edits": [],
        "parallel_batches": [],
        "total_tool_calls": 0,
        "total_errors": 0,
        "success_rate": 1.0,
    }

    pending_tool = None
    current_batch = []

    for ev in events:
        if ev["type"] == "tool_call":
            patterns["total_tool_calls"] += 1
            patterns["tool_counts"][ev["name"]] += 1

            # Track file edits
            inp = ev["input"]
            if ev["name"] in ("Edit", "Write"):
                fp = inp.get("file_path", "")
                if fp:
                    patterns["file_edits"].append({
                        "tool": ev["name"],
                        "file": fp,
                        "ts": ev.get("ts", "")
                    })

            # Track parallel batches (calls with no result between them)
            current_batch.append(ev["name"])
            pending_tool = ev

        elif ev["type"] == "tool_result":
            if pending_tool and current_batch:
                if len(current_batch) > 1:
                    patterns["parallel_batches"].append(list(current_batch))
                current_batch = []

            if ev["is_error"]:
                patterns["total_errors"] += 1
                if pending_tool:
                    patterns["error_tools"][pending_tool["name"]] += 1
                    error_msg = ev["content_preview"][:200]
                    patterns["error_samples"].append({
                        "tool": pending_tool["name"],
                        "input": str(pending_tool.get("input", {}))[:200],
                        "error": error_msg
                    })
            pending_tool = None

    total = patterns["total_tool_calls"]
    if total > 0:
        patterns["success_rate"] = (total - patterns["total_errors"]) / total

    return patterns


def classify_error(error_msg):
    """Classify error into probable_cause category."""
    msg = error_msg.lower()
    if "does not exist" in msg or "not found" in msg or "no such file" in msg:
        return "file_not_found"
    if "no such tool" in msg or "tool_unavailable" in msg or "unknown tool" in msg:
        return "tool_unavailable"
    if "permission denied" in msg or "eacces" in msg:
        return "permission_denied"
    if "syntax" in msg or "unexpected token" in msg:
        return "syntax_error"
    if "timeout" in msg or "timed out" in msg:
        return "network_timeout"
    if "conflict" in msg or "merge conflict" in msg:
        return "git_conflict"
    if "rate limit" in msg or "too many requests" in msg:
        return "rate_limit"
    if "auth" in msg or "unauthorized" in msg or "401" in msg or "403" in msg:
        return "auth_failure"
    if "browser has been closed" in msg or "target page" in msg:
        return "network_timeout"
    return "unknown"


def generate_learned_patterns(patterns):
    """Generate learned_patterns array from extracted patterns."""
    learned = []

    # Top tool usage
    top_tools = patterns["tool_counts"].most_common(5)
    if top_tools:
        learned.append({
            "pattern": f"Top tools: {', '.join(f'{t}({c})' for t, c in top_tools)}",
            "fix": "Pre-load context for frequently used tools",
            "frequency": sum(c for _, c in top_tools)
        })

    # Error patterns
    for err in patterns["error_samples"][:3]:
        cause = classify_error(err["error"])
        learned.append({
            "pattern": f"{cause} on {err['tool']}: {err['error'][:100]}",
            "fix": get_fix_for_cause(cause),
            "frequency": patterns["error_tools"].get(err["tool"], 1)
        })

    # File clusters (files edited together)
    edit_files = [e["file"] for e in patterns["file_edits"]]
    if len(edit_files) > 3:
        learned.append({
            "pattern": f"Files edited: {len(set(edit_files))} unique of {len(edit_files)} total",
            "fix": "Consider consolidating edits or using project-level refactoring",
            "frequency": len(edit_files)
        })

    # Parallelism observation
    if patterns["parallel_batches"]:
        avg_batch = sum(len(b) for b in patterns["parallel_batches"]) / len(patterns["parallel_batches"])
        learned.append({
            "pattern": f"Parallel tool batches: {len(patterns['parallel_batches'])} batches, avg {avg_batch:.1f} calls/batch",
            "fix": "Maintain parallelism for independent operations",
            "frequency": len(patterns["parallel_batches"])
        })

    return learned


def get_fix_for_cause(cause):
    fixes = {
        "file_not_found": "Glob to find the file before Read/Edit",
        "tool_unavailable": "Use correct tool from available tools list",
        "permission_denied": "Check file permissions or suggest alternative path",
        "syntax_error": "Read exact lines before Edit, match whitespace exactly",
        "network_timeout": "Add fallback URL or retry with longer timeout",
        "git_conflict": "Add git status check before commit",
        "rate_limit": "Add delay between calls or reduce parallelism",
        "auth_failure": "Check credentials, suggest manual auth",
    }
    return fixes.get(cause, "Investigate manually, escalate to requires_review")


def write_learned_memory(learned_patterns, session_id, dry_run=False):
    """Write extracted patterns to auto-memory."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    ts_str = now.strftime("%H:%M")

    memory_file = MEMORY_DIR / f"learned_session_{session_id}.md"
    content = f"""---
name: learned-session-{session_id}
description: Auto-extracted patterns from session {session_id} on {date_str}
type: feedback
---

# Session Patterns — {date_str} {ts_str}

## Tool Usage
"""
    # Not writing full content here to keep it brief — just the patterns
    # The actual learned patterns go to the auto-memory format

    # Write to learned patterns file
    pattern_lines = []
    for lp in learned_patterns:
        pattern_lines.append(f"- **{lp['pattern']}** → {lp['fix']} (×{lp['frequency']})")

    content += "\n".join(pattern_lines) if pattern_lines else "- No significant patterns extracted\n"

    content += f"\n\n*Auto-generated by save-session-memory.py at {now.isoformat()}*"

    if dry_run:
        print(f"[DRY RUN] Would write to: {memory_file}")
        print(content)
    else:
        memory_file.write_text(content)
        print(f"Wrote: {memory_file}")

    return memory_file


def index_to_goodmem(learned_patterns, session_id):
    """Index patterns into GoodMem if available."""
    api_key = os.environ.get("GOODMEM_API_KEY")
    base_url = os.environ.get("GOODMEM_BASE_URL")

    if not api_key or not base_url:
        print("[GoodMem] Skipped — GOODMEM_API_KEY or GOODMEM_BASE_URL not set")
        return False

    # GoodMem indexing would use the MCP tools — this is a placeholder
    # In practice, the session-save-memory.sh hook can call graphify learn
    # which already indexes into the knowledge graph
    print(f"[GoodMem] Would index {len(learned_patterns)} patterns — delegated to graphify learn")
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: save-session-memory.py <transcript.jsonl> [--dry-run] [--goodmem]")
        sys.exit(1)

    transcript_path = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    use_goodmem = "--goodmem" in sys.argv

    if not os.path.exists(transcript_path):
        print(f"File not found: {transcript_path}")
        sys.exit(1)

    # Parse
    events = parse_transcript(transcript_path)
    print(f"Parsed {len(events)} events from {os.path.basename(transcript_path)}")

    # Extract
    patterns = extract_patterns(events)
    print(f"Extracted: {patterns['total_tool_calls']} tool calls, "
          f"{patterns['total_errors']} errors, "
          f"{patterns['success_rate']:.1%} success rate")

    # Generate learnings
    learned = generate_learned_patterns(patterns)
    print(f"Generated {len(learned)} learned patterns")

    # Session ID from filename
    session_id = os.path.basename(transcript_path).replace(".jsonl", "")[:8]

    # Write
    write_learned_memory(learned, session_id, dry_run)

    # Optionally index to GoodMem
    if use_goodmem:
        index_to_goodmem(learned, session_id)

    # Return JSON for hook consumption
    result = {
        "session_id": session_id,
        "patterns_extracted": len(learned),
        "tool_calls": patterns["total_tool_calls"],
        "errors": patterns["total_errors"],
        "success_rate": patterns["success_rate"],
        "learned_patterns": [
            {"pattern": lp["pattern"], "fix": lp["fix"], "frequency": lp["frequency"]}
            for lp in learned[:5]
        ]
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
