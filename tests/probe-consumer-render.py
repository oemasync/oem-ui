#!/usr/bin/env python3
"""Probe a CONSUMER's rendered page in WebKit - the half `check-design-sync.sh`
cannot see.

`check-design-sync.sh` compares the vendored files byte-for-byte and proves
they are IMPORTED. That is necessary and not sufficient: it says nothing about
what a person sees. This probe measures the invariants a re-vendor can break,
at an iPhone viewport and at desktop, in both themes:

  - horizontal overflow (documentElement.scrollWidth - clientWidth must be 0)
  - header tap targets (must clear the 44px floor on a coarse pointer)
  - separator rows: no VISUAL LINE may END with a separator. Both an element
    separator and a generated ::after are counted - the wrong fix leaves no
    element behind, so an element-only probe is blind to it.
  - library freshness: which recent components the SERVED cascade defines.
    A stale copy ships none of them; this is the crisp proof a sync landed.
  - theme: --ink and data-theme per run, so a "dark" run and a "light" run
    cannot be byte-identical (an in-page localStorage write with no reload
    leaves initial state untouched and reports both runs the same).

usage:
  probe-consumer-render.py --dist <dist-dir>     # build from a local build
  probe-consumer-render.py --url <https://...>   # measure a live deployment
  [--path /blog/] [--theme-key <localStorage key>] [--port 4399] [--json]

Exits 1 when an invariant is violated, so it can gate a re-vendor.
"""
import argparse
import json
import os
import subprocess
import sys
import time

# This host exports PLAYWRIGHT_BROWSERS_PATH pointing at a NAS path that was
# removed; playwright then hunts for webkit under the dead dir and refuses to
# launch. Delete it ONLY when it is dead, so a restored cache is never thrown
# away.
_bp = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
if _bp and not os.path.isdir(_bp):
    del os.environ["PLAYWRIGHT_BROWSERS_PATH"]

from playwright.sync_api import sync_playwright  # noqa: E402

# Components shipped in recent batches. A vendored copy older than the library
# defines none of them, so this is a before/after that needs no baseline build:
# a stale consumer reads the 34-37 set only, a current one reads every marker.
# The batches 38-40 entries (artwork, saved views, bell) were added when the
# fleet sat uniformly at 34-37 - the drift was 250 lines in every consumer,
# which is exactly what a re-vendor that never ran looks like.
FRESH_MARKERS = {
    "cm-diff": ".cm-diff",
    "cm-revert": ".cm-revert",
    "cm-guide": ".cm-guide",
    "cm-term__follow-toggle": ".cm-term__follow-toggle",
    "cm-artwork__frame": ".cm-artwork__frame",
    "cm-toolbar__view": ".cm-toolbar__view",
    "cm-bell__count": ".cm-bell__count",
}

