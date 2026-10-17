"""Does a `.cm-byline` separator strand at the end of a wrapped line?

The library deleted the footer's separator ELEMENT for exactly this
reason (d2ec654) and replaced it with a `::before` on the item it
PRECEDES. `.cm-byline__sep` is still an element inside a
`flex-wrap: wrap` row, so the same defect should be present.

The invariant that discriminates: NO VISUAL LINE ENDS WITH A
SEPARATOR. Measure it by grouping items into visual lines (distinct
`top` values) and asking whether the last item on any line is a
separator. A screenshot cannot see this; only geometry can.

Usage: /root/.venvs/mau/bin/python tests/probe-byline-sep.py
"""
import json
from playwright.sync_api import sync_playwright

URL = "http://192.168.1.68:4471/f/prose/"

PROBE = r"""
() => {
  const byline = document.querySelector('.cm-byline');
  if (!byline) return { error: 'no .cm-byline in the document' };
  const kids = [...byline.children].filter(el => el.getBoundingClientRect().height > 0);
  const lines = new Map();
  for (const el of kids) {
    const r = el.getBoundingClientRect();
    const key = Math.round(r.top);
    if (!lines.has(key)) lines.set(key, []);
    lines.get(key).push({ el, r });
  }
  const ordered = [...lines.entries()].sort((a, b) => a[0] - b[0]);
  const isSep = (el) => el.classList.contains('cm-byline__sep');
  const rows = ordered.map(([top, items]) => {
    items.sort((a, b) => a.r.left - b.r.left);
    const last = items[items.length - 1];
    const first = items[0];
    return {
      top,
      n: items.length,
      text: items.map(i => i.el.textContent.trim()).join(' | '),
      lastIsSep: isSep(last.el),
      left: Math.round(first.r.left),
      right: Math.round(last.r.right),
    };
  });
  const seps = [...byline.querySelectorAll('.cm-byline__sep')].map(el => {
    const r = el.getBoundingClientRect();
    return { text: el.textContent.trim(), top: Math.round(r.top), left: Math.round(r.left), right: Math.round(r.right) };
  });
  return {
    width: Math.round(byline.getBoundingClientRect().width),
    sepIsElement: seps.length > 0,
    sepCount: seps.length,
    seps,
    rowCount: rows.length,
    rows,
    anyLineEndsWithSep: rows.some(r => r.lastIsSep),
    bylineHeight: Math.round(byline.getBoundingClientRect().height),
  };
}
"""

NARROW_PROBE = r"""
() => {
  const b = document.querySelector('#__probehost .cm-byline');
  if (!b) return { error: 'host missing' };
  const kids = [...b.children].filter(el => el.getBoundingClientRect().height > 0);
  const lines = new Map();
  for (const el of kids) {
    const r = el.getBoundingClientRect();
    const k = Math.round(r.top);
    if (!lines.has(k)) lines.set(k, []);
    lines.get(k).push(el);
  }
  const rows = [...lines.entries()].sort((a, c) => a[0] - c[0]).map(([top, items]) => {
    items.sort((a, c) => a.getBoundingClientRect().left - c.getBoundingClientRect().left);
    const last = items[items.length - 1];
    return {
      top,
      text: items.map(e => e.textContent.trim()).join(' | '),
      lastIsSep: last.classList.contains('cm-byline__sep'),
      left: Math.round(items[0].getBoundingClientRect().left),
      right: Math.round(last.getBoundingClientRect().right),
    };
  });
  return {
    width: Math.round(b.getBoundingClientRect().width),
    rows,
    anyLineEndsWithSep: rows.some(r => r.lastIsSep),
    bylineHeight: Math.round(b.getBoundingClientRect().height),
  };
}
"""


def run(width, height):
    with sync_playwright() as p:
        b = p.webkit.launch()
        pg = b.new_page(viewport={"width": width, "height": height},
                        device_scale_factor=2)
        pg.emulate_media(reduced_motion="reduce")
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_function(
            "() => document.documentElement.classList.contains('cm-js') || !!window.cliMono",
            timeout=15000)
        pg.evaluate("() => document.fonts.ready")
        pg.wait_for_timeout(250)
        native = pg.evaluate(PROBE)
        pg.evaluate(
            """() => {
              const src = document.querySelector('.cm-byline');
              const host = document.createElement('div');
              host.id = '__probehost';
              host.style.cssText = 'width:190px';
              host.appendChild(src.cloneNode(true));
              document.body.appendChild(host);
            }""")
        pg.wait_for_timeout(150)
        narrow = pg.evaluate(NARROW_PROBE)
        b.close()
        return native, narrow


if __name__ == "__main__":
    for w, h in [(320, 667), (360, 780), (390, 844), (402, 874), (430, 932), (1280, 900)]:
        n, nn = run(w, h)
        print(f"--- {w}x{h}")
        print("   shipped  :", json.dumps(n))
        print("   narrow190:", json.dumps(nn))
