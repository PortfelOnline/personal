# AGENTS.md — Autonomous Dev Pipeline

## Architecture

```
                    MANAGER (autonomous-dev-manager)
                   /      |      \
                  /       |       \
               BRAIN   EXECUTOR   CI-GATE
              (plan)   (execute)  (verify)
                 \        |        /
                  \       |       /
                GITHUB / GITLAB AGENT
                (branch→commit→PR→merge)
```

## Agent Layers

| Layer | Agent | Role | Model |
|-------|-------|------|-------|
| **Orchestration** | `autonomous-dev-manager` | Prioritize, route, monitor KPIs, enforce gates | opus |
| **Planning** | `autonomous-dev-brain` | JSON-enforced task plans, semantic context (7-source Phase 0) | opus |
| **Execution** | `autonomous-dev-executor` | Step-by-step tool execution, JSON output, verify chain | sonnet |
| **CI/CD** | `autonomous-dev-github` | Full PR loop (branch→commit→PR→review→merge) | sonnet |
| **CI/CD** | `autonomous-dev-gitlab` | Full MR loop (GitLab API v4) | sonnet |
| **Verification** | `ci-gate-agent` | Syntax/lint/type checks (php -l, tsc, eslint, go vet) | sonnet |
| **Verification** | `test-runner-agent` | Run project tests (PHPUnit, Jest, pytest, go test) | sonnet |

## Shared Rules (`shared/`)

| File | Purpose |
|------|---------|
| `deepseek-tool-priming.md` | Tool selection heuristics, brain→executor mapping, parallelism rules, anti-patterns |
| `deepseek-anti-meander.md` | 70% conciseness rule, explanation budgets, structured output |
| `feedback-loop.md` | 22-pattern error classifier, revision rules, new failure types (Monitor/Browser/Permission) |

## Task Flow

```
1. MANAGER receives task → classifies complexity (TRIVIAL→CRITICAL)
2. TRIVIAL/LOW → executor directly (fast route, saves 60-80% tokens)
3. MEDIUM/HIGH → brain plans → executor executes → github/gitlab ships
4. CI-GATE verifies syntax + tests before merge (hard gate)
5. On failure → executor diagnostics → brain revised plan (feedback loop)
6. Session end → patterns extracted to auto-memory
```

## SAFE_MODE

- **low risk**: auto-merge if CI gate passes + diff < 200 lines
- **medium risk**: requires manual approval
- **high/critical**: blocked, requires review
- **CI gate failure**: blocked regardless of risk level

## Claude Code Parity — 25 Improvements (#10-#34)

| Tier | # | Feature | Status |
|------|---|---------|--------|
| **1** | #10 | TaskCreate/TaskUpdate integration | ✅ |
| | #11 | Interactive approval gate (EnterPlanMode) | ✅ |
| | #12 | Worktree isolation (EnterWorktree/ExitWorktree) | ✅ |
| | #13 | CI gate wiring (ci-gate-agent) | ✅ |
| **2** | #14 | Error classifier overhaul (22 patterns) | ✅ |
| | #15 | AskUserQuestion in brain | ✅ |
| | #16 | Session checkpoint/resume | ✅ |
| **3** | #17 | Monitor tool (>30s commands) | ✅ |
| | #18 | CronCreate scheduling | ✅ |
| | #19 | Context compaction awareness | ✅ |
| **4** | #20 | Browser automation in brain (Phase 0 step 5) | ✅ |
| | #21 | Auto-test after code changes (executor verify) | ✅ |
| | #22 | Serena LSP mandatory for code tasks | ✅ |
| | #23 | Post-edit auto-lint (php/ts/go/py) | ✅ |
| **5** | #24 | Image/PDF reading in brain (Phase 0 step 6) | ✅ |
| | #25 | Code review auto-trigger in PR flow | ✅ |
| | #26 | Skills gateway (Phase -1: brainstorming/debugging/TDD) | ✅ |
| **6** | #27 | Plugin architecture (auto-discovery, hot-load, contract) | ✅ |
| | #28 | Progress streaming (milestone timeline → manager spinner) | ✅ |
| | #29 | Permission mirroring (allow/deny/ask/defaultMode) | ✅ |
| **7** | #30 | Auto-loop mode (keep working until done, safety gates) | ✅ |
| | #31 | Project CLAUDE.md context (Phase 0 step 0) | ✅ |
| | #32 | WebSearch in Phase 0 + tool_map | ✅ |
| | #33 | Multi-model routing (sonnet/opus by complexity) | ✅ |
| | #34 | GitLab↔GitHub parity (code-review-expert in both) | ✅ |

## Project Files

- `notes/` — topic-specific markdown notes
- `docs/` — specifications, plans, designs

## Working Rules

- Prefer updating existing files over creating near-duplicate ones
- Keep one main topic per file
- Use concise headings and short sections
