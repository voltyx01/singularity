#!/usr/bin/env python
"""Run ONE agent turn non-interactively and post the outcome to the chat bus (manual alternative to orchestrate.py).

usage (from the bridge root):
  python -I tools/agy_run.py T011                      # work on task T011 (prompt built from bridge/RULES.md)
  python -I tools/agy_run.py T011 --extra "focus on X first"
  python -I tools/agy_run.py ask "question for the agent"   # free-form, read-only
  options: --name gemini-1  --mode accept-edits|plan  --timeout 3000  --model <id>  --yolo

--yolo passes --dangerously-skip-permissions: use it ONLY for tasks whose blast radius is already fenced by RULES.md and git.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CFG, LOG_DIR, ROOT, chat_post, p, run_agent, worker_name  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("task")
ap.add_argument("text", nargs="*")
ap.add_argument("--name", default=worker_name(1))
ap.add_argument("--mode", default=None)
ap.add_argument("--timeout", type=int, default=3000)
ap.add_argument("--model")
ap.add_argument("--extra", default="")
ap.add_argument("--yolo", action="store_true")
a = ap.parse_args()
ORCH = CFG["orchestrator"]

if a.task == "ask":
    prompt = "You are a second engineer on this project. Answer briefly and to the point; do not change any files.\n\n" + " ".join(a.text)
    task = ""
    note = "Question: " + " ".join(a.text)
else:
    task = a.task
    rules = open(p(CFG["rules_file"]), encoding="utf-8").read()
    prompt = (f"Project folder: {ROOT}\nYou are agent {a.name}. Your task: {task} (a row in bridge/TASKS.md; set its status to CLAIMED {a.name}).\n\n"
              f"RULES:\n{rules}\n\nAsk the orchestrator through chat.py. When done, write bridge/REPORT/{task}.md and set the status to REVIEW.\n"
              + (f"Extra: {a.extra}\n" if a.extra else ""))
    note = f"Starting {a.name} on {task}" + (f" ({a.extra})" if a.extra else "") + f" [mode={'yolo' if a.yolo else (a.mode or CFG['agent']['mode'])}]"

t0 = time.time()
chat_post(ORCH, a.name, task, note)
r = run_agent(prompt, model=a.model, mode=a.mode, timeout=a.timeout, yolo=a.yolo)
out = r.stdout.strip()
os.makedirs(LOG_DIR, exist_ok=True)
open(os.path.join(LOG_DIR, f"agent-{a.task}-{time.strftime('%Y%m%d-%H%M%S')}.log"), "w", encoding="utf-8").write(out)
print(out)
chat_post(a.name, ORCH, task, f"[agent exit={r.returncode}, {int(time.time() - t0)}s] " + out[-3000:])
