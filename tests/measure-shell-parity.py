#!/usr/bin/env python3
"""
Side-by-side layout measurement: shadcn's docs shell vs oem-ui's showcase.

The parity audit recorded shadcn's shell geometry in prose, and prose ages.
This measures BOTH sites in the same engine, on the same metrics, in one
run, and prints them side by side so a divergence is a number rather than
an opinion.

It is a MEASUREMENT tool, not an assertion tool: it prints a table and
exits 0 whether or not the two agree. The two sites are NOT supposed to be
identical - ours is a different design language (sharp corners, no chroma,
mono) - so what matters is seeing WHICH axis differs and by how much.

  tests/measure-shell-parity.py            # table
  tests/measure-shell-parity.py --json     # same numbers, machine-readable
  CM_BASE=http://host:port/ ...            # measure a different build
"""
import json
import os
import sys
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Safari/605.1.15")

THEIRS = os.environ.get("SHADCN_URL", "https://ui.shadcn.com/docs/components/button")
OURS = os.environ.get("CM_BASE", "http://127.0.0.1:4471/") + "f/panels/"

BOOT = 90000

# name -> (css property to read, ours selectors, shadcn selectors)
# `box` is special: it reads the border box, not a computed property.
ROWS = [
    ("header height",      "box:height",     ["header"],                      ["header"]),
    ("header position",    "position",       ["header"],                      ["header"]),
    ("header bg",          "backgroundColor",["header"],                      ["header"]),
    ("body bg",            "backgroundColor",["body"],                        ["body"]),
    ("body color",         "color",          ["body"],                        ["body"]),
    ("rail width",         "box:width",      ["nav.cm-rail", ".cm-nav", "nav"], ["aside", "[data-sidebar='sidebar']", "nav"]),
    ("rail position",      "position",       ["nav.cm-rail", ".cm-nav", "nav"], ["aside", "[data-sidebar='sidebar']", "nav"]),
    ("rail top",           "top",            ["nav.cm-rail", ".cm-nav", "nav"], ["aside", "[data-sidebar='sidebar']", "nav"]),
    ("content x",          "box:x",          ["main", ".cm-shell"],           ["main"]),
    ("content width",      "box:width",      ["main", ".cm-shell"],           ["main"]),
    ("content max-width",  "maxWidth",       ["main", ".cm-shell"],           ["main"]),
    ("content padding-top","paddingTop",     ["main", ".cm-shell"],           ["main"]),
    ("h1 size",            "fontSize",       ["main h1"],                     ["main h1"]),
    ("h1 weight",          "fontWeight",     ["main h1"],                     ["main h1"]),
    ("h1 y",               "box:y",          ["main h1"],                     ["main h1"]),
    ("h2 size",            "fontSize",       ["main h2"],                     ["main h2"]),
    ("h2 margin-top",      "marginTop",      ["main h2"],                     ["main h2"]),
    ("h2 weight",          "fontWeight",     ["main h2"],                     ["main h2"]),
    ("para size",          "fontSize",       ["main p", "main"],              ["main p", "main"]),
    ("para line-height",   "lineHeight",     ["main p", "main"],              ["main p", "main"]),
    ("para color",         "color",          ["main p", "main"],              ["main p", "main"]),
]


def read(page, selectors, prop):
    """First selector that resolves wins. Returns None if none do."""
    expr = ("e => { const c = getComputedStyle(e); const r = e.getBoundingClientRect(); "
            "return { v: c[%s], x: r.x, y: r.y, w: r.width, h: r.height }; }" % json.dumps(prop))
    for sel in selectors:
        try:
            got = page.eval_on_selector(sel, expr)
        except Exception:
            continue
        if not got:
            continue
        if prop.startswith("box:"):
            key = prop.split(":", 1)[1]
            v = got[{"x": "x", "y": "y", "width": "w", "height": "h"}[key]]
            return round(v, 1)
        if got["v"] not in (None, ""):
            return got["v"]
    return None


def measure(page):
    out = {}
    for name, prop, ours, theirs in ROWS:
        out[name] = read(page, ours, prop)
    return out


def main():
    as_json = "--json" in sys.argv
    with sync_playwright() as pw:
        browser = pw.webkit.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 900}, user_agent=UA)
        page = ctx.new_page()

        page.set_default_timeout(180000)  # starved box: 27s+ to boot

        data = {}
        for label, url in (("shadcn", THEIRS), ("oem-ui", OURS)):
            try:
                page.goto(url, wait_until="networkidle", timeout=BOOT)
            except Exception:
                page.goto(url, wait_until="domcontentloaded", timeout=BOOT)
            page.wait_for_timeout(700)
            data[label] = measure(page)
        browser.close()

    if as_json:
        print(json.dumps({"urls": {"shadcn": THEIRS, "oem-ui": OURS}, "rows": data}, indent=1))
        return

    print(f"shadcn : {THEIRS}")
    print(f"oem-ui : {OURS}\n")
    w = max(len(r[0]) for r in ROWS) + 2
    print(f"{'metric':<{w}}{'shadcn':<26}{'oem-ui':<26}")
    print("-" * (w + 52))
    for name, _p, _o, _t in ROWS:
        t = data["shadcn"].get(name)
        o = data["oem-ui"].get(name)
        mark = ""
        if t is None and o is None:
            mark = "  <- neither resolved"
        print(f"{name:<{w}}{str(t):<26}{str(o):<26}{mark}")


if __name__ == "__main__":
    main()
