#!/usr/bin/env python3
"""mutate-no-hardcoded-colors.py - prove the guard can fail.

Reintroduces each of the two literals that were fixed and asserts the
guard goes red, then restores and asserts green.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSS = os.path.join(ROOT, "src", "styles", "components.css")
GUARD = os.path.join(HERE, "verify-no-hardcoded-colors.py")

# (the exact line to reintroduce, the literal to put back)
MUTANTS = [
    ("\tbackground: var(--scrim);", "\tbackground: rgb(0 0 0 / 0.55);"),
    ("\tbox-shadow: 0 8px 24px -18px var(--shadow-ink);",
     "\tbox-shadow: 0 8px 24px -18px rgba(0, 0, 0, 0.9);"),
]


def run_guard():
    p = subprocess.run([sys.executable, GUARD], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    backup = CSS + ".mutbak"
    shutil.copy2(CSS, backup)
    original = open(CSS, encoding="utf-8").read()
    rc, out = run_guard()
    if rc != 0:
        print("FAIL: guard is red on the CURRENT stylesheets")
        print(out)
        shutil.copy2(backup, CSS)
        os.remove(backup)
        return 1
    print("baseline: guard GREEN")

    bad = 0
    try:
        for good, mutant in MUTANTS:
            if good not in original:
                print("FAIL: anchor not found: %r" % good[:50])
                bad += 1
                continue
            open(CSS, "w", encoding="utf-8").write(
                original.replace(good, mutant, 1))
            rc, out = run_guard()
            if rc == 0:
                print("FAIL: guard stayed GREEN with %r" % mutant.strip()[:50])
                bad += 1
            else:
                print("mutant %-46s : guard RED (correct)" % mutant.strip()[:46])
    finally:
        shutil.copy2(backup, CSS)
        os.remove(backup)

    rc, out = run_guard()
    if rc != 0:
        print("FAIL: guard red after restore")
        print(out)
        return 1
    print("restore : guard GREEN again")
    if bad:
        return 1
    print("MUTATION: OK (guard fails on both reintroduced literals)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
