# Executor → Brain Feedback Loop

When the executor fails, its diagnostics MUST feed back to the brain for plan revision.

## Error Classifier — 20+ Patterns (#14)

| # | Pattern | probable_cause | Brain Fix |
|---|---------|----------------|-----------|
| 1 | `undefined variable/function` | `syntax_error` | Read exact lines, fix reference |
| 2 | `cannot find module` | `file_not_found` | Glob for correct path |
| 3 | `permission denied` | `permission_denied` | Suggest alternative or mark requires_review |
| 4 | `EACCES` | `permission_denied` | Same as above |
| 5 | `connection refused` | `network_timeout` | Retry with delay, check host alive |
| 6 | `ETIMEDOUT` | `network_timeout` | Add fallback URL or skip HTTP step |
| 7 | `tool_unavailable` | `tool_unavailable` | Use correct tool from available tools |
| 8 | `merge conflict` | `git_conflict` | Add git status check before commit |
| 9 | `429 Too Many Requests` | `rate_limit` | Add delay between calls, reduce parallelism |
| 10 | `401 Unauthorized` | `auth_failure` | Mark requires_review, suggest auth check |
| 11 | `403 Forbidden` | `auth_failure` | Same as above |
| 12 | `old_string not found` | `syntax_error` | Read file, use EXACT whitespace/indentation |
| 13 | `file not found / no such file` | `file_not_found` | Glob to find correct path |
| 14 | `ENOSPC` (no space left) | `disk_full` | Mark requires_review, suggest cleanup |
| 15 | `out of memory` | `oom` | Reduce scope, split into smaller steps |
| 16 | `npm ERR!` / `composer ERR!` | `dependency_error` | Check package.json/composer.json, suggest fix |
| 17 | `tsc: command not found` | `tool_unavailable` | Install or skip type check |
| 18 | `cannot allocate memory` | `oom` | Reduce parallelism, free resources |
| 19 | `segmentation fault` | `crash` | Rerun with minimal args, debug |
| 20 | `broken pipe` | `network_timeout` | Retry with longer timeout |
| 21 | `blocked by guard` | `permission_denied` | Escalate approach, don't retry identical action |
| 22 | `hook denied` | `permission_denied` | Check allow/deny rules, adjust step |

## New Failure Types (Tiers 3-7)

### Monitor Failures (Tier 3)
| probable_cause | When | Fix |
|----------------|------|-----|
| `monitor_timeout` | Command exceeded timeout_ms | Increase timeout, split command, or skip |
| `monitor_killed` | Monitor was killed (SIGTERM) | Check resource usage, retry with lower concurrency |
| `monitor_crash` | Command crashed (exit ≠ 0) | Read stderr snippet, fix syntax/deps |

### Browser Failures (Tier 4)
| probable_cause | When | Fix |
|----------------|------|-----|
| `browser_closed` | Chrome crashed or was killed | Restart Chrome: `pkill -9 Chrome && retry` |
| `browser_blocked` | Navigation blocked (unknown domain) | Whitelist domain or skip browser step |
| `browser_timeout` | Page load timeout | Increase timeout or simplify page |

### Permission Failures (Tier 6)
| probable_cause | When | Fix |
|----------------|------|-----|
| `permission_denied` | Action matches deny rule | Change approach, don't retry same action |
| `permission_ask` | Action matches ask rule AND mode ≠ dontAsk | Mark requires_review, wait for approval |
| `guard_blocked` | validate_step check failed | Fix the guard violation, don't bypass |

### Lint Failures (Tier 4)
| probable_cause | When | Fix |
|----------------|------|-----|
| `lint_error` | php -l / tsc / eslint found errors | Read lint output, fix syntax, re-lint |
| `lint_warning` | Non-zero exit but compilation ok | Flag in output, don't block |

### Test Failures (Tier 4)
| probable_cause | When | Fix |
|----------------|------|-----|
| `test_failure` | Test suite returned non-zero | Read test output, identify failing tests, fix |
| `test_timeout` | Test suite exceeded 120s/300s limit | Reduce test scope or increase timeout |
| `no_test_runner` | No phpunit/jest/vitest/pytest detected | Skip tests, note in verification |

## Revision Rules

1. **Do NOT retry identical step** — CHANGE the approach
2. **Use diagnostics to determine WHAT changed**:
   - `syntax_error` + expected/actual differ → file was different than assumed
   - `file_not_found` → path was wrong
   - `permission_denied` → don't retry, escalate
3. **Escalate approach on 2nd failure**:
   - Instead of "Edit file X" → "Read file X, extract exact lines, then Edit"
   - Instead of "Grep for pattern" → "Glob for likely files, then Grep each"
   - Instead of "Bash command" → "Monitor with longer timeout"
4. **3rd failure** → admit defeat, mark requires_review: true, suggest manual approach
5. **Permission denials are FINAL** — NO retry. Escalate approach immediately.

## Feedback Flow

```
EXECUTOR FAILS
  → returns {status: "failure", diagnostics: {probable_cause, stderr_snippet, expected, actual}}
    → MANAGER receives, checks retry count
      → 1st: send to BRAIN with diagnostics → brain produces REVISED plan
      → 2nd: send to BRAIN with full history → brain uses ESCALATED approach
      → 3rd: STOP. Mark requires_review. Log pattern to auto-memory.

BRAIN REVISES PLAN:
  → Read diagnostics.probable_cause
  → Look up fix in error classifier table above
  → Produce new step with CHANGED approach (different tool, different target, different method)
  → NEVER just re-run the same step
```
