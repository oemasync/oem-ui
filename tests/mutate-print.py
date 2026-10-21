#!/usr/bin/env python3
"""Mutation proof for print mode (batch 42).

A check nobody has tried to break is a guess. This harness breaks each half
of the print contract, one at a time, and requires the suite to go RED with
the check that is supposed to own it.

House rules, restated because a proof file that only ever shows a clean run
proves nothing:

- every pattern is PRE-FLIGHTED: it must occur exactly once in the file, or
  the run aborts before mutating anything. A pattern that matches nothing is
  a hole reported as a proof;
- the poisoned-tree check runs FIRST: a file that already contains a mutant's
  `new` text and not its `old` is an interrupted run, not a design decision;
- the originals live IN THIS PROCESS (bytes in a dict), never in a scratch
  directory another subsystem may prune, and every restore is byte-verified;
- SIGINT/SIGTERM/SIGHUP and uncaughtException restore before exiting.
  `finally` does not run for a SIGKILL, but it does for Ctrl-C;
- a build failure and a crash both count as KILLS only when the expected
  check is the one that failed - a run that dies for another reason is a
  broken harness, not a killed mutant;
- source mutants run the suite WITHOUT rebuilding: `npm test` reads the
  source and the built CSS, and a stale dist is what the source checks are
  designed to catch. The one dist-only mutant below rebuilds nothing and
  exists to prove the built-CSS check is not dead weight.

Usage:
  python3 tests/mutate-print.py            # run every mutant
  python3 tests/mutate-print.py --preflight  # validate patterns only
  python3 tests/mutate-print.py --only 4   # resume from mutant 4
"""
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMP = 'src/styles/components.css'
TOK = 'src/styles/tokens.css'

MUTANTS = [
    dict(
        n='palette drifts: paper inherits the dark theme ink',
        file=TOK,
        old="\t\t--ink: #111111;\n\t\t--ink-dim: #4a4a4a;",
        new="\t\t--ink: #e8e8e8;\n\t\t--ink-dim: #4a4a4a;",
        check='print: the print palette IS the light palette, value for value',
    ),
    dict(
        n='the override loses the specificity argument (plain :root)',
        file=TOK,
        old="\t:root,\n\t:root[data-theme='dark'],\n\t:root[data-theme='light'] {",
        new="\t:root {",
        check='print: the override repeats the theme blocks specificity',
    ),
    dict(
        n='@page loses its margin: every page prints to the paper edge',
        file=COMP,
        old="\tmargin: 14mm 12mm;",
        new="\tmargin: 0;",
        check='print: the page box gets a margin',
    ),
    dict(
        n='the copy button is dropped from the hide list',
        file=COMP,
        old="\t.cm-copy,\n\t.cm-codebar__float,",
        new="\t.cm-codebar__float,",
        check='print: chrome does not print',
    ),
    dict(
        n='the hide list loses !important, so .cm-js state rules win on paper',
        file=COMP,
        old="\t\tdisplay: none !important;\n\t}",
        new="\t\tdisplay: none;\n\t}",
        check='print: chrome does not print',
    ),
    dict(
        n='the unclipping keeps max-height: none but loses overflow: visible',
        file=COMP,
        old="\t\tmax-height: none;\n\t\toverflow: visible;\n\t}",
        new="\t\tmax-height: none;\n\t}",
        check='print: every scroll container is unclipped on BOTH axes',
    ),
    dict(
        n='a printed code block stops wrapping',
        file=COMP,
        old="\t\twhite-space: pre-wrap;\n\t}",
        new="\t\twhite-space: pre;\n\t}",
        check='print: a printed code block wraps instead of losing its tail',
    ),
    dict(
        n='the exact-fill list grows an unmeasured entry (the terminal)',
        file=COMP,
        old="\t.cm-btn--primary,\n\t.cm-term__jump-tail,",
        new="\t.cm-btn--primary,\n\t.cm-term,\n\t.cm-term__jump-tail,",
        check='print: an inverted fill keeps its text',
    ),
    dict(
        n='the link rule loses its absolute-only guard',
        file=COMP,
        old="\t.cm-prose a[href^='http']::after,",
        new="\t.cm-prose a::after,",
        check='print: a link prints its destination, and only for absolute http(s)',
    ),
    dict(
        n='a card may be split across a page edge again',
        file=COMP,
        old="\t.cm-row,\n\t.cm-card,\n\t.cm-code,",
        new="\t.cm-row,\n\t.cm-code,",
        check='print: page-break hygiene',
    ),
    dict(
        n='the print block is appended AFTER stack ownership',
        file=COMP,
        old=None,  # the move mutant, handled below
        new=None,
        check='print: the block sits BEFORE stack ownership, which stays last',
    ),
]

