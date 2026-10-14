#!/usr/bin/env python
"""Read-only audit with worker agents: one agent per unit, one report per unit in bridge/REPORT/AUDIT-<unit>.md.

usage: python -I tools/audit.py [--workers 4] [--only unit1,unit2] [--model M]   (skips units whose report already exists)

Units come from bridge/audit_units.json: {"unit-name": ["dir/one", "dir/two"], ...}. The prompt is bridge/AUDIT_PROMPT.md plus the
unit scope. Agents are read-only by contract: they may only write their report, and may search code only through the gateway.
Findings are NOT trusted: the orchestrator must verify each one in the code before changing anything.
"""
import argparse
import json
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CFG, LOG_DIR, ROOT, BRIDGE, p, quota_hit, run_agent, worker_name  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--workers", type=int, default=4)
ap.add_argument("--only", default="")
ap.add_argument("--model", default=None)
ap.add_argument("--timeout", type=int, default=3600)
a = ap.parse_args()

if not os.path.exists(p(CFG["audit_units_file"])):
    sys.exit(f"missing {CFG['audit_units_file']}: copy bridge/audit_units.example.json and list your units")
units = json.load(open(p(CFG["audit_units_file"]), encoding="utf-8-sig"))
prompt_base = open(p(CFG["audit_prompt_file"]), encoding="utf-8").read()
only = set(filter(None, a.only.split(",")))
report_dir = os.path.join(BRIDGE, "REPORT")
os.makedirs(report_dir, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
q = [u for u in units if (not only or u in only) and not os.path.exists(os.path.join(report_dir, f"AUDIT-{u}.md"))]
lock, quota = threading.Lock(), threading.Event()


def run(unit, agent):
    dirs = ", ".join("`" + d + "`" for d in units[unit])
    prompt = (f"Working folder: {ROOT}.\n\n{prompt_base}\n\n## Your scope\nUnit: `{unit}`. Dirs: {dirs}. "
              f"Report file: `bridge/REPORT/AUDIT-{unit}.md`.\n\n"
              f"## Searching code\nThe ONLY command you may run is exactly `python -I tools/gw.py {agent}` from the project folder. "
              f"Before running it, write the request file `bridge/gw/{agent}.json`, e.g. "
              '`{"op":"grep","pattern":"someRegex","path":"src"}`; the result is printed and saved in '
              f"`bridge/gw/{agent}.out`. Any other command aborts your run.")
    r = None
    for _ in range(2):
        r = run_agent(prompt, model=a.model, timeout=a.timeout)
        open(os.path.join(LOG_DIR, f"audit-{unit}.log"), "w", encoding="utf-8").write(r.stdout)
        if "no output produced" not in r.stdout:
            break
        prompt += ("\n\nYOUR PREVIOUS RUN WAS ABORTED because you tried to run a shell command. Do not run any command; "
                   "use only the built-in file list/search/read/write tools.")
    if quota_hit(r.stdout):
        quota.set()
    done = os.path.exists(os.path.join(report_dir, f"AUDIT-{unit}.md"))
    print(f'{unit}: {"report written" if done else "NO REPORT"}', flush=True)


def worker(n):
    while not quota.is_set():
        with lock:
            if not q:
                return
            u = q.pop(0)
        run(u, worker_name(n))


print(f"{len(q)} units", flush=True)
ths = [threading.Thread(target=worker, args=(i + 1,)) for i in range(a.workers)]
[t.start() for t in ths]
[t.join() for t in ths]
print("QUOTA EXHAUSTED, rerun later to continue" if quota.is_set() else "all done", flush=True)
