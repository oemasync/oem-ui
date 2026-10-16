#!/usr/bin/env python3
"""
Audit every demo on the showcase: present, in place, spaced, working.

Four questions, each answered by measurement rather than by reading source:

  1. PRESENT      every interactive control has an accessible name, and every
                  demo panel renders at least one element
  2. IN PLACE     nothing overflows its own container horizontally; no
                  element escapes the viewport sideways
  3. SPACED       every interactive control clears the WCAG 2.2 target-size
                  floor (24x24 CSS px), and controls we style as primaries
                  clear the 44px touch floor wherever the pointer is coarse
                  (on a fine pointer a dense `--sm` steps below AAA on
                  purpose and is reported, not failed - see below)
  4. WORKING      clicking every control raises no JS error, and does not
                  navigate away or detach the page

It runs at BOTH viewports because the phone is the one this library is
verified against and the one most likely to be broken by a desktop-sized
fix. The phone pass runs with `has_touch`, because a 390px-wide
fine-pointer window is not a phone: `pointer: coarse` is what turns the
tap-floor rules on, and the audit must read the page the way the device
renders it.

  tests/audit-demos.py [base_url] [--json]

Exit codes: 0 clean, 1 findings, 2 the INSTRUMENT died (the browser
closed, the server was down) - an invalid run is not a clean run.

Findings print as section + element + the measured number, so each is
actionable. Items that are information rather than a defect - the 44px
AAA floor on a fine pointer - report under "informational" and do NOT
fail the run; the harness contract (tests/run.mjs tap-floor pins) is the
gate for the floors themselves.
"""
import json
import os
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") \
    else os.environ.get("CM_BASE", "http://127.0.0.1:4471/")
BOOT = 90000
TAP_MIN = 24.0    # WCAG 2.2 AA target size (minimum)
TOUCH_MIN = 44.0  # our own convention for anything that behaves as a primary

findings = []


def note(kind, where, detail):
    findings.append({"kind": kind, "where": where, "detail": detail})


# Informational items are reported (they are worth seeing) but do not
# fail the run; see the docstring. They print under their own heading and
# carry `"info": true` in the JSON, so a consumer can tell them apart
# without guessing from the kind.
infos = []


def inform(kind, where, detail):
    infos.append({"kind": kind, "where": where, "detail": detail, "info": True})


# Controls that are expected to do something on click. A control that is
# decorative (a spec sample showing a state) is excluded by the page's own
# markup: specimens inside `.cm-spec__sample` are pictures of states, not
# live controls, and clicking them is not a contract.
CLICKABLE = """
() => {
  const out = [];
  const seen = new Set();
  for (const el of document.querySelectorAll('button, [role=button], a[href^="#"], summary')) {
    if (seen.has(el)) continue;
    seen.add(el);
    if (el.closest('.cm-spec__sample')) continue;   // a picture of a state
    if (el.closest('nav, header, .cm-doc__toc, .cm-pager')) continue;  // chrome
    if (el.disabled) continue;
    out.push(el);
  }
  return out;
}
"""

# One evaluate, not two: passing DOM elements across the evaluate boundary
# turns them into plain objects, and `el.getAttribute` then silently stops
# existing. Collect and annotate in a single pass.
NAMING = """
() => {
  const els = (""" + CLICKABLE + """)();
  window.__els = els;
  const out = [];
  els.forEach((el, i) => {
    // `innerText` is EMPTY for off-screen `content-visibility: auto`
    // items (the scroller's articles carry it) - measured: a reaction
    // button reported no name until scrolled into view. Accessible-name
    // computation reads the text nodes, so fall back to textContent.
    const text = (el.innerText || el.textContent || '').trim();
    const aria = el.getAttribute('aria-label') || '';
    const labelled = el.getAttribute('aria-labelledby');
    let by = labelled ? (document.getElementById(labelled)?.innerText || '').trim() : '';
    const title = el.getAttribute('title') || '';
    const name = aria || by || title || text;
    const r = el.getBoundingClientRect();
    out.push({
      i,
      tag: el.tagName,
      cls: String(el.className || '').slice(0, 60),
      name: name.slice(0, 50),
      w: Math.round(r.width * 10) / 10,
      h: Math.round(r.height * 10) / 10,
      visible: r.width > 0 && r.height > 0,
      section: (el.closest('section[id]') || {}).id || '?',
    });
  });
  return out;
}
"""

