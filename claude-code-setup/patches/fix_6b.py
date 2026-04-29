#!/usr/bin/env python3
"""Add response_format to both API body blocks in agent.py"""
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "/root/deepseek-agent/agent.py"
with open(path) as f:
    src = f.read()

changes = 0

# Non-streaming body
old = """                body = {
                    "model": attempt_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if tools:"""
new = """                body = {
                    "model": attempt_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if response_format:
                    body["response_format"] = response_format
                if tools:"""
if old in src and "response_format" not in src[src.find(old):src.find(old)+len(old)+50]:
    src = src.replace(old, new, 1)
    changes += 1
    print("[6b] response_format added to non-streaming body")
else:
    print("[6b] SKIP — non-streaming")

# Streaming body
old2 = """                body = {
                    "model": attempt_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True,
                }
                if tools:"""
new2 = """                body = {
                    "model": attempt_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True,
                }
                if response_format:
                    body["response_format"] = response_format
                if tools:"""
if old2 in src and "response_format" not in src[src.find(old2):src.find(old2)+len(old2)+50]:
    src = src.replace(old2, new2, 1)
    changes += 1
    print("[6b] response_format added to streaming body")
else:
    print("[6b] SKIP — streaming")

if changes:
    with open(path, 'w') as f:
        f.write(src)
    print(f"\nDone: {changes} change(s)")
else:
    print("\nNo changes")