MEASURE = r"""
() => {
  const de = document.documentElement;
  const out = {};
  out.scrollWidth = de.scrollWidth;
  out.clientWidth = de.clientWidth;
  out.overflowX = de.scrollWidth - de.clientWidth;

  const taps = [...document.querySelectorAll('.cm-header a, .cm-header button')]
    .map(el => { const r = el.getBoundingClientRect();
                 return { tag: el.tagName, cls: el.className || '',
                          w: +r.width.toFixed(1), h: +r.height.toFixed(1) }; })
    .filter(t => t.h > 0);
  out.tapTargets = taps;
  out.minTapHeight = taps.length ? Math.min(...taps.map(t => t.h)) : null;

  // Ask whether a VISUAL LINE ends or starts with a separator.
  //
  // An element-only walk is WRONG and it fails in the direction that gets a
  // correct page rejected: oem-portfolio's footer is
  // `<span class="cm-footer__dot">●</span> deployed from a private repo`, so
  // the row has exactly one ELEMENT child - the dot - and the row was reported
  // as "1 line ending in a separator" at every viewport, in both themes, while
  // MEASURED the dot sits at x=20..27.2 and the text follows it at 39.4..241 on
  // the same line. A trailing text node is painted content, so it is collected
  // as an item too. A probe that reports a false failure on a correct page is
  // worse than no probe: the tempting repair is to rewrite the consumer's
  // markup, which would have been a regression.
  //
  // Separator identity:
  //   - an element whose own class is a dot/sep (`cm-footer__dot`, `dot`, `sep`)
  //   - an element whose ::after paints content, when it is LAST on its line
  //     (the ::after fix attaches the dot to the PRECEDING fragment, so the
  //     defect leaves no element behind and only this test can see it)
  //   - an element whose ::before paints content, when it is FIRST on its line
  //     (the shipped ::before fix; a line MAY start with a separator - that is
  //     the documented trade - so startsWithSep is reported, not a violation)
  const rows = [...document.querySelectorAll('.cm-footer__meta, .cm-byline, .cm-footer__status')];
  const clsOf = (el) => String((el && el.className && el.className.baseVal !== undefined)
    ? el.className.baseVal : (el && el.className) || '');
  const paints = (el, pseudo) => {
    const c = getComputedStyle(el, pseudo).content;
    return !!c && c !== 'none' && c !== 'normal' && c !== '""' && c !== "''";
  };
  const isSepEl = (el) => /(^|[\s_-])sep($|[\s_-])|cm-footer__dot|(^|\s)dot($|\s)/.test(clsOf(el));
  out.separatorRows = rows.map(row => {
    const items = [];
    const addEl = (el) => {
      const r = el.getBoundingClientRect();
      if (r.height <= 0 || r.width <= 0) return;  // closed drawer / hidden sibling
      items.push({ kind: 'el', left: r.left, right: r.right, top: r.top, bottom: r.bottom,
                   sep: isSepEl(el), before: paints(el, '::before'), after: paints(el, '::after') });
    };
    for (const el of row.children) addEl(el);
    for (const n of row.childNodes) {
      if (n.nodeType !== 3 || !n.textContent.trim()) continue;
      const rg = document.createRange();
      rg.selectNodeContents(n);
      for (const r of rg.getClientRects()) {
        if (r.height <= 0 || r.width <= 0) continue;
        items.push({ kind: 'text', left: r.left, right: r.right, top: r.top, bottom: r.bottom,
                     sep: false, before: false, after: false });
      }
    }
    // Cluster by vertical OVERLAP, not by equal top: an inline dot's box and the
    // text beside it sit at different tops (2748.8 vs 2752 measured) and an
    // equal-top grouping splits one line into two.
    const lines = [];
    for (const it of items.sort((a, b) => a.top - b.top || a.left - b.left)) {
      const line = lines.find(L => {
        const overlap = Math.min(L.bottom, it.bottom) - Math.max(L.top, it.top);
        return overlap > 0.5 * Math.min(L.bottom - L.top, it.bottom - it.top);
      });
      if (line) {
        line.items.push(it);
        line.top = Math.min(line.top, it.top);
        line.bottom = Math.max(line.bottom, it.bottom);
      } else lines.push({ top: it.top, bottom: it.bottom, items: [it] });
    }
    let endsWithSep = 0, startsWithSep = 0;
    for (const L of lines) {
      L.items.sort((a, b) => a.left - b.left);
      const first = L.items[0], last = L.items[L.items.length - 1];
      if (last.sep || last.after) endsWithSep++;
      if (first.sep || first.before) startsWithSep++;
    }
    return { cls: clsOf(row), children: items.length, lines: lines.length, endsWithSep, startsWithSep };
  });

  out.hasHeader = !!document.querySelector('.cm-header');
  out.theme = de.getAttribute('data-theme');
  out.ink = getComputedStyle(de).getPropertyValue('--ink').trim();
  return out;
}
"""

SERVED_CSS = r"""
(markers) => {
  const out = {};
  const seen = [];
  for (const sheet of document.styleSheets) {
    try { for (const r of sheet.cssRules) seen.push(r.cssText); } catch (e) { /* cross-origin */ }
  }
  const blob = seen.join(String.fromCharCode(10));
  for (const [name, sel] of Object.entries(markers)) out[name] = blob.includes(sel);
  out.sheetBytes = blob.length;
  return out;
}
"""