OVERFLOW = """
() => {
  const out = [];
  for (const el of document.querySelectorAll('main *')) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    if (el.closest('[data-cm-no-overflow-check]')) continue;
    // A scroll container is SUPPOSED to overflow; that is its job. The
    // question is whether it is one on purpose (overflow-x auto/scroll)
    // or by accident (overflow visible/hidden while content is wider).
    // sr-only text is clipped to 1px ON PURPOSE; its "overflow" is the
    // mechanism, not a defect.
    if (el.closest('.cm-sr-only') ||
        [...el.querySelectorAll('.cm-sr-only')].length) continue;
    // The same sr-only idiom expressed by a media query instead of the
    // class: the prose table's thead below 760px is a 1x1 absolutely
    // positioned box clipped by `clip` / `clip-path`, kept in the tree
    // for readers. Its "overflow" is that mechanism - the same reasoning
    // as the class, measured by the mechanism itself.
    if (cs.position === 'absolute' &&
        el.clientWidth <= 1 && el.clientHeight <= 1 &&
        cs.overflow === 'hidden' &&
        (cs.clip !== 'auto' || cs.clipPath !== 'none')) continue;
    const ox = cs.overflowX;
    const scrollable = ox === 'auto' || ox === 'scroll';
    const over = el.scrollWidth - el.clientWidth;
    // an ellipsis is a DESIGNED clip: the component says "this text is
    // longer than the box and I am telling you so". Flagging it would
    // report every truncate in the library as broken.
    const designed = cs.textOverflow === 'ellipsis';
    if (over > 1 && !scrollable && !designed && cs.overflow !== 'visible') {
      const r = el.getBoundingClientRect();
      out.push({
        tag: el.tagName,
        cls: String(el.className || '').slice(0, 70),
        over,
        section: (el.closest('section[id]') || {}).id || '?',
        w: Math.round(r.width),
        scrollW: el.scrollWidth,
      });
    }
  }
  return out;
}
"""


