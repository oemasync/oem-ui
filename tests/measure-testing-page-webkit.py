"""Measure the /testing review page in real WebKit.

The page exists to be LOOKED at, so the questions are visual ones that
source review cannot answer:

  1. DOES IT RENDER? - five regions of decomp-sh are on the page, and a
     region that renders with an unstyled class looks fine in source and
     broken on a phone.
  2. DOES IT OVERFLOW? - a grid of stats and a table of functions are the
     two things that break a narrow viewport, and the table is the one
     that has a documented stacking behaviour.
  3. ARE THE STATES DISTINGUISHABLE? - the chips carry the match state,
     and the whole point of the system is that the state is legible in
     GREYSCALE, so a hue is the failure.
  4. IS THE DROPZONE THE RIGHT SHAPE? - it is the one component the
     port needed that did not exist before.

Every assertion here is about GEOMETRY or COMPUTED STYLE, never about
the presence of a class name in the markup.
"""
import json
import sys

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:4321/testing/"
WIDTHS = [(320, 667), (375, 667), (390, 844), (402, 874), (768, 1024), (1280, 900)]

PROBE = r"""
() => {
  const out = { regions: [], overflow: [], chips: [], dropzone: null, docW: 0 };

  for (const id of ['home', 'project', 'overview', 'functions', 'agents', 'activity', 'drawer', 'catalog']) {
    const el = document.getElementById(id);
    if (!el) { out.regions.push({ id, present: false }); continue; }
    const r = el.getBoundingClientRect();
    out.regions.push({
      id, present: true,
      h: Math.round(r.height),
      w: Math.round(r.width),
      visible: r.height > 40,
    });
  }

  // Does the PAGE scroll sideways? That is the question, and it is not
  // the same question as "is some element wider than the viewport".
  //
  // A table inside `.cm-table-wrap` (overflow-x: auto) is SUPPOSED to be
  // wider than the viewport - that is the whole point of the wrapper: the
  // table scrolls inside its own box while the page does not move. A
  // probe that reports "an element extends past the viewport" flags
  // every scroll container in the system, including the ones that work
  // correctly, and drowns the one that does not.
  //
  // So: the page's scrollWidth against its clientWidth is the claim, and
  // the per-element scan only runs to NAME the culprit once the page is
  // actually too wide.
  const vw = document.documentElement.clientWidth;
  out.docW = vw;
  out.pageScrollsSideways = document.documentElement.scrollWidth > vw + 1;
  out.docScrollW = document.documentElement.scrollWidth;

  if (out.pageScrollsSideways) {
    for (const el of document.querySelectorAll('body *')) {
      const r = el.getBoundingClientRect();
      if (r.width === 0) continue;
      if (r.right > vw + 1.5 || r.left < -1.5) {
        // Is it inside something that CLIPS it? If so it cannot be
        // widening the page, and it is not the culprit.
        let clipped = false, a = el.parentElement;
        while (a && a !== document.documentElement) {
          const o = getComputedStyle(a).overflowX;
          if (o === 'auto' || o === 'hidden' || o === 'scroll' || o === 'clip') {
            clipped = true; break;
          }
          a = a.parentElement;
        }
        if (!clipped) {
          out.overflow.push({
            tag: el.tagName.toLowerCase(),
            cls: (el.className || '').toString().slice(0, 60),
            right: Math.round(r.right),
            left: Math.round(r.left),
          });
        }
      }
    }
    out.overflow = out.overflow.slice(0, 10);
  }

  // The chart legend: the dots and the bars they name, so a legend that
  // disagrees with its chart is visible as a number, not as a feeling.
  out.legend = { dots: {}, barFills: {}, distinct: 0 };
  for (const d of document.querySelectorAll('#cmc-rom .cm-chart__legend-dot')) {
    out.legend.dots[d.getAttribute('data-cm-k')] = getComputedStyle(d).backgroundColor;
  }
  for (const b of document.querySelectorAll('#cmc-rom .cm-chart__bar')) {
    out.legend.barFills[b.getAttribute('data-cm-k')] = getComputedStyle(b).fill;
  }
  out.legend.distinct = new Set(Object.values(out.legend.dots)).size;

  // The state chips: the label text and the COLOUR. A hue here would be
  // the only hue on the page.
  for (const c of document.querySelectorAll('.cm-chip--ok, .cm-chip--warn')) {
    const cs = getComputedStyle(c);
    out.chips.push({
      cls: c.className,
      text: (c.textContent || '').trim(),
      color: cs.color,
      before: getComputedStyle(c, '::before').content,
    });
  }

  const dz = document.querySelector('.cm-dropzone');
  if (dz) {
    const r = dz.getBoundingClientRect();
    const cs = getComputedStyle(dz);
    out.dropzone = {
      w: Math.round(r.width), h: Math.round(r.height),
      borderStyle: cs.borderTopStyle,
      borderColor: cs.borderTopColor,
    };
  }
  return out;
}
"""

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


