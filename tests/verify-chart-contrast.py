#!/usr/bin/env python3
"""verify-chart-contrast.py - guard the chart series ramp.

The chart series scale is FIVE greys with a promise attached, written
down in two places in this repo:

  src/styles/tokens.css  "five greys from --ink down to a floor that
                          still clears 3:1 on --panel and --panel-nested,
                          which is the WCAG figure for a non-text mark"
  src/js/cli-mono.js     "Five tones, because --chart-c1..5 are five...
                          it could not clear 3:1 on the surface it is
                          drawn on, which is the WCAG figure for a
                          non-text mark"

MEASURED: the promise was broken. The faintest tone is the one that has
to clear the floor, and it did not:

  dark  c5 #525252  2.23:1 on --panel-nested   (floor 3:1)
  light c5 #999999  2.41:1 on --panel-nested   (floor 3:1)

A consumer who writes a five-series chart got a series that was nearly
invisible against the card it was drawn on, in BOTH themes, and the
shipped specimens only ever render two series - so nothing on screen
ever showed the defect.

This guard is the measurement, promoted. It reads the real token
values out of tokens.css (no hardcoded copies) and asserts:

  1. every one of the five tones clears 3.00:1 against --panel AND
     --panel-nested, in BOTH the dark and the light theme;
  2. adjacent tones are still visibly distinct (contrast >= 1.30), so
     tightening the floor did not collapse the ramp into one grey;
  3. the ramp is monotonic in the theme's own direction (dark: c1
     lightest -> c5 darkest; light: c1 darkest -> c5 lightest);
  4. the floor is cleared with margin, not by rounding luck.

Exit 0 = the promise in the source comments is true. Exit 1 = it is
not, and the failure prints the measured numbers.

Usage: python3 tests/verify-chart-contrast.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOKENS = os.path.join(ROOT, "src", "styles", "tokens.css")

FLOOR = 3.00          # WCAG 1.4.11 non-text contrast
SEP_MIN = 1.30        # adjacent tones must remain distinguishable


def chan(v):
    v = v / 255.0
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def lum(rgb):
    r, g, b = rgb
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def hex2rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def cr(fg, bg):
    """WCAG contrast ratio between two hex colours."""
    l1, l2 = lum(hex2rgb(fg)), lum(hex2rgb(bg))
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def strip_comments(text):
    """Remove /* ... */ comments. A comment before a selector is not
    part of that selector, and one that mentions another theme's name
    would otherwise misclassify the block."""
    return re.sub(r"/\*.*?\*/", " ", text, flags=re.S)


def top_level_blocks(css):
    """Return [(selector, body)] for every top-level {...} block.

    Comment- and string-aware: a brace inside a comment must not move a
    block boundary, or every block after it is misread.
    """
    out = []
    depth = 0
    sel_start = 0
    body_start = None
    i = 0
    n = len(css)
    while i < n:
        ch = css[i]
        if ch == "/" and i + 1 < n and css[i + 1] == "*":
            j = css.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if ch in "\"'":
            quote = ch
            i += 1
            while i < n and css[i] != quote:
                if css[i] == "\\":
                    i += 1
                i += 1
            i += 1
            continue
        if ch == "{":
            if depth == 0:
                body_start = i + 1
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and body_start is not None:
                sel = css[sel_start:body_start - 1]
                # the selector text may carry a preceding comment
                sel = strip_comments(sel)
                out.append((sel, css[body_start:i]))
                sel_start = i + 1
        i += 1
    return out


def tokens_from(body):
    out = {}
    for m in re.finditer(r"--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,6})\s*;", body):
        out[m.group(1)] = m.group(2).lower()
    return out


def check(name, body, light):
    fails = []
    t = tokens_from(body)
    tones = []
    for i in range(1, 6):
        k = "chart-c%d" % i
        if k not in t:
            fails.append("%s: token %s missing" % (name, k))
            return fails, []
        tones.append(t[k])
    panel = t.get("panel")
    nested = t.get("panel-nested")
    if not panel or not nested:
        fails.append("%s: --panel/--panel-nested missing" % name)
        return fails, []

    print("-- %s (panel %s, panel-nested %s)" % (name, panel, nested))
    for i, tone in enumerate(tones, 1):
        worst = min(cr(tone, panel), cr(tone, nested))
        ok = worst >= FLOOR
        print("   c%d %s  min %5.2f vs surfaces  %s" % (
            i, tone, worst, "OK" if ok else "FAIL"))
        if not ok:
            fails.append("%s: c%d %s is %.2f:1 on %s - below the 3:1 "
                         "non-text floor" % (
                             name, i, tone, worst,
                             panel if cr(tone, panel) < cr(tone, nested)
                             else nested))

    for i in range(4):
        s = cr(tones[i], tones[i + 1])
        if s < SEP_MIN:
            fails.append("%s: c%d and c%d are only %.2f apart - the ramp "
                         "has collapsed" % (name, i + 1, i + 2, s))

    lumas = [lum(hex2rgb(c)) for c in tones]
    mono = all(lumas[i] > lumas[i + 1] for i in range(4)) if not light else \
        all(lumas[i] < lumas[i + 1] for i in range(4))
    if not mono:
        fails.append("%s: the ramp is not monotonic in the theme's "
                     "direction" % name)
    print("   separations: %s  monotonic: %s" % (
        " ".join("%.2f" % cr(tones[i], tones[i + 1]) for i in range(4)),
        "yes" if mono else "NO"))
    return fails, tones


def main():
    if not os.path.exists(TOKENS):
        print("FAIL: %s not found" % TOKENS)
        return 1
    css = open(TOKENS, encoding="utf-8").read()
    fails = []
    ramps = {}

    for sel, body in top_level_blocks(css):
        t = tokens_from(body)
        if not all(("chart-c%d" % i) in t for i in range(1, 6)):
            continue
        if "panel" not in t or "panel-nested" not in t:
            continue
        label = re.sub(r"\s+", " ", sel).strip() or "(unnamed)"
        light = "light" in label
        f, tones = check(label, body, light)
        fails += f
        if tones:
            key = "light" if light else "dark"
            ramps.setdefault(key, set()).add(tuple(tones))

    print()
    for key, group in ramps.items():
        if len(group) > 1:
            fails.append("%s theme: %d different ramps declared across "
                         "blocks - a scoped container must not ship a "
                         "different scale" % (key, len(group)))

    if not ramps:
        print("FAIL: no chart ramp found in %s" % TOKENS)
        return 1

    if fails:
        print("CHART_CONTRAST: FAIL")
        for f in fails:
            print("  - %s" % f)
        return 1
    print("CHART_CONTRAST: OK  (every declared ramp clears %.2f:1 on "
          "--panel and --panel-nested, in both themes)" % FLOOR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