def run_viewport(page, label, width, height):
    page.set_viewport_size({"width": width, "height": height})
    page.goto(BASE, wait_until="domcontentloaded", timeout=BOOT)
    # Settle on the RUNTIME, not a fixed sleep: the runtime boots after
    # the document is parsed and on a starved box that lands tens of
    # seconds after the HTML arrives. A fixed 1200ms read the page
    # mid-boot, where geometry is placeholder-grade and both the
    # overflow probe and the click loop operate on nonsense (the same
    # race the showcase probe documents in
    # verify-showcase-nowrap-webkit.py).
    page.wait_for_function("() => !!window.cliMono", timeout=BOOT)
    page.wait_for_timeout(1200)

    # ---- 1. PRESENT: accessible names on every live control -------------
    named = page.evaluate(NAMING)
    for n in named:
        if not n["visible"]:
            continue
        if not n["name"]:
            note("no-name", f"{label} {n['section']}",
                 f"<{n['tag'].lower()} class=\"{n['cls']}\"> has no accessible name")

        # ---- 3. SPACED: WCAG 2.2 AA target size (2.5.8, 24x24) ------
        # with its SPACING exception, which is the case that matters for
        # dense rows (reactions, inline actions): the target passes if a
        # 24x24 circle centred on it does not intersect another target's.
        if n["w"] < TAP_MIN - 0.5 or n["h"] < TAP_MIN - 0.5:
            # 2.5.8's INLINE exception: a link inside a sentence is
            # constrained by the line-height of the text around it, and
            # forcing it to 24px would break the paragraph. Measured case:
            # an `<a>` at 85.8x15 inside prose in the lists section.
            inline = page.evaluate(
                """([idx]) => {
                  const me = window.__els[idx];
                  const cs = getComputedStyle(me);
                  if (cs.display !== 'inline' && cs.display !== 'inline-block') return false;
                  const par = me.parentElement;
                  if (!par) return false;
                  // in a sentence: siblings are text/inline, not a stack of targets
                  const pc = getComputedStyle(par);
                  return pc.display === 'block' || pc.display === 'p' ||
                         par.tagName === 'P' || pc.display.startsWith('inline');
                }""", [n["i"]])
            if inline:
                pass  # exempt by the inline exception
            else:
              crowded = page.evaluate(
                """([idx, min]) => {
                  const me = window.__els[idx];
                  const a = me.getBoundingClientRect();
                  const ac = {x: a.x + a.width/2, y: a.y + a.height/2};
                  for (let i = 0; i < window.__els.length; i++) {
                    if (i === idx) continue;
                    const b = window.__els[i].getBoundingClientRect();
                    if (b.width < 1 || b.height < 1) continue;
                    const bc = {x: b.x + b.width/2, y: b.y + b.height/2};
                    const dx = Math.abs(ac.x - bc.x), dy = Math.abs(ac.y - bc.y);
                    // circles of radius min/2 each: they intersect when
                    // both axes are within min
                    if (dx < min && dy < min) return true;
                  }
                  return false;
                }""", [n["i"], TAP_MIN])
              if crowded:
                note("small-target", f"{label} {n['section']}",
                     f"<{n['tag'].lower()} class=\"{n['cls']}\"> is {n['w']}x{n['h']}, "
                     f"under the {TAP_MIN:g}px floor and has no spacing to compensate")
        elif "cm-btn" in n["cls"] and (n["w"] < TOUCH_MIN or n["h"] < TOUCH_MIN):
            # informational: 44px is WCAG 2.5.5 (AAA). A named small size
            # (`--sm`) that clears the AA floor steps below AAA on a FINE
            # pointer by design - density is the variant's entire point -
            # and takes the full floor under `pointer: coarse`. Failing
            # the run here would contradict the design the harness
            # already gates (run.mjs's tap-floor pins), so it is reported
            # apart from the failures.
            inform("below-touch", f"{label} {n['section']}",
                   f"<button class=\"{n['cls']}\"> is {n['w']}x{n['h']}, "
                   f"under the {TOUCH_MIN:g}px AAA touch floor (AA is {TAP_MIN:g})")

    # ---- 2. IN PLACE: accidental horizontal overflow -------------------
    for o in page.evaluate(OVERFLOW):
        note("overflow", f"{label} {o['section']}",
             f"<{o['tag'].lower()} class=\"{o['cls']}\"> content is {o['over']}px wider "
             f"than its {o['w']}px box and cannot scroll")

    # document-level sideways escape
    doc_over = page.evaluate(
        "() => { const d = document.documentElement;"
        " return { over: d.scrollWidth - d.clientWidth,"
        "          sw: d.scrollWidth, cw: d.clientWidth }; }"
    )
    if doc_over["over"] > 1:
        note("sideways", label,
             f"the document scrolls sideways by {doc_over['over']}px "
             f"({doc_over['sw']} > {doc_over['cw']})")

    # ---- 4. WORKING: click every control, watch for errors -------------
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)[:200]))
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text[:160]}")
            if m.type == "error" else None)

    total = page.evaluate("window.__els.length")
    url_before = page.url
    for i in range(total):
        try:
            el = page.evaluate_handle(f"window.__els[{i}]")
            box = el.evaluate("e => { const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }")
            if box[2] < 1 or box[3] < 1:
                continue
            # scroll into view, then click where it actually is
            el.evaluate("e => e.scrollIntoView({block:'center'})")
            page.wait_for_timeout(30)
            box = el.evaluate("e => { const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }")
            page.mouse.click(box[0] + box[2] / 2, box[1] + box[3] / 2)
            page.wait_for_timeout(25)
            # same-document hash navigation (a TOC row, a rail link) is
            # the intended behaviour of an anchor, not a defect; only a
            # navigation that leaves the document is worth reporting
            same_doc = (page.url.split('#')[0] == url_before.split('#')[0]
                        and '#' in page.url)
            if page.url != url_before and not same_doc:
                note("navigated", f"{label} control #{i}",
                     f"clicking navigated to {page.url}")
                page.goto(url_before, wait_until="domcontentloaded", timeout=BOOT)
                page.wait_for_function("() => !!window.cliMono", timeout=BOOT)
                page.wait_for_timeout(400)
                page.evaluate("window.__els = (" + CLICKABLE + ")()")
                url_before = page.url
        except Exception as exc:
            msg = str(exc)
            # A dead BROWSER is an instrument failure, not a pile of
            # findable defects: every control after it fails with "target
            # closed" and the run must not be read as product data (the
            # phone pass in aud4 died mid-loop at #380 and masqueraded as
            # 171 click-failed items). Report it once and stop - an
            # invalid run is not a clean run, and it is not a bad page
            # either.
            b = page.context.browser
            if b is not None and not b.is_connected():
                print(f"INSTRUMENT: the browser died at {label} control "
                      f"#{i} - invalid run, not a clean one", file=sys.stderr)
                sys.exit(2)
            if ("Execution context was destroyed" in msg or "Target closed" in msg
                    or "Target page, context or browser has been closed" in msg):
                note("detached", f"{label} control #{i}", "the page was destroyed by the click")
                if page.is_closed():
                    # the PAGE (not the browser) went away: rebuild it and
                    # keep auditing the rest of the controls
                    page = page.context.new_page()
                    page.on("pageerror", lambda e: errors.append(str(e)[:200]))
                    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text[:160]}")
                            if m.type == "error" else None)
                page.goto(BASE, wait_until="domcontentloaded", timeout=BOOT)
                page.wait_for_function("() => !!window.cliMono", timeout=BOOT)
                page.wait_for_timeout(600)
                page.evaluate("window.__els = (" + CLICKABLE + ")()")
            else:
                note("click-failed", f"{label} control #{i}", msg[:160])

    for e in errors[:12]:
        note("js-error", label, e)


