#!/usr/bin/env python3
"""mutate-chart-contrast.py - prove the guard can fail.

A guard that has never been seen red is not a guard. This flips each
chart tone in turn back to its PRE-FIX value and asserts the guard
fails, then restores the file and asserts it passes.
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOKENS = os.path.join(ROOT, "src", "styles", "tokens.css")
GUARD = os.path.join(HERE, "verify-chart-contrast.py")

# the value each tone had before the fix, in the dark ramp
OLD = {
    "chart-c3": "#8a8a8a",
    "chart-c4": "#6b6b6b",
    "chart-c5": "#525252",
}


def run_guard():
    p = subprocess.run([sys.executable, GUARD], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    backup = TOKENS + ".mutbak"
    shutil.copy2(TOKENS, backup)
    original = open(TOKENS, encoding="utf-8").read()
    rc, out = run_guard()
    if rc != 0:
        print("FAIL: guard is red on the CURRENT tokens (should be green)")
        print(out)
        shutil.copy2(backup, TOKENS)
        os.remove(backup)
        return 1
    print("baseline: guard GREEN on current tokens")

    bad = 0
    try:
        for token, oldval in OLD.items():
            # mutate only the DARK ramp (first occurrence of the token)
            idx = original.index("--%s:" % token)
            end = original.index(";", idx)
            line = original[idx:end]
            mutated = line.replace(oldval, "#525252" if token == "chart-c5" else oldval)
            if token == "chart-c5":
                mutated = line.replace(oldval, "#525252")
            if mutated == line:
                # already the old value in this copy; find the new one instead
                new = {"chart-c3": "#8c8c8c", "chart-c4": "#787878",
                       "chart-c5": "#666666"}[token]
                mutated = line.replace(new, oldval)
            open(TOKENS, "w", encoding="utf-8").write(
                original[:idx] + mutated + original[end:])
            rc, out = run_guard()
            if rc == 0:
                print("FAIL: guard stayed GREEN with %s reverted to %s"
                      % (token, oldval))
                bad += 1
            else:
                print("mutant %-9s -> %-8s : guard RED (correct)" % (
                    token, oldval))
    finally:
        shutil.copy2(backup, TOKENS)
        os.remove(backup)

    rc, out = run_guard()
    if rc != 0:
        print("FAIL: guard red after restore")
        print(out)
        return 1
    print("restore : guard GREEN again")

    if bad:
        return 1
    print("MUTATION: OK (guard fails on every reverted tone)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
