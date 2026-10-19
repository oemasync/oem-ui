#!/root/.venvs/mau/bin/python
"""Mutation proof for the reading-progress runtime (cmInitProgress).

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
     "bar.style.setProperty('--cm-progress', pct + '%');",
     "", 'suite'),
    ('aria-valuenow stops being written (the pair splits)', 'src/js/cli-mono.js',
     "bar.setAttribute('aria-valuenow', String(pct));",
     "", 'suite'),
    ('the bar never paints at bind time', 'src/js/cli-mono.js',
     "window.addEventListener('resize', paint, { passive: true });\n\t\t\t\tpaint();",
     "window.addEventListener('resize', paint, { passive: true });", 'suite'),
    ('no scroll listener is bound', 'src/js/cli-mono.js',
     "(src || window).addEventListener('scroll', paint, { passive: true });",
     "", 'suite'),
    ('no resize listener is bound', 'src/js/cli-mono.js',
     "\t\t\t\twindow.addEventListener('resize', paint, { passive: true });",
     "", 'suite'),
    ('the rubber-band clamps are gone', 'src/js/cli-mono.js',
     'return pct < 0 ? 0 : pct > 100 ? 100 : pct;',
     'return pct;', 'suite'),
    ('the no-scroll page writes NaN', 'src/js/cli-mono.js',
     'if (max <= 0) return 100;', '', 'suite'),
    ('an orphan bar is written to', 'src/js/cli-mono.js',
     'if (!src) return;', '', 'suite'),
    ('a second bind double-binds the listeners', 'src/js/cli-mono.js',
     'if (bar.__cmProgressBound) return;', '', 'suite'),
    ('a container bar reads the PAGE instead of its container', 'src/js/cli-mono.js',
     'var box = src\n\t\t\t\t\t\t|| document.scrollingElement',
     'var box = document.scrollingElement', 'suite'),
    ('cmInitProgress leaves init()', 'src/js/cli-mono.js',
     '\t\tcmInitProgress(root);\n', '', 'suite'),
    ('initProgress leaves the handle', 'src/js/cli-mono.js',
     'initProgress: cmInitProgress', 'initProgress: null', 'suite'),
    ('the late-markup observer forgets the bar', 'src/js/cli-mono.js',
     "'[data-cm-navmenu], [data-cm-progress], .cm-prose-table'",
     "'[data-cm-navmenu], .cm-prose-table'", 'suite'),
    ('the showcase stops shipping a live bar', 'src/pages/[...family].astro',
     '<div class="cm-progress" data-cm-progress style="--cm-progress:0%"',
     '<div class="cm-progress" style="--cm-progress:0%"', 'suite'),
    ('the fill loses the property it draws from', 'src/styles/components.css',
     'transform: translateX(calc(var(--cm-progress, 0%) - 100%));',
     'transform: translateX(calc(50% - 100%));', 'suite'),
    ('the static specimen pair splits (aria authored, property gone)',
     'src/pages/[...family].astro',
     'style="--cm-progress:33%" role="progressbar" aria-valuenow="33"',
     'role="progressbar" aria-valuenow="33"', 'suite'),
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
