#!/usr/bin/env python
"""Scoped verification for parallel agents.

usage (from the bridge root):  python -I tools/check.py <scope prefix> [...] [--max N] [-r]

Runs the project's check command (singularity.json -> check.cmd; serialised across agents with a lock file), parses the output
with check.error_regex (named groups: file, line, msg) and prints only the errors that belong to the given scope prefixes.
`file` has check.scope_root stripped from its start; a prefix matches files DIRECTLY in that directory (sub-directories are other
scopes) unless -r is given. Exit code 0 = no errors in scope. The full log is kept in bridge/logs/.
"""
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CFG, LOG_DIR, BRIDGE, ROOT  # noqa: E402

args = sys.argv[1:]
maxn = 40
if "--max" in args:
    i = args.index("--max")
    maxn = int(args[i + 1])
    del args[i:i + 2]
recursive = "-r" in args
args = [a for a in args if a != "-r"]
prefixes = [a.strip("/\\").replace("\\", "/") for a in args]
if not prefixes:
    sys.exit("give at least one scope prefix")

c = CFG["check"]
os.makedirs(LOG_DIR, exist_ok=True)
lock = os.path.join(BRIDGE, ".check.lock")
t0 = time.time()
while True:
    try:
        os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        break
    except FileExistsError:
        if time.time() - os.path.getmtime(lock) > c["timeout"] + 60:  # stale
            os.remove(lock)
            continue
        if time.time() - t0 > 900:
            sys.exit("timeout waiting for the check lock")
        time.sleep(3)

env = dict(os.environ)
env.update(c.get("env", {}))
try:
    log = subprocess.run(c["cmd"], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         errors="replace", timeout=c["timeout"], shell=isinstance(c["cmd"], str)).stdout
finally:
    if os.path.exists(lock):
        os.remove(lock)
open(os.path.join(LOG_DIR, time.strftime("%Y%m%d-%H%M%S") + ".log"), "w", encoding="utf-8").write(log)

rx = re.compile(c["error_regex"])
scope_root = c["scope_root"].replace("\\", "/").strip("/")
lines = log.split("\n")
total = shown = 0
for i, ln in enumerate(lines):
    m = rx.match(ln.rstrip("\r"))
    if not m:
        continue
    rel = m.group("file").replace("\\", "/")
    if scope_root and scope_root + "/" in rel:
        rel = rel.split(scope_root + "/", 1)[1]
    rel_dir = rel.rsplit("/", 1)[0] if "/" in rel else ""
    if not any((rel.startswith(p) if recursive else (rel == p or rel_dir == p)) for p in prefixes):
        continue
    total += 1
    if shown < maxn:
        shown += 1
        ctx = " | ".join(x.strip() for x in lines[i + 1:i + 4] if x.strip())
        print(f"{rel}:{m.group('line')}: {m.group('msg')}   {ctx[:200]}")
print(f"ERRORS in scope {prefixes}: {total}")
if c["ok_marker"] and c["ok_marker"] in log:
    print("whole project OK")
sys.exit(0 if total == 0 else 1)
