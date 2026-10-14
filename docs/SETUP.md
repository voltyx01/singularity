# Setup

Requirements: Python 3.9+ (standard library only), git, the Google Antigravity CLI `agy` (logged in with your own account), and
whatever builds your project. Windows, Linux and macOS work; the examples use forward slashes.

## 1. Put the bridge next to your project

Easiest: clone this repository **as a folder inside (or beside) your project** and treat that folder as the bridge root
(`tools/` and `bridge/` live there). Paths in `singularity.json` are relative to the bridge root.

```
git clone https://github.com/voltyx01/singularity.git
cd singularity
cp singularity.example.json singularity.json
cp bridge/audit_units.example.json bridge/audit_units.json     # only if you want audits
```

If your project is a git repository, run the bridge from inside it (so `git commit` through the gateway commits to your project), e.g. copy
`tools/` and `bridge/` into your repo root, or point `work_dirs` at your sources.

## 2. Log `agy` in (once)

```
agy            # follow the login flow; credentials stay in agy's own store, never in this repo
agy models     # pick a model id for "agent.model" (empty = agy default)
```

No API key is ever put in `singularity.json` or any script. If you ever feel the need to, something is wrong.

## 3. Configure `singularity.json`

| Key | Meaning |
|---|---|
| `orchestrator` | name of the reviewing AI on the chat bus (default `claude`) |
| `worker_prefix` | workers are `<prefix>-1`, `<prefix>-2`, ... (default `gemini`) |
| `work_dirs` | directories workers may edit |
| `read_roots` | extra read-only roots for the gateway `grep` (put the original/reference code here) |
| `commit_allow` | paths the gateway `commit` accepts (trailing `/` = directory prefix) |
| `check.cmd` | your build/test command (list or string). It is run from the bridge root, one at a time |
| `check.error_regex` | regex with named groups `file`, `line`, `msg` matching ONE error line of that command's output |
| `check.scope_root` | prefix stripped from `file` so task scopes can be short (`core` instead of `src/main/java/.../core`) |
| `check.ok_marker` | optional text meaning "whole project OK" |
| `agent.cmd / model / mode` | the CLI, model id and mode (`accept-edits` or `plan`) |
| `agent.cwd / add_dirs` | working directory of the agent and extra directories it may see (`--add-dir`) |
| `agent.quota_markers` | substrings of the agent output that mean "quota exhausted" |

Examples of `check` for other stacks:

```jsonc
// TypeScript
"check": {"cmd": ["npx", "tsc", "--noEmit", "--pretty", "false"],
          "error_regex": "^(?P<file>[^(\\n]+)\\((?P<line>\\d+),\\d+\\): error (?P<msg>.*)$", "scope_root": "src"}
// Rust
"check": {"cmd": ["cargo", "check", "--message-format=short"],
          "error_regex": "^(?P<file>[^:\\n]+):(?P<line>\\d+):\\d+: error(?:\\[\\w+\\])?: (?P<msg>.*)$", "scope_root": "src"}
// Python (mypy)
"check": {"cmd": ["mypy", "--no-pretty", "."],
          "error_regex": "^(?P<file>[^:\\n]+):(?P<line>\\d+): error: (?P<msg>.*)$", "scope_root": "src"}
```

Test it without any agent: `python -I tools/check.py core` should print `ERRORS in scope ['core']: <n>` and exit 0/1.

## 4. Write the project-specific instructions

Edit `bridge/RULES.md` (goal, where the original lives, conventions, hard rules) and `bridge/AUDIT_PROMPT.md` (bug patterns for your
domain). These are injected into every worker prompt; the more concrete they are, the fewer wrong edits you review.
Replace the example rows of `bridge/TASKS.md` with your own.

## 5. Smoke test

```
python -I tools/chat.py post --from user --to claude "hello"
python -I tools/chat.py read
echo '{"op":"inbox"}' > bridge/gw/gemini-1.json && python -I tools/gw.py gemini-1
python -I tools/orchestrate.py --dry-run
python -I tools/console.py --open          # optional: web UI on http://127.0.0.1:8765
python -I tools/agy_run.py ask "say ok"    # proves agy works and is logged in
```

Then run the first real task with `python -I tools/orchestrate.py --only T001` and read what happens in the console before scaling up.
