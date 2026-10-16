#!/usr/bin/env python3
"""
Verify the --measure-title specimen and its live readout in WebKit.

The readout is only worth shipping if it tells the TRUTH, so the central
assertion is a cross-check against the real row rather than against a
restated copy of the media queries: the readout says "handed off" if and
only if the actual `.cm-row__desc` computes to display:none, and reports
the actual width when live.

Also checks the progressive contract. The readout is JS-written, so with
scripting disabled the specimen must still render its token sample and
must not leave an empty cell behind. A JS-dependent control that is
merely hidden is a dead site.
"""
import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://192.168.1.68:4321/"

# `--measure-title` is 42ch, and getComputedStyle resolves `ch` to px. The
# RESOLVED value is what proves the specimen is painted from the token
# rather than typed beside it - but the px it resolves to is a property of
# the FONT, not of this repo. It was written down here as a constant
# (404.578125px, the then-current fallback monospace's advance) and went
# stale when the box's system fonts changed under it: a red check that
# read as a code regression while the specimen itself was correct
# (403.265625px, matching the 42ch the page resolves to the hundredth).
# The probe now resolves `42ch` in the sample's own font context, on the
# page, and swaps the custom property to prove the cap tracks it.

# (width, expect_live)
CASES = [
    (1440, True), (1280, True), (1100, True), (1090, True),
    (1060, True), (1056, True),      # just above the rail band
    (1040, False), (1024, False), (1000, False),   # rail band
    (996, True), (990, True),         # rail gone
    (860, True), (846, True),         # just above the lower band
    (844, False), (800, False), (700, False), (390, False),
]

PROBE = r"""
() => {
  const spec = document.querySelector('[data-spec="measure-title"]');
  if (!spec) return {error: 'no [data-spec=measure-title] specimen'};
  const readout = spec.querySelector('.cm-spec__state');
  const sample = spec.querySelector('.cm-spec__sample .cm-lede');
  const desc = document.querySelector('.cm-rows--inline .cm-row__desc');
  const rows = document.querySelectorAll('.cm-rows--inline .cm-row');
  // Resolve the token's `ch` IN THE SAMPLE'S OWN FONT CONTEXT, so the
  // expectation is measured on the page instead of typed into this file.
  // It shipped for months as a hardcoded 404.578125px; when the box's
  // fallback monospace changed under it (a system font this repo does
  // not ship), the check went red and read like a code regression. The
  // specimen was fine - the same 42ch resolved in-page matched it to
  // the hundredth: 403.265625px.
  const cs0 = getComputedStyle(sample);
  const probe = document.createElement('span');
  probe.style.cssText = 'position:absolute;visibility:hidden;white-space:nowrap;'
    + 'width:42ch;font-family:' + cs0.fontFamily + ';font-size:' + cs0.fontSize;
  document.body.appendChild(probe);
  const tokenCh = probe.getBoundingClientRect().width;
  probe.remove();
  // ...and prove the cap TRACKS the custom property: a typed `404px`
  // would neither follow the font nor move when the token is swapped.
  const swap = {};
  try {
    swap.before = parseFloat(getComputedStyle(sample).maxWidth);
    spec.style.setProperty('--measure-title', '30ch');
    swap.during = parseFloat(getComputedStyle(sample).maxWidth);
    spec.style.removeProperty('--measure-title');
    swap.after = parseFloat(getComputedStyle(sample).maxWidth);
  } catch (e) { swap.error = String(e); }
  return {
    hasReadout: !!readout,
    readoutText: readout ? readout.textContent.trim() : null,
    readoutState: readout ? readout.getAttribute('data-state') : null,
    readoutCount: spec.querySelectorAll('.cm-spec__state').length,
    // the specimen must be RENDERED FROM the token, not typed beside it
    sampleWidth: sample ? Math.round(sample.getBoundingClientRect().width*100)/100 : null,
    // numeric: `ch` is resolved by getComputedStyle, so the value comes
    // back in px and is compared as a number, not as the string '42ch'
    sampleMaxWidth: sample ? parseFloat(getComputedStyle(sample).maxWidth) : null,
    tokenCh: Math.round(tokenCh*1000)/1000,
    swap: swap,
    descDisplay: desc ? getComputedStyle(desc).display : null,
    descWidth: desc ? Math.round(desc.getBoundingClientRect().width*100)/100 : null,
    rowCount: rows.length,
  };
}
"""


