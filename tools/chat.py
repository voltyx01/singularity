#!/usr/bin/env python
"""File-based message bus between the orchestrator AI, worker agents and you.  Log: bridge/chat.jsonl (append-only).

  python -I tools/chat.py post --from gemini-1 --to claude --task T011 "can't find the super constructor, what now?"
  python -I tools/chat.py read [--to NAME] [--task T011] [--last 20] [--since ID]
  python -I tools/chat.py watch [--to NAME]        # live feed: run it in a spare terminal (or under Claude Code's Monitor tool)
  python -I tools/chat.py inbox NAME               # unread messages addressed to NAME (or 'all'); marks them read

Names: the orchestrator (default `claude`), `<worker_prefix>-<n>`, `user`, or `all`. Keep messages short; put long material
in bridge/REPORT/<task>.md and link it.  Set CHAT_INBOUND_ONLY=1 with `watch --to NAME` to see only messages TO that name.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BRIDGE, CFG, CHAT_LOG as LOG  # noqa: E402

READ_DIR = os.path.join(BRIDGE, ".read")
os.makedirs(BRIDGE, exist_ok=True)
COLORS = {CFG["orchestrator"]: "\033[38;5;208m", "user": "\033[38;5;111m"}


def load():
    out = []
    if os.path.exists(LOG):
        with open(LOG, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if ln:
                    try:
                        out.append(json.loads(ln))
                    except ValueError:
                        pass
    return out


def post(frm, to, task, text):
    msgs = load()
    mid = (msgs[-1]["id"] + 1) if msgs else 1
    m = {"id": mid, "ts": time.strftime("%Y-%m-%d %H:%M:%S"), "from": frm, "to": to, "task": task, "text": text}
    with open(LOG, "a", encoding="utf-8") as f:  # one write call per line keeps concurrent appends from interleaving
        f.write(json.dumps(m, ensure_ascii=False) + "\n")
    return m


def fmt(m, color=True):
    c = COLORS.get(m["from"], "\033[38;5;114m") if color else ""
    r = "\033[0m" if color else ""
    t = f" [{m['task']}]" if m.get("task") else ""
    return f"{c}#{m['id']} {m['ts'][11:]} {m['from']} -> {m['to']}{t}{r}\n    " + m["text"].replace("\n", "\n    ")


def addressed(m, name):
    return m["to"] in (name, "all") or m["from"] == name


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("post")
    pp.add_argument("--from", dest="frm", required=True)
    pp.add_argument("--to", default=CFG["orchestrator"])
    pp.add_argument("--task", default="")
    pp.add_argument("text", nargs="+")
    r = sub.add_parser("read")
    r.add_argument("--to")
    r.add_argument("--task")
    r.add_argument("--last", type=int, default=30)
    r.add_argument("--since", type=int, default=0)
    w = sub.add_parser("watch")
    w.add_argument("--to")
    i = sub.add_parser("inbox")
    i.add_argument("name")
    a = ap.parse_args()

    if a.cmd == "post":
        m = post(a.frm, a.to, a.task, " ".join(a.text))
        print(f"posted #{m['id']}")
    elif a.cmd == "read":
        ms = [m for m in load() if m["id"] > a.since]
        if a.to:
            ms = [m for m in ms if addressed(m, a.to)]
        if a.task:
            ms = [m for m in ms if m.get("task") == a.task]
        for m in ms[-a.last:]:
            print(fmt(m, sys.stdout.isatty()))
    elif a.cmd == "inbox":
        os.makedirs(READ_DIR, exist_ok=True)
        mark = os.path.join(READ_DIR, a.name)
        last = int(open(mark).read() or 0) if os.path.exists(mark) else 0
        allm = load()
        ms = [m for m in allm if m["id"] > last and m["to"] in (a.name, "all") and m["from"] != a.name]
        for m in ms:
            print(fmt(m, False))
        if not ms:
            print("(no new messages)")
        if allm:
            open(mark, "w").write(str(allm[-1]["id"]))
    elif a.cmd == "watch":
        seen = 0
        print(f"watching {LOG} (Ctrl+C to stop)", flush=True)
        while True:
            for m in load():
                if m["id"] > seen:
                    seen = m["id"]
                    if not a.to or addressed(m, a.to):
                        if os.environ.get("CHAT_INBOUND_ONLY") and (m["from"] == a.to or m["to"] not in (a.to, "all")):
                            continue
                        print(fmt(m, sys.stdout.isatty()), flush=True)
            time.sleep(1.0)


main()
