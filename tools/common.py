"""Shared helpers: config loading, paths, task-board parsing. No third-party dependencies (Python 3.9+)."""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # the folder that holds tools/ and bridge/

DEFAULTS = {
    # Names used on the chat bus.
    "orchestrator": "claude",          # the reviewing / coordinating AI (Claude Code, ...)
    "worker_prefix": "gemini",         # worker agents are called <prefix>-1, <prefix>-2, ...
    # Layout, all relative to ROOT unless absolute.
    "bridge_dir": "bridge",
    "work_dirs": ["src"],              # where workers may edit files
    "read_roots": ["src"],             # extra read-only roots for the gateway `grep` op (e.g. a reference tree)
    "commit_allow": ["src/", "bridge/REPORT/", "bridge/TASKS.md", "bridge/REQUESTS.md"],
    # Verification: the command that compiles / tests the project; its output is parsed for errors.
    "check": {
        "cmd": ["echo", "configure check.cmd in singularity.json"],
        "error_regex": r"^(?P<file>[^:\n]+):(?P<line>\d+): error: (?P<msg>.*)$",
        "scope_root": "",              # stripped from the start of `file` before matching task prefixes
        "ok_marker": "",               # optional text that means 'whole project OK' (e.g. BUILD SUCCESSFUL)
        "timeout": 900,
        "env": {},
    },
    # The headless agent CLI (Google Antigravity: `agy`).
    "agent": {
        "cmd": "agy",
        "model": "",
        "mode": "accept-edits",
        "cwd": ".",                    # working directory of the agent process
        "add_dirs": [],                # extra directories the agent may see (repeatable --add-dir)
        "print_timeout": 2400,
        "quota_markers": ["RESOURCE_EXHAUSTED", "Individual quota reached"],
    },
    "rules_file": "bridge/RULES.md",
    "gateway_file": "bridge/GATEWAY.md",
    "audit_prompt_file": "bridge/AUDIT_PROMPT.md",
    "audit_units_file": "bridge/audit_units.json",
}


def _merge(base, over):
    out = dict(base)
    for k, v in over.items():
        out[k] = _merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def load_config():
    path = os.environ.get("SINGULARITY_CONFIG") or os.path.join(ROOT, "singularity.json")
    cfg = DEFAULTS
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8-sig") as f:
                cfg = _merge(DEFAULTS, json.load(f))
        except ValueError as e:
            sys.exit(f"{path}: invalid JSON ({e}). Remember to double every backslash in regexes: \\d, \\n.")
    return cfg


CFG = load_config()


def p(*parts):
    """Path under ROOT (absolute paths pass through)."""
    joined = os.path.join(*parts)
    return joined if os.path.isabs(joined) else os.path.normpath(os.path.join(ROOT, joined))


BRIDGE = p(CFG["bridge_dir"])
CHAT_LOG = os.path.join(BRIDGE, "chat.jsonl")
TASKS_FILE = os.path.join(BRIDGE, "TASKS.md")
LOG_DIR = os.path.join(BRIDGE, "logs")
PY = [sys.executable, "-I"]


def tool(name):
    return os.path.join(HERE, name)


def chat_post(frm, to, task, text):
    subprocess.run(PY + [tool("chat.py"), "post", "--from", frm, "--to", to, "--task", task, text[:3500]], check=False)


# ---- task board ------------------------------------------------------------------------------------------------------
# A markdown table whose header contains the columns Id, Scope, Owner, Status (extra columns are ignored).

def read_tasks():
    rows, cols = [], None
    if not os.path.exists(TASKS_FILE):
        return rows
    for ln in open(TASKS_FILE, encoding="utf-8"):
        if not ln.lstrip().startswith("|"):
            cols = None
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if cols is None:
            low = [c.lower() for c in cells]
            if "id" in low and "status" in low:
                cols = low
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        row = dict(zip(cols, cells))
        scope = row.get("scope", "").strip("`")
        rows.append({"id": row.get("id", ""), "scope": scope, "owner": row.get("owner", ""), "status": row.get("status", "")})
    return rows


def set_status(task_id, status):
    lines = open(TASKS_FILE, encoding="utf-8").read().split("\n")
    cols = None
    for i, ln in enumerate(lines):
        if not ln.lstrip().startswith("|"):
            cols = None
            continue
        cells = ln.strip().strip("|").split("|")
        low = [c.strip().lower() for c in cells]
        if cols is None:
            if "id" in low and "status" in low:
                cols = low
            continue
        if cells[cols.index("id")].strip() == task_id:
            cells[cols.index("status")] = " " + status + " "
            lines[i] = "|" + "|".join(cells) + "|"
    open(TASKS_FILE, "w", encoding="utf-8").write("\n".join(lines))


def quota_hit(text):
    return any(m in text for m in CFG["agent"]["quota_markers"])


def agent_command(prompt, model=None, mode=None, timeout=None, yolo=False):
    a = CFG["agent"]
    cmd = [a["cmd"], "-p", prompt, "--print-timeout", f"{timeout or a['print_timeout']}s"]
    for d in a["add_dirs"]:
        cmd += ["--add-dir", p(d)]
    m = model if model is not None else a["model"]
    if m:
        cmd += ["--model", m]
    cmd += ["--dangerously-skip-permissions"] if yolo else ["--mode", mode or a["mode"]]
    return cmd


def agent_cwd():
    return p(CFG["agent"]["cwd"])


def run_agent(prompt, **kw):
    return subprocess.run(agent_command(prompt, **kw), cwd=agent_cwd(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding="utf-8", errors="replace")


def worker_name(n):
    return f"{CFG['worker_prefix']}-{n}"
