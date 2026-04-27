# Executor → Brain Feedback Loop

When the executor fails, its diagnostics MUST feed back to the brain for plan revision.

## Diagnosis → Fix Mapping (DeepSeek-specific)

| probable_cause | Root Cause | Brain Fix |
|----------------|-----------|-----------|
| `syntax_error` | Edit old_string didn't match (whitespace, indentation) | Read exact lines before Edit, use EXACT match |
| `file_not_found` | File path wrong or renamed | Glob to find the file first |
| `permission_denied` | Can't write to target | Suggest alternative path or mark requires_review |
| `network_timeout` | URL unreachable | Add fallback URL or skip HTTP step |
| `tool_unavailable` | Wrong tool name in tool_map | Use correct tool from available tools |
| `git_conflict` | Branch/merge conflict | Add git status check before commit |
| `rate_limit` | API rate limit hit | Add delay between calls or reduce parallelism |
| `auth_failure` | Credentials missing/expired | Mark requires_review, suggest auth check |

## Revision Rules

1. **Do NOT retry identical step** — CHANGE the approach
2. **Use diagnostics to determine WHAT changed**:
   - `syntax_error` + expected/actual differ → file was different than assumed
   - `file_not_found` → path was wrong
3. **Escalate approach on 2nd failure**:
   - Instead of "Edit file X" → "Read file X, extract exact lines, then Edit"
   - Instead of "Grep for pattern" → "Glob for likely files, then Grep each"
4. **3rd failure** → admit defeat, mark requires_review: true, suggest manual approach

## Feedback Flow

```
EXECUTOR FAILS
  → returns {status: "failure", diagnostics: {probable_cause, stderr_snippet, expected, actual}}
    → MANAGER receives, checks retry count
      → 1st: send to BRAIN with diagnostics → brain produces REVISED plan
      → 2nd: send to BRAIN with full history → brain uses ESCALATED approach
      → 3rd: STOP. Mark requires_review. Log pattern.
```