def measure_page(pg, url, theme, theme_key):
    pg.goto(url, wait_until="load", timeout=30000)
    # The runtime marks itself. Not every consumer calls init() (links never
    # has), so a missing marker is recorded, never waited on forever.
    js_ready = True
    try:
        pg.wait_for_function("document.documentElement.classList.contains('cm-js')", timeout=5000)
    except Exception:
        js_ready = False
    # Set the theme the way the runtime does, then RELOAD: an in-page write with
    # no reload leaves initial state untouched and reports both runs identical.
    pg.evaluate("([k, t]) => { try { localStorage.setItem(k, t); } catch (e) {} }", [theme_key, theme])
    pg.reload(wait_until="load")
    try:
        pg.wait_for_function("document.documentElement.classList.contains('cm-js')", timeout=5000)
    except Exception:
        js_ready = False
    pg.wait_for_timeout(250)  # settle: the 0.01ms reduced-motion transition is not synchronous
    m = pg.evaluate(MEASURE)
    m["css"] = pg.evaluate(SERVED_CSS, FRESH_MARKERS)
    m["js_ready"] = js_ready
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist")
    ap.add_argument("--url")
    ap.add_argument("--path", default="/")
    ap.add_argument("--theme-key", default="cm-theme")
    ap.add_argument("--port", type=int, default=4399)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not a.dist and not a.url:
        ap.error("one of --dist or --url is required")

    server = None
    if a.dist:
        server = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(a.port), "--bind", "127.0.0.1",
             "--directory", a.dist],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        base = f"http://127.0.0.1:{a.port}"
        time.sleep(1.0)
    else:
        base = a.url.rstrip("/")
    url = base + a.path

    results, verdicts = {}, []
    try:
        with sync_playwright() as p:
            browser = p.webkit.launch()
            for label, vw, vh in (("iphone", 390, 844), ("desktop", 1280, 900)):
                for theme in ("light", "dark"):
                    ctx = browser.new_context(viewport={"width": vw, "height": vh},
                                              device_scale_factor=2, reduced_motion="reduce",
                                              has_touch=True)
                    pg = ctx.new_page()
                    m = measure_page(pg, url, theme, a.theme_key)
                    results[f"{label}-{theme}"] = m
                    ctx.close()
                    if m["overflowX"] != 0:
                        verdicts.append(f"{label}-{theme}: horizontal overflow {m['overflowX']}px")
                    if m["minTapHeight"] is not None and m["minTapHeight"] < 44:
                        verdicts.append(f"{label}-{theme}: header tap target {m['minTapHeight']}px < 44px")
                    for row in m["separatorRows"]:
                        if row["endsWithSep"]:
                            verdicts.append(f"{label}-{theme}: {row['cls']} has {row['endsWithSep']} line(s) ending in a separator")
            browser.close()
    finally:
        if server:
            server.terminate()
            server.wait(timeout=5)

    fresh = sum(bool(results["iphone-light"]["css"].get(k)) for k in FRESH_MARKERS)
    if a.json:
        print(json.dumps(results, indent=2))
    else:
        for k, v in results.items():
            print(f"{k:15s} overflow={v['overflowX']:>3}  minTap={str(v['minTapHeight']):>5}  "
                  f"lines={[r['lines'] for r in v['separatorRows']]}  "
                  f"startsWithSep={[r['startsWithSep'] for r in v['separatorRows']]}  "
                  f"ink={v['ink'] or '(none)'}")
        print(f"\nserved css: {results['iphone-light']['css']['sheetBytes']} bytes, "
              f"{fresh}/{len(FRESH_MARKERS)} recent components defined "
              f"({', '.join(k for k in FRESH_MARKERS if results['iphone-light']['css'].get(k)) or 'none'})")
        print(f"header present: {results['iphone-light']['hasHeader']}   "
              f"runtime armed: {results['iphone-light']['js_ready']}")
        if verdicts:
            print("\nVIOLATIONS")
            for v in verdicts:
                print("  " + v)
        else:
            print("\nno violations")
    return 1 if verdicts else 0


if __name__ == "__main__":
    sys.exit(main())
