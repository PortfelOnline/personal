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

## Key Design Decisions

- **JSON-enforced brain output**: no markdown fences, no text outside JSON — prevents DeepSeek meandering
- **`mcp__*` tool auto-discovery**: brain sees all MCP servers (Serena, Graphify, GitHub, GoodMem, Context7, Playwright, Chrome) without hardcoding
- **Phase 0 semantic context**: Graphify/Serena queries before file reads — 50-500 tokens vs 2000-10000
- **Parallel dispatch**: dependency matrix → max 4 concurrent executors for independent tasks
- **Feedback loop**: executor failures → diagnostics → brain revised plan (never retry identical step)
- **Hook pipeline**: PreToolUse (edit/destructive guards), PostToolUse (lint, graphify), SessionStart (context), Stop (memory)

## Infrastructure

| Component | Path | Purpose |
|-----------|------|---------|
| Hooks | `hooks/` | Pre/post tool guards, session lifecycle |
| Scripts | `scripts/save-session-memory.py` | Cross-session pattern extraction from JSONL |
| Settings | `~/.claude/settings.json` | Hook wiring, permissions, MCP config |

## Expert Agents (57 total)

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
- `1945881` — improvements #1-5 (DeepSeek priming, anti-meandering, semantic context, hooks, parallel dispatch)
- `948e852` — #6 feedback loop
- `5450a53` — #7 CI gate agent
- `b55a375` — #8 cross-session learning + infrastructure mirror
- `3c5c585` — #9 test runner + deepseek priming batch
