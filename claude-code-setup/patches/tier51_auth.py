#!/usr/bin/env python3
"""Tier 51: API key auth + multi-tenancy for DeepSeek Agent.
All features opt-in (server starts without auth by default)."""
import sys, json, secrets, os

path = sys.argv[1] if len(sys.argv) > 1 else "/root/deepseek-agent/agent.py"

with open(path) as f:
    src = f.read()

changes = 0
API_KEYS_FILE = "/root/deepseek-agent/api_keys.json"

# ── 1. Constants & storage after last import ──
# Insert after the last top-level import or config block
marker = 'scheduler = BackgroundScheduler(timezone="UTC")'
block = '''# ── API Key Auth ─────────────────────────────────────────────────
AUTH_ENABLED = os.environ.get("AGENT_AUTH_ENABLED", "0") == "1"
API_KEYS_FILE = "/root/deepseek-agent/api_keys.json"

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
        print(f"\\n{'='*60}")
        print(f"  AGENT AUTH: First run — generated admin API key")
        print(f"  KEY: {new_key}")
        print(f"  FILE: {API_KEYS_FILE}")
        print(f"  To protect: AGENT_AUTH_ENABLED=1 and use header:")
        print(f"    Authorization: Bearer {new_key}")
        print(f"{'='*60}\\n")
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

scheduler = BackgroundScheduler(timezone="UTC")'''

if marker in src and "AUTH_ENABLED" not in src:
    src = src.replace(marker, block, 1)
    changes += 1
    print("[1/4] Auth constants + helpers added")
else:
    print("[1/4] SKIP")

# ── 2. Modify do_POST: add auth check ──
old_post_start = '''    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/")

        # ── Task triggers ──'''
new_post_start = '''    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/")
        # API Key auth check
        auth_prefix, auth_err = _check_auth(self.headers)
        if auth_err:
            self._json(auth_err, 401)
            return

        # ── Task triggers ──'''
if old_post_start in src and "auth_err" not in src[src.find(old_post_start):src.find(old_post_start)+len(old_post_start)+100]:
    src = src.replace(old_post_start, new_post_start, 1)
    changes += 1
    print("[2/4] do_POST: auth check added")
else:
    print("[2/4] SKIP")

# ── 3. Modify do_DELETE: add auth check ──
old_delete_start = '''    def do_DELETE(self):
        path = urlparse(self.path).path.rstrip("/")'''
new_delete_start = '''    def do_DELETE(self):
        path = urlparse(self.path).path.rstrip("/")
        # API Key auth check
        auth_prefix, auth_err = _check_auth(self.headers)
        if auth_err:
            self._json(auth_err, 401)
            return'''
if old_delete_start in src and "auth_err" not in src[src.find(old_delete_start):src.find(old_delete_start)+len(old_delete_start)+100]:
    src = src.replace(old_delete_start, new_delete_start, 1)
    changes += 1
    print("[3/4] do_DELETE: auth check added")
else:
    print("[3/4] SKIP")

# ── 4. Add API key management tools ──
# Create or update api-key management tool definitions and dispatch entries

# Add tool definitions to TOOL_DEFS
tool_defs_marker = 'TOOL_DISPATCH = {'
new_tools_block = '''
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

'''
# Insert before TOOL_DISPATCH
if tool_defs_marker in src and "_create_api_key" not in src:
    src = src.replace("TOOL_DISPATCH = {", new_tools_block + "TOOL_DISPATCH = {", 1)
    changes += 1
    print("[4a/4] Auth tool functions added")
else:
    print("[4a/4] SKIP")

# Add to TOOL_DISPATCH
dispatch_marker = 'TOOL_DISPATCH = {'
if dispatch_marker in src and '"create-api-key"' not in src:
    dispatch_entries = '''TOOL_DISPATCH = {
    "create-api-key": _create_api_key,
    "revoke-api-key": _revoke_api_key,
    "list-api-keys": _list_api_keys,'''
    src = src.replace(dispatch_marker, dispatch_entries, 1)
    changes += 1
    print("[4b/4] Auth tools added to TOOL_DISPATCH")
else:
    print("[4b/4] SKIP")

# ── 5. Run seed on startup ──
# Find the init section and add key seeding
main_marker = 'init_mcp()'
if main_marker in src and "_seed_admin_key()" not in src:
    src = src.replace(main_marker, '''init_mcp()
_seed_admin_key()''', 1)
    changes += 1
    print("[5/4] Startup seed for admin key")
else:
    print("[5/4] SKIP")

# ── Write ──
if changes:
    with open(path, 'w') as f:
        f.write(src)
    print(f"\n✅ Applied {changes} change(s)")
else:
    print("\n⚠️  No changes")
