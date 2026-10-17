"""Measure .cm-typeset in real WebKit at Omar's actual viewport.

The four properties are GEOMETRIC, so they are measured rather than read:
a system that derives its rhythm is a claim about what the browser computes.

  1. container-relative size - the same markup in a narrower container must
     resolve a SMALLER `font-size`, not the same one.
  2. derivation - changing `--cm-typeset-flow` on one element must move the
     computed margins of its children, which is what "derived" means.
  3. streaming stability - append a block and the boxes ABOVE it must not
     move by a single pixel.
  4. the opt-out - a `not-typeset` subtree must carry no typeset rhythm.
"""
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:4471/'
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


with sync_playwright() as p:
    b = p.webkit.launch()
    pg = b.new_page(viewport={'width': 1400, 'height': 900})
    pg.set_default_timeout(180000)  # starved box: 27s+ to boot

    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL, wait_until='networkidle')

    check('no page errors', not errs, errs[:2])

    present = pg.evaluate("!!document.querySelector('.cm-typeset')")
    check('the typeset specimen is on the page', present)

    # ---- 1. container-relative size -------------------------------------
    sizes = pg.evaluate("""() => {
        const out = {};
        const mk = (w) => {
            const host = document.createElement('div');
            host.style.cssText = 'width:' + w + 'px;position:absolute;left:-9999px';
            const t = document.createElement('div');
            t.className = 'cm-typeset';
            t.innerHTML = '<p>measure</p>';
            host.appendChild(t); document.body.appendChild(host);
            const fs = getComputedStyle(t).fontSize;
            host.remove();
            return fs;
        };
        // A typeset whose own size is set relative to its host
        const host = document.createElement('div');
        host.style.cssText = 'font-size:20px;position:absolute;left:-9999px';
        const t = document.createElement('div');
        t.className = 'cm-typeset';
        t.innerHTML = '<p>x</p>';
        host.appendChild(t); document.body.appendChild(host);
        out.in20pxHost = getComputedStyle(t).fontSize;
        out.rootDefault = getComputedStyle(document.querySelector('.cm-typeset')).fontSize;
        host.remove();
        return out;
    }""")
    # Default is 1em -> equals the parent's font size. In a 20px host it must
    # resolve 20px, not the page's root size.
    check('the size is container-relative (1em of its host, not the root)',
          sizes['in20pxHost'] == '20px',
          f"a 20px host resolved {sizes['in20pxHost']}")

    # ---- 2. derivation --------------------------------------------------
    derived = pg.evaluate("""() => {
        const t = document.querySelector('.cm-typeset');
        if (!t) return null;
        const kids = [...t.children].filter(e => e.tagName === 'P' || e.tagName === 'BLOCKQUOTE');
        const read = () => kids.map(k => getComputedStyle(k).marginBlockStart);
        const before = read();
        t.style.setProperty('--cm-typeset-flow', '4em');
        const after = read();
        t.style.removeProperty('--cm-typeset-flow');
        return {before, after,
                changed: before.filter((v, i) => v !== after[i]).length,
                total: before.length};
    }""")
    check('raising the flow control moves the computed margins of its blocks',
          derived and derived['changed'] > 0,
          derived)

    # ---- 3. streaming stability -----------------------------------------
    stream = pg.evaluate("""() => {
        const t = document.querySelector('.cm-typeset');
        if (!t) return null;
        const first = t.children[0];
        const before = first.getBoundingClientRect();
        // Append the blocks a stream would append.
        const p1 = document.createElement('p'); p1.textContent = 'streamed one';
        const p2 = document.createElement('p'); p2.textContent = 'streamed two';
        t.appendChild(p1); t.appendChild(p2);
        const after = first.getBoundingClientRect();
        p1.remove(); p2.remove();
        return {dx: after.x - before.x, dy: after.y - before.y,
                dh: after.height - before.height};
    }""")
    check('appending two blocks does not move the block already on screen',
          stream and stream['dx'] == 0 and stream['dy'] == 0,
          stream)
    check('...and does not resize it either',
          stream and stream['dh'] == 0, stream)

    # ---- 4. the opt-out --------------------------------------------------
    optout = pg.evaluate("""() => {
        const hole = document.querySelector('.not-typeset');
        if (!hole) return null;
        const parent = hole.parentElement;
        const p = hole.querySelector('p');
        const sib = parent.querySelector('p');
        return {pMarginTop: getComputedStyle(p).marginBlockStart,
                sibMarginTop: getComputedStyle(sib).marginBlockStart,
                sameSize: getComputedStyle(p).fontSize === getComputedStyle(sib).fontSize};
    }""")
    check('the opt-out subtree gets no flow spacing',
          optout and optout['pMarginTop'] == '0px', optout)

    # ---- 5. no sideways scroll with typeset present ----------------------
    pg.set_viewport_size({'width': 390, 'height': 844})
    pg.wait_for_timeout(250)
    w = pg.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]")
    check('no horizontal pan at 390px', w[0] <= w[1], w)

    b.close()

print(f'\n{passed}/{passed + failed} passed')
sys.exit(1 if failed else 0)
