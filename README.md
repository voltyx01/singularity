# Singularity

> Русская версия: [README.ru.md](README.ru.md) · **If you are an AI, read [AGENTS.md](AGENTS.md) first.**

A tiny, dependency-free **bridge between an orchestrating AI (Claude Code) and headless worker agents (Google Antigravity CLI `agy`,
running Gemini models)**. The orchestrator plans, reviews and owns the shared code; the workers grind through hundreds of files in parallel;
you watch it all in a live web console. Everything is plain files and ~800 lines of standard-library Python.

## Why

- Orchestrator tokens are expensive; a worker's quota is separate. Let the cheap model type, let the strong model judge.
- A headless `agy -p` agent cannot ask permission, so any unexpected shell command kills its run. A **gateway** (`tools/gw.py`) gives it one
  pre-approved command that executes only whitelisted operations: verify, grep, commit, chat.
- "It compiles" is not "it works". Every task ends in a `REVIEW` state, and a read-only **audit** mode hunts for silent behavioural drift.

## What's inside

```
tools/  common.py chat.py gw.py check.py orchestrate.py audit.py auto_resume.py agy_run.py console.py
bridge/ TASKS.md  RULES.md  GATEWAY.md  AUDIT_PROMPT.md  REQUESTS.md   (+ REPORT/ gw/ logs/ notes/ at runtime)
docs/   ARCHITECTURE.md  ORCHESTRATOR.md  WORKER.md  SETUP.md
singularity.example.json
```

| Piece | One line |
|---|---|
| `bridge/TASKS.md` | markdown task board, one directory scope per task, statuses `OPEN → CLAIMED → REVIEW → DONE / RETURNED` |
| `bridge/chat.jsonl` + `chat.py` | append-only message bus: orchestrator ⇄ workers ⇄ you |
| `gw.py` | the gateway: `check`, `grep`, `commit`, `post`, `inbox`, `diffstat` and nothing else |
| `check.py` | runs your build/test command under a lock, shows only the errors of one scope |
| `orchestrate.py` | unattended loop: run agent → verify independently → retry with the error list → escalate |
| `audit.py` | read-only agents compare new code with the original and write finding reports |
| `auto_resume.py` | sleeps until the model quota returns, then restarts the loop |
| `console.py` | local web UI: live chat, task board, send messages |

## Quick start

```bash
git clone https://github.com/voltyx01/singularity.git && cd singularity
cp singularity.example.json singularity.json     # set check.cmd, work_dirs, ...
agy                                              # log in once; no API keys are used anywhere here
python -I tools/check.py core                    # your build command, filtered to one scope
python -I tools/orchestrate.py --dry-run         # list OPEN tasks
python -I tools/orchestrate.py --only T001       # run one task end to end
python -I tools/console.py --open                # watch it live
```

Details: [docs/SETUP.md](docs/SETUP.md). How it works: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Instructions for the AIs

- Orchestrator (Claude Code etc.): [docs/ORCHESTRATOR.md](docs/ORCHESTRATOR.md)
- Worker agents (`agy -p`): [docs/WORKER.md](docs/WORKER.md), plus the project-specific `bridge/RULES.md` and `bridge/GATEWAY.md` that the
  scripts inject into every prompt.

## Security notes

- **No credentials live in this repository or are read by it.** `agy` authenticates through its own login. `.gitignore` excludes chat logs, reports,
  gateway files, local config and common secret file names.
- Everything in a prompt is sent to a third-party model: do not put secrets or private data in `RULES.md`, notes or the code you expose.
- The gateway refuses paths outside `commit_allow` / `read_roots`; the console binds to `127.0.0.1` only. Treat both as guard rails,
  not a sandbox, and review what workers commit.
- `agy`'s flags change between releases; `tools/common.py::agent_command` is the one place to adapt.

## License

MIT, see [LICENSE](LICENSE).
