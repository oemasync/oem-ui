#!/usr/bin/env python3
"""MEASURE: the coarse-pointer type floor does not reach INTO the components.

`base.css` floors bare prose elements on a coarse pointer. The library's
own components wrap those same elements in their own slots - a
`.cm-head__sub` holding a `<p>`, a `.cm-lede` holding a `<code>`, a
`.cm-row__meta` holding a `<time>` - and those children sit OUTSIDE the
bare floor's selector list, so they render at the component's own
reduced font-size with no floor at all.

Reads, per fixture at a phone viewport with a COARSE pointer emulated:
  - the computed font-size of the OUTER component element
  - the computed font-size of the INNER bare element it wraps
  - the resolved line-height in px (line-height is unitless in the
    library, so it is font-size x ratio - the number a reader feels)

Run: /root/.venvs/mau/bin/python tests/measure-slot-floor.py
"""
import json
import sys
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:4321/"

# Each fixture: a component element (with its real class) wrapping the bare
# element a real consumer puts inside it. The wrapper is appended to a
# fixed-width host so nothing else decides the box.
FIXTURES = [
    ("cm-head__sub + p", '<p class="cm-head__sub"><p>the sub-line a head carries</p></p>'),
    ("cm-lede + code", '<p class="cm-lede">a lede naming <code>--tap</code> inline</p>'),
    ("cm-head__sub + code", '<p class="cm-head__sub">a sub naming <code>--tap</code></p>'),
    ("cm-row__meta + time", '<span class="cm-row__meta"><time datetime="2026-10-13">Oct 13, 2026</time></span>'),
    ("cm-row__desc + code", '<span class="cm-row__desc">a desc with <code>cm-row</code></span>'),
    ("cm-footer__meta + a", '<span class="cm-footer__meta"><a href="#">contact</a></span>'),
    ("cm-head__sub (bare)", '<p class="cm-head__sub">plain text, no child element</p>'),
    ("p (bare, control)", '<p>a plain paragraph, the floor\'s control</p>'),
]

JS = """
(fixtures) => {
  const out = [];
  const host = document.createElement('div');
  host.style.width = '340px';
  document.body.appendChild(host);
  for (const [name, html] of fixtures) {
    const box = document.createElement('div');
    box.innerHTML = html;
    const outer = box.firstElementChild;
    host.appendChild(outer);
    const inner = outer.querySelector('*');
    const cs = (el) => el ? getComputedStyle(el) : null;
    const oc = cs(outer), ic = cs(inner);
    out.push({
      name,
      outerClass: outer.className,
      outerFont: oc ? oc.fontSize : null,
      outerLH: oc ? oc.lineHeight : null,
      innerTag: inner ? inner.tagName.toLowerCase() : null,
      innerFont: ic ? ic.fontSize : null,
      innerLH: ic ? ic.lineHeight : null,
    });
    host.removeChild(outer);
  }
  host.remove();
  return {
    fixtures: out,
    minFont: getComputedStyle(document.documentElement).getPropertyValue('--min-font').trim(),
    tap: getComputedStyle(document.documentElement).getPropertyValue('--tap').trim(),
  };
}
"""


def main():
    with sync_playwright() as pw:
        browser = pw.webkit.launch()
        ctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
        )
        page = ctx.new_page()
        page.goto(URL, wait_until="load")
        page.wait_for_function("document.documentElement.classList.contains('cm-js')", timeout=15000)
        page.emulate_media(reduced_motion="reduce")
        page.evaluate("document.fonts.ready")
        # is_mobile/has_touch is not enough for `pointer: coarse` in WebKit;
        # assert the media query so a false reading cannot pass as a finding.
        coarse = page.evaluate("matchMedia('(pointer: coarse)').matches")
        print(f"pointer: coarse == {coarse}   (viewport 390x844, dsf 3)")
        if not coarse:
            print("REFUSING: the floor is gated on coarse; this context is not coarse.")
            browser.close()
            return 2

        data = page.evaluate(JS, FIXTURES)
        print(f"--min-font = {data['minFont']}   --tap = {data['tap']}\n")
        print(f"{'fixture':24s} {'outer':>9s} {'inner':>9s} {'lh(outer)':>10s} {'lh(inner)':>10s}  verdict")
        for f in data["fixtures"]:
            inner = f["innerFont"] or "-"
            lhi = f["innerLH"] or "-"
            floor = float(data["minFont"].replace("px", ""))
            try:
                under = float(inner.replace("px", "")) < floor
            except ValueError:
                under = False
            verdict = "UNDER FLOOR" if under else "ok"
            print(
                f"{f['name']:24s} {f['outerFont']:>9s} {inner:>9s} "
                f"{f['outerLH']:>10s} {lhi:>10s}  {verdict}"
            )
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