def main() -> int:
    fails = []
    with sync_playwright() as p:
        b = p.webkit.launch()
        try:
            for w, expect_live in CASES:
                ctx = b.new_context(
                    viewport={"width": w, "height": 900},
                    is_mobile=w < 700, has_touch=w < 700,
                )
                pg = ctx.new_page()
                # A starved box (a spec campaign runs alongside) takes ~27s
                # to reach `load` on this page: the default 30s timeout is a
                # race, not a margin. Same lesson as the showcase probe.
                pg.set_default_timeout(180000)
                pg.goto(URL, wait_until="load", timeout=180000)
                pg.wait_for_function("() => !!window.cliMono", timeout=180000)
                title = pg.title()
                if w == CASES[0][0]:
                    print(f"page title: {title!r}")
                    if "oem/ui" not in title:
                        print("FAIL wrong page served on 4321")
                        return 1
                r = pg.evaluate(PROBE)
                if "error" in r:
                    print(f"w={w}: {r['error']}")
                    return 1

                # The TRUTHFUL check: the readout agrees with the DOM.
                actual_live = r["descDisplay"] != "none"
                if r["hasReadout"]:
                    if (r["readoutState"] == "live") != actual_live:
                        fails.append(
                            f"w={w}: readout says {r['readoutState']!r} but "
                            f"the excerpt computes to {r['descDisplay']!r} - "
                            f"the readout is lying"
                        )
                    # The readout prints a ROUNDED width, so compare
                    # against the rounded value. The first version of
                    # this check compared 'excerpt 205px' to 205.11px and
                    # reported 24 failures against a correct readout.
                    if actual_live and r["readoutText"] != \
                            f"excerpt {round(r['descWidth'])}px":
                        fails.append(
                            f"w={w}: readout {r['readoutText']!r} does not "
                            f"match the measured width {r['descWidth']}px"
                        )
                if actual_live != expect_live:
                    fails.append(
                        f"w={w}: expected the excerpt "
                        f"{'rendered' if expect_live else 'handed off'}, "
                        f"got display={r['descDisplay']!r}"
                    )
                # Idempotence: init() runs again on every Astro page-load,
                # so re-run it and prove the cell still holds ONE readout.
                # Asserting this in the source is a regex over a guard
                # clause; counting the nodes after a real re-init is the
                # claim itself.
                pg.evaluate("() => window.cliMono && window.cliMono.init(document)");
                pg.evaluate("() => window.cliMono && window.cliMono.init(document)")
                after = pg.evaluate(
                    "() => document.querySelectorAll("
                    "'[data-spec=\"measure-title\"] .cm-spec__state').length")
                if after != 1:
                    fails.append(
                        f"w={w}: {after} readouts after two extra init() calls "
                        f"- the readout stacks on every page-load"
                    )
                if r["readoutCount"] > 1:
                    fails.append(
                        f"w={w}: {r['readoutCount']} readouts in one cell - "
                        f"init() is stacking them"
                    )
                # The specimen is rendered FROM the token, not typed beside
                # it. Two claims, both measured on the page: the cap equals
                # the `42ch` the PAGE resolves in this sample's font
                # context, and it MOVES when the custom property is swapped
                # (a typed px value does neither). The expectation is no
                # longer a constant in this file - see the probe's note.
                if r["sampleMaxWidth"] is None or r["tokenCh"] is None:
                    fails.append(f"w={w}: the specimen or the token probe is missing")
                else:
                    if abs(r["sampleMaxWidth"] - r["tokenCh"]) > 0.5:
                        fails.append(
                            f"w={w}: specimen resolves max-width to "
                            f"{r['sampleMaxWidth']}px but 42ch resolves to "
                            f"{r['tokenCh']}px in the same font context - it "
                            f"is not rendered from the token"
                        )
                    sw = r.get("swap") or {}
                    if "error" in sw:
                        fails.append(f"w={w}: the token swap probe threw: {sw['error']}")
                    elif not (sw["during"] < sw["before"] - 40):
                        fails.append(
                            f"w={w}: swapping --measure-title to 30ch did not "
                            f"move the specimen ({sw['before']} -> "
                            f"{sw['during']}) - the cap is not read from the "
                            f"custom property"
                        )
                    elif abs(sw["after"] - sw["before"]) > 0.5:
                        fails.append(
                            f"w={w}: the token swap did not restore "
                            f"({sw['before']} -> {sw['after']})"
                        )
                print(f"w={w:<5} descDisp={r['descDisplay']:<7} "
                      f"descW={r['descWidth']:<9} readout={r['readoutText']!r}")
                ctx.close()

            # Progressive: no JS must not break the specimen.
            ctx = b.new_context(viewport={"width": 1280, "height": 900},
                                java_script_enabled=False)
            pg = ctx.new_page()
            pg.set_default_timeout(180000)
            pg.goto(URL, wait_until="load", timeout=180000)
            sample = pg.locator(
                '[data-spec="measure-title"] .cm-spec__sample .cm-lede')
            box = sample.bounding_box()
            val = pg.locator('[data-spec="measure-title"] .cm-spec__val')
            # The rendered width here is the sample's own text width,
            # NOT the token's cap: `max-width` is a ceiling and the cell
            # is narrower than 42ch at this width, so the text wraps
            # inside it. What must hold with JS off is that the cap still
            # resolves from the token, which is a computed-style read and
            # needs no script of ours.
            maxw = pg.evaluate(
                "() => getComputedStyle(document.querySelector("
                "'[data-spec=\"measure-title\"] .cm-spec__sample .cm-lede'"
                ")).maxWidth")
            # ...and the expectation is resolved on THIS page too, in the
            # same font context (see the note at the top of the file).
            token_ch = pg.evaluate(
                "() => { const s = document.querySelector("
                "'[data-spec=\"measure-title\"] .cm-spec__sample .cm-lede');"
                " const cs = getComputedStyle(s);"
                " const p = document.createElement('span');"
                " p.style.cssText = 'position:absolute;visibility:hidden;"
                "white-space:nowrap;width:42ch;font-family:' + cs.fontFamily"
                " + ';font-size:' + cs.fontSize;"
                " document.body.appendChild(p);"
                " const w = p.getBoundingClientRect().width; p.remove();"
                " return Math.round(w*1000)/1000; }")
            print(f"\nno-JS: specimen visible={sample.is_visible()} "
                  f"renderedW={box['width'] if box else None} "
                  f"maxW={maxw} 42ch={token_ch} val={val.inner_text()!r}")
            if not sample.is_visible():
                fails.append("no-JS: the --measure-title specimen vanished")
            if abs(float(maxw.replace('px', '')) - token_ch) > 0.5:
                fails.append(
                    f"no-JS: specimen max-width resolves to {maxw} but 42ch "
                    f"resolves to {token_ch}px in the same context - it is "
                    f"not rendered from the token")
            if "42ch" not in val.inner_text():
                fails.append(
                    f"no-JS: the value cell lost its token: "
                    f"{val.inner_text()!r}")
            if pg.locator('[data-spec="measure-title"] .cm-spec__state').count():
                fails.append(
                    "no-JS: a readout exists - it is JS-written, so its "
                    "absence is the progressive contract working")
            ctx.close()
        finally:
            b.close()

    print()
    if fails:
        print(f"FAIL ({len(fails)})")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("PASS: readout tracks the real row, specimen renders from the "
          "token, no-JS intact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
