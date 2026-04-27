# Autonomous Dev Pipeline

DeepSeek reasoning + Claude Code MCP execution stack. 60+ specialized agents orchestrated by a manager→brain→executor pipeline with full PR/MR lifecycle automation.

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
| **Planning** | `autonomous-dev-brain` | JSON-enforced task plans, semantic context (Serena/Graphify/GoodMem) | opus |
| **Execution** | `autonomous-dev-executor` | Step-by-step tool execution, JSON output | sonnet |
| **CI/CD** | `autonomous-dev-github` | Full PR loop (branch→commit→PR→review→merge) | sonnet |
| **CI/CD** | `autonomous-dev-gitlab` | Full MR loop (GitLab API v4) | sonnet |
| **Verification** | `ci-gate-agent` | Syntax/lint/type checks (php -l, tsc, eslint, go vet) | sonnet |
| **Verification** | `test-runner-agent` | Run project tests (PHPUnit, Jest, pytest, go test) | sonnet |

## Shared Rules (`shared/`)

| File | Purpose |
|------|---------|
| `deepseek-tool-priming.md` | Tool selection heuristics, parallelism rules, anti-patterns |
| `deepseek-anti-meander.md` | 70% conciseness rule, explanation budgets |
| `feedback-loop.md` | Executor→Brain error diagnosis→fix mapping, revision rules |

## Task Flow

```
1. MANAGER receives task → classifies complexity (TRIVIAL→CRITICAL)
2. TRIVIAL/LOW → executor directly (fast route, saves 60-80% tokens)
3. MEDIUM/HIGH → brain plans → executor executes → github/gitlab ships
4. CI-GATE verifies syntax + tests before merge (hard gate)
5. On failure → executor diagnostics → brain revised plan (feedback loop)
6. Session end → patterns extracted to auto-memory (save-session-memory.py)
```

## SAFE_MODE

- **low risk**: auto-merge if CI gate passes + diff < 200 lines
- **medium risk**: requires manual approval
- **high/critical**: blocked, requires review
- **CI gate failure**: blocked regardless of risk level

## Claude Code Parity — 26 Improvements (#10–#35)

| Tier | # | Feature | Status |
|------|---|---------|--------|
| **1** | #10 | TaskCreate/TaskUpdate integration | ✅ |
| | #11 | Interactive approval gate (EnterPlanMode) | ✅ |
| | #12 | Worktree isolation (EnterWorktree/ExitWorktree) | ✅ |
| | #13 | CI gate wiring (ci-gate-agent) | ✅ |
| **2** | #14 | Error classifier overhaul (20+ patterns) | ✅ |
| | #15 | AskUserQuestion in brain | ✅ |
| | #16 | Session checkpoint/resume | ✅ |
| **3** | #17 | Monitor tool (>30s commands) | ✅ |
| | #18 | CronCreate scheduling | ✅ |
| | #19 | Context compaction awareness | ✅ |
| **4** | #20 | Browser automation in brain (Phase 0 step 5) | ✅ |
| | #21 | Auto-test after code changes (executor verify) | ✅ |
| | #22 | Serena LSP mandatory for code tasks (Phase 0 step 3) | ✅ |
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
| **8** | #35 | Agent validation hook (PostToolUse: validate-agents.py) | ✅ |

## Key Design Decisions

- **JSON-enforced brain output**: no markdown fences, no text outside JSON — prevents DeepSeek meandering
- **`mcp__*` tool auto-discovery**: brain sees all MCP servers (Serena, Graphify, GitHub, GoodMem, Context7, Playwright, Chrome) without hardcoding
- **Phase -1 Skills Gateway**: brainstorming/debugging/TDD detected BEFORE context reading — changes plan structure
- **Phase 0 (6 sources)**: Graphify → GoodMem → Serena (mandatory) → Context7 → Browser → Image/PDF — all before first file read
- **Parallel dispatch**: dependency matrix → max 4 concurrent executors for independent tasks
- **Feedback loop**: executor failures → diagnostics → brain revised plan (never retry identical step)
- **SAFE_MODE**: low-risk auto-merge if CI passes + diff < 200 lines; medium needs approval; high/critical blocked
- **Fast Router**: TRIVIAL/LOW tasks skip brain → executor directly (60-80% token savings)
- **Hook pipeline**: PreToolUse (edit/destructive guards), PostToolUse (lint, graphify), SessionStart (context), Stop (memory)

## Infrastructure

| Component | Path | Purpose |
|-----------|------|---------|
| Hooks | `hooks/` | Pre/post tool guards, session lifecycle |
| Scripts | `scripts/save-session-memory.py` | Cross-session pattern extraction from JSONL |
| Settings | `~/.claude/settings.json` | Hook wiring, permissions, MCP config |

## Expert Agents (60+ total)

**Code Quality**: code-review-expert, php-reviewer, shell-reviewer, sql-reviewer, code-simplifier, linting-expert, refactoring-expert

**Framework**: nestjs-expert, nextjs-expert, react-expert, loopback-expert, vite-expert, webpack-expert

**Language**: typescript-expert, typescript-type-expert, typescript-build-expert, cli-expert, ai-sdk-expert

**Database**: db-migration-agent, postgres-expert, mongodb-expert, database-expert

**Infrastructure**: devops-expert, docker-expert, docker-reviewer, nginx-reviewer, github-actions-expert, iac-reviewer

**Testing**: testing-expert, jest-testing-expert, vitest-testing-expert, playwright-expert

**Performance**: performance-profiler, react-performance-expert

**Security**: api-contract-reviewer, oracle

**SEO** (15 agents): seo-technical, seo-content, seo-schema, seo-performance, seo-dataforseo, seo-google, seo-local, seo-maps, seo-geo, seo-image-gen, seo-sitemap, seo-visual, seo-backlinks, seo-cluster, seo-ecommerce, seo-drift, seo-sxo

**Research**: research-expert, code-search, triage-expert, Explore

## Commit History

See `git log --oneline` for full history. Key milestones:
- `235baba` — initial 61 agents
- `1945881` — #1-#5 (DeepSeek priming, anti-meandering, semantic context, hooks, parallel dispatch)
- `948e852` — #6 feedback loop
- `5450a53` — #7 CI gate agent
- `b55a375` — #8 cross-session learning + infrastructure mirror
- `3c5c585` — #9 test runner + deepseek priming batch
- `02783e8` — Tier 3: #17-#19 (Monitor, CronCreate, compaction awareness)
- `40ce864` — Tier 4: #20-#23 (browser, auto-test, mandatory Serena, auto-lint)
- `acf1ffb` — Tier 5: #24-#26 (image/PDF, code review auto-trigger, skills gateway)
- `c3f606b` — Tier 6: #27-#29 (plugin architecture, progress streaming, permission mirroring)
- `478f66e` — Tier 7: #30-#34 (auto-loop, CLAUDE.md context, WebSearch, model routing, GitLab parity)
