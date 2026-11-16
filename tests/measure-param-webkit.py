#!/usr/bin/env python3
"""WebKit probe for the parameter row specimen (cm-param).

The contract checks read the CSS source; this probe reads the BUILT
page in the engine Omar actually uses (Safari/WebKit) at phone and
desktop widths. Three claims, each falsifiable:

1. THE DESCRIPTION WRAPS BY HEIGHT, NOT BY SPLITTING THE HEAD. The
   row is flex-wrap: the head items (name, required mark, type, in
   badge - or a status code on the response rows) are short and stay
   on one line; the description carries `flex: 1 1 10rem`, so it
   shares the line when the head leaves room and falls to its own
   line when it does not. The expectation is DERIVED, not hardcoded:
   headW + column-gap + 10rem <= the row's content width says
   "same line"; anything wider says "own line". A row whose
   description never wraps overruns the viewport on a phone, and a
   row that always wraps wastes the desktop line - the derived check
   fails either way. The probe must exercise BOTH branches, so it
   refuses a run in which every row made the same decision.

2. THE REQUIRED MARK IS THE FORM'S OWN. The required rows carry a
   `*` that computes to the :root --ink-faint of the ACTIVE theme -
   read after the theme is set AND the frame has settled (set the
   attribute, wait, then read; a same-tick read has reported wrong
   pairs before). The theme runs are proven different: the
   data-theme attribute and the computed --ink are printed for each.
   The token is a hex and the computed value an rgb() - the
   comparison normalises both to rgb, or a correct build fails on a
   format difference.

3. NOTHING OVERRUNS. Every row's description stays inside the row's
   own right edge at every width, and the document itself does not
   grow sideways (baseline at HEAD: scrollWidth == innerWidth at all
   four widths, so a new overflow is a regression this change
   introduced, not an inherited one).

Runs against the LAN preview (Omar's rule: bind 0.0.0.0, verify over
the LAN). Usage: /root/.venvs/mau/bin/python tests/measure-param-webkit.py
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

# Read in-page: one pass per row (named and response alike), everything
# the claims need. The head of a row is everything before the description.
PROBE = """
() => {
  const sec = document.querySelector('#param');
  if (!sec) return { missing: true };
  const root = getComputedStyle(document.documentElement);
  const out = {
    missing: false,
    theme: document.documentElement.getAttribute('data-theme'),
    ink: root.getPropertyValue('--ink').trim(),
    inkFaint: root.getPropertyValue('--ink-faint').trim(),
    inkDim: root.getPropertyValue('--ink-dim').trim(),
    rem: parseFloat(root.fontSize),
    docOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    totalRows: sec.querySelectorAll('.cm-param').length,
    rows: [],
  };
  sec.querySelectorAll('.cm-param').forEach(row => {
    const name = row.querySelector('.cm-param__name');
    const desc = row.querySelector('.cm-param__desc');
    const req = row.querySelector('.cm-param__req');
    const inB = row.querySelector('.cm-param__in');
    const rc = getComputedStyle(row);
    const rrect = row.getBoundingClientRect();
    const contentW = rrect.width - (parseFloat(rc.paddingLeft) || 0) - (parseFloat(rc.paddingRight) || 0);
    const lead = name ? name.getBoundingClientRect() : rrect;
    const headItems = [...row.children].filter(c => c !== desc);
    const headRight = Math.max(...headItems.map(c => c.getBoundingClientRect().right));
    const headW = headRight - lead.left;
    const gap = parseFloat(rc.columnGap) || 0;
    const descBasis = 10 * out.rem;
    const sameLine = (headW + gap + descBasis) <= contentW;
    const dr = desc ? desc.getBoundingClientRect() : null;
    // The top comparison must start from the HEAD's own top, not the
    // row's border box: the row carries top padding, so a description
    // on the same line reads 8px "below" the row's top while sitting
    // exactly on the head's baseline. The head items' top is the
    // shared line.
    const headTop = headItems.length
      ? Math.min(...headItems.map(c => c.getBoundingClientRect().top))
      : lead.top;
    out.rows.push({
      label: name ? name.textContent : (row.textContent || '').trim().slice(0, 24),
      isNamed: !!name,
      hasReq: !!req,
      reqColor: req ? getComputedStyle(req).color : null,
      inText: inB ? inB.textContent : null,
      nameColor: name ? getComputedStyle(name).color : null,
      headW: Math.round(headW * 10) / 10,
      contentW: Math.round(contentW * 10) / 10,
      gap: Math.round(gap * 10) / 10,
      sameLine,
      descTopDelta: dr ? Math.round((dr.top - headTop) * 10) / 10 : null,
      leadLeft: Math.round(lead.left * 10) / 10,
      descRight: dr ? Math.round(dr.right * 10) / 10 : null,
      rowRight: Math.round(rrect.right * 10) / 10,
      wrapStyle: rc.flexWrap,
    });
  });
  return out;
}
"""


def to_rgb(css_color: str) -> str:
    """Normalise a computed colour or a hex token to 'rgb(r, g, b)' so the
    two sides of a comparison share one format. The token is authored as a
    hex; getComputedStyle answers in rgb(). Comparing the raw strings is a
    format failure that reads as a colour failure."""
    c = css_color.strip()
    if c.startswith("#"):
        h = c.lstrip("#")
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        return f"rgb({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)})"
    return c


def main() -> int:
    fails = 0
    all_decisions = []
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
                    print(f"  FAIL {tag}: no #param section in the built page")
                    fails += 1
                    continue

                # 3. NOTHING OVERRUNS. The document must not grow
                #    sideways: at HEAD it did not at any width, so a
                #    new overflow is this change's, not inherited.
                if d["docOverflow"] > 0:
                    print(f"  FAIL {tag}: document overflows sideways by {d['docOverflow']}px")
                    fails += 1

                if d["totalRows"] != 7:
                    print(f"  FAIL {tag}: expected 7 rows (5 parameter + 2 response), got {d['totalRows']}")
                    fails += 1
                    continue

                decisions = []
                for r in d["rows"]:
                    if r["wrapStyle"] != "wrap":
                        print(f"  FAIL {tag}: row '{r['label']}' does not compute flex-wrap: wrap")
                        fails += 1
                    # 3b. the description stays inside the row's own
                    #     right edge (viewport coordinates on both
                    #     sides - not width against position).
                    if r["descRight"] is not None and r["descRight"] > r["rowRight"] + 1:
                        print(f"  FAIL {tag}: row '{r['label']}' description overruns the row's right edge "
                              f"({r['descRight']} > {r['rowRight']})")
                        fails += 1
                    if r["leadLeft"] < 0:
                        print(f"  FAIL {tag}: row '{r['label']}' lead is off-screen left")
                        fails += 1
                    # 1. THE WRAP DECISION. Derived, not hardcoded:
                    #    same-line when the head leaves room, own line
                    #    otherwise. The measured tops decide.
                    if r["descTopDelta"] is None:
                        print(f"  FAIL {tag}: row '{r['label']}' has no description")
                        fails += 1
                        continue
                    if r["sameLine"]:
                        if abs(r["descTopDelta"]) > 4:
                            print(f"  FAIL {tag}: row '{r['label']}' should share the line "
                                  f"(head {r['headW']} + gap {r['gap']} + basis fits in {r['contentW']}) "
                                  f"but the description sits {r['descTopDelta']}px below")
                            fails += 1
                    else:
                        if r["descTopDelta"] < 4:
                            print(f"  FAIL {tag}: row '{r['label']}' should fall to its own line "
                                  f"(head {r['headW']} + gap {r['gap']} + basis exceeds {r['contentW']}) "
                                  f"but the description still shares it (delta {r['descTopDelta']}px)")
                            fails += 1
                    decisions.append(r["sameLine"])

                # The probe must exercise BOTH branches of the wrap
                # decision ACROSS the runs, or one half of it is
                # unproven: the named rows are narrow grid columns
                # (own line on a phone, shared line when the grid
                # column widens) and the full-width response rows
                # share their line when there is room. The global
                # check below refuses a sweep in which every row
                # every width made the same decision.
                all_decisions.extend(decisions)
                named = [r for r in d["rows"] if r["isNamed"]]
                if len(named) != 5:
                    print(f"  FAIL {tag}: expected 5 named parameter rows, got {len(named)}")
                    fails += 1

                # 2. THE REQUIRED MARK IS THE FORM'S OWN, per theme.
                reqRows = [r for r in named if r["hasReq"]]
                if len(reqRows) != 2:
                    print(f"  FAIL {tag}: expected 2 required rows, got {len(reqRows)}")
                    fails += 1
                faint = to_rgb(d["inkFaint"])
                for r in reqRows:
                    if to_rgb(r["reqColor"]) != faint:
                        print(f"  FAIL {tag}: required mark on '{r['label']}' reads {r['reqColor']}, "
                              f"not the theme's ink-faint {d['inkFaint']} ({faint})")
                        fails += 1
                # The name reads the theme's full ink; the in badge and
                # the description read the theme's ink-dim.
                ink = to_rgb(d["ink"])
                dim = to_rgb(d["inkDim"])
                for r in named:
                    if to_rgb(r["nameColor"]) != ink:
                        print(f"  FAIL {tag}: row '{r['label']}' name reads {r['nameColor']}, not the theme's ink {d['ink']}")
                        fails += 1

                # Prove the two theme runs differed: attribute + token.
                print(f"  ok {tag}: theme={d['theme']} ink={d['ink']} faint={d['inkFaint']} "
                      f"rows={d['totalRows']} overflow={d['docOverflow']}px "
                      f"wrap-decisions " +
                      " ".join(f"{r['label']}:{'same' if r['sameLine'] else 'own'}" for r in d["rows"]))

        browser.close()

    # Both branches of the wrap decision must have been exercised
    # across the runs, or one half of the check never ran.
    if not (any(all_decisions) and any(not x for x in all_decisions)):
        print(f"FAIL: every row made the same wrap decision across all runs "
              f"({sorted(set(all_decisions))}) - one branch of the wrap check is unexercised")
        fails += 1

    if fails:
        print(f"\n{fails} FAILURE(S)")
        return 1
    print("\nall parameter-row WebKit checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
