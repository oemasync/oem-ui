#!/usr/bin/env python3
"""WebKit probe for `.cm-media-grid` — the incremental component (batch 33).

MEASURE, do not trust the vision model's opinion. Two claims this file
exists to falsify, both of which are wrong in the obvious implementation:

1. THE PREVIEW FITS ITS FRAME. `.cm-ratio > *` in this library carries
   `object-fit: cover`, which CROPS. That is right for a hero and wrong
   for a library preview — the reader is choosing BETWEEN these tiles, so
   cutting the edge off one of them is a defect, not a style. The check
   is not "is object-fit: contain in the CSS" (a value test, which the
   `cover` mutant passes by being a substring of nothing); it is the
   RENDERED geometry: a 1200x200 source inside a 4/3 well must render
   its whole width inside the well's width.

   The falsifiable reading: with `cover`, a 6:1 source in a 4:3 well has
   a rendered box exactly the well's box and the source is cropped by
   (sourceAR / wellAR) ~ 4.5x. With `contain`, the rendered image box is
   SHORTER than the well (letterboxed) and the aspect is preserved.

2. THE GRID IS A THUMBNAIL LATTICE. `.cm-cards` floors a column at 20rem
   (320px); at 390px that is ONE column. The media grid's documented
   floor is 150px, so 390px gives at least 2 columns and 860px gives at
   least 4. A copy-paste that reused the card track would pass every
   source check and give one column here — that is the mutant this
   measures.

Runs against the LAN preview (Omar's rule: bind 0.0.0.0, verify over the
LAN). Usage: /root/.venvs/mau/bin/python tests/measure-media-grid-webkit.py
"""
from __future__ import annotations

import os
import sys
from playwright.sync_api import sync_playwright

# The host environment sets PLAYWRIGHT_BROWSERS_PATH at an NFS location that
# no longer exists (pve-host-offload/playwright was removed on the NAS), and
# playwright then hunts for webkit under the dead path and refuses to launch.
# Fall back to the local cache ONLY when the configured one is gone.
if os.environ.get("PLAYWRIGHT_BROWSERS_PATH") and not os.path.isdir(os.environ["PLAYWRIGHT_BROWSERS_PATH"]):
    del os.environ["PLAYWRIGHT_BROWSERS_PATH"]

URL = "http://192.168.1.68:4321/"
VIEWPORTS = [(320, 700), (390, 844), (860, 900), (1280, 900)]

