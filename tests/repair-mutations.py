#!/root/.venvs/mau/bin/python
"""Re-anchor a mutation harness's stale patterns, mechanically.

usage: repair_noop.py <target.py> <corrections.json>

corrections.json maps a mutant's label to its corrected pattern text:
    {"<label>": {"old": "<text the target file has NOW>",
                 "new": "<optional new replacement>"}, ...}

Why a tool: a sweep's anchors rot as the tree moves, and rewriting them by
hand is where a "repair" quietly changes what the mutant MEANS. This one
takes the resolved entry (through tests/preflight_probe.py, so tables built
from module constants work), swaps only the fields named in the correction,
splices the whole entry back as one plain literal at its exact AST span, and
refuses to write unless every corrected pattern matches its target file
EXACTLY ONCE - the same count==1 rule the sweeps themselves pre-check.
"""
import ast
import json
import os
import subprocess
import sys

PROBE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preflight_probe.py")


def probe_bad(script):
    r = subprocess.run([sys.executable, PROBE, script, "--dump"],
                       capture_output=True, text=True, timeout=60)
    line = [l for l in r.stdout.strip().splitlines() if l.startswith("{")][-1]
    return {b["label"]: b for b in json.loads(line).get("bad", [])}


def find_span(src, label):
    """The (start, end) source offsets of the list element whose text names
    this label. Elements are matched by the label's own quoted text, so a
    composed entry (constants, helper calls) still resolves."""
    tree = ast.parse(src)
    table = None
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign)
                and getattr(node.targets[0], "id", "") in
                ("MUTANTS", "MUTATIONS", "PATTERNS", "MUTANTS_LIST")
                and isinstance(node.value, ast.List) and node.value.elts):
            table = node.value
            break
    if table is None:
        raise SystemExit("no table in " + src)
    needle = "'" + label + "'"
    for el in table.elts:
        seg = ast.get_source_segment(src, el)
        if seg and (needle in seg or '"' + label + '"' in seg):
            return el.lineno, el.col_offset, el.end_lineno, el.end_col_offset
    return None


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    script, corrections_path = sys.argv[1], sys.argv[2]
    corrections = json.load(open(corrections_path, encoding="utf8"))
    bad = probe_bad(script)
    original = src = open(script, encoding="utf8").read()
    lines = src.split("\n")

    for label, fix in corrections.items():
        if label not in bad:
            print("SKIP (not stale now):", label)
            continue
        entry = list(bad[label]["entry"])
        target = bad[label]["path"]
        old = fix["old"]
        n = open(target, encoding="utf8").read().count(old)
        if n != 1:
            print("REFUSE %-52s pattern matches %d times in %s" % (label, n, target))
            continue
        entry[2] = old
        if "new" in fix:
            entry[3] = fix["new"]
        span = find_span(src, label)
        if span is None:
            print("REFUSE %-52s no source span found" % label)
            continue
        start = sum(len(l) + 1 for l in lines[:span[0] - 1]) + span[1]
        end = sum(len(l) + 1 for l in lines[:span[2] - 1]) + span[3]
        pretty = "[\n" + "".join(" " * 8 + repr(v) + ",\n" for v in entry) + " " * 4 + "]"
        src = src[:start] + pretty + src[end:]
        print("ok     %-52s anchored" % label)
        # offsets shifted with the splice; recompute for the next label
        lines = src.split("\n")

    if src != original:
        open(script, "w", encoding="utf8").write(src)
        print("\nwrote", script)
    else:
        print("\nnothing to change - file left byte-identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
