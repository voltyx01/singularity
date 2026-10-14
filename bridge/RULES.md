# Rules for worker agents

> Headless agents cannot run shell commands. Read `bridge/GATEWAY.md` first; wherever these rules say `tools/check.py`,
> `tools/chat.py` or `git commit`, use the gateway request instead.

**Edit this file for your project**: replace the placeholders in "Ground truth" and "Hard rules" with the real goal, source/reference
locations and conventions. Everything else is the generic protocol and can stay.

## Ground truth
- Goal: <ONE sentence - e.g. "identical behaviour to the original, idiomatic code for the new platform">.
- Reference (read-only): `<path to the original code>`, same relative path as your file.
- Work tree: `src/...`. Edit files **only inside your claimed task's scope**.
- Shared code (do NOT edit, ask via `bridge/REQUESTS.md`): `<list of shared directories>`.

## How to work
1. Take your task from `bridge/TASKS.md` (the orchestrator sets the status; one task per agent at a time).
2. Read the reference before changing logic. Keep names, packages and public signatures unless the task says otherwise.
3. Verify with the gateway `check` op; it must report `ERRORS in scope [...]: 0`. Errors that originate in a file *outside* your scope are
   not yours: record them in `bridge/REQUESTS.md` (what symbol, who needs it) and stub nothing yourself.
4. Commit only your paths through the gateway. Never `git add -A`, never rewrite history, never touch other tasks' files.
5. Write 3-6 lines in `bridge/REPORT/<task id>.md`: what changed, what you could NOT do (and why), behaviours you are unsure about.

## Hard rules
- Never invent APIs. If unsure that a method exists, search the sources / dependency jars you can read instead of guessing.
- Do not delete behaviour to make errors disappear. If something truly cannot be done, leave a `// TODO(<task id>): reason` and list it in the report.
- No blanket warning suppression, no casts to a catch-all type to dodge the type checker, no empty catch blocks.
- Keep numeric constants, formulas and timings exactly as in the reference.

## Chat with the orchestrator (live channel)
Through the gateway: `post` to ask, `inbox` to read replies (check it after each larger step and before asking again).
Ask instead of guessing when the original behaviour is unclear, an API you need is missing from shared code, or a decision affects other tasks.
Keep messages short; put details in the report. Do not wait idle for an answer: continue with other files of your task.
