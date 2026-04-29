#!/usr/bin/env python3
"""Fix skipped sections from fix_agent_gap.py that were blocked by guards."""
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "/root/deepseek-agent/agent.py"
with open(path) as f:
    src = f.read()

changes = 0

# ── [3d] Add budget tracking after successful API call in handle_chat ──
# Insert _track_budget call before content = result.get("content", "")
old = '        content = result.get("content", "")'
new = '''        # Track API spend
        usage = result.get("usage", {})
        if usage:
            _track_budget(session_id, result.get("model", "deepseek-v4-flash"),
                          usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0),
                          usage.get("completion_tokens", 0) or usage.get("output_tokens", 0))
        content = result.get("content", "")'''
# Need to find the occurrence in handle_chat (not handle_chat_stream)
# Find the one that follows session.add("assistant", ...) return pattern
if old in src:
    # Only add if not already there
    idx = src.find(old)
    # Check if this is in handle_chat (after the "except" block, not in streaming)
    before = src[max(0,idx-200):idx]
    if "session.add(" in before and "_track_budget" not in src[idx-100:idx+100]:
        src = src.replace(old, new, 1)
        changes += 1
        print("[fix-3d] budget tracking after API call added")
    else:
        print("[fix-3d] SKIP — already present or wrong context")
else:
    print("[fix-3d] SKIP — marker not found")

# ── [4b] Fix streaming loop: use local_max_iter + budget check ──
old_stream_loop = '''    for iteration in range(TOOL_CALL_MAX_ITER):
        try:
            gen = _api_call_with_tools_stream(
                session.api_msgs(),
                tools=TOOL_DEFS,
                temperature=temperature,
            )'''
new_stream_loop = '''    for iteration in range(local_max_iter):
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
            )'''
if old_stream_loop in src and "local_max_iter" not in src[src.find(old_stream_loop):src.find(old_stream_loop)+len(old_stream_loop)+100]:
    src = src.replace(old_stream_loop, new_stream_loop, 1)
    changes += 1
    print("[fix-4b] streaming loop: effort+budget")
else:
    print("[fix-4b] SKIP")

# ── [6b] Add response_format to _api_call_with_tools body ──
# This is inside the retry loop in _call_with_retry
old_body_block = '''                body = {
                    "model": attempt_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False,
                }'''
new_body_block = '''                body = {
                    "model": attempt_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False,
                }
                if response_format:
                    body["response_format"] = response_format'''
if old_body_block in src and "response_format" not in src[src.find(old_body_block):src.find(old_body_block)+len(old_body_block)+50]:
    src = src.replace(old_body_block, new_body_block, 1)
    changes += 1
    print("[fix-6b] response_format in request body")
else:
    print("[fix-6b] SKIP")

# ── [4b-ext] Also fix the streaming handle_chat_stream to pass result to _track_budget ──
# After the streaming loop, there's a non-streaming fallback
# Find in handle_chat_stream: content = result.get("content", "")
old_sc = '        content = result.get("content", "")'
new_sc = '''        # Track API spend
        usage = result.get("usage", {})
        if usage:
            _track_budget(session_id, result.get("model", "deepseek-v4-flash"),
                          usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0),
                          usage.get("completion_tokens", 0) or usage.get("output_tokens", 0))
        content = result.get("content", "")'''
# Need to find the occurrence in handle_chat_stream (has sse_callback nearby)
if old_sc in src:
    # Check if this is in handle_chat_stream by looking for sse_callback context
    idx = src.find(old_sc)
    # Skip the first occurrence (in handle_chat) that we already patched
    second_idx = src.find(old_sc, idx + len(old_sc))
    if second_idx > 0:
        before = src[max(0,second_idx-200):second_idx]
        if "sse_callback" in before and "_track_budget" not in src[second_idx-100:second_idx+100]:
            src = src[:second_idx] + new_sc + src[second_idx + len(old_sc):]
            changes += 1
            print("[fix-4b-ext] streaming budget tracking added")
        else:
            print("[fix-4b-ext] SKIP")
    else:
        print("[fix-4b-ext] SKIP — no second occurrence")
else:
    print("[fix-4b-ext] SKIP — marker not found")

if changes:
    with open(path, 'w') as f:
        f.write(src)
    print(f"\n✅ Applied {changes} more change(s)")
else:
    print("\n⚠️  No changes applied")
