import os
"""Multi-turn session management with context compaction."""

import time
from datetime import datetime, timezone

MAX_MSGS = 12  # compact earlier = smaller context = cheaper calls
COMPACT_TRIGGER = 15


class Session:
    def __init__(self, sid, system=""):
        self.id = sid
        self.created = datetime.now(timezone.utc).isoformat()
        self.updated = self.created
        self.system = system
        self.name = ""
        self.messages = []
        self.compacted = False
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def add(self, role, content, tool_calls=None, tool_call_id=None, reasoning_content=None):
        msg = {"role": role, "content": content or ""}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        if tool_call_id:
            msg["tool_call_id"] = tool_call_id
        if reasoning_content:
            msg["reasoning_content"] = reasoning_content
        self.messages.append(msg)
        self.updated = datetime.now(timezone.utc).isoformat()

    def api_msgs(self):
        msgs = []
        if self.system:
            msgs.append({"role": "system", "content": self.system})
        msgs.extend(self.messages)
        while len(msgs) > MAX_MSGS + 1:
            for i, m in enumerate(msgs):
                if m["role"] != "system":
                    msgs.pop(i)
                    break
        return msgs


    def log_usage(self, prompt, completion):
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.updated = datetime.now(timezone.utc).isoformat()

    def needs_compact(self):
        return len(self.messages) >= COMPACT_TRIGGER and not self.compacted

    def compact(self, chat_func):
        """Summarize old messages using chat_func. Falls back to truncation."""
        if not self.needs_compact():
            return
        keep = MAX_MSGS // 2
        old = self.messages[:-keep]
        new = self.messages[-keep:]
        parts = []
        for m in old:
            role = m["role"]
            content = (m.get("content") or "")[:500]
            if role == "user":
                parts.append("User: " + content)
            elif role == "assistant":
                text = content
                if not text and m.get("tool_calls"):
                    names = ", ".join(tc["function"]["name"] for tc in m["tool_calls"])
                    text = "[called: " + names + "]"
                if text:
                    parts.append("Assistant: " + text)
            elif role == "tool":
                parts.append("[Tool result: " + content[:200] + "]")
        if not parts:
            self.messages = new
            return
        prompt = (
            "Compress this conversation into 2-3 sentences. "
            "Keep: task goals, decisions made, file paths, key findings. "
            "Discard: tool mechanics, error messages, streamed tokens, intermediate results.\n\n"
            + "\n".join(parts)
        )
        try:
            summary = chat_func(prompt)
            summary = summary.strip().strip('"').strip("'")
            self.messages = [
                {"role": "assistant", "content": "[Compact]: " + summary}
            ] + new
            self.compacted = True
        except Exception:
            self.messages = new

    def stats(self):
        return {
            "id": self.id, "name": getattr(self, "name", ""),
            "msgs": len(self.messages),
            "compacted": self.compacted,
            "created": self.created, "updated": self.updated,
            "prompt_tokens": self.prompt_tokens, "completion_tokens": self.completion_tokens,
        }


class SessionManager:
    def __init__(self):
        self._sessions = {}

    def create(self, sid=None, system=""):
        sid = sid or "s" + str(safe_time())
        self._sessions[sid] = Session(sid, system)
        return sid

    def get(self, sid):
        return self._sessions.get(sid)

    def delete(self, sid):
        return self._sessions.pop(sid, None) is not None

    def list(self):
        return {s: self._sessions[s].stats() for s in self._sessions}

    def save(self, path):
        """Save all sessions to JSON file."""
        import json
        data = {}
        for sid, session in self._sessions.items():
            data[sid] = {
                "id": session.id,
                "created": session.created,
                "updated": session.updated,
                "system": session.system,
                "name": getattr(session, "name", ""),
                "messages": session.messages,
                "compacted": session.compacted,
                "prompt_tokens": session.prompt_tokens,
                "completion_tokens": session.completion_tokens,
            }
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)  # atomic

    def load(self, path):
        """Load sessions from JSON file. Returns count of restored sessions."""
        import json
        if not os.path.exists(path):
            return 0
        with open(path) as f:
            data = json.load(f)
        for sid, d in data.items():
            s = Session(sid, d.get("system", ""))
            s.created = d.get("created", s.created)
            s.updated = d.get("updated", s.updated)
            s.name = d.get("name", "")
            s.messages = d.get("messages", [])
            s.compacted = d.get("compacted", False)
            s.prompt_tokens = d.get("prompt_tokens", 0)
            s.completion_tokens = d.get("completion_tokens", 0)
            self._sessions[sid] = s
        return len(data)

    def fork(self, sid, new_sid=None):
        """Create a new session seeded from an existing one. Returns new_sid."""
        import copy
        src = self._sessions.get(sid)
        if not src:
            return None
        new_sid = new_sid or ("s" + str(int(__import__("time").time())) + "_fork")
        s = Session(new_sid, src.system)
        s.messages = copy.deepcopy(src.messages)
        s.name = src.name + " (fork)" if src.name else "Forked session"
        self._sessions[new_sid] = s
        return new_sid

    def export_session(self, sid):
        """Export full session data as dict."""
        s = self._sessions.get(sid)
        if not s:
            return None
        return {
            "id": s.id,
            "name": getattr(s, "name", ""),
            "created": s.created,
            "updated": s.updated,
            "system": s.system,
            "messages": s.messages,
            "compacted": s.compacted,
            "prompt_tokens": s.prompt_tokens,
            "completion_tokens": s.completion_tokens,
        }

    def import_session(self, data):
        """Import session from dict. Returns new_sid or None."""
        if not data or "id" not in data:
            return None
        sid = data["id"]
        s = Session(sid, data.get("system", ""))
        s.created = data.get("created", s.created)
        s.updated = data.get("updated", s.updated)
        s.name = data.get("name", "")
        s.messages = data.get("messages", [])
        s.compacted = data.get("compacted", False)
        s.prompt_tokens = data.get("prompt_tokens", 0)
        s.completion_tokens = data.get("completion_tokens", 0)
        self._sessions[sid] = s
        return sid

    def rename(self, sid, name):
        """Set human-readable name for a session."""
        s = self._sessions.get(sid)
        if not s:
            return False
        s.name = name
        s.updated = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        return True

    def get_last_active(self):
        """Return the most recently updated session, or None."""
        best = None
        best_ts = ""
        for s in self._sessions.values():
            if s.updated > best_ts:
                best_ts = s.updated
                best = s
        return best


def safe_time():
    return int(time.time())