def main():
    as_json = "--json" in sys.argv
    with sync_playwright() as pw:
        browser = pw.webkit.launch()
        try:
            ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            run_viewport(page, "desktop", 1280, 900)
            ctx.close()

            # The phone is a TOUCH device: `has_touch` flips
            # `pointer: coarse`, and THAT is what turns the tap-floor
            # rules on (measured: has_touch=True -> {coarse: True,
            # fine: False} in WebKit). A 390px-wide fine-pointer window
            # would read floors the phone never has to live with.
            ctx = browser.new_context(viewport={"width": 390, "height": 844},
                                      has_touch=True)
            page = ctx.new_page()
            run_viewport(page, "phone", 390, 844)
            ctx.close()
        except SystemExit:
            raise
        except Exception as exc:
            # e.g. the server is down and the first goto times out: that
            # is an instrument failure, not a page full of defects (the
            # aud5 run reported this way was an empty file, not a clean
            # audit).
            print(f"INSTRUMENT: the run died ({exc}) - invalid run, "
                  "not a clean one", file=sys.stderr)
            sys.exit(2)
        finally:
            try:
                browser.close()
            except Exception:
                pass

    if as_json:
        print(json.dumps(findings + infos, indent=1))
    else:
        if not findings:
            tail = f" ({len(infos)} informational notes below.)" if infos else ""
            print("clean: every demo control is named, in its box, over the "
                  "floor, and clicking it raised nothing." + tail)
        by_kind = {}
        for f in findings:
            by_kind.setdefault(f["kind"], []).append(f)
        for kind, items in sorted(by_kind.items(), key=lambda kv: -len(kv[1])):
            print(f"\n== {kind} ({len(items)}) ==")
            for f in items[:25]:
                print(f"  {f['where']}: {f['detail']}")
            if len(items) > 25:
                print(f"  ... and {len(items) - 25} more")
        if infos:
            print(f"\n== informational ({len(infos)}) - reported, not failures ==")
            for f in infos[:25]:
                print(f"  {f['where']}: {f['detail']}")
            if len(infos) > 25:
                print(f"  ... and {len(infos) - 25} more")
    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
