#!/root/.venvs/mau/bin/python
"""The chart's INHERITED direction, through the batched init.

WHY THIS FILE EXISTS. `cmInitCharts()` reads every chart's width and
rendered direction first, then renders them all. Before that, each chart's
render asked `getComputedStyle()` for its direction right after the previous
chart wrote its markup, and every one of those reads waited on a style recalc
of the whole document: 11.3s of init on the showcase in WebKit, ~700ms per
cartesian or pie chart. The read now happens up front (`chReadDir`) and
reaches the renderer as an explicit `ltr` / `rtl`.

That moved the one path no other harness touches: a chart with NO `dir` of
its own, laid out right to left because an ANCESTOR is RTL. The showcase's
RTL specimen (`#cmc-rtl`) carries `dir="rtl"` itself, so it short-circuits
before any computed read, and `verify-chart.py` stays green whether this
path works or not.

HOW THE ASSERTIONS ARE WRITTEN. The LTR line chart (`#cmc-line`, no `dir`) is
cloned twice, unbound: once into a `dir="rtl"` wrapper, once into a
`dir="ltr"` one, and `cliMono.init(wrapper)` binds each the way a SPA would.
Neither clone carries a `dir`, so only the inherited direction can tell them
apart. Each is measured the way `verify-chart.py` measures the mirror (value
axis x, first/last category x, gridline extent), then the wrapper is resized,
which re-renders through the ResizeObserver path, and measured again. The RTL
clone must mirror the LTR one at BOTH moments, and must match the explicit
`dir="rtl"` specimen's orientation, so a renderer that drops the inherited
read fails here instead of going quiet. The LTR clone is the control: it must
NOT mirror, or the fixture is not discriminating.
"""
import os
import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('OEM_UI_URL', 'http://127.0.0.1:4471/')
fails = []


def check(name, ok, detail=''):
    print(('ok    ' if ok else 'FAIL  ') + name + ('' if ok else '  :: ' + str(detail)))
    if not ok:
        fails.append(name)


MEASURE = r"""(box) => {
  const svg = box.querySelector('svg');
  if (!svg) return null;
  const W = +svg.getAttribute('width');
  const labs = [...box.querySelectorAll('.cm-chart__tick-label')]
    .map(t => ({x: +t.getAttribute('x'), a: t.getAttribute('text-anchor')}));
  const val = labs.filter(t => t.a === 'start' || t.a === 'end').map(t => t.x);
  const cat = labs.filter(t => t.a === 'middle');
  const gx = [...box.querySelectorAll('.cm-chart__grid')]
    .flatMap(l => [+l.getAttribute('x1'), +l.getAttribute('x2')]).filter(n => !Number.isNaN(n));
  return {W, val: val.length ? val[0] : null,
          first: cat.length ? cat[0].x : null, last: cat.length ? cat[cat.length - 1].x : null,
          lo: gx.length ? Math.min(...gx) : null, hi: gx.length ? Math.max(...gx) : null};
}"""


def mirrored(m):
    # First category at the far (right) edge and the value axis on the right.
    return (m is not None and None not in (m['first'], m['last'], m['val'])
            and m['first'] > m['last'] and m['val'] > m['W'] / 2)


def plain(m):
    return (m is not None and None not in (m['first'], m['last'], m['val'])
            and m['first'] < m['last'] and m['val'] < m['W'] / 2)


with sync_playwright() as p:
    b = p.webkit.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.goto(URL, wait_until='load', timeout=180000)
    pg.wait_for_function('() => window.cliMono && document.querySelector("#cmc-line svg")', timeout=60000)

    explicit = pg.evaluate('(m) => (' + MEASURE + ')(document.getElementById("cmc-rtl"))')
    source = pg.evaluate('(m) => (' + MEASURE + ')(document.getElementById("cmc-line"))')
    check('positive control: the explicit dir="rtl" specimen renders mirrored', mirrored(explicit), explicit)
    check('positive control: the LTR source chart renders unmirrored', plain(source), source)

    pg.evaluate(r"""() => {
      const src = document.getElementById('cmc-line');
      if (src.hasAttribute('dir')) throw new Error('the source chart carries dir; the fixture would not test inheritance');
      for (const d of ['rtl', 'ltr']) {
        const wrap = document.createElement('div');
        wrap.id = 'inh-' + d;
        wrap.setAttribute('dir', d);
        wrap.style.width = '720px';
        const c = src.cloneNode(true);
        c.id = 'inh-chart-' + d;
        c.removeAttribute('data-cm-chart-bound');
        c.querySelector('.cm-chart__plot').innerHTML = '';
        wrap.appendChild(c);
        src.parentNode.insertBefore(wrap, src.nextSibling);
        window.cliMono.init(wrap);
      }
    }""")
    pg.wait_for_timeout(300)
    m = {d: pg.evaluate('(m) => (' + MEASURE + ')(document.getElementById("inh-chart-' + d + '"))') for d in ('rtl', 'ltr')}
    check('the clones carry no dir of their own (only the ancestor can decide)',
          pg.evaluate('() => !document.getElementById("inh-chart-rtl").hasAttribute("dir") && !document.getElementById("inh-chart-ltr").hasAttribute("dir")'))
    check('init: a chart inside an RTL ancestor renders mirrored', mirrored(m['rtl']), m['rtl'])
    check('init: the same chart inside an LTR ancestor does not (control)', plain(m['ltr']), m['ltr'])
    check('init: both clones drew the same plot width', m['rtl'] and m['ltr'] and m['rtl']['W'] == m['ltr']['W'], m)

    pg.evaluate("() => { for (const d of ['rtl', 'ltr']) document.getElementById('inh-' + d).style.width = '560px'; }")
    pg.wait_for_function("() => +document.querySelector('#inh-chart-rtl svg').getAttribute('width') !== %d" % (m['rtl']['W'] if m['rtl'] else -1), timeout=15000)
    pg.wait_for_timeout(300)
    r = {d: pg.evaluate('(m) => (' + MEASURE + ')(document.getElementById("inh-chart-' + d + '"))') for d in ('rtl', 'ltr')}
    check('resize: the RTL-ancestor chart re-rendered at the new width', r['rtl'] and m['rtl'] and r['rtl']['W'] < m['rtl']['W'], r)
    check('resize: and is still mirrored (the ResizeObserver path reads direction too)', mirrored(r['rtl']), r['rtl'])
    check('resize: the LTR control is still unmirrored', plain(r['ltr']), r['ltr'])
    check('no page error', not errors, errors)
    b.close()

print()
print('%d check(s) failed' % len(fails) if fails else 'an inherited RTL chart mirrors at init and after a resize')
sys.exit(1 if fails else 0)
