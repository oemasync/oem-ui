#!/root/.venvs/mau/bin/python
"""Preflight every mutation harness that exposes a static table: test each
(name, path, old, ...) pattern against the file it targets and report the
NO-OP count BEFORE a sweep spends twenty minutes discovering it.

Read-only for the repo: nothing is written, no suite runs, no browser. Each
harness is loaded in its OWN subprocess under a timeout, so a script that
does slow work at import time cannot stall the census - it is reported as a
skip instead.

A NO-OP is a harness whose pattern no longer matches the tree: the mutant
would "pass" without ever being applied. Fix those first; then the sweep
proves kills.

Usage: tests/preflight-mutations.py [glob ...]   (default: the whole fleet)
"""
import glob, subprocess, sys, os

CHECK = r'''
import importlib.util, os, sys, json
path = sys.argv[2]
spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
m = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(m)
except SystemExit:
    pass
table = None
for a in ("MUTATIONS", "MUTANTS", "MUTANTS_LIST"):
    t = getattr(m, a, None)
    if isinstance(t, list) and t:
        table = t
        break
if table is None:
    print(json.dumps({"skip": "no static table"})); raise SystemExit(0)
import os
repo = os.getcwd()
rows = []
for e in table:
    if not isinstance(e, (list, tuple)) or len(e) < 3:
        continue
    name, cand, old = e[0], e[1], e[2]
    # Tables come in several shapes. Only judge an entry when its second
    # element names a file that EXISTS - otherwise the table is
    # (name, old, new, expect, tag) shaped and this census cannot resolve
    # it. Unresolvable entries are counted, never called stale.
    if not isinstance(cand, str) or not isinstance(old, str) or not os.path.isfile(cand):
        rows.append([str(name), "unclassified"]); continue
    if not os.path.abspath(cand).startswith(repo + os.sep):
        rows.append([str(name), "WRONG-TREE " + cand]); continue
    try:
        src = open(cand, encoding="utf8").read()
    except OSError:
        rows.append([str(name), "unreadable " + cand]); continue
    if old not in src:
        rows.append([str(name), "NO-OP"])
print(json.dumps({"rows": rows}))
'''

def main():
    pats = sys.argv[1:] or ["tests/mutate-*.py", "scripts/mutate-*.py"]
    files = [f for p in pats for f in sorted(glob.glob(p))]
    total = 0
    import json
    for f in files:
        # Only import a script that has a __main__ guard: without one,
        # importing RUNS it, and running a mutation sweep as a side effect
        # of a census is exactly the kind of interference this tool exists
        # to prevent.
        src = open(f, encoding="utf8").read()
        if "__main__" not in src:
            print("skip %-34s no __main__ guard - never imported" % os.path.basename(f)); continue
        try:
            r = subprocess.run([sys.executable, "-c", CHECK, "-", f],
                               capture_output=True, text=True, timeout=30)
            data = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else {}
        except subprocess.TimeoutExpired:
            data = {"skip": "import slower than 30s"}
        except Exception as e:
            data = {"skip": "%s: %s" % (type(e).__name__, e)}
        if "skip" in data:
            print("skip %-34s %s" % (os.path.basename(f), data["skip"])); continue
        rows = data.get("rows", [])
        bad = [r for r in rows if r[1] not in ("unclassified",)]
        skipped_n = sum(1 for r in rows if r[1] == "unclassified")
        total += len(bad)
        tail = "all match" if not bad else "%d problem(s)" % len(bad)
        if skipped_n:
            tail += " (%d unclassified)" % skipped_n
        print("%-4s %-34s %3d patterns  %s" % ("PASS" if not bad else "WARN",
              os.path.basename(f), len(rows), tail))
        for name, why in bad:
            print("        %-14s %s" % (why, name))
    print("\n%d stale pattern(s) across %d harness(es)" % (total, len(files)))
    return 1 if total else 0

if __name__ == "__main__":
    sys.exit(main())
