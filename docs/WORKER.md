# Instructions for worker agents (headless, launched with `agy -p`)

You were started non-interactively by `tools/orchestrate.py`, `tools/audit.py` or `tools/agy_run.py`. Nobody can answer a permission
prompt, so **any shell command other than the gateway aborts your run**.

## What you may do
- List, read, search and edit files with your built-in tools (inside your task's scope only).
- Run exactly one command: `python -I tools/gw.py <your-agent-name>` (from the project root), after writing one JSON request to
  `bridge/gw/<your-agent-name>.json`. The answer is printed and also saved to `bridge/gw/<your-agent-name>.out`.

| Request | Does |
|---|---|
| `{"op":"check","prefixes":["scope"]}` | Verifies the project; shows only errors in your scope; must end with `ERRORS in scope [...]: 0` |
| `{"op":"grep","pattern":"regex","path":"src"}` | Read-only regex search (allowed roots only) |
| `{"op":"post","to":"claude","task":"T001","text":"..."}` | Message to the orchestrator |
| `{"op":"inbox"}` | Unread messages for you |
| `{"op":"commit","task":"T001","message":"...","paths":["..."]}` | Commit your own paths |
| `{"op":"diffstat"}` | Summary of your uncommitted changes |

## Workflow
1. Read `bridge/RULES.md` (project rules) and, if your prompt includes them, the special notes for your task.
2. Read the original / reference before changing logic. Keep names, packages and public signatures.
3. Edit only the files of your task. Anything needed from shared code goes into `bridge/REQUESTS.md` as one line
   (`- [you/task] symbol -> where needed -> what it must do`); never stub shared code yourself.
4. Run `check` after each larger step, fix, repeat until `ERRORS in scope [...]: 0`.
5. Commit through the gateway (only your paths). Write `bridge/REPORT/<task>.md`: what you did, what you could **not** do and why,
   what you are unsure about. Honesty here is worth more than a clean-looking report.
6. Do not edit `bridge/TASKS.md` statuses; the orchestrator does.

## Do not
- invent APIs: if you are not sure a method exists, find it in the sources or dependencies you can read;
- delete behaviour to make an error go away (leave `// TODO(<task>): reason` and report it);
- run anything except the gateway, touch files outside your scope, or rewrite history;
- put secrets (keys, tokens, personal paths) into code, reports or chat.

## Audit mode
If your prompt says "read-only audit": you write **only** `bridge/REPORT/AUDIT-<unit>.md`, in the format given in the prompt. Every finding
needs concrete file:line on both sides (new code and original), what happens at runtime, and a concrete fix. No "should check" items.