PRINT_BANNER = '/* ============ print: the page a reader keeps ============'
STACK_BANNER = '/* ============ stack ownership (LAST, on purpose) ============'

_originals = {}
_restored = False


def read(p):
    return (ROOT / p).read_text()


def write(p, text):
    (ROOT / p).write_text(text)


def restore_all(*_args):
    global _restored
    if _restored:
        return
    _restored = True
    for p, text in _originals.items():
        write(p, text)
    ok = all(read(p) == text for p, text in _originals.items())
    print(('restored ' if ok else 'RESTORE FAILED ') + ', '.join(_originals))
    if not ok:
        sys.exit(2)


def on_signal(signum, _frame):
    print(f'\nsignal {signum}: restoring the tree before exit')
    restore_all()
    sys.exit(130)


def move_print_block(text):
    """Cut the print block and append it after stack ownership."""
    at = text.index(PRINT_BANNER)
    end = text.index(STACK_BANNER)
    block = text[at:end]
    rest = text[:at] + text[end:]
    return rest.rstrip('\n') + '\n\n' + block.rstrip('\n') + '\n'


def preflight():
    bad = []
    sources = {}
    for m in MUTANTS:
        if m['old'] is None:
            src = read(COMP)
            if PRINT_BANNER not in src or STACK_BANNER not in src:
                bad.append(f"{m['n']}: the print/stack banners are gone, so the move cannot be made")
            if src.index(PRINT_BANNER) > src.index(STACK_BANNER):
                bad.append(f"{m['n']}: the print block is ALREADY after stack ownership (poisoned tree)")
            continue
        src = sources.setdefault(m['file'], read(m['file']))
        n = src.count(m['old'])
        if n != 1:
            bad.append(f"{m['n']}: pattern occurs {n}x in {m['file']}, want exactly 1")
        # poisoned-tree pre-flight: the mutant is already applied
        if m['old'] not in src and m['new'] in src:
            bad.append(f"{m['n']}: a mutant is already in the tree (interrupted run) - "
                       f'restore {m["file"]} before sweeping')
    if bad:
        print('PRE-FLIGHT FAILED - nothing was mutated:')
        for b in bad:
            print('  -', b)
        sys.exit(1)
    print(f'pre-flight ok: {len(MUTANTS)} mutants, every pattern occurs exactly once')


def run_suite():
    r = subprocess.run(['node', 'tests/run.mjs'], cwd=ROOT, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def main(argv):
    start = 1
    if '--preflight' in argv:
        preflight()
        return 0
    if '--only' in argv:
        start = int(argv[argv.index('--only') + 1])

    preflight()
    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGHUP, on_signal)

    for p in (COMP, TOK):
        _originals[p] = read(p)

    survivors, kills = [], []
    try:
        for i, m in enumerate(MUTANTS, 1):
            if i < start:
                continue
            before = read(m['file'])
            if m['old'] is None:
                mutated = move_print_block(before)
            else:
                mutated = before.replace(m['old'], m['new'], 1)
            assert mutated != before, f"{m['n']}: mutation was a NO-OP"
            write(m['file'], mutated)
            # A mutation that did not land is a hole reported as a proof.
            after = read(m['file'])
            assert after == mutated, f"{m['n']}: the write did not land"

            rc, out = run_suite()
            killed = rc != 0 and m['check'] in out
            status = 'KILLED' if killed else ('SURVIVED' if rc == 0 else 'WRONG CHECK')
            print(f'[{i}/{len(MUTANTS)}] {status}: {m["n"]}')
            if not killed:
                print('    expected check:', m['check'])
                tail = [l for l in out.splitlines() if l.startswith('FAIL')][:4]
                for l in tail:
                    print('   ', l)
                survivors.append(m['n'])
            else:
                kills.append(m['n'])
            restore_all()
            assert read(m['file']) == before, f"{m['n']}: restore was not byte-exact"
            _restored = False
    finally:
        for p, text in _originals.items():
            if read(p) != text:
                print(f'the tree still differs from HEAD at {p} - restoring')
                write(p, text)

    print()
    print(f'{len(kills)} killed, {len(survivors)} survived, {len(MUTANTS)} mutants')
    if survivors:
        print('SURVIVORS (a survivor is either a bad mutant or a check measuring the wrong node):')
        for s in survivors:
            print('  -', s)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
