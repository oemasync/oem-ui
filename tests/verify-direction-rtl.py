#!/root/.venvs/mau/bin/python
"""The Direction baseline, on the one overlay whose room is computed in
script: the tooltip clamp.

WHY THIS FILE EXISTS. `--start` / `--end` are spelled logically in the
stylesheet (`inset-inline-start` / `inset-inline-end`), so which SCREEN
edge a tip is pinned to is a function of the RENDERED direction. The
clamp in `initTooltipClamp()` measures room from the physical box, and it
used to hardcode the LTR mapping - so in an RTL subtree it capped the tip
against the space BEHIND it. Measured before the fix: an RTL `--start`
tip was capped to 20px, a sliver, because the room was read off the wrong
side of the trigger.

HOW THE ASSERTIONS ARE WRITTEN. Not "the tip fits" - that would pass
under the broken code too. For each specimen the harness derives BOTH
candidate rooms from the live geometry (the direction-aware one and the
LTR-only one), then requires the cap actually applied to the element to
match the direction-aware one and to MISS the LTR-only one, so a future
refactor that drops the direction read cannot pass by accident. It also
requires the two candidates to differ, so a fixture that stops
discriminating fails loudly instead of going quiet.

The CSS-only cap is read with the runtime's inline write temporarily
removed: a computed `max-width` is the USED value, so with the inline
style in place the comparison would be circular.
"""
import sys

from playwright.sync_api import sync_playwright

from harness_wait import boot_timeout

URL = 'http://127.0.0.1:4471/'
NAV_TIMEOUT = boot_timeout(base=90000)

passed = 0
failed = []


def check(name, ok, detail=''):
    global passed
    if ok:
        passed += 1
        print(f'ok   {name}' + (f' :: {detail}' if detail else ''))
    else:
        failed.append(name)
        print(f'FAIL {name}' + (f' :: {detail}' if detail else ''))


PROBE = """
(sel) => {
  const tip = document.querySelector(sel);
  if (!tip) return { missing: sel };
  const host = tip.closest('.cm-tooltip');
  const tr = host.getBoundingClientRect();
  const vw = document.documentElement.clientWidth;
  const probe = document.createElement('div');
  probe.style.cssText = 'position:absolute;visibility:hidden;width:1rem';
  document.body.appendChild(probe);
  const rem = parseFloat(getComputedStyle(probe).width) || 16;
  probe.remove();
  const inline = tip.style.maxWidth || '';
  tip.style.removeProperty('max-width');
  const cssCap = parseFloat(getComputedStyle(tip).maxWidth) || null;
  if (inline) tip.style.maxWidth = inline;
  const r = tip.getBoundingClientRect();
  return {
    vw: vw,
    rem: rem,
    gutter: 1.25 * rem,
    dir: getComputedStyle(host).direction,
    hostLeft: tr.left,
    hostRight: tr.right,
    tipLeft: r.left,
    tipRight: r.right,
    tipW: r.width,
    inline: inline,
    cssCap: cssCap,
    applied: parseFloat(getComputedStyle(tip).maxWidth) || null,
    cls: host.className,
  };
}
"""


def cap_for(m, grow_right):
    """The cap the runtime should apply for a tip growing in one screen
    direction: the smaller of the CSS-only cap and the room on that side."""
    room = (m['vw'] - m['hostLeft'] - m['gutter']) if grow_right \
        else (m['hostLeft'] - m['gutter'])
    cap = m['cssCap'] or float('inf')
    return min(cap, room)


