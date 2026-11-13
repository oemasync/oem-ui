#!/usr/bin/env python3
"""verify-state-webkit.py - prove the <State> wrapper in real WebKit.

The contract check reads source; this reads the painted page. The claim
under test is that the wrapper's output is the HAND-TYPED SHAPE: same
tiers, same geometry, same tap floor. The proof is a pair comparison -
each wrapper specimen against its hand-typed twin in the same section,
so the two read under identical cascade conditions.

Tokens are read off the page, never from a hex in this file. The
coarse pointer is set with emulate_media, the deterministic knob: the
tap floor on the actions row only holds where (pointer: coarse)
matches, and a context that silently keeps pointer: fine would let the
mutant through.

    /root/.venvs/mau/bin/python tests/verify-state-webkit.py
"""
import os

# A dead PLAYWRIGHT_BROWSERS_PATH makes the launch refuse with
# "Executable doesn't exist" while the real cache sits in
# ~/.cache/ms-playwright. Delete the var ONLY when its directory is
# gone - an unconditional delete discards a restored cache.
_pw_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
if _pw_path and not os.path.isdir(_pw_path):
    del os.environ["PLAYWRIGHT_BROWSERS_PATH"]

import sys
from playwright.sync_api import sync_playwright

URL = "http://192.168.1.68:4321/"
# 390 = iPhone 15 Pro (coarse), 375 = iPhone SE (coarse),
# 1440 = desktop (fine pointer).
VIEWPORTS = [(390, 844, True), (375, 667, True), (1440, 900, False)]

JS_MEASURE = r"""
() => {
    const root = document.documentElement;
    const sec = document.querySelector('#states');
    if (!sec) return { error: '#states not found' };
    const token = (name) => getComputedStyle(root).getPropertyValue(name).trim();
    const rgb = (c) => {
        let m = /#[0-9a-f]{6}/i.exec(c);
        if (!m) {
            // The light --ink is declared 3-digit (#111): expand it, or
            // the computed rgb(17, 17, 17) can never equal the token.
            const s = /#([0-9a-f]{3})\b/i.exec(c);
            if (!s) return c;
            const v = s[1].split('').map((x) => x + x).join('');
            return `rgb(${parseInt(v.slice(0, 2), 16)}, ${parseInt(v.slice(2, 4), 16)}, ${parseInt(v.slice(4, 6), 16)})`;
        }
        const v = m[0].slice(1);
        return `rgb(${parseInt(v.slice(0, 2), 16)}, ${parseInt(v.slice(2, 4), 16)}, ${parseInt(v.slice(4, 6), 16)})`;
    };
    const out = {
        theme: root.getAttribute('data-theme') || 'default(dark)',
        classList: root.className,
        pointer: matchMedia('(pointer: coarse)').matches,
        tap: token('--tap'),
        ink: rgb(token('--ink')),
        dim: rgb(token('--ink-dim')),
        faint: rgb(token('--ink-faint')),
        secOverflow: sec.scrollWidth - sec.clientWidth,
        rootFont: parseFloat(getComputedStyle(root).fontSize) || 16,
        full: null,
        noMarkPair: [],
    };
    // The full specimen: the only state on the page that carries a
    // body, a mark and an actions row.
    const fulls = [...sec.querySelectorAll('.cm-state__body')]
        .map((b) => b.closest('.cm-state'));
    if (fulls.length) {
        const el = fulls[fulls.length - 1];  // the wrapper's, last in source order
        const cs = getComputedStyle(el);
        const r = el.getBoundingClientRect();
        const mark = el.querySelector('.cm-state__mark');
        const title = el.querySelector('.cm-state__title');
        const body = el.querySelector('.cm-state__body');
        const actions = el.querySelector('.cm-state__actions');
        const btn = actions ? actions.querySelector('.cm-btn') : null;
        out.full = {
            title: title ? title.textContent.trim().slice(0, 30) : null,
            textAlign: cs.textAlign,
            border: cs.borderStyle + ' ' + cs.borderWidth,
            markPresent: !!mark,
            markAria: mark ? mark.getAttribute('aria-hidden') : null,
            markW: mark ? mark.getBoundingClientRect().width : null,
            markBorder: mark ? getComputedStyle(mark).borderStyle : null,
            titleColor: title ? getComputedStyle(title).color : null,
            bodyColor: body ? getComputedStyle(body).color : null,
            bodyMaxWidth: body ? parseFloat(getComputedStyle(body).maxWidth) : null,
            actionsPresent: !!actions,
            btnMinH: btn ? getComputedStyle(btn).minHeight : null,
            btnH: btn ? btn.getBoundingClientRect().height : null,
            width: r.width,
        };
        // The hand-typed twin (the first body state in the section).
        if (fulls.length > 1) {
            const twin = fulls[0];
            const tr = twin.getBoundingClientRect();
            const tbtn = twin.querySelector('.cm-state__actions .cm-btn');
            out.fullTwin = {
                width: tr.width,
                titleColor: getComputedStyle(twin.querySelector('.cm-state__title')).color,
                btnMinH: tbtn ? getComputedStyle(tbtn).minHeight : null,
            };
        }
    }
    // The no-mark pair: two states titled "No rows in this state", the
    // hand-typed one first, the wrapper's second.
    for (const el of sec.querySelectorAll('.cm-state')) {
        const t = el.querySelector('.cm-state__title');
        if (!t || t.textContent.trim() !== 'No rows in this state') continue;
        const text = el.querySelector('.cm-state__text');
        const r = el.getBoundingClientRect();
        const tr = text ? text.getBoundingClientRect() : null;
        out.noMarkPair.push({
            width: r.width,
            markPresent: !!el.querySelector('.cm-state__mark'),
            actionsPresent: !!el.querySelector('.cm-state__actions'),
            textColor: text ? getComputedStyle(text).color : null,
            textLeft: tr ? tr.left : null,
            textWidth: tr ? tr.width : null,
        });
    }
    // The empty-div gate: NO state without a way out may carry an
    // actions row at all.
    out.statesWithoutActions = [...sec.querySelectorAll('.cm-state')]
        .filter((el) => !el.querySelector('.cm-state__actions')).length;
    out.nStates = sec.querySelectorAll('.cm-state').length;
    return out;
}
"""


