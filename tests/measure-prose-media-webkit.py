"""Prose media blocks: what does the library give an image in a post?

`.cm-prose` and `.cm-typeset` are the two prose systems. Before this cycle
neither named `img`, `figure`, `figcaption` or `video`, so a screenshot a
renderer emitted arrived at the platform's defaults: the figure carried the
UA's own inline margin (off the rail its paragraph is set to), the caption
was byte-identical to body copy, and a 1200px `<video>` overflowed a 390px
column outright.

This probe measures that markup in real WebKit, in BOTH systems, at an
iPhone viewport and at desktop, and prints the numbers rather than an
opinion. Measuring only `.cm-prose` would report the Typeset half as fixed:
`.cm-typeset`'s own `:where(*)` reset is zero-specificity and beats a bare
`figure img` descendant rule, so the two systems need the rules stated
separately and both are measured here.

Run:  /root/.venvs/mau/bin/python tests/measure-prose-media-webkit.py [base-url]
"""
import sys
from playwright.sync_api import sync_playwright
import os

BASE = sys.argv[1] if len(sys.argv) > 1 else (os.environ.get('CLI_MONO_URL') or 'http://127.0.0.1:4471/')
URL = BASE + 'f/prose/'
passed = failed = 0


def check(name, cond, extra=''):
    global passed, failed
    if cond:
        passed += 1
        print('ok   ' + name)
    else:
        failed += 1
        print('FAIL ' + name + (' :: ' + str(extra) if extra else ''))


# A 1200px-wide image is the case that matters: every real screenshot is
# wider than a phone, and it is the one the library never handled. The
# container class is injected by `measure()` so the same fixture serves both
# systems.
FIXTURE = """
<div id="probe-host" style="position:absolute;left:-9999px;top:0;width:390px">
  <div id="probe-prose">
    <p id="probe-lead">the paragraph the image must line up with</p>
    <figure id="probe-figure">
      <img id="probe-img" width="1200" height="600" alt="a wide screenshot">
      <figcaption id="probe-cap">fig 1. the caption</figcaption>
    </figure>
    <video id="probe-video" width="1200" height="600"></video>
  </div>
</div>
"""

READ = """() => {
    const lead = document.getElementById('probe-lead');
    const fig  = document.getElementById('probe-figure');
    const img  = document.getElementById('probe-img');
    const cap  = document.getElementById('probe-cap');
    const vid  = document.getElementById('probe-video');
    const r = (el) => { const b = el.getBoundingClientRect();
        return {l: +b.left.toFixed(2), r: +b.right.toFixed(2), w: +b.width.toFixed(2)}; };
    const cs = (el, p) => getComputedStyle(el).getPropertyValue(p).trim();
    return {
        lead: r(lead), fig: r(fig), img: r(img), cap: r(cap), vid: r(vid),
        figMarginInlineStart: cs(fig, 'margin-inline-start'),
        imgMaxWidth: cs(img, 'max-width'),
        imgBorderWidth: cs(img, 'border-top-width'),
        imgBorderRadius: cs(img, 'border-top-left-radius'),
        capFontSize: cs(cap, 'font-size'),
        capColor:    cs(cap, 'color'),
        bodyFontSize: cs(lead, 'font-size'),
        vidMaxWidth: cs(vid, 'max-width'),
    };
}"""


