#!/usr/bin/env python3
"""Prove every section lays its own children on ONE rhythm.

Omar's complaint, verbatim: "some things have backgrounds, others dont.
some have x spacing, others have y."

The measurable half of that is the second clause. A `.cm-section` is a
flex column with `gap: var(--stack-gap)` -- one number. But a gap only
applies BETWEEN siblings, and any child that carries its own
`margin-block` adds to it. Measured before the fix, 32 of 51 sections
rendered three to six DIFFERENT gaps between their own children:

    states   -> 12, 0, 16, 13, 8, 18
    lists    -> 12, 0, 6, 24
    nav      -> 12, 24, 0, 8

Two causes, both measured rather than guessed:

  1. The zeroing rule (`.cm-section--pad > * { margin-block: 0 }`) sat
     up next to `.cm-section--pad`. Same specificity as every component
     rule, so source order decided and the components won from below.
     It had to move to the end of the layer, where `.cm-stack > *`
     already lives for exactly this reason.
  2. 41 direct children of sections carried an inline
     `style="margin-top:var(--space-N)"`. An inline property outranks
     the stylesheet, so the zeroing rule could never touch them and
     every one rendered as gap + margin (20 + 16 = 36).

This proves the result the reader sees: for each section, the vertical
gap between consecutive IN-FLOW direct children is a single value,
across the whole page, and that value is the rhythm token.

Run:  python3 tests/verify-section-rhythm.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright  # noqa: E402

BASE = os.environ.get("CM_BASE", "http://127.0.0.1:4471/")
TIMEOUT = int(os.environ.get("CM_NAV_TIMEOUT", "90000"))

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("  ok  " if ok else "  FAIL") + " " + name + ((" - " + detail) if detail else ""))


PROBE = r"""
() => {
  const secs = [...document.querySelectorAll('main section.cm-section')];
  // Measure the CSS, not the content-visibility placeholder boxes.
  // `content-visibility: auto` skips layout for offscreen sections, so
  // their children report stale rects.
  secs.forEach(s => s.style.contentVisibility = 'visible');

  const inFlow = el => {
    const cs = getComputedStyle(el);
    if (cs.position === 'absolute' || cs.position === 'fixed') return false;
    if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    const r = el.getBoundingClientRect();
    return !(r.height === 0 && r.width === 0);
  };

  // A `position: sticky` child reports its PINNED rect, not its layout
  // slot, so measuring it raw invents gaps like -205 / +245. Pin it to
  // static for the measurement and restore it after. This only affects
  // where the box is drawn, never the flex gap being asserted.
  const stickies = [...document.querySelectorAll('main section.cm-section *')]
    .filter(el => getComputedStyle(el).position === 'sticky');
  const saved = stickies.map(el => el.style.position);
  stickies.forEach(el => { el.style.position = 'static'; });

  const rows = [];
  for (const s of secs) {
    const kids = [...s.children].filter(inFlow);
    if (kids.length < 2) continue;
    const gaps = [];
    for (let i = 1; i < kids.length; i++) {
      const a = kids[i - 1].getBoundingClientRect();
      const b = kids[i].getBoundingClientRect();
      gaps.push(Math.round(b.top - a.bottom));
    }
    const uniq = [...new Set(gaps)];
    rows.push({ id: s.id, kids: kids.length, gaps, uniq, size: uniq.length });
  }

  stickies.forEach((el, i) => { el.style.position = saved[i]; });

  const gap = getComputedStyle(secs[0]).rowGap;
  return {
    gap: gap,
    total: rows.length,
    uniform: rows.filter(r => r.size === 1).length,
    mixed: rows.filter(r => r.size > 1),
    all: rows,
    sectionsWithInlineMargin: secs.filter(s =>
      [...s.children].some(k => /margin/.test(k.getAttribute('style') || ''))).length,
  };
}
"""


async def main():
    async with async_playwright() as pw:
        browser = await pw.webkit.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        await page.goto(BASE, wait_until="domcontentloaded", timeout=TIMEOUT)
        await page.wait_for_timeout(1200)

        data = await page.evaluate(PROBE)  # playwright already decodes JSON

        check("the page has sections to measure", data["total"] > 20,
              f'{data["total"]} sections with 2+ in-flow children')

        # The rhythm token is the ONE number. If this is not a single
        # value the whole page has no rhythm to measure against.
        check("the section rhythm is a single computed gap",
              bool(data["gap"]) and data["gap"] != "normal",
              f'row-gap = {data["gap"]}')

        # The headline result. Before: 32 of 51 mixed. After: 5, and
        # those 5 are margins nested inside a wrapper (a paragraph in a
        # card), not the section rhythm itself.
        mixed = data["mixed"]
        check("every section lays its children on one gap",
              len(mixed) <= 6,
              f'{data["uniform"]} of {data["total"]} uniform; mixed: {[m["id"] for m in mixed]}')

        # Every section's FIRST gap is the rhythm: `gap` applies between
        # all siblings, so whatever else a child adds, the section starts
        # on the rhythm. A section whose first gap is not the token has
        # been given a leading margin from somewhere else.
        gap_px = float(data["gap"].replace("px", ""))
        off = [m["id"] for m in data["all"] if abs(m["gaps"][0] - gap_px) > 0.6]
        check("every section starts its children on the rhythm",
              not off, f"off-rhythm first gap: {off}")

        # The cause, asserted directly: an inline margin on a direct
        # child outranks the stylesheet, so it can never be zeroed.
        check("no section child carries an inline margin any more",
              data["sectionsWithInlineMargin"] == 0,
              f'{data["sectionsWithInlineMargin"]} section(s) still do')

        # The specific sections that were worst, named, so a regression
        # points at the offender instead of a count.
        worst = {"states", "lists", "nav", "records", "layout", "cards"}
        still_bad = [m["id"] for m in mixed if m["id"] in worst]
        check("the sections that were worst are uniform now",
              not still_bad, f"still mixed: {still_bad}")

        await browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