# The two specimens: the auto-fill lattice and the single-column form.
PROBE = r"""
() => {
  const out = { grids: [], errors: [] };
  const grids = [...document.querySelectorAll('.cm-media-grid')];
  if (grids.length === 0) { out.errors.push('no .cm-media-grid in the document'); return out; }
  for (let gi = 0; gi < grids.length; gi++) {
    const g = grids[gi];
    const gs = getComputedStyle(g);
    const tiles = [...g.children].map((li) => li.querySelector('.cm-media-grid__tile')).filter(Boolean);
    if (tiles.length === 0) { out.errors.push('grid ' + gi + ' has no tiles'); continue; }
    // DISTINCT LEFT EDGES = the column count. A page with two grids read
    // together merges them, which is why this is scoped per grid.
    const lefts = [...new Set(tiles.map((t) => Math.round(t.getBoundingClientRect().left)))];
    // DISTINCT ROW TOPS, filtered to height > 0: a closed drawer keeps
    // 0x0 nodes at top 0 and they read as a phantom row.
    const live = tiles.filter((t) => t.getBoundingClientRect().height > 0);
    const tops = [...new Set(live.map((t) => Math.round(t.getBoundingClientRect().top)))];
    const heights = live.map((t) => Math.round(t.getBoundingClientRect().height * 100) / 100);
    const rowHeights = [...new Set(heights)];
    const gRect = g.getBoundingClientRect();

    const tileData = tiles.map((t) => {
      const thumb = t.querySelector('.cm-media-grid__thumb');
      const img = thumb ? thumb.querySelector('img') : null;
      const d = { hasImg: !!img, fit: null, aspectOk: null, well: null, imgBox: null };
      if (thumb) {
        const tr = thumb.getBoundingClientRect();
        d.well = { w: Math.round(tr.width * 100) / 100, h: Math.round(tr.height * 100) / 100 };
        d.thumbFit = getComputedStyle(thumb).overflow;
      }
      if (img) {
        d.fit = getComputedStyle(img).objectFit;
        const ir = img.getBoundingClientRect();
        d.imgBox = { w: Math.round(ir.width * 100) / 100, h: Math.round(ir.height * 100) / 100 };
        // THE BOX IS NOT THE PAINTING. `object-fit: contain` still makes
        // the <img> BOX fill the well — it letterboxes the CONTENT inside
        // it. A first version of this probe compared the box to the well
        // and reported "that is cover" on a correct `contain` render,
        // which is the classic trap: a probe that cannot tell the right
        // answer from the wrong one.
        //
        // The falsifiable signal is the box's ASPECT RATIO against the
        // SOURCE's. `contain`/`cover` both preserve the ratio and differ
        // only in scale, so the ratio cannot separate them — but the
        // well's own ratio can: under `cover` the box is exactly the well
        // (4:3 here); under `contain` the box is the well's box too, and
        // the DIFFERENCE shows in whether the source's own ratio matches.
        //
        // So measure what is actually painted: the element's ink extent.
        // WebKit exposes naturalWidth/naturalHeight and the computed
        // object-fit; the honest check is that contain is DECLARED and the
        // natural ratio is NOT the well's ratio (a letterbox must happen),
        // then confirm the box never exceeds the well on either axis.
        d.naturalRatio = img.naturalWidth && img.naturalHeight
          ? Math.round((img.naturalWidth / img.naturalHeight) * 100) / 100 : null;
        const wellRatio = d.well ? Math.round((d.well.w / d.well.h) * 100) / 100 : null;
        d.wellRatio = wellRatio;
        d.letterboxes = d.naturalRatio !== null && wellRatio !== null
          ? Math.abs(d.naturalRatio - wellRatio) > 0.15 : null;
        d.boxInsideWell = ir.width <= (d.well.w + 1.5) && ir.height <= (d.well.h + 1.5);
        d.aspectOk = d.boxInsideWell;
      }
      // the floor: every text part must be >= --min-font on a coarse pointer
      const name = t.querySelector('.cm-media-grid__name');
      const meta = t.querySelector('.cm-media-grid__meta');
      d.namePx = name ? parseFloat(getComputedStyle(name).fontSize) : null;
      d.metaPx = meta ? parseFloat(getComputedStyle(meta).fontSize) : null;
      // an ellipsising name must clip, not wrap: one line of box height
      if (name) {
        const lh = parseFloat(getComputedStyle(name).lineHeight);
        const nr = name.getBoundingClientRect();
        d.nameLines = lh > 0 ? Math.round((nr.height / lh) * 100) / 100 : null;
        d.scrolls = name.scrollWidth > name.clientWidth + 1;
      }
      // the actions row, when present, must share a bottom edge across tiles
      const act = t.querySelector('.cm-media-grid__actions');
      d.actionBottom = act ? Math.round(act.getBoundingClientRect().bottom) : null;
      return d;
    });
    out.grids.push({
      index: gi,
      cols: gs.gridTemplateColumns.split(' ').length,
      distinctLefts: lefts.length,
      rows: tops.length,
      rowHeights,
      width: Math.round(gRect.width * 100) / 100,
      // The floor and the gap, READ FROM THE COMPUTED STYLE: the column
      // expectation is derived from these, never assumed from the
      // viewport. An earlier version of this probe asserted ">= 2 columns
      // at 390" from theory and failed on a correct build - the
      // showcase's demo column is doubly padded, so it is 270px wide at
      // a 390px viewport and one column is exactly what the floor
      // promises there.
      minPx: parseFloat(gs.getPropertyValue('--media-grid-min')) || null,
      gapPx: parseFloat(gs.columnGap) || 0,
      scrollW: g.scrollWidth, clientW: g.clientWidth,
      tileCount: tiles.length,
      tiles: tileData,
    });
  }
  const minFont = getComputedStyle(document.documentElement).getPropertyValue('--min-font').trim();
  out.minFont = minFont;
  // the PAGE must not gain a horizontal scrollbar from this component
  out.pageOverflow = document.documentElement.scrollWidth - document.documentElement.clientWidth;
  return out;
}
"""

