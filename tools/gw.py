#!/usr/bin/env python
"""Command gateway for headless agents.

Why: in print mode the agent CLI cannot run arbitrary shell, and its permission rules match the exact command string. So every
worker gets ONE fixed, pre-approved command, `python -I tools/gw.py <agent>`, which reads a JSON request the agent wrote with its
file tools and executes only a small whitelist of operations.

Protocol:
  1. write  bridge/gw/<agent>.json   e.g. {"op":"check","prefixes":["block","item"]}
  2. run    python -I tools/gw.py <agent>
  3. read   bridge/gw/<agent>.out (also printed)

Ops (everything else is refused):
  check    {"prefixes":[...], "max":30}                        scoped verification (tools/check.py)
  post     {"to":"claude","task":"T011","text":"..."}           chat message
  inbox    {}                                                   unread messages for this agent
  commit   {"task":"T011","message":"...","paths":[...]}        git add + commit; paths must match singularity.json -> commit_allow
  diffstat {}                                                   git diff --stat HEAD over the work dirs
  grep     {"pattern":"regex","path":"src/...","max":200}       read-only regex search under work_dirs / read_roots
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BRIDGE, CFG, PY, ROOT, p, tool  # noqa: E402

agent = sys.argv[1] if len(sys.argv) > 1 else ""
if not re.fullmatch(r"[a-z][a-z0-9]*-\d{1,2}", agent):
    sys.exit(f"usage: gw.py {CFG['worker_prefix']}-<n>")
gwdir = os.path.join(BRIDGE, "gw")
os.makedirs(gwdir, exist_ok=True)
reqp = os.path.join(gwdir, agent + ".json")
outp = os.path.join(gwdir, agent + ".out")


def run(cmd, timeout=1000):
    r = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    return r.stdout.strip() + f"\n[exit {r.returncode}]"


def ok_path(path):
    path = path.replace("\\", "/").lstrip("./")
    if ".." in path.split("/") or os.path.isabs(path):
        return False
    return any(path == a.rstrip("/") or (a.endswith("/") and path.startswith(a)) for a in CFG["commit_allow"])


def grep(pattern, path, mx):
    rx = re.compile(pattern)
    base = p(path)
    roots = [p(r) for r in CFG["work_dirs"] + CFG["read_roots"]]
    if not any(base == r or base.startswith(r + os.sep) for r in roots):
        return "refused: path must be under " + ", ".join(CFG["work_dirs"] + CFG["read_roots"])
    hits = []
    files = [base] if os.path.isfile(base) else [os.path.join(d, f) for d, _, fs in os.walk(base) for f in fs]
    for fp in files:
        try:
            lines = open(fp, encoding="utf-8", errors="replace").read().split("\n")
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            if rx.search(line):
                hits.append(f"{os.path.relpath(fp, ROOT)}:{i}: {line.strip()[:200]}")
                if len(hits) >= mx:
                    return "\n".join(hits) + f"\n... (stopped at {mx})"
    return "\n".join(hits) or "no matches"


try:
    req = json.load(open(reqp, encoding="utf-8-sig"))
    op = req.get("op")
    if op == "check":
        pf = [x for x in req.get("prefixes", []) if re.fullmatch(r"[\w/\-.]+", x)]
        out = run(PY + [tool("check.py")] + pf + ["--max", str(int(req.get("max", 30)))]) if pf else "no valid prefixes"
    elif op == "post":
        out = run(PY + [tool("chat.py"), "post", "--from", agent, "--to", str(req.get("to", CFG["orchestrator"])),
                        "--task", str(req.get("task", "")), str(req["text"])[:3500]])
    elif op == "inbox":
        out = run(PY + [tool("chat.py"), "inbox", agent])
    elif op == "diffstat":
        out = run(["git", "diff", "--stat", "HEAD", "--"] + CFG["work_dirs"])
    elif op == "commit":
        paths = req.get("paths", [])
        bad = [x for x in paths if not ok_path(x)]
        if bad or not paths:
            out = f"refused: paths outside allowed areas: {bad}"
        else:
            msg = f"{req.get('task', '')}: {req.get('message', '')}".strip()[:200]
            out = run(["git", "add", "--"] + paths) + "\n" + run(["git", "commit", "-q", "-m", msg, "--"] + paths)
    elif op == "grep":
        out = grep(str(req.get("pattern", "")), str(req.get("path", CFG["work_dirs"][0])), int(req.get("max", 200)))
    else:
        out = f"refused: unknown op {op!r}"
except Exception as e:  # report to the agent instead of crashing silently
    out = f"gateway error: {e}"
open(outp, "w", encoding="utf-8").write(out)
print(out)