def measure(pg, system, width):
    """Inject the fixture inside `system`, read it, assert, print."""
    pg.evaluate("""(args) => {
        const old = document.getElementById('probe-host');
        if (old) old.remove();
        const d = document.createElement('div');
        d.innerHTML = args.html.replace('id="probe-prose"',
                                        'id="probe-prose" class="' + args.system + '"');
        document.body.appendChild(d.firstElementChild);
    }""", {'html': FIXTURE, 'system': system})
    pg.wait_for_timeout(60)   # settle: on this house style a 0.01ms transition is not instant
    m = pg.evaluate(READ)
    print('\n--- %s @ %spx ---' % (system, width))
    for k, v in m.items():
        print('    %-22s %s' % (k, v))

    check('[%s %s] the image fits its column' % (system, width),
          m['img']['r'] <= m['lead']['r'] + 0.5 and m['img']['w'] <= m['lead']['w'] + 0.5,
          'img %s vs lead %s' % (m['img'], m['lead']))
    check('[%s %s] the image starts on the paragraph rail' % (system, width),
          abs(m['img']['l'] - m['lead']['l']) < 0.5,
          'img.l %s vs lead.l %s' % (m['img']['l'], m['lead']['l']))
    check('[%s %s] the figure box matches the paragraph box' % (system, width),
          abs(m['fig']['w'] - m['lead']['w']) < 0.5,
          'fig %s vs lead %s' % (m['fig'], m['lead']))
    check('[%s %s] the video fits its column' % (system, width),
          m['vidMaxWidth'] != 'none' and m['vid']['w'] <= m['lead']['w'] + 0.5,
          'vidMaxWidth %s vid %s lead %s' % (m['vidMaxWidth'], m['vid'], m['lead']))
    check('[%s %s] the video starts on the paragraph rail' % (system, width),
          abs(m['vid']['l'] - m['lead']['l']) < 0.5,
          'vid.l %s vs lead.l %s' % (m['vid']['l'], m['lead']['l']))
    # The caption is the one claim assertable without a reference image:
    # measuring byte-identical to body copy means it IS body copy.
    check('[%s %s] the caption is set apart from body copy' % (system, width),
          m['capFontSize'] != m['bodyFontSize'] and m['capColor'] != 'rgb(232, 232, 232)',
          'cap %s/%s vs body %s' % (m['capFontSize'], m['capColor'], m['bodyFontSize']))
    # The frame. Deliberately a COMPUTED value and not a source grep: the
    # interesting question is not whether the declaration exists but whether
    # it reaches the image, and inside `.cm-typeset` it did not - the
    # zero-specificity `:where(*)` reset outranks a bare `figure img`.
    check('[%s %s] the image is FRAMED, not bare' % (system, width),
          m['imgBorderWidth'] != '0px' and m['imgMaxWidth'] == '100%',
          'border %s max-width %s' % (m['imgBorderWidth'], m['imgMaxWidth']))


with sync_playwright() as p:
    b = p.webkit.launch()
    for width in (390, 320, 1280):
        pg = b.new_page(viewport={'width': width, 'height': 844})
        pg.set_default_timeout(180000)  # starved box: 27s+ to boot

        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(URL, wait_until='networkidle')
        pg.wait_for_function("() => document.documentElement.classList.contains('cm-js')",
                             timeout=180000)
        check('[%spx] no page errors' % width, not errs, str(errs[:2]))
        for system in ('cm-prose', 'cm-typeset'):
            measure(pg, system, width)
        pg.close()

    # --- the NON-REGRESSION half: `.cm-media` is the library's own opt-in
    # frame and it must keep its own box. `figure img` is (0,0,2); a
    # `.cm-media img` at (0,1,1) outranks it, so the component must not be
    # dragged onto the element defaults. This is the direction the
    # `:not([class])` trap fails in, and nothing else here would see it.
    # On the WHOLE page, not the family route: `.cm-media` is demonstrated in
    # the `surface` section, and `f/prose/` does not render it - the first
    # version of this check read `null is not an object (evaluating
    # 'f.querySelector')` for exactly that reason.
    pg = b.new_page(viewport={'width': 390, 'height': 844})
    pg.goto(BASE, wait_until='networkidle')
    pg.wait_for_function("() => document.documentElement.classList.contains('cm-js')",
                         timeout=180000)
    m = pg.evaluate("""() => {
        const f = document.querySelector('figure.cm-media');
        if (!f) return {missing: true};
        const i = f.querySelector('img');
        const cs = (el, p) => getComputedStyle(el).getPropertyValue(p).trim();
        return {figMargin: cs(f, 'margin-top'),
                imgW: cs(i, 'width'), imgRadius: cs(i, 'border-top-left-radius'),
                imgBorder: cs(i, 'border-top-width')};
    }""")
    print('\n--- .cm-media opt-in frame ---')
    for k, v in m.items():
        print('    %-22s %s' % (k, v))
    check('the .cm-media specimen is on the page at all', not m.get('missing'), m)
    check('the .cm-media frame keeps its own box off the element default',
          not m.get('missing') and (m['imgRadius'] != '0px' or m['imgBorder'] != '0px'),
          m)
    pg.close()
    b.close()

print('\n%d passed, %d failed' % (passed, failed))
sys.exit(1 if failed else 0)
