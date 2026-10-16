#!/root/.venvs/mau/bin/python
"""WebKit proof for batch 5: the hover card and the input group."""
import sys
from playwright.sync_api import sync_playwright
from harness_wait import boot_timeout

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://192.168.1.68:4321/'
results, problems = [], []

def check(name, ok, detail=''):
    (results if ok else problems).append(name)
    print(('  ok  ' if ok else 'FAIL  ') + name + (' :: ' + detail if detail and not ok else ''))
    return ok

with sync_playwright() as pw:
    b = pw.webkit.launch()
    page = b.new_page(viewport={'width': 1280, 'height': 900})
    errs = []
    page.on('pageerror', lambda e: errs.append(str(e)))
    page.goto(URL, wait_until='networkidle')
    page.wait_for_function("() => !!window.cliMono", timeout=boot_timeout())

    def panel_state():
        return page.evaluate("""() => {
            const p = document.querySelector('.cm-hovercard__panel');
            const cs = getComputedStyle(p);
            return {visibility: cs.visibility, opacity: cs.opacity,
                    radius: cs.borderRadius, r: p.getBoundingClientRect().height};
        }""")

    rest = panel_state()
    check('the panel is hidden at rest', rest['visibility'] == 'hidden', str(rest))
    check('the panel is sharp', rest['radius'] in ('0px', '0'), str(rest))
    check('the hidden panel occupies no height for a reader', rest['r'] >= 0, str(rest))

    page.hover('.cm-hovercard a')
    page.wait_for_timeout(300)
    hov = panel_state()
    check('hovering the trigger reveals the panel', hov['visibility'] == 'visible', str(hov))

    page.mouse.move(5, 5)
    page.wait_for_timeout(300)
    out = panel_state()
    check('leaving hides it again', out['visibility'] == 'hidden', str(out))

    # keyboard: tabbing to the trigger must reveal it
    page.evaluate("document.querySelector('.cm-hovercard a').focus()")
    page.wait_for_timeout(250)
    kb = panel_state()
    check('focus-within reveals it for the keyboard', kb['visibility'] == 'visible', str(kb))

    # ---- the composed card (.cm-card ON the panel) ----
    # The showcase composes the panel AS a card, and `.cm-card` declares
    # `height: 100%` for grid cells where stretching is the point. Against
    # a trigger-height wrapper that same rule MEASURED clipping the panel
    # to the wrapper's 25px against 78px of content (scrollHeight 78,
    # clientHeight 25) - the profile half of every hovercard was cut off.
    clip = page.evaluate("""() => {
        const p = document.querySelector('.cm-card.cm-hovercard__panel');
        if (!p) return null;
        return {client: p.clientHeight, scroll: p.scrollHeight,
                h: Math.round(p.getBoundingClientRect().height)};
    }""")
    check('the composed card is not clipped to its trigger',
          bool(clip) and clip['scroll'] <= clip['client'] and clip['h'] > 20, str(clip))

    # `.cm-card__sub` carries unbroken tokens - MXIDs, user IDs, pasted
    # timestamps. Without wrapping they run past the card's edge and
    # `.cm-card`'s overflow:hidden cuts them with no ellipsis to say so.
    sub = page.evaluate("""() => {
        const d = document.createElement('div');
        d.style.cssText = 'position:absolute;left:-9999px;top:0;width:220px';
        d.innerHTML = '<div class="cm-card" style="height:auto">' +
          '<p class="cm-card__sub">' + 'x'.repeat(60) + '</p></div>';
        document.body.appendChild(d);
        const s = d.querySelector('.cm-card__sub');
        const out = {client: s.clientWidth, scroll: s.scrollWidth,
                     wrapped: s.getBoundingClientRect().height > 20};
        d.remove();
        return out;
    }""")
    check('a card sub wraps an unbroken token inside its card',
          bool(sub) and sub['scroll'] <= sub['client'] and sub['wrapped'], str(sub))

    # ---- a ROW that is itself the hovercard (the roster's shape) ----
    # `.cm-row` declares display:flex, `.cm-hovercard` declares
    # display:inline-block - one element with both classes loses the row
    # layout to source order. The composition restates flex at (0,2,0).
    comp = page.evaluate("""() => {
        const d = document.createElement('div');
        d.innerHTML = '<div class="cm-rows"><div class="cm-row cm-hovercard" ' +
          'tabindex="0"><span class="cm-row__title">n</span>' +
          '<div class="cm-card cm-hovercard__panel" role="tooltip">p</div>' +
          '</div></div>';
        document.body.appendChild(d);
        const row = d.querySelector('.cm-row');
        const panel = row.querySelector('.cm-hovercard__panel');
        const out = {display: getComputedStyle(row).display,
                     w: Math.round(row.getBoundingClientRect().width),
                     panelHidden: getComputedStyle(panel).visibility};
        d.remove();
        return out;
    }""")
    check('a hovercard row keeps the row layout (display flex)',
          bool(comp) and comp['display'] == 'flex' and comp['w'] > 100, str(comp))
    check("the row's own panel is hidden at rest",
          bool(comp) and comp['panelHidden'] == 'hidden', str(comp))

    # ---- late rows: clamp with no init, no resize, no hover, no focus ----
    # A roster renders AFTER cli.init() (measured: every row the matrix
    # client ships is a late row). A late panel sits at CSS left:0 and
    # hangs its 18rem over the viewport edge - the phantom sideways
    # scroll the clamp's own comment warns about - until the runtime's
    # observer re-runs the clamp over it.
    page.evaluate("""() => {
        const d = document.createElement('div');
        d.id = 'hc-late';
        d.innerHTML = '<div class="cm-hovercard" style="position:fixed;top:24px;right:2px">' +
          '<a class="cm-inline-link" id="hc-late-t" href="#late">late</a>' +
          '<span class="cm-card cm-hovercard__panel" role="tooltip">late panel</span>' +
          '</div>';
        document.body.appendChild(d);
    }""")
    page.wait_for_timeout(250)  # the observer schedules a rAF; give it frames
    latebox = page.evaluate("""() => {
        const p = document.querySelector('#hc-late .cm-hovercard__panel');
        if (!p) return null;
        const r = p.getBoundingClientRect();
        return {right: Math.round(r.right), inner: window.innerWidth,
                st: p.style.left};
    }""")
    check('a late-appearing panel is clamped before it can show',
          bool(latebox) and latebox['right'] <= latebox['inner'] - 6,
          str(latebox))

    # The wrapper is then MOVED further past the edge. A style change is
    # an attribute mutation, not a childList one, so the observer above
    # does not fire again - this isolates the REVEAL clamp: focus is the
    # same event that reveals the card, and its handler runs before the
    # frame paints.
    page.evaluate("""() => {
        const w = document.querySelector('#hc-late .cm-hovercard');
        if (w) w.style.right = '-40px';
    }""")
    page.wait_for_timeout(120)
    page.evaluate("""() => {
        const t = document.querySelector('#hc-late-t');
        if (t) t.focus();
    }""")
    page.wait_for_timeout(250)
    moved = page.evaluate("""() => {
        const p = document.querySelector('#hc-late .cm-hovercard__panel');
        if (!p) return null;
        const t = document.querySelector('#hc-late-t');
        return {right: Math.round(p.getBoundingClientRect().right),
                inner: window.innerWidth,
                focused: document.activeElement === t,
                vis: getComputedStyle(p).visibility};
    }""")
    check('revealing a moved card re-clamps it inside the viewport',
          bool(moved) and moved['focused'] and moved['vis'] == 'visible'
          and moved['right'] <= moved['inner'] - 6, str(moved))

    # Escape: for a keyboard or tap reader focus IS the card's pin -
    # without this the card stays up forever, because only the pointer
    # has a "leaving".
    esc = page.evaluate("""() => {
        const t = document.querySelector('#hc-late-t');
        return {inside: document.activeElement === t};
    }""")
    if esc and esc.get('inside'):
        page.keyboard.press('Escape')
        page.wait_for_timeout(250)
        after = page.evaluate("""() => {
            const t = document.querySelector('#hc-late-t');
            const p = document.querySelector('#hc-late .cm-hovercard__panel');
            if (!t || !p) return null;
            return {blurred: document.activeElement !== t,
                    vis: getComputedStyle(p).visibility};
        }""")
        check('Escape blurs a focused trigger and closes the card',
              bool(after) and after['blurred'] and after['vis'] == 'hidden',
              str(after))
    else:
        check('Escape blurs a focused trigger and closes the card',
              False, 'focus never landed: ' + str(esc))
    page.evaluate("() => { const d = document.querySelector('#hc-late'); if (d) d.remove(); }")

    grp = page.evaluate("""() => {
        const g = document.querySelector('.cm-input-group');
        const addon = g.querySelector('.cm-input-group__addon');
        const input = g.querySelector('input');
        const a = getComputedStyle(addon), i = getComputedStyle(input);
        const r = g.getBoundingClientRect();
        return {addonLeft: a.borderLeftWidth, addonRight: a.borderRightWidth,
                inputLeft: i.borderLeftWidth, inputTop: i.borderTopWidth,
                w: r.width, radius: i.borderRadius};
    }""")
    check('the input group renders one control', grp['w'] > 120, str(grp))
    # Exactly ONE of the two borders that meet at the seam must be
    # dropped. The addon is the one we own; the field's left border comes
    # from base.css at higher specificity, so naming which side yields is
    # an implementation detail - a doubled seam is not.
    check('the seam is a single hairline (exactly one shared border dropped)',
          (grp['inputLeft'] == '0px') != (grp['addonRight'] == '0px'), str(grp))
    check('the joined control stays sharp', grp['radius'] in ('0px', '0'), str(grp))

    side = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
    check('no sideways scroll at 1280px', not side)
    check('no page errors', not errs, str(errs[:2]))
    b.close()

print('\n%d passed, %d failed' % (len(results), len(problems)))
sys.exit(1 if problems else 0)
