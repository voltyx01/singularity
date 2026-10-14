#!/usr/bin/env python
"""Wait for the agent quota to come back, then run the orchestrator automatically (zero orchestrator-AI tokens).
usage: python -I tools/auto_resume.py [--workers 4] [--poll 600] [--model M]   (runs until the queue is empty)"""
import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PY, ROOT, chat_post, quota_hit, run_agent, tool  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--workers", type=int, default=4)
ap.add_argument("--poll", type=int, default=600)
ap.add_argument("--model", default=None)
a = ap.parse_args()


def say(text):
    chat_post("auto-resume", "user", "", text)


def quota_ok():
    try:
        r = run_agent("reply with one word: ok", model=a.model, timeout=300)
    except Exception as e:  # noqa: BLE001
        return False
    return not quota_hit(r.stdout) and "quota" not in r.stdout.lower()


say(f"auto-resume: waiting for the quota to come back, polling every {a.poll // 60} min.")
while not quota_ok():
    time.sleep(a.poll)
say("auto-resume: quota is back, starting the orchestrator.")
while True:
    cmd = PY + [tool("orchestrate.py"), "--workers", str(a.workers), "--max-rounds", "3"] + (["--model", a.model] if a.model else [])
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode == 3:  # quota exhausted again
        say("auto-resume: quota exhausted again, waiting.")
        time.sleep(a.poll)
        while not quota_ok():
            time.sleep(a.poll)
        continue
    break
say("auto-resume: the orchestrator finished the queue.")
