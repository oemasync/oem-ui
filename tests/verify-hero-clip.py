#!/usr/bin/env python3
"""verify-hero-clip.py - regression guard for the hero title clip (2026-10-20).

The root hero (`.cm-hero.cm-card`) is a card, so `overflow:hidden` clips any
word wider than the card's PADDING box. Measured 2026-10-20: at 44.8px the
word "Everything" is ~260px wide but the box is 198px at a 320px viewport,
so the card's `overflow:hidden` cuts the right edge of the word. The clip
band was 320-368px (plus a 1px sub-pixel cut at 372) under the default
`2rem + 4vw` ramp; the fix is a narrow-band ramp
`clamp(var(--head-h1), 17.5vw - 21px, 4rem)` for `max-width: 392px`.

This harness re-measures the invariant the fix protects, against the
PADDING-box clip line (NOT the border box - the first cut used the border
box and under-reported by the border width): for every word of the hero
title, its right edge must not be past the card's padding-box right at any
width from 320 to 404. A word ending flush on the clip line still shows a
cut glyph tip in WebKit, so the pass threshold is `over <= 0`, not `< 0`.

Run: PLAYWRIGHT_BROWSERS_PATH=... python tests/verify-hero-clip.py
Exit 0 = every word fits at every width; exit 1 = a word is clipped.
"""
import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("OEM_UI_BASE", "http://127.0.0.1:4471/")
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 "
      "Safari/604.1")

JS = """
() => {
  const card = document.querySelector('#hero .cm-card');
  const h2 = document.querySelector('#hero .cm-hero__title');
  if (!card || !h2) return { missing: true };
  const cs = getComputedStyle(card);
  // padding-box right = the true overflow:hidden clip line.
  const clipRight = card.getBoundingClientRect().right - parseFloat(cs.borderLeftWidth);
  const out = { font: getComputedStyle(h2).fontSize, clips: [] };
  const walker = document.createTreeWalker(h2, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    const txt = node.nodeValue;
    let idx = 0;
    while (idx < txt.length) {
      const end = txt.indexOf(' ', idx);
      const wend = end === -1 ? txt.length : end;
      const word = txt.slice(idx, wend).trim();
      if (word) {
        const r = document.createRange();
        const start = idx + (txt.slice(idx, wend).length - word.length);
        r.setStart(node, start);
        r.setEnd(node, start + word.length);
        const rects = r.getClientRects();
        if (rects.length) {
          const right = Math.max(...[...rects].map(x => x.right));
          const over = right - clipRight;
          if (over > 0) out.clips.push({ word, over: Math.round(over * 10) / 10 });
        }
      }
      idx = wend + 1;
    }
  }
  return out;
}
"""

WIDTHS = list(range(320, 405, 4))


def main():
    fails = 0
    with sync_playwright() as p:
        b = p.webkit.launch()
        for w in WIDTHS:
            ctx = b.new_context(viewport={"width": w, "height": 844},
                                is_mobile=True, has_touch=True,
                                device_scale_factor=2, user_agent=UA)
            pg = ctx.new_page()
            pg.goto(BASE, wait_until="networkidle")
            pg.wait_for_timeout(150)
            r = pg.evaluate(JS)
            ctx.close()
            if r.get("missing"):
                print(f"w={w}: FAIL  hero card or title not found")
                fails += 1
                continue
            if r["clips"]:
                worst = max(c["over"] for c in r["clips"])
                words = ", ".join(f"'{c['word']}' +{c['over']}px" for c in r["clips"][:4])
                print(f"w={w}: FAIL  title {r['font']}: {words}  (worst +{worst}px past clip line)")
                fails += 1
            else:
                print(f"w={w}: ok    title {r['font']}, every word inside the padding box")
        b.close()
    if fails:
        print(f"\nHERO_CLIP_EXIT=1  ({fails}/{len(WIDTHS)} widths clip)")
        return 1
    print(f"\nHERO_CLIP_EXIT=0  ({len(WIDTHS)}/{len(WIDTHS)} widths clean)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
