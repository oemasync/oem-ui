#!/usr/bin/env python3
"""measure-state-text-webkit.py - prove .cm-state__text in real WebKit.

The contract check reads source; this reads the painted page. The
documented empty-state one-liner is one tier fainter than __body and
takes the narrow measure, in both themes, at a phone and a desktop
width. The tokens are read OFF THE PAGE (--ink-faint, --ink-dim,
--space-2, --measure-narrow resolved by the engine), never from a
hex in this file: a probe that hardcodes the expected colour passes
the wrong theme while reading the right one.

The load gate is the runtime's own mark: wait_until="commit" and poll
for document.documentElement.classList.contains('cm-js'). The LAN
preview has been measured to time out on wait_until="load" and to
make the first wait_for_function after commit lie, so the poll is a
plain evaluate loop with one retry on the trivial expression.

    /root/.venvs/mau/bin/python tests/measure-state-text-webkit.py
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
# 375 = iPhone SE (the short-height device), 390 = iPhone 15 Pro,
# 1440 = desktop.
VIEWPORTS = [(375, 667), (390, 844), (1440, 900)]

JS_MEASURE = r"""
() => {
    const root = document.documentElement;
    const sec = document.querySelector('#states');
    if (!sec) return { error: '#states not found' };
    const token = (name) => getComputedStyle(root).getPropertyValue(name).trim();
    // getComputedStyle returns colours as rgb(...); the token returns
    // the hex it was declared as. 139 == 0x8b - normalise both to the
    // engine's form before comparing, or every run is a format miss.
    const rgb = (c) => {
        const m = /#[0-9a-f]{6}/i.exec(c);
        if (!m) return c;
        const v = m[0].slice(1);
        return `rgb(${parseInt(v.slice(0, 2), 16)}, ${parseInt(v.slice(2, 4), 16)}, ${parseInt(v.slice(4, 6), 16)})`;
    };
    const px = (v) => parseFloat(v);
    const out = {
        theme: root.getAttribute('data-theme') || 'default(dark)',
        classList: root.className,
        ink: token('--ink'),
        texts: [],
        states: [],
        secOverflow: sec.scrollWidth - sec.clientWidth,
        tokens: {
            faint: rgb(token('--ink-faint')),
            dim: rgb(token('--ink-dim')),
        },
    };
    // --space-2 and 34ch resolve through the engine, never through a
    // parser: a .5rem token breaks a px regex, and ch has no px value
    // in the token itself. Measure both with throwaway elements.
    const first = sec.querySelector('.cm-state__text');
    if (first) {
        const probe = document.createElement('span');
        probe.textContent = '0'.repeat(34);
        probe.style.position = 'absolute';
        probe.style.visibility = 'hidden';
        probe.style.font = getComputedStyle(first).font;
        document.body.appendChild(probe);
        out.ch34 = probe.getBoundingClientRect().width;
        probe.remove();
    }
    const sp = document.createElement('span');
    sp.style.position = 'absolute';
    sp.style.visibility = 'hidden';
    sp.style.width = 'var(--space-2)';
    document.body.appendChild(sp);
    out.space2 = sp.getBoundingClientRect().width;
    sp.remove();
    for (const el of sec.querySelectorAll('.cm-state__text')) {
        const cs = getComputedStyle(el);
        const r = el.getBoundingClientRect();
        const title = el.previousElementSibling;
        const stateBox = el.closest('.cm-state');
        const sr = stateBox ? stateBox.getBoundingClientRect() : null;
        const item = {
            text: el.textContent.trim().slice(0, 40),
            color: cs.color,
            maxWidth: parseFloat(cs.maxWidth),
            marginL: cs.marginLeft,
            textAlign: cs.textAlign,
            rect: { top: r.top, left: r.left, width: r.width, height: r.height },
            markPresent: !!(stateBox && stateBox.querySelector('.cm-state__mark')),
            markAria: stateBox
                ? (stateBox.querySelector('.cm-state__mark') || {}).getAttribute
                    ? stateBox.querySelector('.cm-state__mark').getAttribute('aria-hidden')
                    : null
                : null,
        };
        if (title && title.classList.contains('cm-state__title')) {
            const tr = title.getBoundingClientRect();
            item.gapFromTitle = r.top - tr.bottom;
            item.titleColor = getComputedStyle(title).color;
        }
        if (sr) item.centering = { left: r.left - sr.left, right: sr.right - r.right };
        out.texts.push(item);
    }
    // The tier ladder: title --ink, body --ink-dim, text --ink-faint.
    // Read all three off the first specimen that carries a body.
    const withBody = sec.querySelector('.cm-state .cm-state__body');
    if (withBody) {
        out.ladder = {
            bodyColor: getComputedStyle(withBody).color,
            bodyMaxWidth: getComputedStyle(withBody).maxWidth,
        };
    }
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
    data = page.evaluate(JS_MEASURE)
    if data.get("error"):
        raise AssertionError(data["error"])
    check_theme(data)
    print(f"  [{theme or 'dark(default)'}] classList={data['classList']!r} "
          f"ink={data['ink']} faint={data['tokens']['faint']} "
          f"dim={data['tokens']['dim']}")
    return data


def rgb_eq(a, b):
    return a.strip() == b.strip()


def check_theme(d):
    assert len(d["texts"]) == 2, f"expected 2 .cm-state__text specimens, got {len(d['texts'])}"
    faint, dim = d["tokens"]["faint"], d["tokens"]["dim"]
    assert faint and dim, "ink tokens did not resolve"
    assert not rgb_eq(faint, dim), "--ink-faint and --ink-dim collapsed to one value"
    space2 = d["space2"]
    ch34 = d.get("ch34")
    verbatim = None
    for t in d["texts"]:
        # 1. the colour is the faint TIER, resolved by the engine
        assert t["color"] == faint, \
            f"{t['text']!r}: colour {t['color']} != --ink-faint {faint}"
        # 2. the narrow measure: 34ch in the text's own font
        assert ch34, "could not measure ch"
        assert abs(t["maxWidth"] - ch34) <= 1.5, \
            f"{t['text']!r}: max-width {t['maxWidth']} != 34ch ({ch34:.1f}px)"
        # 3. the block never exceeds the measure, and when it is
        #    narrower than its container the gutters are equal -
        #    centred. At 375 the mono 34ch CAN fill the container, in
        #    which case both gutters read 0 and equality still proves
        #    the centreing.
        c = t["centering"]
        assert t["rect"]["width"] <= ch34 + 1.5, \
            f"{t['text']!r}: block {t['rect']['width']:.1f}px exceeds the 34ch measure ({ch34:.1f}px)"
        assert c["left"] >= -1.5 and c["right"] >= -1.5, \
            f"{t['text']!r}: block leaves the container (left {c['left']:.1f}, right {c['right']:.1f})"
        assert abs(c["left"] - c["right"]) <= 1.5, \
            f"{t['text']!r}: not centred (left {c['left']:.1f} vs right {c['right']:.1f})"
        # 4. the title's bottom margin is the only gap: exactly --space-2
        assert abs(t["gapFromTitle"] - space2) <= 0.5, \
            f"{t['text']!r}: title->text gap {t['gapFromTitle']:.1f} != --space-2 ({space2}px)"
        # 5. the title sits at the full tier, the hint one step down
        assert t["titleColor"] != faint, \
            f"{t['text']!r}: title colour fell to the faint tier"
        if t["markPresent"]:
            assert t["markAria"] == "true", f"{t['text']!r}: mark must be aria-hidden"
            verbatim = t
    assert verbatim, "no specimen carries the documented mark+title+text shape"
    no_mark = [t for t in d["texts"] if not t["markPresent"]]
    assert len(no_mark) == 1, \
        f"expected exactly one no-mark specimen, got {len(no_mark)}"
    # the tier ladder: body sits between title and text
    lad = d.get("ladder")
    assert lad, "the body specimen is missing - the ladder is unproven"
    assert lad["bodyColor"] == dim, f"body colour {lad['bodyColor']} != --ink-dim {dim}"
    # the section does not grow sideways
    assert d["secOverflow"] <= 1, f"#states overflows sideways by {d['secOverflow']}px"
    print(f"    2 specimens: faint={faint} body={lad['bodyColor']} "
          f"gap={space2:g}px ch34={ch34:.1f}px overflow={d['secOverflow']}px")


def main():
    failures = []
    with sync_playwright() as pw:
        browser = pw.webkit.launch()
        seen = {}
        for w, h in VIEWPORTS:
            page = browser.new_page(viewport={"width": w, "height": h})
            theme = None
            try:
                page.goto(URL, wait_until="commit", timeout=30000)
                wait_for_runtime(page)
                page.locator('#states').scroll_into_view_if_needed()
                page.wait_for_timeout(100)
                for theme in (None, "light"):
                    print(f"[{w}x{h}] {theme or 'dark(default)'}")
                    data = run_theme(page, theme)
                    seen[(theme or "dark")] = data
            except Exception as e:
                failures.append(f"{w}x{h} {theme}: {type(e).__name__}: {e}")
            finally:
                page.close()
        browser.close()
    # The two themes must actually differ: print-classList proof that
    # the runs were not byte-identical.
    dark, light = seen.get("dark"), seen.get("light")
    if dark and light:
        assert dark["ink"] != light["ink"], "dark and light runs read the same --ink"
        assert dark["texts"][0]["color"] != light["texts"][0]["color"], \
            "the faint tier read identically in both themes - one run was stale"
    if failures:
        print("FAIL")
        for f in failures:
            print(" ", f)
        sys.exit(1)
    print("OK - .cm-state__text holds the faint tier, the narrow measure,")
    print("    the centred block and the --space-2 rhythm in WebKit.")


if __name__ == "__main__":
    main()
