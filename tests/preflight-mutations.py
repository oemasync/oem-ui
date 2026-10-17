#!/root/.venvs/mau/bin/python
"""Preflight every mutation harness: test each (name, path, old, ...) pattern
against the file it targets and report the NO-OP count BEFORE a sweep spends
twenty minutes discovering it.

Read-only for the repo: nothing is written, no suite runs, no browser. Each
harness is inspected by tests/preflight_probe.py in its own subprocess, and
that probe blocks writes and subprocesses - so a harness without a __main__
guard cannot sweep the tree as a side effect of being read. That happened
once: two timed-out census runs started unguarded sweeps in parallel with a
queued sweep, and the leftover mutants cost a whole queue plus a re-run of
the sweep whose verdicts they invalidated.

A NO-OP is a harness whose pattern no longer matches the tree: the mutant
would "pass" without ever being applied. Fix those first; then the sweep
proves kills.

Usage: tests/preflight-mutations.py [glob ...]   (default: the whole fleet)
"""
import glob
import json
import os
import subprocess
import sys

PROBE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preflight_probe.py")


def main():
    pats = sys.argv[1:] or ["tests/mutate-*.py", "tests/mutate-*.mjs",
                            "tests/mutate-*.sh", "scripts/mutate-*.py",
                            "scripts/mutate-*.mjs"]
    files = sorted({f for p in pats for f in glob.glob(p)})
    total, skipped = 0, []
    for f in files:
        if not f.endswith(".py"):
            # The probe is Python: it reaches a table by executing the file.
            # A .mjs/.sh harness is not something it can read - say so rather
            # than reporting a parse error as if the harness were broken.
            skipped.append((f, "not a python harness - probe cannot read it; "
                               "its drift shows up in its own sweep (it pre-checks "
                               "each pattern) or in an explicit run"))
            continue
        rel = os.path.relpath(f, os.getcwd())
        try:
            r = subprocess.run([sys.executable, PROBE, rel],
                               capture_output=True, text=True, timeout=60)
            lines = [l for l in r.stdout.strip().splitlines() if l.startswith("{")]
            data = json.loads(lines[-1]) if lines else {}
        except subprocess.TimeoutExpired:
            data = {"skip": "probe timed out (60s)"}
        except Exception as e:
            data = {"skip": "%s: %s" % (type(e).__name__, e)}
        if "skip" in data:
            skipped.append((f, data["skip"]))
            continue
        rows = data.get("rows", [])
        if not rows:
            # A probe that read the table but produced no rows is broken, not
            # clean. The healthy case has its own row now, so this only fires
            # when the read itself failed.
            rows = [["(no rows read)", "BROKEN READ - the probe saw a table but reported nothing"]]
        not_a_finding = ("unclassified", "under-mutation (skipped)")
        # A verdict that begins with "ok" is a pass even when it carries a
        # note ("ok (2 matches, count-all sweep)"): counting it as a problem
        # made the fleet summary lie about two healthy sweeps.
        bad = [r for r in rows if not (str(r[1]).startswith("ok") or r[1] in not_a_finding)]
        unclassified = sum(1 for r in rows if r[1] not in ("under-mutation (skipped)",) and r[1] == "unclassified")
        mid = sum(1 for r in rows if r[1] == "under-mutation (skipped)")
        total += len(bad)
        tail = "all match" if not bad else "%d problem(s)" % len(bad)
        if unclassified:
            tail += " (%d unclassified)" % unclassified
        if mid:
            tail += " (%d mid-mutation, skipped - re-run when the sweep ends)" % mid
        print("%-4s %-34s %3d patterns  %s" % ("PASS" if not bad else "WARN",
                                               os.path.basename(f), len(rows), tail))
        for label, why in bad:
            print("        %-14s %s" % (why, label))
    for f, why in skipped:
        print("skip %-34s %s" % (os.path.basename(f), why))
    print("\n%d stale pattern(s) across %d harness(es)" % (total, len(files)))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
