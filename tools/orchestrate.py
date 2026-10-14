#!/usr/bin/env python
"""Unattended driver: runs worker agents over OPEN tasks, verifies them, escalates to the orchestrator AI through the chat bus.

  python -I tools/orchestrate.py [--workers 1] [--max-rounds 3] [--only T011,T012] [--dry-run] [--model M] [--first-id 1]

Per task (status OPEN in bridge/TASKS.md, Owner != the orchestrator):
  1. mark CLAIMED, run the agent with RULES.md + GATEWAY.md (+ bridge/notes/<task>.md if present)
  2. verify independently with tools/check.py <task scope>  (no trust in the agent's own claim)
  3. 0 errors -> status REVIEW (the orchestrator reviews the diff and report); errors -> retry up to --max-rounds with the error list;
     still failing -> status RETURNED + a chat message to the orchestrator.
Costs zero orchestrator tokens while it runs. Safe to stop/restart: all state is the TASKS.md table + git.
"""
import argparse
import os
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (BRIDGE, CFG, LOG_DIR, PY, ROOT, chat_post, p, quota_hit, read_tasks, run_agent, set_status, tool,  # noqa: E402
                    worker_name)

ap = argparse.ArgumentParser()
ap.add_argument("--workers", type=int, default=1)
ap.add_argument("--max-rounds", type=int, default=3)
ap.add_argument("--only", default="")
ap.add_argument("--timeout", type=int, default=CFG["agent"]["print_timeout"])
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--model", default=None)
ap.add_argument("--first-id", type=int, default=1, help="first agent number for this instance (run several instances side by side)")
a = ap.parse_args()
only = set(x for x in a.only.split(",") if x)
ORCH = CFG["orchestrator"]
os.makedirs(LOG_DIR, exist_ok=True)


def check(scope):
    r = subprocess.run(PY + [tool("check.py"), scope, "--max", "25"], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, encoding="utf-8", errors="replace")
    return r.returncode == 0, r.stdout


def read(path):
    path = p(path)
    return open(path, encoding="utf-8").read() if os.path.exists(path) else ""


def work(task, agent):
    tid, scope = task["id"], task["scope"]
    rules, gw = read(CFG["rules_file"]), read(CFG["gateway_file"])
    notes = read(os.path.join(BRIDGE, "notes", tid + ".md"))
    feedback = ""
    set_status(tid, f"CLAIMED {agent} {time.strftime('%m-%d')}")
    ok0, _ = check(scope)
    if ok0:
        set_status(tid, "REVIEW")
        chat_post(agent, ORCH, tid, f"{tid}: scope {scope} already verifies clean, agent not started (review against the original only).")
        return
    for rnd in range(1, a.max_rounds + 1):
        chat_post(ORCH, agent, tid, f"orchestrator: round {rnd}/{a.max_rounds} for {tid} ({scope})")
        prompt = (f"Project folder: {ROOT}. You are agent {agent}. Task {tid}: scope `{scope}`.\n\n"
                  f"RULES:\n{rules}\n\nCOMMANDS:\n{gw}\n\n"
                  f"When done, commit through the gateway and write bridge/REPORT/{tid}.md (what was done / what could not be done / doubts). "
                  f"Task statuses in TASKS.md are managed by the orchestrator - do not touch them.\n"
                  + (f"\nSPECIAL NOTES FOR THIS TASK:\n{notes}\n" if notes else "")
                  + (f"\nTHE PREVIOUS VERIFICATION FAILED, fix this:\n{feedback}\n" if feedback else ""))
        r = run_agent(prompt, model=a.model, timeout=a.timeout)
        open(os.path.join(LOG_DIR, f"agent-{tid}-r{rnd}.log"), "w", encoding="utf-8").write(r.stdout)
        if "no output produced" in r.stdout and "permission" in r.stdout:
            feedback = "The previous run was rejected: shell commands are not allowed; use ONLY the gateway (bridge/GATEWAY.md)."
        if quota_hit(r.stdout):
            set_status(tid, "OPEN")
            chat_post(agent, ORCH, tid, f"QUOTA: the model quota is exhausted ({a.model or 'default'}); orchestrator stops, {tid} is OPEN again.")
            os._exit(3)
        ok, out = check(scope)
        if ok:
            set_status(tid, "REVIEW")
            chat_post(agent, ORCH, tid, f"{tid} ready for review: 0 errors in {scope} (round {rnd}). Report: bridge/REPORT/{tid}.md")
            return
        feedback = out[-2500:]
    set_status(tid, "RETURNED")
    chat_post(agent, ORCH, tid, f"{tid} not delivered after {a.max_rounds} round(s), remaining errors:\n{feedback[-1500:]}")


def main():
    tasks = [t for t in read_tasks() if t["status"] == "OPEN" and t["owner"].lower() != ORCH and (not only or t["id"] in only)]
    print(f"{len(tasks)} OPEN tasks")
    if a.dry_run:
        for t in tasks:
            print(" ", t["id"], t["scope"])
        return
    q, qlock = list(tasks), threading.Lock()

    def worker(n):
        while True:
            with qlock:
                if not q:
                    return
                t = q.pop(0)
            work(t, worker_name(n + a.first_id - 1))

    ths = [threading.Thread(target=worker, args=(i + 1,)) for i in range(a.workers)]
    [t.start() for t in ths]
    [t.join() for t in ths]
    chat_post(ORCH, "user", "", f"orchestrator: queue empty ({len(tasks)} tasks processed)")


main()
