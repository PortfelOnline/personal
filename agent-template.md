---
name: your-agent-name
description: >-
  What it does and when to use it. Include PROACTIVELY if the agent should be
  auto-dispatched. Keep under 200 chars — used in manager dispatch decisions.
tools: Read, Grep, Glob, Bash, Edit, Write, WebFetch
model: sonnet                       # sonnet | opus | haiku (default: sonnet)
category: custom                    # See category routing table below
displayName: Your Agent Name
color: blue                         # grey | blue | green | orange | red | purple | yellow
---

# Your Agent Name

## Purpose

What problem does this agent solve? 2-3 sentences.

## When to Use

- Specific trigger conditions
- Input format expected
- What NOT to use this agent for

## Available Tools

Brief tool usage guidance. If the agent has restricted tools (e.g., read-only), state it here.

## Output Format

What the agent returns. JSON schema if structured output is expected.

## Rules

Any constraints, anti-patterns, or project conventions to follow.

## Category Routing Reference

| Category | Directory | When Dispatched |
|----------|-----------|-----------------|
| `dev` | `/` (root) | Pipeline orchestration (manager, brain, executor, CI/CD) |
| `custom` | `/` (root) | User-created custom agents |
| `code-quality` | `code-quality/`, `/` (root) | Code review, linting, refactoring |
| `review` | `/` (root) | PHP, shell, SQL, API contract review |
| `testing` | `testing/` | Jest, Vitest, Playwright, testing strategies |
| `database` | `database/` | PostgreSQL, MongoDB, migrations, general DB |
| `typescript` | `typescript/` | Type system, build, general TypeScript |
| `react` | `react/` | React components, performance, patterns |
| `frontend` | `frontend/` | Accessibility, CSS styling |
| `build-tools` | `build-tools/` | Vite, Webpack |
| `infrastructure` | `infrastructure/` | Docker, Nginx, GitHub Actions, IaC |
| `devops` | `devops/` | General DevOps and CI/CD |
| `framework` | `framework/` | Next.js |
| `nodejs` | `nodejs/` | Node.js runtime |
| `git` | `git/` | Git workflows, merge conflicts |
| `documentation` | `documentation/` | Documentation quality and structure |
| `e2e` | `e2e/` | Playwright E2E testing |
| `kafka` | `kafka/` | Apache Kafka |
| `loopback` | `loopback/` | LoopBack 4 framework |
| `seo` | `/` (root) | 17 SEO specialized agents |
| `research` | `/` (root) | Research, code search, triage |
| `general` | `/` (root) | Oracle, triage, general-purpose |
| `api` | `/` (root) | API contract review, AI SDK |

## JSON Contract (for autonomous dev pipeline)

All agents must return structured JSON:

```json
{
  "status": "success|failure|blocked",
  "output": "Result summary",
  "requires_review": false,
  "findings": ["finding 1", "finding 2"],
  "severity": "info|warning|error|critical"
}
```

For executor agents: use the full contract with `permission`, `progress`, `verification` fields.