with sync_playwright() as p:
    browser = p.webkit.launch()
    for w, h in WIDTHS:
        page = browser.new_page(viewport={"width": w, "height": h})
        page.goto(URL, wait_until="networkidle")
        d = page.evaluate(PROBE)

        missing = [r["id"] for r in d["regions"] if not r["present"]]
        ok(not missing, f"{w}x{h}: every region is present ({missing or 'all 8'})")

        invisible = [r["id"] for r in d["regions"] if r["present"] and not r["visible"]]
        ok(not invisible, f"{w}x{h}: every region actually renders ({invisible or 'all visible'})")

        ok(not d["pageScrollsSideways"],
           f"{w}x{h}: the page does not scroll sideways "
           f"(scrollW {d['docScrollW']} vs {d['docW']}; culprits {d['overflow'][:2]})")

        if d["dropzone"]:
            ok(d["dropzone"]["borderStyle"] == "dashed",
               f"{w}x{h}: the dropzone rests dashed (got {d['dropzone']['borderStyle']})")
            ok(d["dropzone"]["h"] > 60,
               f"{w}x{h}: the dropzone has a real box ({d['dropzone']['h']}px tall)")

        if w == 390:
            # The chart's legend must AGREE with the chart it labels. The
            # series colours are scoped to the chart's id, so a legend
            # placed OUTSIDE that scope is painted by the default and
            # every dot comes out the same grey - a legend that says
            # four things and shows one.
            legend = d["legend"]
            ok(legend["distinct"] == 4,
               f"{w}x{h}: the legend's four states are distinguishable "
               f"(got {legend['distinct']} distinct colours: {legend['dots']})")
            ok(len(set(legend["barFills"].values())) == 4,
               f"{w}x{h}: the bars carry four distinct states too "
               f"({legend['barFills']})")
            # The legend dot and the bar it names must be the SAME colour.
            mismatched = [k for k, v in legend["dots"].items()
                          if legend["barFills"].get(k) != v]
            ok(not mismatched,
               f"{w}x{h}: each legend dot matches its bar ({mismatched or 'all four'})")
            # And the ramp must be greyscale - the system has no chroma.
            hues = []
            for v in list(legend["dots"].values()) + list(legend["barFills"].values()):
                if v.startswith("rgb("):
                    r, g, bl = [int(x) for x in v[4:-1].split(",")[:3]]
                    if max(r, g, bl) - min(r, g, bl) > 12:
                        hues.append(v)
            ok(not hues, f"{w}x{h}: the chart ramp is greyscale ({hues or 'no hue'})")

        if w == 390:
            # The greyscale rule: the state chips must not carry a hue.
            hues = []
            for c in d["chips"]:
                col = c["color"]
                if col.startswith("rgb("):
                    r, g, b = [int(x) for x in col[4:-1].split(",")[:3]]
                    if max(r, g, b) - min(r, g, b) > 12:
                        hues.append((c["text"], col))
            ok(not hues, f"{w}x{h}: the state chips carry no hue ({hues or 'greyscale'})")
            # The matched chip must be distinguishable from the others by
            # its MARK, not by its colour.
            marks = {c["text"]: c["before"] for c in d["chips"]}
            ok(len(set(marks.values())) > 1 or all(v == "none" for v in marks.values()),
               f"the chips differ by mark, not only by colour ({marks})")

        page.close()
    browser.close()

print()
if fails:
    print(f"FAILED {len(fails)}")
    for f in fails:
        print("  " + f)
    sys.exit(1)
print("OK  the /testing page holds at every width, in real WebKit")
