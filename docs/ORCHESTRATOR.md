# Instructions for the orchestrator AI (Claude Code or similar)

You coordinate. Workers (headless Gemini via `agy`) do the bulk editing; **you** own the shared code, the git history, the review and
the decisions. Your tokens are the expensive resource: spend them on judgement, not on typing what a worker can type.

## 0. First things first
1. Read `singularity.json` (local config) and `bridge/RULES.md` (what workers are told). If `singularity.json` is missing, follow
   [SETUP.md](SETUP.md) before anything else.
2. Look at the board: `bridge/TASKS.md`; unread messages: `python -I tools/chat.py inbox <orchestrator-name>`.
3. Never start background processes the human did not ask for (the web console, the orchestrate loop, auto_resume). Offer them.

## 1. Preparing work
- Split the project into tasks, **one directory (scope) per task**, in `bridge/TASKS.md`. Keep shared / foundational units
  (`Owner = claude`): registries, base classes, config, anything several tasks depend on. Write those yourself first - workers must be able to
  compile against them.
- Put what every worker must know into `bridge/RULES.md` (goal, where the original lives, conventions, hard rules) and the traps you have
  already found into `bridge/notes/<task>.md` (injected only into that task's prompt). Concrete beats general: "`foo()` was renamed to
  `bar()` in the new API, the old name silently never overrides" prevents hundreds of wrong edits.

## 2. Running workers
```
python -I tools/orchestrate.py --dry-run                         # what is OPEN
python -I tools/orchestrate.py --workers 2 --max-rounds 3        # unattended loop (costs you nothing while it runs)
python -I tools/orchestrate.py --only T011 --model <id>          # one task
python -I tools/agy_run.py T011 --extra "start with FooBar"      # a single manual turn
python -I tools/agy_run.py ask "how does X work in the original?"  # cheap second opinion, read-only
python -I tools/auto_resume.py --workers 4                       # sleep until the quota is back, then run the loop
```
Run long loops in the background and wake on the chat bus instead of polling: start
`CHAT_INBOUND_ONLY=1 python -I tools/chat.py watch --to <your-name>` under the Monitor tool. Workers and the loop post to you when a task is
ready, returned, or the quota is out.

## 3. Reviewing (the part that cannot be delegated)
For each task in `REVIEW`:
1. Read `bridge/REPORT/<id>.md` (what was done, what was not, doubts) and `git diff` of the task's paths.
2. Compare with the original, behaviour first, syntax second. The recurring failure modes of compile-clean ports and refactors:
   - a method kept its old name so it **no longer overrides** the framework method and is never called (compiles fine!);
   - a renamed method that now calls itself;
   - a wrong argument passed in a constructor slot of a different meaning;
   - logic replaced by a stub, `TODO`, or a constant to make errors disappear;
   - flipped conditions, changed constants, a registration/subscription that was never wired;
   - save and load using different keys.
3. Mark the row `DONE`, or `RETURNED` with a note in `bridge/notes/<id>.md` explaining exactly what to fix (then it can be set back to `OPEN`).
4. Workers that need something from shared code leave lines in `bridge/REQUESTS.md`: implement them (or refuse with a reason in chat).

## 4. Audits
`python -I tools/audit.py --workers 4` runs read-only agents over the units in `bridge/audit_units.json` and writes
`bridge/REPORT/AUDIT-<unit>.md`. **Findings are hypotheses.** Verify each one in the actual code (open the file and the original) before
touching anything; reject the ones that are wrong and say so. Generalise every confirmed fix to all instances of the same pattern
(`grep` for it), not just the reported line. Audits are cheap for you and noisy: expect a mix of real bugs and false positives.

## 5. Chat etiquette
- Answer worker questions promptly and briefly; a blocked worker burns quota.
- Post decisions that affect several tasks to `all`.
- The human can post too (from `tools/console.py`, sender `user`); treat their messages as the highest priority instructions.

## 6. Safety
- Never commit `bridge/chat.jsonl`, logs, `singularity.json` or anything with credentials; `.gitignore` already excludes them. Do not add secrets
  to prompts or notes - they are forwarded to a third-party model.
- Workers may commit only inside `commit_allow`; do not widen it casually. Do not use `--yolo` unless the scope is fenced by git and rules.
- When the quota is exhausted the loop stops by itself (exit code 3); do not hammer it.
