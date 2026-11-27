#!/usr/bin/env python3
"""Status colour, measured in WebKit: the hue a state paints, in both themes,
with colour on (the default) and inside data-cm-chroma="off".

WHY THIS FILE EXISTS. tests/run.mjs proves the CSS is written right: every
state rule reads `var(--tone, <grey>)`, every setter lists its state, the
token hexes are AA. None of that proves a browser resolves it. A setter that
loses a specificity fight, a `--tone` that is inherited from the wrong
ancestor, or an `initial` that a browser does not treat as invalid would all
pass the suite and paint the wrong colour.

So the specimen in #chroma (surfaces page) is measured: two columns of the
same markup, the first at the default and the second inside
data-cm-chroma="off". For each probe the computed colour of the painted part
must be the theme's --chroma-<role> in the first column and must NOT be any
hue in the second (it must equal the grey the same probe paints without any
tone). Text probes are also checked for 4.5:1 against the background they
actually sit on.

Usage: verify-status-colour.py [URL]   (or OEM_UI_URL)
"""
import os
import re
import sys

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('OEM_UI_URL', 'http://127.0.0.1:4321/')
URL = BASE.rstrip('/') + '/f/surfaces/'
fails = []
passed = 0


def check(name, ok, detail=''):
    global passed
    print(('ok    ' if ok else 'FAIL  ') + name + ('' if ok else '  :: ' + str(detail)))
    if ok:
        passed += 1
    else:
        fails.append(name)


# selector inside a column, role, property, is it text (needs 4.5:1)
PROBES = [
    ('.cm-chip--ok', 'ok', 'color', True),
    ('.cm-chip--warn', 'warn', 'color', True),
    ('.cm-chip--err', 'err', 'color', True),
    ('.cm-chip--info', 'info', 'color', True),
    ('.cm-alert--err', 'err', 'border-left-color', False),
    ('.cm-alert--warn', 'warn', 'border-left-color', False),
    ('.cm-alert--ok', 'ok', 'border-left-color', False),
    ('.cm-alert--info', 'info', 'border-left-color', False),
    ('.cm-status-code--ok', 'ok', 'color', True),
    ('.cm-status-code--warn', 'warn', 'color', True),
    ('.cm-status-code--err', 'err', 'color', True),
    ('.cm-method--delete', 'err', 'color', True),
    ('.cm-btn--danger', 'err', 'border-top-color', False),
    ('.cm-field__error', 'err', 'color', True),
    ('.cm-stat.cm-tone--ok', 'ok', 'border-top-color', False),
    ('.cm-dot.cm-tone--err', 'err', 'background-color', False),
]

READ = r"""([sel, prop]) => {
  const cols = [...document.querySelectorAll('#chroma .cm-surface.cm-surface--flat.cm-stack')];
  return cols.map((c) => {
    const el = c.querySelector(sel);
    if (!el) return null;
    const v = getComputedStyle(el).getPropertyValue(prop);
    // the opaque background the element actually sits on
    let bg = null;
    for (let a = el; a; a = a.parentElement) {
      const b = getComputedStyle(a).backgroundColor;
      const m = /rgba?\(([^)]+)\)/.exec(b);
      if (m) { const p = m[1].split(',').map(Number); if (p.length < 4 || p[3] > 0) { bg = b; if (p.length < 4 || p[3] >= 1) break; } }
    }
    return {v, bg, off: c.getAttribute('data-cm-chroma')};
  });
}"""

TOKENS = r"""() => {
  const s = getComputedStyle(document.querySelector('#chroma .cm-surface.cm-surface--flat.cm-stack'));
  const o = {};
  for (const r of ['ok', 'warn', 'err', 'info']) o[r] = s.getPropertyValue('--chroma-' + r).trim();
  return o;
}"""


def rgb(v):
    m = re.search(r'rgba?\(([^)]+)\)', v or '')
    if m:
        p = [float(x) for x in m.group(1).replace('/', ',').split(',') if x.strip()]
        return tuple(int(round(x)) for x in p[:3]), (p[3] if len(p) > 3 else 1.0)
    m = re.fullmatch(r'#([0-9a-fA-F]{6})', (v or '').strip())
    if m:
        h = m.group(1)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)), 1.0
    return None, None


def lum(c):
    def ch(x):
        x /= 255
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def is_grey(c):
    return max(c) - min(c) <= 12


with sync_playwright() as p:
    b = p.webkit.launch()
    for theme in ('dark', 'light'):
        ctx = b.new_context(viewport={'width': 1280, 'height': 900})
        ctx.add_init_script(f"try {{ localStorage.setItem('cm-theme', '{theme}'); }} catch (e) {{}}")
        pg = ctx.new_page()
        pg.goto(URL, wait_until='load', timeout=240000)
        # The guard sets data-theme="light" and leaves dark as the default.
        got_theme = pg.evaluate("document.documentElement.getAttribute('data-theme') || 'dark'")
        check(f'{theme}: the page is in the {theme} theme', got_theme == theme, got_theme)
        cols = pg.evaluate("document.querySelectorAll('#chroma .cm-surface.cm-surface--flat.cm-stack').length")
        check(f'{theme}: the #chroma specimen has two columns', cols == 2, cols)
        offs = pg.evaluate("[...document.querySelectorAll('#chroma .cm-surface.cm-surface--flat.cm-stack')].map(c => c.getAttribute('data-cm-chroma'))")
        check(f'{theme}: only the second column is off', offs == [None, 'off'], offs)
        tok = {k: rgb(v)[0] for k, v in pg.evaluate(TOKENS).items()}
        check(f'{theme}: the four tokens resolve to colours', all(tok.values()), tok)
        for sel, role, prop, text in PROBES:
            on, off = pg.evaluate(READ, [sel, prop])
            if not on or not off:
                check(f'{theme}: {sel} is in both columns', False, (on, off))
                continue
            c_on, _ = rgb(on['v'])
            c_off, _ = rgb(off['v'])
            check(f'{theme}: {sel} {prop} is --chroma-{role} by default', c_on == tok[role], f"{on['v']} vs {tok[role]}")
            check(f'{theme}: {sel} {prop} is grey with data-cm-chroma="off"', c_off is not None and is_grey(c_off), off['v'])
            if text and on['bg']:
                bg_c, _ = rgb(on['bg'])
                r = ratio(c_on, bg_c)
                check(f'{theme}: {sel} text is AA on its background ({r:.2f}:1)', r >= 4.5, f"{on['v']} on {on['bg']}")
        # The danger button's hover fill, through a real pointer.
        btn = pg.locator('#chroma .cm-surface.cm-surface--flat.cm-stack').nth(0).locator('.cm-btn--danger')
        btn.scroll_into_view_if_needed()
        btn.hover()
        pg.wait_for_timeout(400)
        hv = btn.evaluate("e => [getComputedStyle(e).backgroundColor, getComputedStyle(e).color]")
        fill, ink = rgb(hv[0])[0], rgb(hv[1])[0]
        check(f'{theme}: a hovered danger button fills with --chroma-err', fill == tok['err'], hv)
        if fill and ink:
            check(f'{theme}: its label is AA on the fill ({ratio(fill, ink):.2f}:1)', ratio(fill, ink) >= 4.5, hv)
        ctx.close()
    b.close()

print(f'\n{passed} passed, {len(fails)} failed')
sys.exit(1 if fails else 0)
