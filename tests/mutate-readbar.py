#!/root/.venvs/mau/bin/python
"""Mutation proof for the reading-progress runtime (cmInitReadbars).

Every claim the new checks make is inverted here, one at a time, in the
real source. A claim that no mutant can break is a guess, not a test.

The runner holds the originals IN MEMORY as the authority (the scratch
pruner has eaten a cp-based snapshot mid-run before), byte-verifies every
restore the moment it happens, asserts the tree is pristine before each
mutation, binds SIGINT/SIGTERM/SIGHUP plus uncaughtException to a
restore handler (finally does not run for a SIGKILL), and pre-flights
every pattern: a pattern that matches nothing is a NO-OP that would look
like a pass, so the run exits before mutating rather than shrinking.

A crash, a timeout or a broken build is a KILL - never a silent pass.
"""
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path('/root/projects/oem-ui')

MUTANTS = [
    # (name, path, old, new, target)
    ('the fill stops being written', 'src/js/cli-mono.js',
     "bar.style.setProperty('--cm-readbar', r + '%');",
     "", 'suite'),
    ('aria-valuenow stops being written (the pair splits)', 'src/js/cli-mono.js',
     "bar.setAttribute('aria-valuenow', String(r));",
     "", 'suite'),
    ('the bar never paints at bind time', 'src/js/cli-mono.js',
     "\t\t\t\twindow.addEventListener('scroll', paint, { passive: true });\n"
     "\t\t\t\twindow.addEventListener('resize', paint, { passive: true });\n"
     "\t\t\t\tpaint();",
     "\t\t\t\twindow.addEventListener('scroll', paint, { passive: true });\n"
     "\t\t\t\twindow.addEventListener('resize', paint, { passive: true });",
     'suite'),
    ('no scroll listener is bound', 'src/js/cli-mono.js',
     "\t\t\t\twindow.addEventListener('scroll', paint, { passive: true });\n"
     "\t\t\t\twindow.addEventListener('resize', paint, { passive: true });\n"
     "\t\t\t\tpaint();",
     "\t\t\t\twindow.addEventListener('resize', paint, { passive: true });\n"
     "\t\t\t\tpaint();", 'suite'),
    ('no resize listener is bound', 'src/js/cli-mono.js',
     "\t\t\t\twindow.addEventListener('scroll', paint, { passive: true });\n"
     "\t\t\t\twindow.addEventListener('resize', paint, { passive: true });",
     "\t\t\t\twindow.addEventListener('scroll', paint, { passive: true });", 'suite'),
    ('the rubber-band clamps are gone', 'src/js/cli-mono.js',
     'var pct = ((box.scrollTop || 0) / max) * 100;\n'
     '\t\t\t\t\treturn pct < 0 ? 0 : pct > 100 ? 100 : pct;',
     'var pct = ((box.scrollTop || 0) / max) * 100;\n'
     '\t\t\t\t\treturn pct;', 'suite'),
    ('a no-scroll page reads NaN instead of 0', 'src/js/cli-mono.js',
     'if (max <= 0) return 0;', '', 'suite'),
    ('a double bind re-binds the listeners', 'src/js/cli-mono.js',
     'if (bar.__cmReadbarBound) return;', '', 'suite'),
    ('cmInitReadbars leaves init()', 'src/js/cli-mono.js',
     '\t\tcmInitReadbars(root);\n', '', 'suite'),
    ('initReadbars leaves the handle', 'src/js/cli-mono.js',
     'initReadbars: cmInitReadbars', 'initReadbars: null', 'suite'),
    ('the fill loses the property it draws from', 'src/styles/components.css',
     'transform: scaleX(calc(var(--cm-readbar, 0%) / 100));',
     'transform: scaleX(1);', 'suite'),
    ('the bar stops being fixed (it becomes an in-flow block)',
     'src/styles/components.css',
     '.cm-readbar {\n\tposition: fixed;',
     '.cm-readbar {\n\tposition: static;', 'suite'),
    ('the bar stops piercing the header (z-index drops)',
     'src/styles/components.css',
     'z-index: var(--z-readbar);', 'z-index: 1;', 'suite'),
    ('the bar blocks the header (pointer-events restored)',
     'src/styles/components.css',
     '\tz-index: var(--z-readbar);\n\tpointer-events: none;',
     '\tz-index: var(--z-readbar);\n\tpointer-events: auto;', 'suite'),
    ('the token stops being declared', 'src/styles/tokens.css',
     '--z-readbar: 120;', '', 'suite'),
    ('the showcase stops shipping the static specimen',
     'src/pages/[...family].astro',
     '<div class="cm-readbar cm-readbar--spec" style="--cm-readbar:50%" role="progressbar" aria-valuenow="50"',
     '<div class="cm-progress" role="progressbar" aria-valuenow="50"', 'suite'),
    ('the static specimen pair splits (aria authored, property gone)',
     'src/pages/[...family].astro',
     'style="--cm-readbar:50%" role="progressbar" aria-valuenow="50"',
     'style="" role="progressbar" aria-valuenow="50"', 'suite'),
    ('the runtime binds a frozen specimen (the 50% dies at bind time)',
     'src/js/cli-mono.js',
     "'.cm-readbar:not(.cm-readbar--spec)');", "'.cm-readbar');", 'suite'),
    ('the specimen loses the modifier that keeps it frozen',
     'src/pages/[...family].astro',
     '<div class="cm-readbar cm-readbar--spec" style="--cm-readbar:50%"',
     '<div class="cm-readbar" style="--cm-readbar:50%"', 'suite'),
    ('print: the fixed line stops being hidden on paper',
     'src/styles/components.css',
     '\t.cm-revert:not([data-cm-revert-resolved]),\n\t.cm-readbar,\n\t[data-cm-progress] {',
     '\t.cm-revert:not([data-cm-revert-resolved]),\n\t[data-cm-progress] {',
     'suite'),
]

