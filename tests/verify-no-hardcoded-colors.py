#!/usr/bin/env python3
"""verify-no-hardcoded-colors.py - no painted colour outside the tokens.

A theme swap only re-colours what goes through a token. A hex or rgb()
literal written directly in a component rule paints the SAME colour in
both themes, which is how a dark-theme border ends up near-invisible on
a light surface - or a black veil lands on a near-white page at a
weight meant for a near-black one.

MEASURED: two such literals existed and both were wrong in light theme.

  .cm-js .cm-nav-scrim   background: rgb(0 0 0 / 0.55)
      The rule painted 0.55 black in BOTH themes while --scrim is
      theme-aware (#000000b8 dark, #1818186b light). The same alpha
      over a near-black page and over a near-white one hides the page
      by very different amounts - the reason --scrim exists at all.
      Now var(--scrim).

  .cm-header.is-scrolled  box-shadow: 0 8px 24px -18px rgba(0,0,0,0.9)
      A black 0.9 cast under a light bar is a hard band, not a
      separation. Now var(--shadow-ink), a new token whose light
      value is rgba(0, 0, 0, 0.18).

This guard reads the real stylesheets and fails if any colour
property outside the theme blocks carries a literal instead of a
token. The theme blocks themselves (the :root, [data-theme=...] and
[data-cm-theme=...] declarations) are where colours are SUPPOSED to
live, so they are excluded.

Usage: python3 tests/verify-no-hardcoded-colors.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STYLES = os.path.join(ROOT, "src", "styles")

COLOR_PROPS = re.compile(
    r"(?:^|[;{\s])(color|background|background-color|"
    r"border(?:-[a-z]+)?|border-color|"
    r"border-(?:top|right|bottom|left)-color|outline|outline-color|"
    r"fill|stroke|caret-color|accent-color|box-shadow|text-shadow|"
    r"column-rule-color|text-decoration-color|background-image)"
    r"\s*:\s*([^;{}]*)",
    re.I)

LITERAL = re.compile(
    r"#[0-9a-fA-F]{3,8}\b"
    r"|\brgba?\s*\([^)]*\)"
    r"|\b(?:white|black)\b")

# a declaration that is entirely a token reference is fine
TOKEN_ONLY = re.compile(r"^var\(\s*--[a-z0-9-]+\s*\)$")


def strip_comments(css):
    return re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), css,
                  flags=re.S)


def blank_token_blocks(css):
    """Blank out the blocks that DEFINE theme tokens."""
    keep = []
    depth = 0
    i = 0
    n = len(css)
    start = 0
    body_start = 0
    while i < n:
        ch = css[i]
        if ch == "{":
            if depth == 0:
                body_start = i + 1
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                sel = css[start:body_start]
                if (":root" in sel or "data-theme" in sel
                        or "data-cm-theme" in sel):
                    keep.append((start, i + 1))
                start = i + 1
        i += 1
    res = []
    prev = 0
    for a, b in keep:
        res.append(css[prev:a])
        res.append("\n" * css[a:b].count("\n"))
        prev = b
    res.append(css[prev:])
    return "".join(res)


def main():
    if not os.path.isdir(STYLES):
        print("FAIL: %s not found" % STYLES)
        return 1
    findings = []
    for fn in sorted(os.listdir(STYLES)):
        if not fn.endswith(".css"):
            continue
        path = os.path.join(STYLES, fn)
        css = strip_comments(open(path, encoding="utf-8").read())
        body = blank_token_blocks(css)
        sel = ""
        for ln_no, line in enumerate(body.split("\n"), 1):
            m = re.match(r"\s*([.#@:\[][^{}]*)\{", line)
            if m:
                sel = m.group(1).strip()
            for dm in COLOR_PROPS.finditer(line):
                val = dm.group(2).strip()
                if not val or TOKEN_ONLY.match(val):
                    continue
                for lit in LITERAL.finditer(val):
                    findings.append((fn, ln_no, sel, lit.group(0),
                                     dm.group(1).strip() + ": " + val[:64]))

    if findings:
        print("HARDCODED_COLORS: FAIL  (%d literal(s) outside the theme "
              "blocks)" % len(findings))
        for fn, ln, sel, lit, decl in findings:
            print("  - %s:%d  %s  %s   [%s]" % (fn, ln, sel[:36], lit, decl))
        return 1
    print("HARDCODED_COLORS: OK  (every painted colour outside the theme "
          "blocks resolves through a token)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
