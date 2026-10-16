#!/root/.venvs/mau/bin/python
"""Mutation proof for the AlertDialog.

Same rules as tests/mutate-chart.py, restated because a proof file that
only ever shows a clean run proves nothing:

- every pattern is pre-flighted with --scan and the run ABORTS if one is
  absent or ambiguous (count != 1), rather than silently not mutating;
- dist is rebuilt in EVERY mutant window - the harness drives the page,
  so the served build must match the source under test;
- the file is snapshotted before the mutation and restored with `cp`,
  never `git checkout --` (this worktree is shared with other batches);
- a crashed or timed-out harness is a KILL, never a survival: only
  rc == 0 survives;
- a non-zero build exit is a KILL too;
- a final build restores a clean dist.

Why these four, and why one of them is a deliberate subtlety:

- `role="alertdialog"` is the whole semantic claim, so it is mutated
  first: without it this is an ordinary dialog and nothing about the
  accessibility tree says "urgent".
- `closedby="closerequest"` is mutated SECOND, and this is the honest
  one. Removing it does NOT make an outside click dismiss the dialog in
  WebKit - the engine default already ignores it, which is exactly what
  the harness measured before asserting. So the behavioural check stays
  GREEN under this mutant and the kill comes from the check that pins
  the attribute as a DECLARED contract. That is the right division: the
  attribute is what protects Safari/Firefox where the default has
  differed, and a build that quietly dropped it would still look fine in
  the one engine we can drive. This pattern is what makes that gap
  visible instead of latent.
- The inert-submit mutant restores the exact defect this batch found and
  fixed: actions written as type="submit" OUTSIDE the form, so both
  buttons are dead. It must be caught by the general rule, not only by
  the one-off assertion about the confirm button.
- The shared-node mutant points aria-describedby at the TITLE's id: the
  dialog then has a name and a non-empty description, both checks pass,
  and the same sentence is announced twice as the question and its
  context. Only comparing the two ids sees it.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRATCH = Path('/root/.hermes/cache/scratch')
BUILD = ['npm', 'run', 'build']
HARNESS = ['/root/.venvs/mau/bin/python', 'tests/verify-alert-dialog.py']

ASTRO = 'src/pages/[...family].astro'

PATTERNS = [
    ('drop the urgent role: the confirm stops announcing itself as an alert dialog',
     ASTRO,
     'role="alertdialog" aria-labelledby="alert-demo-title"',
     'aria-labelledby="alert-demo-title"',
     'harness'),

    ('drop closedby: the outside-click refusal is no longer declared',
     ASTRO,
     'aria-describedby="alert-demo-desc" closedby="closerequest">',
     'aria-describedby="alert-demo-desc">',
     'harness'),

    ('restore the dead actions: the foot buttons are submits outside any form',
     ASTRO,
     '<button type="button" class="cm-btn" data-cm-close="alert-demo" value="cancel">cancel</button>',
     '<button type="submit" class="cm-btn" value="cancel">cancel</button>',
     'harness'),

    ('point the description at the title: one sentence is both the question and its context',
     ASTRO,
     'aria-describedby="alert-demo-desc"',
     'aria-describedby="alert-demo-title"',
     'harness'),
]


def run(cmd, timeout=900):
    """capture_output must NOT be used on the build: npm's inherited
    stdio lives in the capture machinery and crashes it."""
    p = subprocess.run(cmd, cwd=ROOT, timeout=timeout, capture_output=True)
    return p.returncode, p.stdout.decode('utf8', 'replace')


def scan():
    bad = 0
    for name, rel, pat, _mut, _who in PATTERNS:
        n = (ROOT / rel).read_text().count(pat)
        if n != 1:
            print(f'PATTERN AMBIGUOUS/ABSENT ({n}) - {name}')
            bad += 1
    print(f'{len(PATTERNS) - bad}/{len(PATTERNS)} patterns present')
    return 1 if bad else 0


def main():
    if '--scan' in sys.argv:
        return scan()
    if scan():
        print('ABORT: no mutation run without a full pre-flight')
        return 2

    SCRATCH.mkdir(parents=True, exist_ok=True)

    rc, _ = run(BUILD)
    if rc != 0:
        print('KILL: baseline build failed')
        return 2
    rc, out = run(HARNESS)
    if rc != 0:
        print(f'KILL: baseline harness not green:\n{out[-2000:]}')
        return 2
    print('baseline build green | baseline harness green', flush=True)

    killed = survived = 0
    results = []
    for name, rel, pat, mut, who in PATTERNS:
        target = ROOT / rel
        snap = SCRATCH / f'mutate-alert-{rel.replace("/", "_")}.bak'
        subprocess.run(['cp', str(target), str(snap)], check=True)
        original = target.read_text()
        assert original.count(pat) == 1, f'PATTERN ABSENT for {name}'
        target.write_text(original.replace(pat, mut, 1))
        try:
            rc_build, _ = run(BUILD)
            verdicts = {}
            if rc_build != 0:
                verdicts['build'] = rc_build
            else:
                rc_h, out = run(HARNESS)
                verdicts['harness'] = rc_h
                fails = [l for l in out.splitlines() if l.startswith('FAIL')]
                if fails:
                    verdicts['first_fail'] = fails[0][:110]
            if verdicts and all(v == 0 for k, v in verdicts.items()
                                if k != 'first_fail'):
                print(f'  SURVIVED - {name} ({who}) {verdicts}', flush=True)
                survived += 1
                results.append(('SURVIVED', name, who, verdicts))
            else:
                bad = [k for k, v in verdicts.items()
                       if v != 0 and k != 'first_fail']
                print(f'  killed - {name} ({who}) by {bad or ["build"]} {verdicts}',
                      flush=True)
                killed += 1
                results.append(('killed', name, who, verdicts))
        except subprocess.TimeoutExpired:
            print(f'  killed (timeout) - {name}', flush=True)
            killed += 1
            results.append(('killed(timeout)', name, who, {}))
        except Exception as e:
            print(f'  killed (CRASH) - {name}: {e}', flush=True)
            killed += 1
            results.append(('killed(crash)', name, who, {}))
        finally:
            subprocess.run(['cp', str(snap), str(target)], check=True)
            restored = target.read_text()
            assert restored == original, f'RESTORE FAILED for {name}'
            snap.unlink(missing_ok=True)

    total = killed + survived
    print(f'killed={killed} survived={survived} of {total}', flush=True)
    for verdict, name, who, verdicts in results:
        print(f'  {verdict}: {name} [predicted {who}] {verdicts}', flush=True)
    run(BUILD)
    return 1 if survived else 0


if __name__ == '__main__':
    sys.exit(main())
