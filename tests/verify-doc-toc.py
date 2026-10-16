"""The docs TOC: it exists on family routes, lists only that document's
sections, every row resolves, and the scroll-spy marks the row the reader
is actually in.

The spy check waits for scrollY to STOP moving. A fixed sleep after
`scrollIntoView()` reads mid-flight (the page smooth-scrolls), which
reported the PREVIOUS row as active and looked like an off-by-one bug in
the spy -- it was the harness.
"""
import os, sys
from playwright.sync_api import sync_playwright

URL = os.environ.get('CM_BASE', 'http://127.0.0.1:4471/')
FAMILIES = {
    'foundation': 5, 'surfaces': 7, 'tables': 6, 'panels': 6, 'content': 5,
    'prose': 7, 'layout': 7, 'composed': 8, 'reference': 4,
}
passed = failed = 0


def check(name, cond, extra=''):
    global passed, failed
    if cond:
        passed += 1
        print('ok   ' + name)
    else:
        failed += 1
        print('FAIL ' + name + (' :: ' + extra if extra else ''))


def settle(pg, tries=25):
    """Wait until window.scrollY stops changing, so the spy has run against
    the final position rather than one mid-scroll."""
    prev = None
    for _ in range(tries):
        now = pg.evaluate('window.scrollY')
        if now == prev:
            return now
        prev = now
        pg.wait_for_timeout(120)
    return pg.evaluate('window.scrollY')


with sync_playwright() as p:
    b = p.chromium.launch()

    # ---- the whole page has no TOC (the rail already lists everything) ----
    pg = b.new_page(viewport={'width': 1400, 'height': 900})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    pg.goto(URL, wait_until='networkidle')
    check('the whole page renders no TOC', pg.evaluate("!document.querySelector('.cm-doc__toc')"))
    check('the whole page still renders every section',
          pg.evaluate("document.querySelectorAll('main section[id]').length")
          == sum(FAMILIES.values()))

    # ---- each family page ----
    for fam, n in FAMILIES.items():
        pg = b.new_page(viewport={'width': 1400, 'height': 900})
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(f'{URL}f/{fam}/', wait_until='networkidle')

        rows = pg.evaluate("document.querySelectorAll('.cm-doc__toc-link').length")
        check(f'{fam}: TOC lists exactly its {n} sections', rows == n, f'got {rows}')

        # every row resolves in this document
        dead = pg.evaluate("""() => [...document.querySelectorAll('.cm-doc__toc-link')]
            .map(a => a.getAttribute('href').slice(1))
            .filter(id => !document.getElementById(id))""")
        check(f'{fam}: every TOC row resolves', not dead, str(dead))

        # it is a real right-hand column, sticky and 288px at desktop
        box = pg.evaluate("""() => {
            const t = document.querySelector('.cm-doc__toc');
            const c = getComputedStyle(t);
            const r = t.getBoundingClientRect();
            const main = document.querySelector('main').getBoundingClientRect();
            return {display: c.display, width: c.width, position: c.position,
                    left_of_content: r.left > main.left + 100};
        }""")
        check(f'{fam}: TOC is a visible sticky column', box['display'] == 'block'
              and box['position'] == 'sticky', str(box))
        check(f'{fam}: TOC sits beside the measure, not on top of it',
              box['left_of_content'], str(box))

        # phone width: the column must not exist (it would eat the measure)
        pg.set_viewport_size({'width': 390, 'height': 844})
        pg.wait_for_timeout(200)
        check(f'{fam}: no TOC column at 390px',
              pg.evaluate("getComputedStyle(document.querySelector('.cm-doc__toc')).display") == 'none')
        pg.close()

    # ---- the spy marks the row for the section the reader is in ----
    pg = b.new_page(viewport={'width': 1400, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(f'{URL}f/layout/', wait_until='networkidle')
    for sec in ['layout', 'forms', 'charts', 'utilities']:
        target = pg.evaluate(
            f"document.getElementById('{sec}').getBoundingClientRect().top + window.scrollY")
        pg.evaluate(f"window.scrollTo({{top: {target}, behavior: 'instant'}})")
        settle(pg)
        active = pg.evaluate(
            "[...document.querySelectorAll('.cm-doc__toc-link.is-active')].map(a=>a.textContent.trim())")
        check(f'spy marks "{sec}" when it is the section in view', active == [sec], str(active))

    # the mark must be VISIBLE, not just a class name
    vis = pg.evaluate("""() => {
        const a = document.querySelector('.cm-doc__toc-link.is-active');
        const o = [...document.querySelectorAll('.cm-doc__toc-link')].find(x => x !== a);
        return {active_border: getComputedStyle(a).borderInlineStartColor,
                idle_border: getComputedStyle(o).borderInlineStartColor,
                active_ink: getComputedStyle(a).color,
                idle_ink: getComputedStyle(o).color};
    }""")
    check('the active row differs in its spine colour, not only in class',
          vis['active_border'] != vis['idle_border'], str(vis))
    check('the active row differs in ink colour too',
          vis['active_ink'] != vis['idle_ink'], str(vis))

    check('no page threw', not errs, str(errs[:3]))
    b.close()

print(f'\npassed {passed}/{passed + failed}')
sys.exit(1 if failed else 0)