def wait_for_runtime(page):
    """Poll for the runtime's own mark. Never a timer, never
    networkidle - both have been measured to lie on this preview."""
    for _ in range(60):
        try:
            if page.evaluate("() => document.documentElement.classList.contains('cm-js')"):
                return
        except Exception:
            pass
        page.wait_for_timeout(100)
    raise AssertionError('runtime mark (cm-js) never appeared')


def run_theme(page, theme):
    if theme:
        page.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
    else:
        page.evaluate("() => document.documentElement.removeAttribute('data-theme')")
    # Set a theme, then WAIT, then read: the same-tick read has been
    # measured to report the previous theme's tokens.
    page.wait_for_timeout(150)
    return page.evaluate(JS_MEASURE)


def check(d, label, coarse):
    assert not d.get("error"), d.get("error")
    f = d["full"]
    assert f, "the body + actions specimen is missing from the painted page"
    # 1. the wrapper's full specimen carries every element it claims
    assert f["markPresent"] and f["markAria"] == "true", \
        f'{label}: wrapper mark missing or not aria-hidden ({f["markAria"]})'
    assert f["actionsPresent"], f"{label}: wrapper actions row did not render"
    # 2. the tiers: title at full ink, body at the dim tier
    assert f["titleColor"] == d["ink"], \
        f'{label}: title {f["titleColor"]} != --ink {d["ink"]}'
    assert f["bodyColor"] == d["dim"], \
        f'{label}: body {f["bodyColor"]} != --ink-dim {d["dim"]}'
    assert f["bodyMaxWidth"] > 100, f"{label}: body lost its measure"
    # 3. the frame: dashed mark, solid box, centred text
    assert f["textAlign"] == "center", f"{label}: state is not centred"
    assert f["markBorder"] == "dashed", \
        f'{label}: mark border is {f["markBorder"]}, not dashed'
    # the mark box is 2.4rem, derived from the page's own root font:
    # a hardcoded 38.4 would fail the day the showcase retunes the root.
    assert abs(f["markW"] - 2.4 * d["rootFont"]) <= 1.5, \
        f'{label}: mark box {f["markW"]} != 2.4rem ({2.4 * d["rootFont"]:.1f}px)'
    # 4. like for like: the wrapper's specimen and the hand-typed twin
    #    are the same width, the same title tier, the same floor.
    if d.get("fullTwin"):
        tw = d["fullTwin"]
        assert abs(f["width"] - tw["width"]) <= 1.5, \
            f'{label}: wrapper {f["width"]:.1f}px vs hand-typed twin {tw["width"]:.1f}px'
        assert f["titleColor"] == tw["titleColor"], \
            f"{label}: the two titles sit at different tiers"
        if f["btnMinH"] != tw["btnMinH"]:
            raise AssertionError(
                f'{label}: floor differs between twins '
                f'(wrapper {f["btnMinH"]}, twin {tw["btnMinH"]})')
    # 5. the tap floor: under a coarse pointer the sm button in the
    #    actions row takes the floor even though it is --sm; under a
    #    fine pointer it keeps its dense size. The context must PROVE
    #    the pointer it claims, or the floor half of this check was
    #    never exercised and the run is worth nothing.
    if d["pointer"] != coarse:
        raise AssertionError(
            f'{label}: context wanted pointer={"coarse" if coarse else "fine"}, '
            f'page reads pointer:coarse={d["pointer"]} - the floor half is unexercised')
    tap = float(d["tap"].rstrip("px") or 0)
    btn_min = float(f["btnMinH"].rstrip("px") or 0)
    if coarse:
        assert btn_min == tap, \
            f'{label}: coarse pointer, button min-height {f["btnMinH"]} != --tap {d["tap"]}'
        assert f["btnH"] >= tap - 0.5, \
            f'{label}: button height {f["btnH"]} below the {tap:g}px floor'
    else:
        assert btn_min < tap, \
            f'{label}: fine pointer should keep the dense size (min {f["btnMinH"]})'
    # 6. the no-mark pair: hand-typed and wrapper are the same width and
    #    their one-liners sit at the same left edge and the same tier.
    assert len(d["noMarkPair"]) == 2, \
        f'{label}: expected the two no-mark states, got {len(d["noMarkPair"])}'
    hand, wrap = d["noMarkPair"]
    assert not hand["markPresent"] and not wrap["markPresent"], \
        f"{label}: a no-mark state rendered a mark"
    assert abs(hand["width"] - wrap["width"]) <= 1.5, \
        f'{label}: no-mark pair widths differ ({hand["width"]:.1f} vs {wrap["width"]:.1f})'
    assert hand["textColor"] == wrap["textColor"] == d["faint"], \
        f'{label}: no-mark one-liners off the faint tier ({hand["textColor"]}, {wrap["textColor"]})'
    assert abs(hand["textLeft"] - wrap["textLeft"]) <= 1.5, \
        f'{label}: no-mark one-liners at different left edges ({hand["textLeft"]:.1f} vs {wrap["textLeft"]:.1f})'
    # 7. the slot gate: the states without a way out carry no actions
    #    row at all. Six states on the page (hand-typed 3 + wrapper 3);
    #    only the two that carry a way out own an actions row.
    assert d["nStates"] == 6, f'{label}: expected 6 states on the page, got {d["nStates"]}'
    assert d["statesWithoutActions"] == 4, \
        f'{label}: expected 4 states without an actions row, got {d["statesWithoutActions"]}'
    # 8. the section does not grow sideways
    assert d["secOverflow"] <= 1, f'{label}: #states overflows sideways by {d["secOverflow"]}px'