with sync_playwright() as p:
    browser = p.webkit.launch()
    page = browser.new_page(viewport={'width': 390, 'height': 844})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    try:
        page.goto(URL, wait_until='load', timeout=NAV_TIMEOUT)
        page.wait_for_function('() => !!document.querySelector("#tip-rtl-end")',
                               timeout=NAV_TIMEOUT)
        page.wait_for_timeout(400)   # the clamp runs on init and on resize

        specimens = [
            # label, id, does it grow toward the physical RIGHT edge?
            ('ltr --start', '#tip-demo', True),
            ('ltr --end', '#tip-demo-end', False),
            ('rtl --start', '#tip-rtl-start', False),  # inline-start = right
            ('rtl --end', '#tip-rtl-end', True),       # inline-end   = left
        ]
        measured = []
        for label, sel, grow_right in specimens:
            m = page.evaluate(PROBE, sel)
            check(f'{label}: the specimen is present in the built page',
                  'missing' not in m, f"missing {m.get('missing', '')}")
            measured.append((label, m, grow_right))

        check('the specimens render in the direction they claim',
              all(('missing' in m) or m['dir'] == want
                  for (_, m, _), want in
                  zip(measured, ['ltr', 'ltr', 'rtl', 'rtl'])),
              ' | '.join(f"{l}:{m.get('dir')}" for l, m, _ in measured))

        # ---- the discriminating checks ------------------------------
        for label, m, grow_right in measured:
            if 'missing' in m:
                continue
            want = cap_for(m, grow_right)
            wrong = cap_for(m, not grow_right)
            applied = m['applied']
            check(f'{label}: the cap comes from the direction-aware room',
                  applied is not None and abs(applied - want) <= 1.0,
                  f'applied={applied} want={round(want, 1)} '
                  f'(the ltr-only formula gives {round(wrong, 1)})')
            check(f'{label}: the applied cap MISSES the ltr-only answer',
                  applied is not None and abs(applied - wrong) > 1.0,
                  f'applied={applied} ltr-only={round(wrong, 1)}')
            check(f'{label}: this fixture still separates the two formulas',
                  abs(want - wrong) > 1.0,
                  f'{round(want, 1)} vs {round(wrong, 1)}')

        # ---- the contract the clamp exists for ---------------------
        for label, m, _ in measured:
            if 'missing' in m:
                continue
            check(f'{label}: the tip stays inside the viewport',
                  m['tipLeft'] >= -0.5 and m['tipRight'] <= m['vw'] + 0.5,
                  f"tip {round(m['tipLeft'])}..{round(m['tipRight'])} vw={m['vw']}")
            check(f'{label}: the tip is not squeezed into a sliver',
                  m['tipW'] >= 120,
                  f"width {round(m['tipW'])}px (the ltr-only formula left the "
                  f'rtl --start tip at 20px)')

        # The reader-facing claim is "the page cannot be PANNED sideways",
        # not "scrollWidth equals clientWidth". Those differ: the root uses
        # `overflow-x: clip`, which refuses the pan while still reporting a
        # scrollWidth wider than the viewport (an absolutely-positioned
        # overlay that escapes its trigger widens the document without ever
        # being reachable). Asserting the numbers would fail on a page that
        # behaves correctly, so the attempt itself is made here.
        pan = page.evaluate("""() => {
          const de = document.documentElement;
          const before = window.scrollX;
          window.scrollTo(500, 0);
          const afterWindow = window.scrollX;
          de.scrollLeft = 500;
          const afterElement = de.scrollLeft;
          window.scrollTo(before, 0);
          return { overflowX: getComputedStyle(de).overflowX,
                   afterWindow: afterWindow, afterElement: afterElement,
                   scrollW: de.scrollWidth, clientW: de.clientWidth };
        }""")
        check('an rtl overlay cannot pan the page sideways',
              pan['afterWindow'] == 0 and pan['afterElement'] == 0,
              f"attempted 500px, landed at window={pan['afterWindow']} "
              f"element={pan['afterElement']} "
              f"(scrollWidth {pan['scrollW']} vs clientWidth {pan['clientW']} "
              f"is expected: overflow-x:{pan['overflowX']})")
        check('the root genuinely clips rather than being merely unscrollable',
              pan['overflowX'] in ('clip', 'hidden'),
              f"computed overflow-x = {pan['overflowX']}")
        check('the page threw nothing', not errors, f'{errors[:2]}')
    except Exception as e:   # a crashed harness is a failure, never a pass
        failed.append(f'EXCEPTION {type(e).__name__}: {e}')
        print(f'FAIL exception :: {type(e).__name__}: {e}')
    finally:
        browser.close()

print(f'\npassed {passed}/{passed + len(failed)}')
for f in failed:
    print(f'FAILED: {f}')
sys.exit(1 if failed else 0)
