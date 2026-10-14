# AGENTS.md - read this first if you are an AI

This repository is **Singularity**: a file-based bridge that lets one *orchestrator* AI (e.g. Claude Code) delegate bulk work to
headless *worker* agents (Google Antigravity CLI `agy`, driving Gemini models) and review the results, while a human watches.
Everything is plain files + small Python scripts. No server, no database, no API keys.

Find your role, then read ONLY that document:

| You are... | Read |
|---|---|
| the **orchestrator** (Claude Code or similar: can run shell, owns review and merges) | [docs/ORCHESTRATOR.md](docs/ORCHESTRATOR.md) |
| a **worker agent** (launched headless by `agy -p`, cannot run shell except the gateway) | [docs/WORKER.md](docs/WORKER.md), then `bridge/RULES.md` and `bridge/GATEWAY.md` |
| a human or an AI asked to **set the bridge up** for a project | [docs/SETUP.md](docs/SETUP.md) |
| curious how it works | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |

Ground rules that apply to everyone:
1. **Never put secrets in this repository** (API keys, tokens, cookies, `agy` login state). The bridge needs none; `agy` keeps its own login.
2. **Workers' output is untrusted.** Compiling is not correctness. The orchestrator verifies every claim in the code before acting on it.
3. **Stay in scope.** A worker edits only the files of its claimed task; shared code is changed only by the orchestrator.
4. **State lives in files** (`bridge/TASKS.md`, `bridge/chat.jsonl`, `bridge/REPORT/`, git). If a process dies nothing is lost; rerun it.
5. Keep chat messages short; long material goes to `bridge/REPORT/<task>.md`.