def main():
    failures = []
    seen = {}
    with sync_playwright() as pw:
        browser = pw.webkit.launch()
        for w, h, coarse in VIEWPORTS:
            # The deterministic coarse-pointer knob in this Playwright
            # build: is_mobile + has_touch (verified 2026-11-13, the
            # context reads pointer:coarse true, hover:false). The
            # emulate_media() of this venv takes no pointer argument, so
            # the context is the only way in - and the page must still
            # PROVE it (d['pointer']) before the floor is asserted.
            ctx = browser.new_context(viewport={"width": w, "height": h},
                                      is_mobile=coarse, has_touch=coarse,
                                      device_scale_factor=3 if coarse else 1)
            page = ctx.new_page()
            theme = None
            try:
                page.goto(URL, wait_until="commit", timeout=30000)
                wait_for_runtime(page)
                page.locator('#states').scroll_into_view_if_needed()
                page.wait_for_timeout(100)
                for theme in (None, "light"):
                    print(f"[{w}x{h}] pointer={'coarse' if coarse else 'fine'} "
                          f"{theme or 'dark(default)'}")
                    data = run_theme(page, theme)
                    check(data, f"{w}x{h}/{theme or 'dark'}", coarse)
                    f = data["full"]
                    print(f"  full: {f['title']!r} w={f['width']:.0f} "
                          f"title={f['titleColor']} body={f['bodyColor']} "
                          f"btnMin={f['btnMinH']} btnH={f['btnH']}")
                    print(f"  noMark: " + " | ".join(
                        f"w={p['width']:.0f} left={p['textLeft']:.1f}" for p in data["noMarkPair"]))
                    seen.setdefault(f"{theme or 'dark'}", data)
            except Exception as e:
                failures.append(f"{w}x{h} {theme}: {type(e).__name__}: {e}")
            finally:
                page.close()
                ctx.close()
        browser.close()
    # The two themes must actually differ: print-classList proof that
    # the runs were not byte-identical.
    dark, light = seen.get("dark"), seen.get("light")
    if dark and light:
        assert dark["ink"] != light["ink"], "dark and light runs read the same --ink"
        assert dark["full"]["titleColor"] != light["full"]["titleColor"], \
            "the title tier read identically in both themes - one run was stale"
    if failures:
        print("FAIL")
        for f in failures:
            print(" ", f)
        sys.exit(1)
    print("OK - the <State> wrapper paints the hand-typed shape: same tiers,")
    print("    same width, same tap floor under a coarse pointer, no phantom")
    print("    actions row, no sideways growth.")


if __name__ == "__main__":
    main()
