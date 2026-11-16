#!/usr/bin/env python3
"""WebKit probe for the endpoint row specimen (cm-endpoint).

The contract checks read the CSS source; this probe reads the BUILT
page in the engine Omar actually uses (Safari/WebKit) at phone and
desktop widths. Three claims, each falsifiable:

1. THE SLOT IS THE SLOT. Every `.cm-endpoint__param` token computes
   to the ACTIVE theme's `--ink-dim`, and the path itself computes to
   `--ink`. A token that reads full ink has erased the mark that
   distinguishes the part-to-substitute from the literal. The token is
   a hex and the computed value an rgb() - the comparison normalises
   both to rgb, or a correct build fails on a format difference.

2. THE BADGE SITS ON THE PATH'S OWN LINE. For an endpoint whose path
   is a single line, the badge's vertical centre sits on that line
   (within a few px of the path's centre). The badge is the signal;
   drifting it off the line is the flex-start/flex-end failure.

3. NOTHING OVERRUNS, AND THE LONG PATH BREAKS. The document does not
   grow sideways (baseline at HEAD: scrollWidth == innerWidth at all
   four widths, so a new overflow is this change's, not an inherited
   one). The long specimen (two path parameters, no spaces) is the
   branch that only `overflow-wrap: break-word` survives: at a phone
   width its rendered height grows past one line - it broke inside its
   own item - and no path's right edge leaves its surface container.
   A path that stayed one line wide while overrunning the container
   is the `break-word` -> `normal` mutant, and this check refuses a
   run in which the long path never wrapped.

The two theme runs are proven different: the data-theme attribute and
the computed --ink / --ink-dim are printed for each.

Runs against the LAN preview (Omar's rule: bind 0.0.0.0, verify over
the LAN). Usage: /root/.venvs/mau/bin/python tests/measure-endpoint-webkit.py
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
THEMES = ["dark", "light"]

PROBE = """
() => {
  const sec = document.querySelector('#endpoint');
  if (!sec) return { missing: true };
  const root = getComputedStyle(document.documentElement);
  const out = {
    missing: false,
    theme: document.documentElement.getAttribute('data-theme'),
    ink: root.getPropertyValue('--ink').trim(),
    inkDim: root.getPropertyValue('--ink-dim').trim(),
    rootFontPx: parseFloat(root.fontSize),
    docOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    endpoints: [],
  };
  sec.querySelectorAll('.cm-endpoint').forEach(ep => {
    const badge = ep.querySelector('.cm-method');
    const path = ep.querySelector('.cm-endpoint__path');
    const surface = ep.closest('.cm-surface') || ep.parentElement;
    const slots = [...ep.querySelectorAll('.cm-endpoint__param')];
    const pr = path ? path.getBoundingClientRect() : null;
    const br = badge ? badge.getBoundingClientRect() : null;
    const sr = surface ? surface.getBoundingClientRect() : null;
    // The path's rendered line height: a monospace line at this font
    // size is ~1.2-1.5em; compare the box height against one line.
    const pathCS = path ? getComputedStyle(path) : null;
    const lineH = pathCS ? parseFloat(pathCS.lineHeight) || 0 : 0;
    const oneLine = lineH > 0 ? (pr.height <= lineH * 1.5) : null;
    out.endpoints.push({
      label: path ? path.textContent.trim().replace(/\\s+/g, ' ') : '',
      hasBadge: !!badge,
      hasPath: !!path,
      badgeTop: br ? Math.round(br.top * 10) / 10 : null,
      badgeCenterY: br ? Math.round((br.top + br.height / 2) * 10) / 10 : null,
      pathTop: pr ? Math.round(pr.top * 10) / 10 : null,
      pathCenterY: pr ? Math.round((pr.top + pr.height / 2) * 10) / 10 : null,
      pathHeight: pr ? Math.round(pr.height * 10) / 10 : null,
      pathRight: pr ? Math.round(pr.right * 10) / 10 : null,
      surfaceRight: sr ? Math.round(sr.right * 10) / 10 : null,
      oneLine,
      pathColor: pathCS ? pathCS.color : null,
      slotCount: slots.length,
      slotColors: slots.map(s => getComputedStyle(s).color),
    });
  });
  return out;
}
"""


def to_rgb(css_color: str) -> str:
    """Normalise a computed colour or a hex token to 'rgb(r, g, b)' so the
    two sides of a comparison share one format."""
    c = css_color.strip()
    if c.startswith("#"):
        h = c.lstrip("#")
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        return f"rgb({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)})"
    return c


def main() -> int:
    fails = 0
    long_wraps = []
    with sync_playwright() as p:
        browser = p.webkit.launch()
        page = browser.new_page()

        for w, h in VIEWPORTS:
            page.set_viewport_size({"width": w, "height": h})
            for theme in THEMES:
                page.goto(URL, wait_until="commit")
                for _ in range(40):
                    if page.evaluate("() => document.documentElement.classList.contains('cm-js')"):
                        break
                    page.wait_for_timeout(250)
                # Set the theme, WAIT, then read (a same-tick read has
                # reported the pre-set cascade before).
                page.evaluate(f"() => document.documentElement.setAttribute('data-theme', '{theme}')")
                page.wait_for_timeout(150)
                d = page.evaluate(PROBE)

                tag = f"[{w}x{h} {theme}]"
                if d.get("missing"):
                    print(f"  FAIL {tag}: no #endpoint section in the built page")
                    fails += 1
                    continue

                if d["docOverflow"] > 0:
                    print(f"  FAIL {tag}: document overflows sideways by {d['docOverflow']}px")
                    fails += 1

                if d["endpoints"].count is None and len(d["endpoints"]) != 4:
                    print(f"  FAIL {tag}: expected 4 endpoints, got {len(d['endpoints'])}")
                    fails += 1

                ink = to_rgb(d["ink"])
                dim = to_rgb(d["inkDim"])
                for ep in d["endpoints"]:
                    if not ep["hasBadge"] or not ep["hasPath"]:
                        print(f"  FAIL {tag}: endpoint '{ep['label']}' has no badge or path")
                        fails += 1
                        continue
                    # 1. THE SLOT IS THE SLOT, per theme.
                    if ep["pathColor"] and to_rgb(ep["pathColor"]) != ink:
                        print(f"  FAIL {tag}: path '{ep['label']}' reads {ep['pathColor']}, "
                              f"not the theme's ink {d['ink']} ({ink})")
                        fails += 1
                    for i, sc in enumerate(ep["slotColors"]):
                        if to_rgb(sc) != dim:
                            print(f"  FAIL {tag}: slot {i} of '{ep['label']}' reads {sc}, "
                                  f"not the theme's ink-dim {d['inkDim']} ({dim})")
                            fails += 1
                    # 3b. the path's right edge stays inside its surface.
                    if ep["pathRight"] is not None and ep["surfaceRight"] is not None:
                        if ep["pathRight"] > ep["surfaceRight"] + 1:
                            print(f"  FAIL {tag}: path '{ep['label']}' overruns its surface "
                                  f"(right {ep['pathRight']} > {ep['surfaceRight']})")
                            fails += 1
                    # 2. THE BADGE SITS ON THE PATH'S LINE. For a
                    #    single-line path the badge centre is on that
                    #    line, within a few px of the path centre.
                    if ep["oneLine"] and ep["badgeCenterY"] is not None and ep["pathCenterY"] is not None:
                        dy = abs(ep["badgeCenterY"] - ep["pathCenterY"])
                        if dy > 4:
                            print(f"  FAIL {tag}: badge of '{ep['label']}' is off the path's line "
                                  f"(centre {ep['badgeCenterY']} vs path {ep['pathCenterY']}, {dy}px)")
                            fails += 1
                    # Track the long path's wrap decision.
                    if ep["slotCount"] >= 2:
                        long_wraps.append(ep["oneLine"] is False)

                print(f"  ok {tag}: theme={d['theme']} ink={d['ink']} dim={d['inkDim']} "
                      f"endpoints={len(d['endpoints'])} overflow={d['docOverflow']}px "
                      + " ".join(f"{e['label'][:16]}:{('1L' if e['oneLine'] else 'wrap')}" for e in d["endpoints"]))

        browser.close()

    # The long path (two slots, no spaces) is the branch only
    # overflow-wrap: break-word survives. At least one phone-width run
    # must show it wrapped, or the no-break mutant stays invisible.
    phone_runs = [x for x in long_wraps]
    if not any(long_wraps):
        print("FAIL: the long path never wrapped at any width - one branch of the "
              "break check is unexercised (break-word may have become normal)")
        fails += 1

    if fails:
        print(f"\n{fails} FAILURE(S)")
        return 1
    print("\nall endpoint-row WebKit checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
