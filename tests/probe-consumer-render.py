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

# Components shipped in batches 34-37. A vendored copy older than the library
# defines none of them, so this pair is a before/after that needs no baseline
# build: 0/4 means stale, 4/4 means the sync landed.
FRESH_MARKERS = {
    "cm-diff": ".cm-diff",
    "cm-revert": ".cm-revert",
    "cm-guide": ".cm-guide",
    "cm-term__follow-toggle": ".cm-term__follow-toggle",
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

  // Group the row's children into VISUAL LINES by top edge, then ask whether a
  // line ends in a separator. A closed drawer / hidden sibling sits at 0x0 and
  // would merge every line, so filter on height.
  const rows = [...document.querySelectorAll('.cm-footer__meta, .cm-byline, .cm-footer__status')];
  out.separatorRows = rows.map(row => {
    const kids = [...row.children].filter(k => k.getBoundingClientRect().height > 0);
    const lines = new Map();
    for (const k of kids) {
      const top = Math.round(k.getBoundingClientRect().top);
      if (!lines.has(top)) lines.set(top, []);
      lines.get(top).push(k);
    }
    const isSep = (k) => {
      const c = k.className || '';
      if (c.includes('cm-footer__dot') || c === 'dot' || c.includes('sep')) return true;
      for (const pseudo of ['::before', '::after']) {
        const v = getComputedStyle(k, pseudo).content;
        if (v && v !== 'none' && v !== 'normal' && v !== '""' && /sep|dot/.test(c)) return true;
      }
      return false;
    };
    let endsWithSep = 0, startsWithSep = 0;
    for (const [, ks] of lines) {
      if (isSep(ks[ks.length - 1])) endsWithSep++;
      if (isSep(ks[0])) startsWithSep++;
    }
    return { cls: row.className, children: kids.length, lines: lines.size, endsWithSep, startsWithSep };
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
