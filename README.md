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

## Claude Code Parity — 41 Improvements (#10–#50)

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
| **9** | #36 | PostToolUseFailure hook (лог ошибок инструментов) | ✅ |
| | #37 | PreCompact/PostCompact hooks (чекпоинт при сжатии) | ✅ |
| | #38 | Session report на Stop (structured JSON + stats) | ✅ |
| **10** | #39 | Episodic memory в Phase 0 (brain source #8) | ✅ |
| | #40 | PushNotification в менеджере (критические события) | ✅ |
| | #41 | CronList/CronDelete lifecycle (GC, дедупликация) | ✅ |
| | #42 | Plugin agent discovery (скан ~/.claude/plugins/cache/) | ✅ |
| **11** | #43 | ScheduleWakeup pacing (cache-aware интервалы) | ✅ |
| | #44 | Background task lifecycle (TaskOutput/TaskStop) | ✅ |
| | #45 | RemoteTrigger (внешний запуск через вебхуки) | ✅ |
| | #46 | NotebookEdit support (executor tool mapping) | ✅ |
| | #47 | /init agent (авто-генерация CLAUDE.md) | ✅ |
| | #48 | LSP fallback (прямой LSP tool если Serena недоступна) | ✅ |
| | #49 | UserPromptSubmit hook (лог промптов) | ✅ |
| | #50 | Notification hook (обработка уведомлений) | ✅ |
| **12** | #51 | MCP client env vars (`${VAR}` resolution + subprocess env) | ✅ |
| | #52 | GitHub MCP (37 MCP tools, 2 servers, 49 total tools) | ✅ |
| | #53 | PostgreSQL MCP (read-only, 2 БД: getmyagent + n8n) | ✅ |
| | #54 | Playwright MCP (28 browser tools, 78 total tools) | ✅ |

## Delivered Project: strategy-dashboard

**AI Content Generation Dashboard** for get-my-agent.com — Instagram/Facebook social media content for the Indian market, built and delivered end-to-end with the autonomous pipeline.

**Stack:** React + Vite (client, shadcn/ui), Express + tRPC v11 (server), Drizzle ORM + MySQL, TypeScript, Vitest

**Branch:** [`strategy-dashboard`](https://github.com/PortfelOnline/personal/tree/strategy-dashboard)

| Metric | Value |
|--------|-------|
| Tests | 83 passing across 15 files |
| TypeScript | 0 errors (`tsc --noEmit`) |
| CI | GitHub Actions (typecheck + tests on push/PR via pnpm) |
| Coverage | server routers + db layer + storage + meta API + deepseek |
| Languages | Hinglish, Hindi, English, Tamil, Telugu, Bengali |

**Key deliveries:**
- Meta OAuth 2.0 + Instagram/Facebook posting with image upload pipeline (local → server n → CDN)
- AI article rewriting with search engine ranking data context + queue system
- Multi-platform scheduling (Instagram media containers + Facebook page photos/feed)
- CI workflow from scratch (pnpm + frozen-lockfile, typecheck + test gates)
- Dockerfile + hook scripts for dev/prod lifecycle
- Full test coverage for DB, storage, and AI modules (Vitest chainable mocks, EventEmitter patterns)

## Key Design Decisions

- **JSON-enforced brain output**: no markdown fences, no text outside JSON — prevents DeepSeek meandering
- **`mcp__*` tool auto-discovery**: brain sees all MCP servers (Serena, Graphify, GitHub, GoodMem, Context7, Playwright, Chrome) without hardcoding
- **Phase -1 Skills Gateway**: brainstorming/debugging/TDD detected BEFORE context reading — changes plan structure
- **Phase 0 (9 sources)**: CLAUDE.md → Graphify → GoodMem → Serena/LSP (mandatory) → Context7 → Browser → Image/PDF → WebSearch → Episodic Memory — all before first file read
- **Parallel dispatch**: dependency matrix → max 4 concurrent executors for independent tasks
- **Feedback loop**: executor failures → diagnostics → brain revised plan (never retry identical step)
- **SAFE_MODE**: low-risk auto-merge if CI passes + diff < 200 lines; medium needs approval; high/critical blocked
- **Fast Router**: TRIVIAL/LOW tasks skip brain → executor directly (60-80% token savings)
- **Hook pipeline**: PreToolUse (edit/destructive guards), PostToolUse (lint, graphify, validate-agents), PostToolUseFailure (error logging), PreCompact/PostCompact (checkpoint), SessionStart (context), Stop (memory, session report), UserPromptSubmit (prompt logging), Notification (alert forwarding)

## Infrastructure

| Component | Path | Purpose |
|-----------|------|---------|
| Hooks | `hooks/` | Pre/post tool guards, session lifecycle (12 hooks) |
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
- `c32fd18` — Tier 8: #35 (agent validation hook — 0 errors across 63 agents)
- `fbf3128` — Tier 9-10: #36-#42 (hooks: PostToolUseFailure + Pre/PostCompact + session report; semantic: episodic memory + PushNotification + Cron GC + plugin agents)
- `ec5b8e1` — docs: update README — 33 improvements, Tier 9-10, updated Phase 0 + hooks
- `a382330` — Tier 21: DeepSeek Agent context compaction (summarization via flash) + Permissions UX (dangerous cmd, file size, internal IP blocks) + Tier 22: web tools (web_fetch + web_search with DDG Lite, rate limiter, security chain)
- `5dd3abc` — Tier 13 (delivered project): strategy-dashboard — AI Content Generation Dashboard (tested, 83 tests, 0 TS errors, CI pnpm)
- (this session) — Tier 52: claude command shell fix (.zshrc function was missing, only in Claude internal snapshot)
