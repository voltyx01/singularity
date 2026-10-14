# How it works

```
 you (browser) --> console.py (web UI) --+
                                         |  post / read
                                         v
 orchestrator AI  <-- Monitor wakes it -- bridge/chat.jsonl <-- chat.py post / inbox -- worker agents
 (Claude Code: owns git, shared code,                                                   (agy -p, headless Gemini)
  review)                                                                               - edit files in their task scope
        ^                                                                               - reach the world ONLY via tools/gw.py
        | reads reports, marks DONE / RETURNED                                                  |
        |                                              orchestrate.py / audit.py spawn them, <---+
        +---- bridge/TASKS.md, bridge/REPORT/*  --->   verify with check.py, retry, escalate

 gw.py ops: check | grep | commit | post | inbox | diffstat      ->  your project (git repo + build)
```

## Components

| File | Role |
|---|---|
| `bridge/TASKS.md` | The task board: a markdown table (`Id`, `Scope`, `Owner`, `Status`, ...). The single source of truth for who does what. |
| `bridge/chat.jsonl` | Append-only message bus between orchestrator, workers and you. One JSON object per line. |
| `bridge/REPORT/` | Worker reports (`T001.md`) and audit reports (`AUDIT-<unit>.md`). |
| `bridge/REQUESTS.md` | Things workers need from shared code that they must not write themselves. |
| `bridge/RULES.md`, `GATEWAY.md`, `AUDIT_PROMPT.md` | The instructions injected into every worker prompt. **Project specific: edit them.** |
| `tools/chat.py` | `post` / `inbox` / `read` / `watch` on the message bus. |
| `tools/gw.py` | The **gateway**: the only command a headless worker may run (see below). |
| `tools/check.py` | Runs your build/test command one at a time (lock file), parses errors, shows only those in a scope. |
| `tools/orchestrate.py` | Unattended loop: claim, run agent, independent verification, retry with the error list, REVIEW / RETURNED. |
| `tools/audit.py` | Read-only bug hunt: one agent per unit writes `AUDIT-<unit>.md`. |
| `tools/auto_resume.py` | Waits for the model quota to return, then restarts the orchestrator loop. |
| `tools/agy_run.py` | One-off manual agent turn or free-form question. |
| `tools/console.py` | Local web UI (127.0.0.1 only): live chat, task board, post messages. |
| `tools/common.py` | Config loading, paths, task-board parsing, the single place that builds the `agy` command line. |
| `singularity.json` | Your local configuration (a copy of `singularity.example.json`, git-ignored). |

## Why a gateway?

`agy -p` (print mode) cannot ask for permission interactively, and its permission rules match the **exact command string**. If the agent
tries any other shell command, the run aborts. The gateway turns this limitation into a feature:

1. the agent writes `bridge/gw/<agent>.json` with its file tool: one request, a small JSON object;
2. it runs the one pre-approved command `python -I tools/gw.py <agent>`;
3. `gw.py` executes only whitelisted operations (`check`, `grep`, `commit`, `post`, `inbox`, `diffstat`), refuses paths outside
   `commit_allow` / `read_roots`, and writes the result to `bridge/gw/<agent>.out`.

So a worker can verify, search, commit and talk, but cannot run arbitrary code or touch files it must not touch.

## The task lifecycle

```
OPEN --orchestrate.py--> CLAIMED gemini-1 <date> --agent runs--> check.py (independent of the agent's own claim!)
   errors -> retry (up to --max-rounds) with the error list -> still failing -> RETURNED (+ chat message to the orchestrator)
   clean  -> REVIEW -> orchestrator compares diff + report with the original -> DONE, or RETURNED with comments
quota exhausted -> task goes back to OPEN, the loop exits with code 3 (auto_resume.py waits, then restarts it)
```

"Clean" means the build is clean **in the task's scope**; it does not mean the behaviour is right. That is why `REVIEW` exists, and why
`audit.py` exists: a second, read-only pass that hunts for silent behavioural differences.

## Scopes

`check.py` prints only errors whose file path (after stripping `check.scope_root`) is directly inside a task's scope directory
(`-r` makes it recursive). Give each task a directory; sub-directories are separate tasks. Parallel workers therefore never see each
other's noise, and the lock file serialises the actual build so they do not fight over it.

## Waking the orchestrator

Claude Code can watch the bus without polling: run `CHAT_INBOUND_ONLY=1 python -I tools/chat.py watch --to claude` under its Monitor
tool; every new message addressed to the orchestrator arrives as a notification, so it sleeps (and costs nothing) between events.

## Limits and honest caveats

- Antigravity's CLI flags and permission behaviour change between versions; `tools/common.py::agent_command` is the one place that builds
  the command line. Check `agy --help` after an update.
- Quota detection is string matching (`agent.quota_markers`); adjust it to the wording your account gets.
- Worker output is plausible-looking code written by a model that cannot run anything. Expect to review.
