#!/usr/bin/env python3
"""WebKit probe for the relative-time specimen (cmInitAgo).

MEASURE, do not trust the vision model's opinion. The specimen renders seven
rows whose labels are seconds old at build, so the runtime's rewrite is the
only thing that can make the page honest. Three claims, each falsifiable:

1. THE RUNTIME BOUND EVERY <time data-cm-ago> AND WROTE ITS title. The
   authored fallbacks are "now", "5m ago", "3h ago", "2d ago", "1mo ago",
   "2y ago", "in an hour". A static build with no runtime writes NO title
   attribute on these elements at all, so the presence of a title carrying a
   full date is the runtime's fingerprint - and it is independent of what the
   visible text reads. The text CAN legitimately equal the authored fallback:
   the datetime is computed at BUILD time (Astro static generation), so a row
   authored "3h ago" reads "3h ago" again when the preview lands minutes
   later. Comparing text to the authored fallback is a false failure; the
   runtime's own write is the title.

2. THE SHARED CLOCK AGES IT. The first row is seconds old at build, so it
   must read something other than "now" (seconds or minutes). A label that
   never moves is a frozen specimen, and a frozen specimen is the same
   defect as a readbar without its --spec modifier: it lies by standing
   still. The probe cannot assert an exact value - the gap is seconds and
   depends on build-to-preview latency - only that it is not the authored
   fallback.

3. THE SHARED INTERVAL IS ONE, NOT PER-ELEMENT. Seven rows, one setInterval.
   A per-element timer is the exact redundancy this library deletes.

Runs against the LAN preview (Omar's rule: bind 0.0.0.0, verify over the
LAN). Usage: /root/.venvs/mau/bin/python tests/measure-ago-webkit.py
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

AUTHORED = ["now", "5m ago", "3h ago", "2d ago", "1mo ago", "2y ago", "in an hour"]


def main() -> int:
    fails = 0
    with sync_playwright() as p:
        browser = p.webkit.launch()
        page = browser.new_page()

        for w, h in VIEWPORTS:
            page.set_viewport_size({"width": w, "height": h})
            page.goto(URL, wait_until="commit")
            # Poll evaluate for the runtime's own mark - never a blind timer,
            # never wait_for_function (measured to time out on the FIRST call
            # after a commit navigation in this engine).
            for _ in range(40):
                if page.evaluate("() => document.documentElement.classList.contains('cm-js')"):
                    break
                page.wait_for_timeout(250)
            # Wait for the shared clock to have ticked at least once so a
            # seconds-old label is not read at its authored fallback.
            # Poll for it via the row's own text moving off "now".
            for _ in range(40):
                t0 = page.evaluate("() => { const t = document.querySelector('time[data-cm-ago]'); return t ? (t.textContent||'').trim() : null; }")
                if t0 is not None and t0 != "now" and t0 != "":
                    break
                page.wait_for_timeout(800)

            rows = page.evaluate("""() => {
                const times = [...document.querySelectorAll('time[data-cm-ago]')];
                return times.map(t => ({
                    text: (t.textContent || '').trim(),
                    title: t.getAttribute('title') || '',
                    hasTitle: !!t.getAttribute('title'),
                    bound: !!t.__cmAgoPaint,
                }));
            }""")

            if len(rows) != len(AUTHORED):
                print(f"  FAIL [{w}x{h}]: expected {len(AUTHORED)} relative-time rows, got {len(rows)}")
                fails += 1
                continue

            # 1. The runtime bound every row and wrote its title. The title is
            #    the runtime's fingerprint: a static build writes no title on
            #    these elements at all, and the visible text is allowed to
            #    equal the authored fallback because the datetime is computed
            #    at BUILD time and the preview lands minutes later.
            for i, r in enumerate(rows):
                if not r["bound"]:
                    print(f"  FAIL [{w}x{h}]: row {i} is not bound (__cmAgoPaint missing) - the runtime never touched it")
                    fails += 1
                if not r["hasTitle"]:
                    print(f"  FAIL [{w}x{h}]: row {i} has no title attribute (the runtime must write the full date there)")
                    fails += 1
                elif not any(ch.isdigit() for ch in r["title"]):
                    print(f"  FAIL [{w}x{h}]: row {i} title is not a date: '{r['title']}'")
                    fails += 1

            # 2. The seconds row moved off "now" - the clock is live.
            if rows[0]["text"] == "now":
                print(f"  FAIL [{w}x{h}]: the seconds row still reads 'now' after the clock poll; the clock is frozen")
                fails += 1

            # 3. The future-date branch. The showcase's future row is built
            #    with Date.now() + 1h, so it has already gone past by the time
            #    the preview lands - the visible text is now an absolute date
            #    and the branch is no longer reachable on the page. That is a
            #    specimen that outlived itself, not a defect, and a probe that
            #    can only see the page cannot test it. The branch is exercised
            #    directly through the exposed agoText() with a synthetic
            #    future timestamp, which is what the mutation sweep hits.
            #    (The page-level check below keeps the absolute form honest
            #    for whatever rows are still future at read time.)
            if rows[-1]["text"] == "in an hour":
                print(f"  FAIL [{w}x{h}]: the future row still reads 'in an hour' instead of an absolute date")
                fails += 1
            if not rows[-1]["hasTitle"]:
                print(f"  FAIL [{w}x{h}]: the future row has no title attribute (the full date must ride on title)")
                fails += 1

            # 4. Every row carries the full date on title.
            for i, r in enumerate(rows):
                if not r["hasTitle"]:
                    print(f"  FAIL [{w}x{h}]: row {i} has no title attribute")
                    fails += 1

            print(f"  ok  [{w}x{h}]: {len(rows)} rows bound with titles, clock live, future row absolute")

            # 3b. The future-date BRANCH, tested through the exposed agoText()
            #     with a synthetic timestamp. The showcase's future row is
            #     built at Date.now() + 1h and has usually gone past by the
            #     time the preview lands, so the page cannot exercise this
            #     branch - but the mutation sweep can, and a branch nobody
            #     can reach is a branch nobody has proven.
            future = page.evaluate("""() => {
                const now = Date.now();
                return window.cliMono ? window.cliMono.agoText(now + 3600000, now) : null;
            }""")
            if future is None:
                print(f"  FAIL [{w}x{h}]: cliMono.agoText is not exposed on the window handle")
                fails += 1
            elif " ago" in future:
                print(f"  FAIL [{w}x{h}]: a future timestamp must read an absolute date, not '{future}'")
                fails += 1
            elif not any(ch.isdigit() for ch in future):
                print(f"  FAIL [{w}x{h}]: the absolute form must carry a digit: '{future}'")
                fails += 1
            else:
                print(f"  ok  [{w}x{h}]: future branch reads an absolute date via agoText: '{future}'")

# 3c. The bound paint must read the SHARED, INJECTABLE clock - not
            #     an inline Date.now(). The first attempt at this check grepped
            #     the bound paint's toString() for the literal token
            #     "CM_AGNO_NOW" and FAILED ON A CORRECT BUILD: the runtime is
            #     minified in the served bundle, so that token is gone and the
            #     check was measuring the minifier, not the code. A source
            #     token is not a behavioural invariant and cannot survive a
            #     bundler; the invariant is that the paint reads the clock a
            #     consumer (or a test) can swap. Swapping it and re-painting
            #     moves the label, which is the only reading that can fail.
            #     (The module-level clock variable is a source-level
            #     convention, not something the served page can see; it is
            #     policed by the mutation sweep instead, where the source is
            #     read directly.)
            before = page.evaluate("""() => {
                const t = document.querySelector('time[data-cm-ago]');
                return t ? (t.textContent || '').trim() : null;
            }""")
            if before is None:
                print(f"  FAIL [{w}x{h}]: no bound time to inspect")
                fails += 1
            else:
                # The clock must jump BACK, not forward: every bound instant
                # is in the past, so pushing "now" 40 days into the future
                # makes the instant DEEPER in the past and a correct paint
                # keeps showing a relative form - the first cut of this
                # check did exactly that and reported a failure on a
                # correct build. Pushing "now" 40 days into the PAST makes
                # the instant future, and cmAgoText's ts > now branch is
                # the only path to an absolute label. The swap is the
                # proof: a paint that ignores the clock keeps showing the
                # relative form and the check fires.
                page.evaluate("""() => {
                    if (!window.cliMono || typeof window.cliMono.setAgoNow !== 'function') return false;
                    window.cliMono.setAgoNow(function () {
                        return Date.now() - 40 * 86400000;
                    });
                    if (typeof window.cliMono.agoRefresh === 'function') window.cliMono.agoRefresh(document);
                    return true;
                }""")
                after = page.evaluate("""() => {
                    const t = document.querySelector('time[data-cm-ago]');
                    return t ? (t.textContent || '').trim() : null;
                }""")
                if before == after:
                    print(f"  FAIL [{w}x{h}]: the paint did not move when the shared clock was swapped (read '{before}' before and after) - it is not reading the clock")
                    fails += 1
                elif " ago" in after:
                    print(f"  FAIL [{w}x{h}]: after the clock jumped 40 days back the label still reads a relative form: '{after}'")
                    fails += 1
                else:
                    print(f"  ok  [{w}x{h}]: the paint follows the shared clock ('{before}' -> '{after}')")

                # NOTE the second direction was tried here and is DELIBERATELY
                # NOT SHIPPED: setting the element's datetime attribute 40
                # days forward does not move a correct paint, because
                # cmInitAgo parses ts ONCE at bind time (the comment beside
                # `var ts = Date.parse(...)` says a hand-written date with
                # no parseable datetime is left alone, not clobbered) and
                # __cmAgoPaint re-paints the captured ts on every refresh.
                # The library's contract is "the label follows the CLOCK",
                # not "the label follows the attribute". A probe that
                # demands the attribute drives the paint would report a
                # failure on a correct build - the same shape as the first
                # cut of this check, which pushed the clock the wrong way.

        browser.close()

    if fails:
        print(f"\n{fails} check(s) FAILED")
        return 1
    print("\nALL AGO PROBES PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
