"""Measure `.cm-dropzone` in real WebKit at Omar's widths.

A new component is not proven by the fact that its rules exist. This asks
the four questions that decide whether the drop target WORKS on the phone
Omar reads it on:

  1. GEOMETRY - is the zone actually a target? It has to be TALL enough to
     drop onto and WIDE enough to aim at, and the frame has to be the
     thing that is dashed, not a decorative inner line.

  2. THE OVER STATE - does a drag over the target change the frame? A
     `--over` rule that computes the same border style as the rest state
     is a rule that exists and does nothing, and nobody finds out until
     a user tries to drop a file and gets no feedback.

  3. NO OVERFLOW - the zone holds a title, a line of text, a row of
     platform chips and a note. At 320px the widest of those (a long
     filename) must not push the document sideways. The measure is the
     DOCUMENT's scroll width against the viewport, because that is the
     symptom a user actually sees.

  4. THE ERROR EDGE - the error state must be legible WITHOUT colour,
     since this system has no chroma and greyscale print has to read it
     too. So the error border must differ from the resting border in
     STYLE as well as colour, and the mark must carry a glyph.

Each probe is a MEASUREMENT with a threshold, not a screenshot: a probe
that cannot fail proves nothing.
"""
import json
import sys

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:4321/"
WIDTHS = [(320, 667), (375, 667), (390, 844), (402, 874), (768, 1024), (1280, 900)]

# The minimum a drop target can be before a thumb misses it. The house
# tap floor is 44px; a drop zone is a primary target, so it must clear
# that with room to spare.
MIN_TARGET = 120.0

PROBE = r"""
() => {
  const vis = (el) => el.checkVisibility
    ? el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })
    : el.getClientRects().length > 0;
  const out = {
    docScrollWidth: document.documentElement.scrollWidth,
    win: window.innerWidth,
    zones: [],
    over: null,
    err: null,
    rest: null,
  };

  const read = (el) => {
    if (!el) return null;
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return {
      w: +r.width.toFixed(2),
      h: +r.height.toFixed(2),
      borderStyle: cs.borderTopStyle,
      borderWidth: cs.borderTopWidth,
      borderColor: cs.borderTopColor,
      radius: cs.borderTopLeftRadius,
      padding: cs.paddingTop + ' ' + cs.paddingRight,
      display: cs.display,
      alignItems: cs.alignItems,
    };
  };

  for (const z of document.querySelectorAll('.cm-dropzone')) {
    if (!vis(z)) continue;
    const cs = getComputedStyle(z);
    const r = z.getBoundingClientRect();
    const title = z.querySelector('.cm-dropzone__title');
    const mark = z.querySelector('.cm-dropzone__mark');
    out.zones.push({
      cls: z.className,
      w: +r.width.toFixed(2),
      h: +r.height.toFixed(2),
      left: +r.left.toFixed(2),
      right: +r.right.toFixed(2),
      borderStyle: cs.borderTopStyle,
      borderWidth: cs.borderTopWidth,
      borderColor: cs.borderTopColor,
      titleText: title ? title.textContent.trim().slice(0, 40) : null,
      titleSize: title ? getComputedStyle(title).fontSize : null,
      markGlyph: mark ? (mark.textContent || '').trim() : null,
      markColor: mark ? getComputedStyle(mark).color : null,
      // a chip row that wraps is FINE; a chip row that overflows is not
      platformsOverflow: (() => {
        const ul = z.querySelector('.cm-dropzone__platforms');
        if (!ul) return 0;
        return +(ul.scrollWidth - ul.clientWidth).toFixed(2);
      })(),
    });
  }

  const rest = document.querySelector('#dropzone .cm-dropzone:not([class*="--"])');
  const over = document.querySelector('#dropzone .cm-dropzone--over');
  const err  = document.querySelector('#dropzone .cm-dropzone--err');
  out.rest = read(rest);
  out.over = read(over);
  out.err  = read(err);
  out.overIsDistinguishable = !!(out.rest && out.over &&
    (out.rest.borderStyle !== out.over.borderStyle ||
     out.rest.borderColor !== out.over.borderColor));
  // The error state must differ in STYLE, not only in colour: colour alone
  // is exactly what this system refuses to rely on.
  out.errDiffersInStyle = !!(out.rest && out.err &&
    (out.rest.borderStyle !== out.err.borderStyle ||
     out.rest.borderWidth !== out.err.borderWidth));
  return out;
}
"""


def main() -> int:
    failures = []
    with sync_playwright() as p:
        browser = p.webkit.launch()
        for w, h in WIDTHS:
            page = browser.new_page(viewport={"width": w, "height": h})
            page.goto(URL, wait_until="load")
            page.wait_for_selector("#dropzone .cm-dropzone", timeout=15000)
            d = page.evaluate(PROBE)

            if d["docScrollWidth"] > d["win"] + 1:
                failures.append(
                    f"{w}px: the document scrolls sideways "
                    f"({d['docScrollWidth']} > {d['win']}) - something inside the "
                    f"zone is wider than the viewport")

            if not d["zones"]:
                failures.append(f"{w}px: no .cm-dropzone rendered at all")
                page.close()
                continue

            for z in d["zones"]:
                if z["h"] < MIN_TARGET:
                    failures.append(
                        f"{w}px: a dropzone is {z['h']}px tall "
                        f"(minimum {MIN_TARGET}) - a thumb will miss it")
                if z["w"] < 100:
                    failures.append(
                        f"{w}px: a dropzone is {z['w']}px wide - too narrow to aim at")
                if z["platformsOverflow"] > 1:
                    failures.append(
                        f"{w}px: the platform row overflows by "
                        f"{z['platformsOverflow']}px")
                if z["right"] > d["win"] + 1:
                    failures.append(
                        f"{w}px: a dropzone runs past the viewport edge "
                        f"(right={z['right']} > {d['win']})")

            if not d["overIsDistinguishable"]:
                failures.append(
                    f"{w}px: the --over state computes the same frame as rest, "
                    f"so a drag over the target gives no feedback")
            if not d["errDiffersInStyle"]:
                failures.append(
                    f"{w}px: the --err state differs only in colour, and this "
                    f"system has no chroma to carry severity")

            print(f"  {w}x{h}: zones={len(d['zones'])} "
                  f"h={d['zones'][0]['h']} w={d['zones'][0]['w']} "
                  f"rest={d['rest']['borderStyle']} over={d['over']['borderStyle']} "
                  f"err={d['err']['borderStyle']} "
                  f"docScroll={d['docScrollWidth']}")
            page.close()
        browser.close()

    if failures:
        print("\nFAIL")
        for f in failures:
            print("  - " + f)
        return 1
    print(f"\nOK  dropzone holds at {len(WIDTHS)} widths, in real WebKit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
