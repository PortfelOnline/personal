# personal — Notes & Documentation

**Project:** Personal notes, principles, and reference materials
**Stack:** Markdown files

## Structure
- `notes/` — topic-specific notes and principles

## How to work
- Add new notes as markdown files in `notes/`
- Keep files focused on one topic each

## Agent guide
- For cross-project agent behavior (commands, skills, MCP, rules, settings) see `docs/agent/AGENT_GUIDE.md`.

## Cursor scoped rules
Path-scoped guidance for `notes/` lives in `.cursor/rules/`.

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)
