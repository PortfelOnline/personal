# DeepSeek v4 Tool-Use Constraints

DeepSeek v4 has strong reasoning but weaker tool intuition than Claude. These rules compensate.

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
- **Glob**: use for file discovery. Do NOT Read a directory listing then Glob. Glob IS the discovery tool.
- **Bash**: for git, npm, and simple commands only. No multi-line scripts.
- **Edit**: old_string must be EXACT match including whitespace. If unsure, Read the target lines first.

## Anti-Patterns (DeepSeek-Specific)
- ❌ Reading a file, then Grep-ing the same file in the same batch
- ❌ Calling Glob followed by ls on the same directory
- ❌ Using Bash(cat) instead of Read
- ❌ Using Bash(grep) instead of the Grep tool
- ❌ Grep-ing with `-rn` without a specific directory
- ❌ Reading README.md "just to understand the project" — use Glob for structure
