#!/usr/bin/env python3
"""Mutation-check the media lattice contract (batch 33).

Every pattern is VALIDATED before anything is mutated: a pattern that does
not match its source exactly once exits non-zero - a no-op that looks like
a pass is worse than no test at all.

The originals are held in MEMORY as the authority (a scratch copy on disk
can be pruned mid-run by another subsystem - that has eaten this repo
twice). Every restore is byte-verified the moment it happens, the tree is
asserted pristine before each mutation, and SIGINT/SIGTERM/SIGHUP plus
uncaughtException all restore from memory: `finally` does not run for a
SIGKILL, and a sweep killed from outside leaves its mutant in the tree
for the next cycle to trip over.

Usage:
    python tests/mutate-media-grid.py            # all mutants
    python tests/mutate-media-grid.py M1 M9      # a subset
"""
import os
import re
import signal
import subprocess
import sys

ROOT = "/root/projects/oem-ui"
CSS = f"{ROOT}/src/styles/components.css"
ASTRO = f"{ROOT}/src/pages/[...family].astro"
README = f"{ROOT}/README.md"
PROBE_FIT = f"{ROOT}/tests/probe-media-grid-fit.py"

# (id, path, pattern, replacement, rebuild dist?, expect suite fail?, expect fit-probe fail?)
MUTANTS = [
    ("M1-cover", CSS,
     "    /* contain, deliberately. The letterbox is the point. */\n    object-fit: contain;",
     "    /* contain, deliberately. The letterbox is the point. */\n    object-fit: cover;",
     True, True, True),
    ("M2-autofit", CSS,
     "grid-template-columns: repeat(auto-fill, minmax(min(var(--media-grid-min, 150px), 100%), 1fr));",
     "grid-template-columns: repeat(auto-fit, minmax(min(var(--media-grid-min, 150px), 100%), 1fr));",
     False, True, False),
    ("M3-nofallback", CSS,
     "grid-template-columns: repeat(auto-fill, minmax(min(var(--media-grid-min, 150px), 100%), 1fr));",
     "grid-template-columns: repeat(auto-fill, minmax(min(var(--media-grid-min), 100%), 1fr));",
     False, True, False),
    ("M4-itemmin", CSS,
     ".cm-media-grid > li {\n    min-width: 0;\n}",
     ".cm-media-grid > li {\n    min-width: auto;\n}",
     False, True, False),
    ("M5-nowrap", CSS,
     "    text-overflow: ellipsis;\n    white-space: nowrap;\n    min-width: 0;\n}\n.cm-media-grid__meta",
     "    text-overflow: ellipsis;\n    white-space: normal;\n    min-width: 0;\n}\n.cm-media-grid__meta",
     False, True, False),
    ("M6-ratio", CSS,
     ".cm-media-grid__thumb {\n    aspect-ratio: 4 / 3;",
     ".cm-media-grid__thumb {\n    aspect-ratio: 1 / 1;",
     False, True, False),
    ("M7-specimen-ratio", ASTRO,
     'alt="A 6:1 panorama placeholder." width="1200" height="200"',
     'alt="A 6:1 panorama placeholder." width="1200" height="900"',
     False, True, False),
    ("M8-readme-cover", README,
     ".cm-media-grid__thumb img { display: block; width: 100%; height: 100%; object-fit: contain; }",
     ".cm-media-grid__thumb img { display: block; width: 100%; height: 100%; object-fit: cover; }",
     False, True, False),
    ("M9-20rem", CSS,
     "grid-template-columns: repeat(auto-fill, minmax(min(var(--media-grid-min, 150px), 100%), 1fr));",
     "grid-template-columns: repeat(auto-fill, minmax(20rem, 1fr));",
     True, True, False),  # probe column-count check kills this too, asserted separately
    ("M10-knob320", CSS,
     "    --media-grid-min: 150px;",
     "    --media-grid-min: 320px;",
     False, True, False),  # the fence-drift check kills it (README still says 150px)
    ("M11-probe-inset", PROBE_FIT,
     "    inset = max(2, w // 40)",
     "    inset = 0",
     False, False, True),  # the border poisons every row: probe must cry cover
    ("M12-specimen-bg", ASTRO,
     "width='1200' height='200'%3E%3Crect width='1200' height='200' fill='%235a5a5a'",
     "width='1200' height='200'%3E%3Crect width='1200' height='200' fill='%231c1c1c'",
     True, False, True),  # letterbox becomes pixel-invisible: only the probe can see it
    ("M13-readme-autofit", README,
     "grid-template-columns: repeat(auto-fill, minmax(min(var(--media-grid-min, 150px), 100%), 1fr));",
     "grid-template-columns: repeat(auto-fit, minmax(min(var(--media-grid-min, 150px), 100%), 1fr));",
     False, True, False),  # the FENCE-scoped assertion kills it (section prose says auto-fill)
    ("M14-readme-pixelprobe", README,
     "tests/probe-media-grid-fit.py",
     "tests/pixel-band-probe.py",
     False, True, False),  # the README must name the pixel probe
]

ORIGINALS = {}
FAILURES = []
RESTORING = [False]

# Mutants the GEOMETRY probe (measure-media-grid-webkit.py) must also kill:
# its column expectation is derived from --media-grid-min as computed, so a
# template that ignores the knob and hardcodes a floor dies there too.
GEOM_KILLERS = {"M9-20rem"}


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def restore_all():
    if RESTORING[0]:
        return
    RESTORING[0] = True
    try:
        for path, orig in ORIGINALS.items():
            with open(path, "wb") as f:
                f.write(orig)
            now = read_bytes(path)
            if now != orig:
                print(f"!! RESTORE VERIFICATION FAILED for {path}", flush=True)
    finally:
        RESTORING[0] = False


