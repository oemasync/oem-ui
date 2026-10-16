#!/root/.venvs/mau/bin/python
"""Mutation proof for tests/verify-hovercard.py. Byte-snapshot restore,
rebuild each time because the harness reads dist."""
import pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CSS = 'src/styles/components.css'
JS = 'src/js/cli-mono.js'
PY = '/root/.venvs/mau/bin/python'
URL = sys.argv[1] if len(sys.argv) > 1 else 'http://192.168.1.68:4321/'

# (file, name, old, new) - `old` must occur EXACTLY once in that file, or
# the mutant is reported SKIP and the run exits red. A mutant that cannot
# be applied is a suite that is lying about what it proved.
MUTANTS = [
    (CSS, 'panel visible at rest (visibility gate gone)',
     '\topacity: 0;\n\tvisibility: hidden;\n\ttransform: translateY(-4px);',
     '\topacity: 0;\n\ttransform: translateY(-4px);'),
    (CSS, 'keyboard path dropped',
     '.cm-hovercard:focus-within .cm-hovercard__panel {',
     '.cm-hovercard__panel--unused {'),
    (CSS, 'hover path dropped',
     '.cm-hovercard:hover .cm-hovercard__panel,\n', ''),
    (CSS, 'seam doubles up (addon keeps its seam border)',
     '.cm-input-group > .cm-input-group__addon {\n\tborder-inline-end-width: 0;\n}\n',
     ''),
    (CSS, 'panel rounds its corners',
     '\theight: auto;\n\topacity: 0;',
     '\theight: auto;\n\tborder-radius: 50%;\n\topacity: 0;'),
    # ---- batch: hovercard as a profile card (the matrix roster) ----
    (CSS, 'composed card clips to its trigger (height rule returns)',
     '\theight: auto;\n\topacity: 0;', '\topacity: 0;'),
    (CSS, 'card sub stops wrapping unbroken tokens',
     '\toverflow-wrap: break-word;\n}\n.cm-card__body {', '}\n.cm-card__body {'),
    (CSS, 'hovercard row loses the row layout',
     '.cm-row.cm-hovercard {\n\tdisplay: flex;\n}\n', ''),
    (JS, 'reveal clamp dropped (pointerover+focusin)',
     "document.addEventListener('pointerover', reveal, { passive: true });\n\t\tdocument.addEventListener('focusin', reveal);", ''),
    (JS, 'late-row observer dropped',
     '}).observe(document.body, { childList: true, subtree: true });', '});'),
    (JS, 'Escape stops dismissing a focused card',
     "if (act && act.blur && act.closest && act.closest('.cm-hovercard')) act.blur();",
     'if (false && act && act.blur) act.blur();'),
]


def build():
    return subprocess.run(['npm', 'run', 'build'], cwd=ROOT, capture_output=True).returncode


snaps = {}
for rel in {m[0] for m in MUTANTS}:
    snaps[rel] = (ROOT / rel).read_bytes()

killed, survived, skipped = 0, [], 0
try:
    for rel, name, old, new in MUTANTS:
        path = ROOT / rel
        text = path.read_text()
        if text.count(old) != 1:
            print('SKIP     %-46s (pattern x%d)' % (name, text.count(old)))
            skipped += 1
            continue
        path.write_text(text.replace(old, new, 1))
        build()
        r = subprocess.run([PY, str(ROOT / 'tests/verify-hovercard.py'), URL],
                           capture_output=True, text=True, env=None)
        fails = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith('FAIL')]
        if r.returncode != 0:
            print('KILLED   %-46s %s' % (name, (fails[0] if fails else '(crashed)')[:80]))
            killed += 1
        else:
            print('SURVIVED %s' % name)
            survived.append(name)
        path.write_bytes(snaps[rel])
finally:
    for rel, snap in snaps.items():
        (ROOT / rel).write_bytes(snap)
    build()

total = len(MUTANTS) - skipped
print('\n%d/%d mutants killed, %d skipped' % (killed, total, skipped))
sys.exit(1 if survived or skipped else 0)