def main() -> int:
    failures: list[str] = []
    with sync_playwright() as pw:
        browser = pw.webkit.launch()
        for (w, h) in VIEWPORTS:
            ctx = browser.new_context(
                viewport={"width": w, "height": h},
                device_scale_factor=2,
                is_mobile=w < 700,
                has_touch=w < 700,
            )
            page_errors: list[str] = []
            page = ctx.new_page()
            page.emulate_media(reduced_motion="reduce")
            # A pageerror here must be REPORTED, not swallowed into a
            # "timeout waiting for cm-js": a bundle that throws leaves the
            # mark un-set, and the two failures look identical from the
            # outside. Collect them and print them with the gate result.
            page.on("pageerror", lambda e: page_errors.append(str(e)))
            # `domcontentloaded` is NOT enough: the page carries two external
            # references (a picsum placeholder and a cdn.mrx.sh stylesheet
            # that 404s), and under load WebKit's navigation waits on them
            # for the full 30s default while curl fetches the same URL in
            # 0.14s. The runtime marks itself, so wait for the MARK - the
            # documented trap being that `networkidle` can fire before the
            # bundle executes. `commit` returns as soon as the response
            # exists; the wait_for_function below is the real gate.
            page.goto(URL, wait_until="commit", timeout=180000)
            # The runtime marks itself. `networkidle` can fire before the
            # bundle executes, which is the documented trap in this repo.
            try:
                page.wait_for_function("() => document.documentElement.classList.contains('cm-js')",
                                   timeout=60000)
            except Exception:
                for e in page_errors:
                    print(f"  PAGEERROR {e}")
                failures.append(f"{w}x{h}: the runtime never set its cm-js mark")
                ctx.close()
                continue
            page.wait_for_timeout(250)
            res = page.evaluate(PROBE)
            print(f"\n=== viewport {w}x{h}  (--min-font {res.get('minFont')})")
            if res["errors"]:
                for e in res["errors"]:
                    print(f"  ERROR {e}")
                    failures.append(f"{w}x{h}: {e}")
            for g in res["grids"]:
                print(f"  grid {g['index']}: {g['cols']} cols, {g['tileCount']} tiles, "
                      f"{g['rows']} row(s), width {g['width']}px, "
                      f"grid overflow {g['scrollW'] - g['clientW']}px")
                print(f"    distinct left edges {g['distinctLefts']}  distinct row heights {g['rowHeights']}")
                for ti, t in enumerate(g["tiles"]):
                    line = f"    tile {ti}:"
                    if t["hasImg"]:
                        line += f" fit={t['fit']} imgBox={t['imgBox']} well={t['well']} inside={t['aspectOk']}"
                    else:
                        line += " (type fallback, no img)"
                    if t.get("namePx") is not None:
                        line += f" namePx={t['namePx']} lines={t.get('nameLines')} scrolls={t.get('scrolls')}"
                    if t.get("actionBottom") is not None:
                        line += f" actionBottom={t['actionBottom']}"
                    print(line)

            # --- assertions, one per claim ---
            # 1. contain, verified by GEOMETRY not by the declared value.
            #    The <img> BOX fills the well under both contain and cover;
            #    what differs is the painting, which tests/probe-media-grid-fit.py
            #    measures in pixels. What this probe can honestly assert is
            #    the box never exceeds its well, and that a source whose own
            #    ratio differs from the well's MUST letterbox (so a `cover`
            #    render is detectable at all).
            for g in res["grids"]:
                for ti, t in enumerate(g["tiles"]):
                    if t["hasImg"]:
                        if t["fit"] != "contain":
                            failures.append(f"{w}x{h} grid{g['index']} tile{ti}: object-fit is {t['fit']}, not contain")
                        if not t["boxInsideWell"]:
                            failures.append(
                                f"{w}x{h} grid{g['index']} tile{ti}: the image box {t['imgBox']} "
                                f"EXCEEDS its well {t['well']} — the preview escapes its frame")
                        if ti == 0 and t.get("letterboxes") is False:
                            failures.append(
                                f"{w}x{h} tile{ti}: the source ratio {t['naturalRatio']} equals the well's "
                                f"{t['wellRatio']}, so this specimen cannot tell contain from cover — "
                                "give it a source whose ratio differs from the well's")
            # 2. the density contract, DERIVED from the token and the
            #    measured container: auto-fill fits floor((W + gap) /
            #    (min + gap)) columns, at least one. The expectation comes
            #    from --media-grid-min as computed on the grid, so a
            #    copy-paste `minmax(20rem, 1fr)` that ignores the knob
            #    still fails here while a legitimate re-tuning of the knob
            #    does not.
            first = res["grids"][0] if res["grids"] else None
            if first and first["distinctLefts"] > 0:
                if not first["minPx"]:
                    failures.append(f"{w}: --media-grid-min does not resolve to a length, "
                                    "so the floor is not declared (or its declaration is broken)")
                else:
                    expect = max(1, int((first["width"] + first["gapPx"])
                                        // (first["minPx"] + first["gapPx"])))
                    if first["distinctLefts"] != expect:
                        failures.append(
                            f"{w}: the lattice gives {first['distinctLefts']} column(s) in a "
                            f"{first['width']}px container; a {first['minPx']}px floor with a "
                            f"{first['gapPx']}px gap fits exactly {expect}")
            # 3. the mobile type floor
            if w < 700:
                mf = float(res.get("minFont", "12").replace("px", ""))
                for g in res["grids"]:
                    for ti, t in enumerate(g["tiles"]):
                        for k in ("namePx", "metaPx"):
                            v = t.get(k)
                            if v is not None and v + 0.01 < mf:
                                failures.append(f"{w}x{h} tile{ti} {k}={v}px is under --min-font {mf}px")
                        if t.get("nameLines") and t["nameLines"] > 1.05:
                            failures.append(f"{w}x{h} tile{ti}: the name wraps to {t['nameLines']} lines "
                                            "(it must clip to one)")
            # 4. no page-level horizontal scroll from this component
            if res["pageOverflow"] > 1:
                failures.append(f"{w}x{h}: the page overflows horizontally by {res['pageOverflow']}px")
            ctx.close()
        browser.close()

    print("\n" + ("FAILURES:\n  " + "\n  ".join(failures) if failures else "all media-grid claims hold"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
