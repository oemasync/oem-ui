#!/usr/bin/env python3
"""
WebKit proof for the two components shadcn gained while our ledger was
pinned: Code Block's body features and Trace.

Reads COMPUTED values and CLICKED state from a real engine. Nothing here
is a source-text assertion: the suite already greps markup, and a page can
carry correct markup that computes to nothing.

Run:  tests/verify-codeblock-trace.py [base_url]
      default base http://127.0.0.1:4471
"""
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:4471"
BOOT = 90000

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("ok   " if ok else "FAIL ") + name + (f" :: {detail}" if (detail and not ok) else ""))


def main():
    with sync_playwright() as pw:
        browser = pw.webkit.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        # Capture what would be written to the clipboard, by overriding the
        # API the runtime calls. This measures the PAYLOAD, not the button:
        # a "copied" label with gutters in the text would pass a UI test.
        ctx.add_init_script(
            """
            window.__copied = [];
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText = function (t) {
                    window.__copied.push(t);
                    return Promise.resolve();
                };
            }
            const _ec = document.execCommand.bind(document);
            document.execCommand = function (cmd) {
                if (cmd === 'copy') {
                    const ta = document.querySelector('textarea[data-cm-capture]');
                    if (ta) window.__copied.push(ta.value);
                    return true;
                }
                return _ec(cmd);
            };
            """
        )
        page = ctx.new_page()
        page.goto(BASE + "/", wait_until="networkidle", timeout=BOOT)

        # ---- start line: the first gutter numeral is 240, not 1 ----------
        nums = page.eval_on_selector_all(
            "#demo-numbered .cm-code__ln", "els => els.map(e => e.textContent)"
        )
        check("start line: gutter begins at 240", nums[:3] == ["240", "241", "242"],
              f"got {nums[:3]}")
        check("gutter covers every line", len(nums) == 6, f"got {len(nums)} numbers")

        # ---- gutter is NOT selectable and NOT announced ------------------
        gs = page.eval_on_selector(
            "#demo-numbered .cm-code__ln",
            "e => getComputedStyle(e).userSelect",
        )
        aria = page.eval_on_selector("#demo-numbered .cm-code__ln",
                                     "e => e.getAttribute('aria-hidden')")
        check("gutter is unselectable", "none" in gs, gs)
        check("gutter is aria-hidden", aria == "true", str(aria))

        # ---- highlight: the marked lines carry the attribute, and it paints
        marks = page.eval_on_selector_all(
            "#demo-numbered .cm-code__line",
            "els => els.map(e => e.hasAttribute('data-highlight'))",
        )
        check("highlight lands on lines 242 and 243",
              marks == [False, False, True, True, False, False], str(marks))
        bg = page.eval_on_selector(
            "#demo-numbered .cm-code__line[data-highlight]",
            "e => getComputedStyle(e).backgroundColor",
        )
        # any non-transparent background proves the band paints
        check("highlight paints a band", bg not in ("rgba(0, 0, 0, 0)", "transparent"), bg)

        # ---- wrap: computed white-space, scroll vs wrap ------------------
        ws_default = page.eval_on_selector("pre#demo-install",
                                           "e => getComputedStyle(e).whiteSpace")
        ws_wrap = page.eval_on_selector("pre#demo-wrap",
                                        "e => getComputedStyle(e).whiteSpace")
        check("unwrapped code scrolls (white-space: pre)", ws_default == "pre", ws_default)
        check("wrap block wraps (pre-wrap)", ws_wrap == "pre-wrap", ws_wrap)

        # ---- wrap: a long line must NOT overflow the viewport ------------
        over = page.evaluate(
            "(() => { const el = document.querySelector('pre#demo-wrap');"
            "return el.scrollWidth > el.clientWidth + 1; })()"
        )
        check("wrapped line does not overflow its box", over is False, str(over))

        # ---- floating action exists and is a real button -----------------
        fl = page.eval_on_selector(".cm-codebar__float",
                                   "e => e.tagName")
        check("floating action is a BUTTON", fl == "BUTTON", fl)

        # ---- copy payload: gutters must NOT reach the clipboard ----------
        # The copy button lives in the BAR, a sibling of the <pre>, so it is
        # anchored by what it targets rather than by containment.
        page.click("button[data-cm-copy='#demo-numbered']")
        page.wait_for_timeout(300)
        copied = page.evaluate("window.__copied")
        check("a copy happened", len(copied) >= 1, str(len(copied)))
        if copied:
            text = copied[-1]
            check("clipboard has no gutter numerals",
                  not any(text.lstrip().startswith(str(n)) for n in (240, 241)) and
                  "240const" not in text and not text.split("\n")[0].strip().startswith("240"),
                  repr(text[:80]))
            check("clipboard keeps the real code",
                  "export function boot(root)" in text, repr(text[:80]))
            check("clipboard keeps line breaks",
                  text.count("\n") == 5, f"newlines={text.count(chr(10))}")

        # ---- trace: markup states ----------------------------------------
        states = page.eval_on_selector_all(
            ".cm-trace__item",
            "els => els.map(e => [...e.classList].filter(c => c.startsWith('is-'))[0] || 'idle')",
        )
        check("trace states render (done, running, error, idle)",
              states.count("is-done") >= 2 and "is-running" in states
              and "is-error" in states and states.count("idle") >= 1,
              str(states))

        # ---- trace: the disclosure actually toggles -----------------------
        trg = page.locator(".cm-trace__trigger[aria-controls='trace-detail-1']")
        before = trg.get_attribute("aria-expanded")
        hidden_before = page.eval_on_selector("#trace-detail-1",
                                              "e => e.hasAttribute('hidden')")
        trg.click()
        page.wait_for_timeout(150)
        after = trg.get_attribute("aria-expanded")
        hidden_after = page.eval_on_selector("#trace-detail-1",
                                             "e => e.hasAttribute('hidden')")
        check("disclosure starts closed", before == "false" and hidden_before,
              f"expanded={before} hidden={hidden_before}")
        check("click opens it", after == "true" and not hidden_after,
              f"expanded={after} hidden={hidden_after}")
        trg.click()
        page.wait_for_timeout(150)
        closed_again = trg.get_attribute("aria-expanded")
        hidden_again = page.eval_on_selector("#trace-detail-1",
                                             "e => e.hasAttribute('hidden')")
        check("second click closes it", closed_again == "false" and hidden_again,
              f"expanded={closed_again} hidden={hidden_again}")

        # ---- trace: keyboard reachability (it is a <button>) --------------
        tag = page.eval_on_selector(".cm-trace__trigger", "e => e.tagName")
        check("trigger is a BUTTON the keyboard can reach", tag == "BUTTON", tag)

        # ---- trace: expanded body is actually visible --------------------
        page.locator(".cm-trace__trigger[aria-controls='trace-detail-1']").click()
        page.wait_for_timeout(120)
        vis = page.eval_on_selector(
            "#trace-detail-1",
            "e => { const r = e.getBoundingClientRect();"
            "return r.height > 0 && getComputedStyle(e).display !== 'none'; }",
        )
        check("revealed detail has height (not just un-hidden)", vis is True, str(vis))

        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
