#!/usr/bin/env python3
"""Print mode, measured in WebKit — the engine Omar reads these pages in.

Print is a render mode, and the only honest way to test it is to ask the
engine to render as print: `emulate_media(media='print')` changes the
cascade AND the page box, so `getComputedStyle` answers the PRINT answer.

THE VIEWPORT IS A4 AT 96dpi (794x1123), not a phone. A print page box is
paper, and measuring print at 390 lays the document out at 390 - which is
not a page anyone prints. The screen-leak check covers the phone width in
a second context.

What this proves, in order:

  1. PAPER IS LIGHT. The dark-theme page resolves --ink #111 under print,
     not #e8e8e8 - measured before the fix at 1.23:1 against paper, i.e.
     an invisible page. The print values EQUAL the light theme's live
     values, so there is one ink-on-light ramp and not a third palette.
  2. SCREEN IS UNCHANGED. Without the emulation the same page still
     resolves the dark palette and still shows its header. A print rule
     that leaked onto the screen would pass (1) and fail here.
  3. CHROME DOES NOT PRINT, and it does on screen.
  4. A SCROLL CONTAINER PRINTS WHOLE. Before: .cm-scrollarea held 747px of
     content in a 222px box and 525px of it never reached the page. The
     unclipping must not widen the page either - measured as a DIFFERENTIAL
     against the same build with the unclipping reverted, because the
     showcase already carries a 12px table overflow of its own.
  5. AN INVERTED FILL KEEPS ITS TEXT (`print-color-adjust: exact`), and
     only the blocks measured inverted are asserted.
  6. A LINK PRINTS ITS DESTINATION, and only for absolute http(s) - a
     relative href must NOT be printed as if it were an address.
  7. Page-break hygiene: a row/card is not split, a heading is not
     orphaned, and a printed code block wraps instead of losing its tail.

Run:  python3 tests/measure-print-webkit.py [url]
Default url is the LAN preview (Omar's rule: bind to the LAN, never
localhost), overridable with OEM_UI_URL.
"""
import json
import os
import sys

if not os.path.isdir(os.environ.get('PLAYWRIGHT_BROWSERS_PATH', '/root/.cache/ms-playwright')):
    # The documented self-rescue: only drop a DEAD path, never a live one.
    os.environ.pop('PLAYWRIGHT_BROWSERS_PATH', None)

from playwright.sync_api import sync_playwright  # noqa: E402

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
    'OEM_UI_URL', 'http://192.168.1.68:4321/')
A4 = {'width': 794, 'height': 1123}   # 210mm x 297mm at 96dpi

CHROME = [
    '.cm-header', '.cm-nav-toggle', '.cm-nav-scrim', '.cm-drawer',
    '.cm-toast-region', '.cm-scroll-fade', '.cm-pager', '.cm-search',
    '.cm-copy', '.cm-codebar__float', '.cm-term__controls', '.cm-keys',
    '.cm-bell', '.cm-revert', '[data-cm-progress]',
]
SCROLLERS = ['.cm-scrollarea', '.cm-scroller', '.cm-table-wrap',
             '.cm-code--scroll', '.cm-typeset-scroll', '.cm-term__body',
             '.cm-codebar pre', 'pre.cm-code']
EXACT = ['.cm-btn--primary', '.cm-term__jump-tail', '.cm-bubble',
         '.cm-cal__day[aria-selected="true"]']

READ = r"""() => {
  const cs = (el) => getComputedStyle(el);
  const root = document.documentElement;
  const out = {};
  out.colorScheme = cs(root).colorScheme;
  out.tokens = {};
  for (const t of ['ink', 'ink-dim', 'ink-faint', 'bg', 'bg-2', 'panel', 'line']) {
    out.tokens[t] = cs(root).getPropertyValue('--' + t).trim();
  }
  out.textColor = cs(document.body).color;
  return out;
}"""


def tokens(page):
    return page.evaluate(READ)



def wait_ready(page, timeout_ms=12000):
    """Poll `evaluate` for the runtime's own mark.

    `wait_for_function` TIMES OUT on the first call after a navigation on
    this host (measured: 10.9s with classList already reading `cm-js`),
    and `networkidle` fires before the bundle runs. Polling evaluate is
    the path that is measured to work.
    """
    waited = 0
    while waited < timeout_ms:
        try:
            if page.evaluate("() => document.documentElement.classList.contains('cm-js')"):
                return True
        except Exception:
            pass
        page.wait_for_timeout(100)
        waited += 100
    return False


