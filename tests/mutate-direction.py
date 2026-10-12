#!/root/.venvs/mau/bin/python
"""Mutation proof for the Direction baseline's script half - the tooltip
clamp.

Same rules as tests/mutate-chart.py, restated because a proof file that
only ever shows a clean run proves nothing:

- every pattern is pre-flighted with --scan and the run ABORTS if one is
  absent or ambiguous (count != 1), rather than silently not mutating;
- dist is rebuilt in EVERY mutant window - the harness drives the page,
  so the served build must match the source under test;
- the file is snapshotted before the mutation and restored with `cp`,
  never `git checkout --` (this worktree is shared with other batches);
- a crashed or timed-out harness is a KILL, never a survival: only rc == 0
  survives, and the kill count and the closing summary are read from the
  same `killed` variable;
- a non-zero build exit is a KILL too (the mutant broke the build, so
  nothing about it can be green), and the build runs in every window;
- a final build restores a clean dist.

WHY THESE PATTERNS. The clamp's direction read has two independent halves
and the fixtures were chosen to separate them:

- `read the direction but ignore it` (`rtl && false`) is the sneaky
  regression: the code still READS `direction`, so any check that merely
  looked for the read would pass. Only a check comparing the applied cap
  against the direction-aware room catches it.
- `drop the read entirely` (hardcode `rtl = false`) is the regression a
  more likely refactor produces, and it must be caught by the same check.
- deleting the RTL specimen is the third way the claim can rot: the
  harness would still pass on the LTR fixtures alone, so a check that the
  fixture exists AND discriminates is what pins it.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRATCH = Path('/root/.hermes/cache/scratch')
BUILD = ['npm', 'run', 'build']
HARNESS = ['/root/.venvs/mau/bin/python', 'tests/verify-direction-rtl.py']

JS = 'src/js/cli-mono.js'
ASTRO = 'src/pages/index.astro'

PATTERNS = [
    # ---- the direction read is dropped, reintroducing the shipped bug ----
    ('hardcode ltr: the clamp ignores the rendered direction again',
     JS,
     "\t\t\t\t\trtl = getComputedStyle(host).direction === 'rtl';",
     '\t\t\t\t\trtl = false;',
     'harness'),

    # ---- the read is kept but neutered: the check must compare, not scan ----
    ('keep the read and discard its answer: direction is read but unused',
     JS,
     "\t\t\t\t\trtl = getComputedStyle(host).direction === 'rtl';",
     "\t\t\t\t\trtl = getComputedStyle(host).direction === 'rtl' && false;",
     'harness'),

    # ---- the fixture that proves it can vanish ----
    ('remove the rtl specimen: nothing left to measure the mapping against',
     ASTRO,
     '\t\t\t\t<p class="cm-btn-group" dir="rtl">',
     '\t\t\t\t<p class="cm-btn-group">',
     'harness'),
]


def run(cmd, timeout=900):
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


def first_fail(out):
    for line in out.splitlines():
        if line.startswith('FAIL') or line.startswith('FAILED'):
            return line[:200]
    return ''


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
        snap = SCRATCH / f'mutate-direction-{rel.replace("/", "_")}.bak'
        subprocess.run(['cp', str(target), str(snap)], check=True)
        original = target.read_text()
        assert original.count(pat) == 1, f'PATTERN ABSENT for {name}'
        target.write_text(original.replace(pat, mut, 1))
        verdicts = {}
        try:
            rc_build, _ = run(BUILD)
            if rc_build != 0:
                verdicts['build'] = rc_build
            else:
                rc_h, out_h = run(HARNESS)
                verdicts['harness'] = rc_h
                verdicts['first_fail'] = first_fail(out_h)
            if verdicts and all(v == 0 for k, v in verdicts.items()
                                if k != 'first_fail'):
                print(f'  SURVIVED - {name} ({who}) {verdicts}', flush=True)
                survived += 1
                results.append(('SURVIVED', name, who, verdicts))
            else:
                bad = [k for k, v in verdicts.items()
                       if k != 'first_fail' and v != 0]
                print(f'  killed - {name} ({who}) by {bad or ["build"]} '
                      f'{verdicts.get("first_fail", "")}', flush=True)
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
            assert target.read_text() == original, f'RESTORE FAILED for {name}'
            snap.unlink(missing_ok=True)

    total = killed + survived
    print(f'killed={killed} survived={survived} of {total}', flush=True)
    for verdict, name, who, verdicts in results:
        print(f'  {verdict}: {name} [predicted {who}] '
              f'{verdicts.get("first_fail", verdicts)}', flush=True)
    run(BUILD)
    return 1 if survived else 0


if __name__ == '__main__':
    sys.exit(main())
