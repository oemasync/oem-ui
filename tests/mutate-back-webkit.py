#!/root/.venvs/mau/bin/python
"""Mutation proof for the <Back> Astro wrapper (cm-back).

The wrapper's whole point is that the tap floor (44px on a coarse pointer)
lives in one rule owned by the library, not in a hand-written <a>. The
mutants below break that contract in the ways a consumer actually would:
delete the floor, hand-write the markup, drop the arrow's aria-hidden. Each
must make run.mjs fail. Mutations are applied ONE AT A TIME and restored
before the next, so a survivor is attributable to a single mutant.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN = ["/usr/bin/node", "tests/run.mjs"]

# (name, relpath, old, new, replace_all)
PATTERNS = [
    ("delete the coarse-pointer tap floor",
     "src/styles/components.css",
     "@media (pointer: coarse) {\n\t.cm-back { min-height: var(--tap); }\n}",
     "",
     False),
    ("drop the arrow's aria-hidden",
     "src/astro/Back.astro",
     'aria-hidden="true"',
     'aria-hidden="false"',
     False),
    ("revert the showcase to hand-written markup",
     "src/pages/[...family].astro",
     "<Back href=",
     '<a class="cm-back" href=',
     True),
]


def run_suite():
    p = subprocess.run(RUN, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def scan():
    bad = 0
    for name, rel, old, _new, _ra in PATTERNS:
        n = (ROOT / rel).read_text().count(old)
        print(f"scan: {name!r}: {n} occurrences")
        if n == 0:
            bad += 1
    return bad


def main():
    if "--scan" in sys.argv:
        sys.exit(scan())

    results = []
    for name, rel, old, new, ra in PATTERNS:
        path = ROOT / rel
        original = path.read_text()
        assert original.count(old) >= 1, f"{name}: pattern not found"
        mutated = original.replace(old, new) if ra else original.replace(old, new, 1)
        path.write_text(mutated)
        rc, out = run_suite()
        path.write_text(original)
        assert path.read_text() == original, f"restore failed for {rel}"
        killed = rc != 0
        results.append((name, killed, rc))
        print(f"\n=== {name} === rc={rc} killed={killed}")
        print(out[-600:])

    print("\n=== SUMMARY ===")
    all_killed = True
    for name, killed, rc in results:
        print(f"  {'KILL' if killed else 'SURVIVED'}  {name} (rc={rc})")
        all_killed = all_killed and killed
    sys.exit(0 if all_killed else 1)


if __name__ == "__main__":
    main()
