"""Mutate each half of the decomp-sh parity guards and prove they can fail.

A guard that cannot fail is not a guard. This mutates the thing the guard
claims to protect, one half at a time, and asserts the suite goes RED.

The halves, and why each is mutated SEPARATELY:

  * the dropzone's DASHED rest frame - a mutation that solidifies it is
    the exact defect the component exists to avoid, and a guard that only
    checked "a rule exists" would let it through;
  * the dropzone's error edge, which must be INK and not a hue;
  * the parity manifest, whose target list must resolve to real RULES -
    deleting the rule a target points at has to fail, and the rule is
    deleted in the stylesheet, not in the manifest, because that is the
    direction that actually rots.

The comments in the stylesheet are stripped before each scan, so a mutation
that only removes a class NAME from a comment is correctly seen as a
no-op: it is prose, not a rule.
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path("/reiki/projects/oem-ui")
CSS = REPO / "src/styles/components.css"
MANIFEST = REPO / "docs/decomp-parity.json"


def run_suite() -> tuple[bool, str]:
    r = subprocess.run(
        ["node", "tests/run.mjs"],
        cwd=REPO, capture_output=True, text=True, timeout=600)
    out = r.stdout + r.stderr
    return r.returncode == 0, out


def css_without_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)),
                  text, flags=re.S)


def mutate_css(old: str, new: str) -> bool:
    src = CSS.read_text()
    if old not in src:
        return False
    CSS.write_text(src.replace(old, new, 1))
    return True


def main() -> int:
    baseline_ok, baseline_out = run_suite()
    if not baseline_ok:
        print("FAIL  the suite is not green before any mutation; a red baseline")
        print("      cannot prove a mutant is caught.")
        for line in baseline_out.splitlines()[-15:]:
            print("      " + line)
        return 1
    print("  ok  baseline is green")

    saved_css = CSS.read_text()
    saved_manifest = MANIFEST.read_text()
    failures = []
    tmpdir = tempfile.mkdtemp(prefix="oem-mutate-")
    survivors = 0
    mutants = 0

    try:
        # --- mutant 1: the dropzone's rest frame goes solid ---------------
        mutants += 1
        if mutate_css("\tborder: 1px dashed var(--line);\n\tborder-radius: var(--radius-sm);\n\tbackground: var(--panel);",
                      "\tborder: 1px solid var(--line);\n\tborder-radius: var(--radius-sm);\n\tbackground: var(--panel);"):
            ok, out = run_suite()
            if ok:
                survivors += 1
                failures.append("the dropzone's dashed rest frame can be solidified "
                                "and the suite stays green")
            else:
                print("  ok  mutant 1 killed: the rest frame is not dashed")
        else:
            failures.append("mutant 1 did not apply - the CSS text changed shape")
        CSS.write_text(saved_css)

        # --- mutant 2: the error edge takes a hue ------------------------
        mutants += 1
        if mutate_css(".cm-dropzone--err {\n\tborder-style: solid;\n\tborder-color: var(--ink);",
                      ".cm-dropzone--err {\n\tborder-style: solid;\n\tborder-color: #b00;"):
            ok, out = run_suite()
            if ok:
                survivors += 1
                failures.append("the dropzone's error edge can take a hue and the "
                                "suite stays green")
            else:
                print("  ok  mutant 2 killed: the error edge must be ink")
        else:
            failures.append("mutant 2 did not apply - the CSS text changed shape")
        CSS.write_text(saved_css)

        # --- mutant 3: a rule the manifest points at is deleted ----------
        # The manifest keeps naming a class whose rule is gone. The check
        # must fail on the UNRESOLVED TARGET, not on anything else.
        mutants += 1
        src = CSS.read_text()
        stripped = css_without_comments(src)
        m = re.search(r"\.cm-dropzone__note\s*\{[^}]*\}", stripped)
        if m:
            # remove the rule, keeping the comment block intact
            rule_text = m.group(0)
            comment_free_src = src
            idx = src.find(rule_text)
            if idx == -1:
                # the rule text in the file carries the original spacing
                idx = src.find(".cm-dropzone__note {")
                end = src.find("}", idx) + 1
                body = src[idx:end]
            else:
                body = rule_text
            CSS.write_text(src[:idx] + src[idx + len(body):])
            ok, out = run_suite()
            if ok:
                survivors += 1
                failures.append("a rule the parity manifest points at can be "
                                "deleted and the suite stays green")
            else:
                print("  ok  mutant 3 killed: a deleted rule breaks the manifest")
        else:
            failures.append("mutant 3 did not apply - .cm-dropzone__note is gone")
        CSS.write_text(saved_css)

        # --- mutant 4: the manifest loses a decomp-sh class --------------
        # The inventory and the mapping must be the same SET, so dropping
        # one from the mapping alone has to fail.
        #
        # Edited STRUCTURALLY, not by a string replace. The manifest is
        # written with indent=1, so the text is `"decomp": [\n "mono",`
        # and a replace on `"decomp": ["mono",` finds nothing - the
        # mutation silently does NOT apply, and the guard is never
        # exercised. A harness that cannot apply its own mutant proves
        # nothing, so the edit asserts that it changed something.
        mutants += 1
        manifest = json.loads(saved_manifest)
        removed = manifest["mapping"][0]["decomp"].pop(0)
        assert manifest["mapping"][0]["decomp"], "the mutation emptied a family"
        MANIFEST.write_text(json.dumps(manifest, indent=1))
        if MANIFEST.read_text() == saved_manifest:
            failures.append("mutant 4 did not apply - the manifest rewrite was a no-op")
        else:
            ok, out = run_suite()
            if ok:
                survivors += 1
                failures.append("a decomp-sh class can vanish from the mapping and "
                                "the suite stays green")
            else:
                print(f"  ok  mutant 4 killed: the inventory and the mapping must "
                      f"agree (dropped {removed!r})")
        MANIFEST.write_text(saved_manifest)

    finally:
        CSS.write_text(saved_css)
        MANIFEST.write_text(saved_manifest)
        shutil.rmtree(tmpdir, ignore_errors=True)

    if failures:
        print(f"\nFAIL  {survivors} of {mutants} mutants survived")
        for f in failures:
            print("  - " + f)
        return 1
    print(f"\nOK  {mutants} mutants, {mutants - survivors} killed, {survivors} survived")
    return 0


if __name__ == "__main__":
    sys.exit(main())