def main() -> int:
    problems = []
    with sync_playwright() as p:
        browser = p.webkit.launch()
        ctx = browser.new_context(viewport=A4, device_scale_factor=1)
        page = ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        # 'networkidle' can fire before the bundle runs; wait for the
        # runtime's own mark, as every other harness here does.
        page.goto(URL, wait_until='networkidle')
        assert wait_ready(page), 'the runtime never marked <html class="cm-js">'
        page.wait_for_timeout(300)

        # ---------- 1. the print palette ----------
        page.emulate_media(media='print')
        page.wait_for_timeout(150)
        pr = tokens(page)
        print('print (dark default):', json.dumps(pr, indent=1))
        if pr['tokens']['ink'].lower() not in ('#111111', '#111', 'rgb(17, 17, 17)'):
            problems.append(f"print --ink is {pr['tokens']['ink']}, not the light palette's #111")
        if pr['colorScheme'] != 'light':
            problems.append(f"print color-scheme is {pr['colorScheme']!r}, want 'light'")
        if pr['textColor'] not in ('rgb(17, 17, 17)', 'rgb(0, 0, 0)'):
            problems.append(f"print body colour is {pr['textColor']} - light text on paper")

        # ---------- 2. the screen is untouched ----------
        page.emulate_media(media='screen')
        page.wait_for_timeout(150)
        sc = tokens(page)
        print('screen (dark default):', json.dumps(sc, indent=1))
        if sc['tokens']['ink'] == pr['tokens']['ink']:
            problems.append('the print palette leaked onto the screen: --ink is identical')
        if sc['colorScheme'] != 'dark':
            problems.append(f"screen color-scheme is {sc['colorScheme']!r}, want 'dark'")

        # print palette == light palette, value for value
        page.evaluate("() => document.documentElement.setAttribute('data-theme', 'light')")
        page.wait_for_timeout(200)
        light = tokens(page)
        page.emulate_media(media='print')
        page.wait_for_timeout(150)
        light_print = tokens(page)
        page.evaluate("() => document.documentElement.removeAttribute('data-theme')")
        page.wait_for_timeout(150)
        print('light (screen):', json.dumps(light['tokens'], indent=1))
        drift = {k: (light['tokens'][k], light_print['tokens'][k])
                 for k in light['tokens'] if light['tokens'][k] != light_print['tokens'][k]}
        if drift:
            problems.append(f'the print palette drifted from the light palette: {drift}')

        # ---------- 3..7 measured inside print media ----------
        page.emulate_media(media='print')
        page.wait_for_timeout(150)

        chrome = page.evaluate(
            """(sels) => sels.map((s) => {
                const el = document.querySelector(s);
                if (!el) return [s, 'absent'];
                const cs = getComputedStyle(el);
                return [s, cs.display, el.getBoundingClientRect().height];
            })""", CHROME)
        print('chrome under print:', json.dumps(chrome))
        seen = 0
        for row in chrome:
            if row[1] == 'absent':
                continue
            seen += 1
            if row[1] != 'none':
                problems.append(f'{row[0]} still prints (display {row[1]}, {row[2]}px)')
        if seen < 10:
            problems.append(f'only {seen} chrome elements found on the page - the check is measuring nothing')

        # ...and the same controls are NOT hidden on screen. Measured at 390,
        # not here: `.cm-nav-toggle` is legitimately display:none above the
        # mobile breakpoint, so asking at A4 reports the burger as "hidden by
        # the print reset" when the breakpoint hid it. The phone width is the
        # one where every one of them is meant to be on screen.
        page.emulate_media(media='print')
        page.wait_for_timeout(150)
        scroll = page.evaluate(
            """(sels) => sels.map((s) => {
                const el = document.querySelector(s);
                if (!el) return [s, 'absent'];
                const cs = getComputedStyle(el);
                return [s, cs.overflowY, cs.maxHeight, cs.whiteSpace,
                        el.scrollHeight, el.clientHeight,
                        el.scrollHeight - el.clientHeight];
            })""", SCROLLERS)
        print('scrollers under print:', json.dumps(scroll))
        for row in scroll:
            if row[1] == 'absent':
                continue
            name, ovy, mh, ws, sh, ch, clipped = row
            if ovy != 'visible':
                problems.append(f'{name} prints with overflow-y {ovy} - it prints its window')
            if mh != 'none':
                problems.append(f'{name} prints with max-height {mh} - the cap cuts the page')
            if clipped > 2:
                problems.append(f'{name} prints clipped: {clipped}px of content is unreachable')
        for row in scroll:
            if row[1] == 'absent' or 'pre' not in row[0]:
                continue
            if row[3] != 'pre-wrap':
                problems.append(f'{row[0]} prints white-space {row[3]!r}; a wide line loses its tail')

        exact = page.evaluate(
            """(sels) => sels.map((s) => {
                const el = document.querySelector(s);
                if (!el) return [s, 'absent'];
                const cs = getComputedStyle(el);
                return [s, cs.printColorAdjust || cs.webkitPrintColorAdjust,
                        cs.backgroundColor, cs.color];
            })""", EXACT)
        print('inverted fills under print:', json.dumps(exact))
        for row in exact:
            if row[1] == 'absent':
                continue
            name, adjust, bg, fg = row
            if adjust != 'exact':
                problems.append(f'{name} does not force its fill ({adjust!r}) - light-on-white on paper')

        breaks = page.evaluate(
            """() => {
                const one = (sel, prop) => {
                    const el = document.querySelector(sel);
                    return el ? getComputedStyle(el)[prop] : 'absent';
                };
                return {
                    row: one('.cm-row', 'breakInside'),
                    card: one('.cm-card', 'breakInside'),
                    code: one('.cm-code', 'breakInside'),
                    term: one('.cm-term', 'breakInside'),
                    proseH2: one('.cm-prose h2', 'breakAfter'),
                };
            }""")
        print('breaks under print:', json.dumps(breaks))
        for key in ('row', 'card', 'code', 'term'):
            if breaks[key] != 'avoid':
                problems.append(f'.cm-{key} break-inside is {breaks[key]!r}, want avoid')
        if breaks['proseH2'] != 'avoid':
            problems.append(f"a prose h2 has break-after {breaks['proseH2']!r}, so it can be orphaned")

        # ---------- 6. link destinations ----------
        links = page.evaluate(
            """() => {
                const host = document.createElement('div');
                host.className = 'cm-prose';
                host.id = 'print-link-fixture';
                host.innerHTML = '<p>absolute <a href="https://example.com/a?b=c">abs</a>'
                  + ' and relative <a href="/blog">rel</a> and in-page <a href="#top">top</a></p>';
                document.body.appendChild(host);
                const nodes = host.querySelectorAll('a');
                const g = (el) => getComputedStyle(el, '::after').content;
                return {abs: g(nodes[0]), rel: g(nodes[1]), top: g(nodes[2])};
            }""")
        print('link ::after under print:', json.dumps(links))
        if 'https://example.com/a?b=c' not in (links['abs'] or ''):
            problems.append(f"an absolute link prints no destination (::after = {links['abs']!r})")
        if '/blog' in (links['rel'] or ''):
            problems.append(f"a RELATIVE link printed {links['rel']!r} as an address")
        if '#top' in (links['top'] or ''):
            problems.append(f"an in-page link printed {links['top']!r} as an address")

        # on screen the same fixture prints nothing
        page.emulate_media(media='screen')
        page.wait_for_timeout(120)
        screen_links = page.evaluate(
            """() => {
                const host = document.querySelector('#print-link-fixture');
                return getComputedStyle(host.querySelector('a'), '::after').content;
            }""")
        print('link ::after on screen:', json.dumps(screen_links))
        if screen_links and 'example.com' in screen_links:
            problems.append('the link destination prints on SCREEN too - the rule is unscoped')

        # ---------- the unclipping must not widen the page ----------
        page.emulate_media(media='print')
        page.wait_for_timeout(120)
        built = page.evaluate(
            "() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        page.add_style_tag(content="""
          @media print {
            .cm-scrollarea,.cm-scroller,.cm-table-wrap,.cm-code--scroll,
            .cm-typeset-scroll,.cm-term__body,.cm-codebar pre,pre.cm-code
              { overflow: revert !important; }
          }""")
        page.wait_for_timeout(150)
        reverted = page.evaluate(
            "() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        print('page width, print as built:', built, ' unclipping reverted:', reverted)
        if built[0] > reverted[0]:
            problems.append(
                f'unclipping widened the printed page: {built[0]} vs {reverted[0]} - '
                'content that used to scroll now runs off the paper edge')

        page.evaluate("() => { const f = document.querySelector('#print-link-fixture'); if (f) f.remove(); }")
        if errors:
            problems.append(f'page errors: {errors}')

        # ---------- and the phone width is not broken by any of it ----------
        phone = browser.new_context(viewport={'width': 390, 'height': 844},
                                    device_scale_factor=3, is_mobile=True, has_touch=True)
        pp = phone.new_page()
        pp.goto(URL, wait_until='networkidle')
        print('phone runtime ready:', wait_ready(pp))
        pp.wait_for_timeout(250)
        screen_chrome = pp.evaluate(
            """(sels) => sels.map((s) => {
                const el = document.querySelector(s);
                return [s, el ? getComputedStyle(el).display : 'absent'];
            })""", CHROME)
        print('chrome on screen at 390:', json.dumps(screen_chrome))
        for row in screen_chrome:
            if row[1] == 'none':
                problems.append(f'{row[0]} is hidden on SCREEN at 390 - the print reset leaked')
        phone_doc = pp.evaluate(
            "() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        print('screen at 390:', phone_doc)
        if phone_doc[0] > phone_doc[1] + 1:
            problems.append(f'screen at 390 overflows: {phone_doc}')
        browser.close()

    print()
    if problems:
        print(f'FAIL - {len(problems)} problem(s)')
        for p_ in problems:
            print('  -', p_)
        return 1
    print('OK - print mode measured clean in WebKit (A4 page, 390 screen)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