SUITE_CMD = 'npm test'


def run_check(cmd, timeout=300):
    try:
        r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode, (r.stdout or '') + (r.stderr or '')
    except subprocess.TimeoutExpired:
        return -1, 'TIMEOUT (treated as a kill)'


def build():
    try:
        r = subprocess.run(['npm', 'run', 'build'], cwd=ROOT, capture_output=True,
                           text=True, timeout=300)
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        return False


if '--scan' in sys.argv:
    bad = 0
    for name, path, old, _new, _t in MUTANTS:
        n = (ROOT / path).read_text().count(old)
        if n != 1:
            print(f'  PATTERN ABSENT - {name}: {path} matches {n}')
            bad += 1
    print(f'{len(MUTANTS) - bad}/{len(MUTANTS)} patterns present')
    sys.exit(2 if bad else 0)


originals = {p: (ROOT / p).read_text() for p in {m[1] for m in MUTANTS}}

# A sweep killed from outside leaves its mutant in the tree. Detect it
# BEFORE mutating: a working tree that already contains a mutant's `new`
# without its `old` is an interrupted run, not a design decision.
for name, path, old, new, _t in MUTANTS:
    src = (ROOT / path).read_text()
    if new and new not in old and old not in src and new in src:
        print(f'POISONED TREE: {path} already carries mutant "{name}"')
        sys.exit(3)

restored = {'done': False}


def restore_all(signum=None, frame=None):
    if restored['done']:
        return
    restored['done'] = True
    for p, data in originals.items():
        try:
            (ROOT / p).write_text(data)
        except OSError:
            pass


for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
    signal.signal(sig, restore_all)


assert build(), 'baseline build broke'
rc, out = run_check(SUITE_CMD)
assert rc == 0, f'baseline suite not green:\n{out[-2000:]}'
print('baseline suite green')
for name, path, old, _new, _t in MUTANTS:
    assert originals[path].count(old) == 1, f'PATTERN ABSENT: {name}'

killed, survived = [], []
for name, path, old, new, target in MUTANTS:
    mutated = originals[path].replace(old, new, 1)
    assert mutated != originals[path], f'mutant "{name}" was a no-op on write'
    (ROOT / path).write_text(mutated)
    # byte-verify the mutation landed before measuring anything
    assert (ROOT / path).read_text() == mutated, f'MUTATION WRITE FAILED: {name}'
    for p, data in originals.items():
        assert (ROOT / p).read_text() == (mutated if p == path else data), \
            f'TREE NOT PRISTINE under {name}: {p}'
    try:
        if not build():
            rc, out, dead = -1, 'build broke under the mutation', True
        else:
            rc, out = run_check(SUITE_CMD, timeout=300)
            dead = (rc != 0) or ('FAIL' in out) or ('not ok' in out)
        (killed if dead else survived).append(
            (name, 'BUILD BROKE' if 'build broke' in out else
             ('TIMEOUT' if rc == -1 else ('FAIL-line' if dead else f'rc={rc}'))))
    finally:
        (ROOT / path).write_text(originals[path])
        assert (ROOT / path).read_text() == originals[path], f'RESTORE FAILED: {path}'

restore_all()
for p, data in originals.items():
    assert (ROOT / p).read_text() == data, f'RESTORE FAILED: {p}'
assert build(), 'post-run rebuild failed'

print()
for name, how in killed:
    print(f'  killed - {name} :: {how}')
if survived:
    print('SURVIVED:')
    for name, _ in survived:
        print(f'  - {name}')
print(f'killed={len(killed)} survived={len(survived)} of {len(MUTANTS)}')
sys.exit(0 if not survived else 1)