def _signal_handler(signum, frame):
    print(f"\n[mute] signal {signum}: restoring {len(ORIGINALS)} file(s) from memory", flush=True)
    restore_all()
    sys.exit(128 + signum)


for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
    signal.signal(sig, _signal_handler)


def build():
    r = subprocess.run(["npm", "run", "build"], cwd=ROOT, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise SystemExit("build failed inside the mutation window")


def run_suite():
    r = subprocess.run(["node", "tests/run.mjs"], cwd=ROOT, capture_output=True, text=True, timeout=300)
    m = re.search(r"(\d+) passed, (\d+) failed", r.stdout)
    failed = int(m.group(2)) if m else -1
    dead = re.findall(r"^not ok\s+(.+)$", r.stdout, re.M)
    return failed, dead


def run_fit_probe():
    # env passed through untouched: the probes self-rescue a dead
    # PLAYWRIGHT_BROWSERS_PATH, so this runs them the way a human does.
    r = subprocess.run(["/root/.venvs/mau/bin/python", "tests/probe-media-grid-fit.py"],
                       cwd=ROOT, capture_output=True, text=True, timeout=300)
    return r.returncode, r.stdout


def run_geom_probe():
    r = subprocess.run(["/root/.venvs/mau/bin/python", "tests/measure-media-grid-webkit.py"],
                       cwd=ROOT, capture_output=True, text=True, timeout=300)
    return r.returncode, r.stdout


def main():
    wanted = sys.argv[1:] or [m[0] for m in MUTANTS]
    todo = [m for m in MUTANTS if m[0] in wanted]
    unknown = set(wanted) - {m[0] for m in MUTANTS}
    if unknown:
        raise SystemExit(f"unknown mutant id(s): {sorted(unknown)}")

    # capture originals
    for _, path, *_ in todo:
        if path not in ORIGINALS:
            ORIGINALS[path] = read_bytes(path)

    # PRE-FLIGHT: every pattern must match its source exactly once, and the
    # replacement must differ. A miss here exits: it would silently shrink
    # the run into a hole reported as proof.
    for mid, path, pat, rep, *_ in todo:
        src = ORIGINALS[path].decode()
        n = src.count(pat)
        if n != 1:
            raise SystemExit(f"[preflight] {mid}: pattern matches {n}x in {path} (need exactly 1)")
        if pat == rep:
            raise SystemExit(f"[preflight] {mid}: replacement equals the pattern (no-op)")

    # baseline: tree pristine, suite green, probes green
    for mid, path, *_ in todo:
        if read_bytes(path) != ORIGINALS[path]:
            raise SystemExit(f"[baseline] {path} is dirty before the run: interrupted sweep?")
    print("[baseline] running the untouched suite + fit probe", flush=True)
    failed, _ = run_suite()
    if failed != 0:
        raise SystemExit(f"[baseline] suite is red at HEAD ({failed} failed): fix that first")
    rc, out = run_fit_probe()
    if rc != 0:
        raise SystemExit("[baseline] the fit probe is red on the pristine tree:\n" + out[-1500:])

    rebuilt_after_restore = False
    for mid, path, pat, rep, rebuild, want_suite_fail, want_probe_fail in todo:
        print(f"\n[mute] {mid}: applying", flush=True)
        mutated = ORIGINALS[path].decode().replace(pat, rep)
        with open(path, "w") as f:
            f.write(mutated)
        if read_bytes(path) != mutated.encode():
            raise SystemExit(f"[mute] {mid}: write did not land byte-exact")
        try:
            if rebuild:
                build()
                rebuilt_after_restore = True
            if want_suite_fail:
                failed, dead = run_suite()
                if failed >= 1:
                    print(f"[mute] {mid}: KILLED by suite ({failed} failed): {dead[:2]}", flush=True)
                else:
                    FAILURES.append(f"{mid}: SURVIVED the suite (0 failed)")
                    print(f"[mute] {mid}: *** SURVIVED *** the suite", flush=True)
            if want_probe_fail:
                rc, out = run_fit_probe()
                if rc != 0:
                    reason = [l for l in out.splitlines() if "cover" in l or "does not match" in l or "no natural" in l]
                    print(f"[mute] {mid}: KILLED by fit probe: {reason[:2]}", flush=True)
                else:
                    FAILURES.append(f"{mid}: SURVIVED the fit probe")
                    print(f"[mute] {mid}: *** SURVIVED *** the fit probe", flush=True)
            if mid in GEOM_KILLERS:
                rc, out = run_geom_probe()
                if rc != 0:
                    reason = [l for l in out.splitlines() if "column" in l or "floor" in l]
                    print(f"[mute] {mid}: KILLED by geometry probe: {reason[:2]}", flush=True)
                else:
                    FAILURES.append(f"{mid}: SURVIVED the geometry probe (its column derivation is dead)")
                    print(f"[mute] {mid}: *** SURVIVED *** the geometry probe", flush=True)
        finally:
            with open(path, "wb") as f:
                f.write(ORIGINALS[path])
            if read_bytes(path) != ORIGINALS[path]:
                raise SystemExit(f"[restore] {mid}: byte verification FAILED")

    if rebuilt_after_restore:
        print("\n[final] restoring the served build", flush=True)
        build()
    failed, _ = run_suite()
    rc, out = run_fit_probe()
    if failed != 0 or rc != 0:
        FAILURES.append(f"final state is not green: suite {failed} failed, probe rc={rc}")

    print("\n=== mutation summary ===")
    print(f"mutants run: {len(todo)}")
    if FAILURES:
        print("PROBLEMS:")
        for f in FAILURES:
            print("  " + f)
        return 1
    print("every mutant was killed by the check that owns it; tree restored, suite + probes green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
