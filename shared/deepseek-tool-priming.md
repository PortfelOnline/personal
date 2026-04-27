# DeepSeek v4 Tool-Use Constraints

DeepSeek v4 has strong reasoning but weaker tool intuition than Claude. These rules compensate.

## Brain → Executor Tool Mapping

The brain dispatches steps using abstract tool names. The executor maps them to Claude Code tools:

| step.tool | Claude Code tools | Tier |
|-----------|-------------------|------|
| `filesystem` | Read, Write, Edit | — |
| `git` | Bash with `git` commands | — |
| `shell` | Bash, Monitor (>30s) | Tier 3 |
| `http` | WebFetch | — |
| `mcp` | Available MCP tools (Serena, Graphify, GoodMem, etc.) | — |
| `browser` | Playwright/Chrome MCP tools | Tier 4 |
| `semantic:web` | WebSearch | Tier 7 |
| `lint:php` | Bash: `php -l <file>` | Tier 4 |
| `lint:ts` | Bash: `npx tsc --noEmit` | Tier 4 |
| `lint:eslint` | Bash: `npx eslint <file>` | Tier 4 |
| `lint:go` | Bash: `go vet <file>` | Tier 4 |
| `lint:py` | Bash: `python3 -m py_compile <file>` | Tier 4 |
| `test:runner` | Auto-detect: phpunit/jest/vitest/go test/pytest | Tier 4 |
| `skills:*` | Skill tool (brainstorming/debugging/TDD) | Tier 5 |

## Tool Selection Heuristics

### WHEN TO CALL A TOOL vs REASON
- Call a tool when the answer depends on facts NOT in your context
- Reason when you have sufficient context and just need to analyze
- If uncertain: CALL THE TOOL. Guessing costs more than a tool call.

### TOOL PARALLELISM RULES
- Tools reading DIFFERENT independent files → parallel batch calls
- Tools where output of B depends on output of A → SEQUENTIAL calls
- NEVER make 2 Read calls to the same file in one batch
- If you need to Read then Edit the same file → SEQUENTIAL (Read first, then Edit)

### TOOL-SPECIFIC GOTCHAS
- **Grep**: Use for pattern search. Do NOT Read the file first "to be safe." One Grep with the right pattern is cheaper than Read + Grep.
- **Read**: use only for files you KNOW you need. Do NOT Read files "for context" that aren't directly relevant.
- **Read**: Image/PDF files supported natively (Tier 5) — use for screenshots, diagrams, PDF specs.
- **Glob**: use for file discovery. Do NOT Read a directory listing then Glob. Glob IS the discovery tool.
- **Bash**: for git, npm, and simple commands only. No multi-line scripts.
- **Monitor**: for commands >30s (builds, installs, test suites). Streams progress, prevents timeouts. (Tier 3)
- **WebSearch**: for current docs, novel errors, library APIs not in Context7. (Tier 7)
- **WebFetch**: for fetching specific URLs. Cached for 15 minutes.
- **Edit**: old_string must be EXACT match including whitespace. If unsure, Read the target lines first.
- **Browser** (Playwright/Chrome MCP): navigate (localhost only unless configured), snapshot, screenshot, evaluate (read-only JS). Blocked: destructive JS, unknown domains, file upload. (Tier 4)

### MCP TOOL AUTO-DISCOVERY
- All `mcp__*` tools are auto-discovered at session start
- Serena: `mcp__serena__find_symbol`, `mcp__serena__read_file`, etc. — MANDATORY for code tasks (Tier 4)
- Graphify: `mcp__graphify__graphify_query`, `mcp__graphify__graphify_path`, etc. — knowledge graph traversal
- GoodMem: `mcp__plugin_goodmem__*` — persistent memory for cross-session learning
- Context7: `mcp__plugin_context7__*` — library docs (resolve-library-id → query-docs)
- Any future MCP server — automatically visible without hardcoding

### Permission Awareness (Tier 6)
- Every executor step includes permission resolution: DENY → ALLOW → ASK → DEFAULT
- Rules use Claude Code prefix-wildcard syntax: `Bash(git *)`, `Write(/etc/*)`
- Blocked actions: `rm -rf`, `sudo`, `git push --force`, unknown-domain navigation
- Plan mode is read-only — no Write/Edit/Bash in plan mode

## Anti-Patterns (DeepSeek-Specific)
- ❌ Reading a file, then Grep-ing the same file in the same batch
- ❌ Calling Glob followed by ls on the same directory
- ❌ Using Bash(cat) instead of Read
- ❌ Using Bash(grep) instead of the Grep tool
- ❌ Grep-ing with `-rn` without a specific directory
- ❌ Reading README.md "just to understand the project" — use Glob for structure
- ❌ Using Bash for commands >30s — use Monitor instead (Tier 3)
- ❌ Guessing library APIs without Context7 or WebSearch — use context first (Tier 7)
- ❌ Executing code tasks without Serena LSP — MANDATORY for code tasks (Tier 4)
- ❌ Skipping lint after code changes — auto-lint is mandatory (Tier 4)
