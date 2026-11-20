"""Measure the card-builder additions in real WebKit: `.cm-number`,
`.cm-repeater` and `.cm-artwork__pick`.

Every check is a measurement with a threshold that can fail, at 390px
(Omar's phone) and 1280px:

  STEPPER
   1. one frame: the inner input draws no border of its own and is not
      stretched to 100% (the element default would do both).
   2. the minus is disabled at min, the plus enabled; stepping to max flips
      them; the value never leaves [min, max].
   3. a step fires `input` and `change` (a framework would miss it otherwise).
   4. a 0.1 step lands on 0.6, not 0.6000000000000001.
   5. on a coarse pointer each button is at least --tap (44px) wide.

  REPEATER
   6. remove renumbers the rows and the count, and focus does not fall to
      <body>.
   7. the first row's up and the last row's down are disabled.
   8. add appends from the template, the new row's stepper is synced, and
      focus moves into the new row.
   9. a nested repeater's add/remove does not touch the outer count.
  10. a cancelled event leaves the DOM alone.
  11. at data-min the remove buttons are disabled; at data-max add is.
  12. the empty state shows only when the list holds no item.
  13. at 390px no row pushes the document sideways.

  ARTWORK PICK
  14. clicking a tile checks its radio; chosen paints a ring and a check
      mark that the unchosen tile does not.
  15. arrow keys move the choice (it is a real radio group).

Usage: python measure-builder-webkit.py [URL]
"""
import json
import os
import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("OEM_UI_URL", "http://127.0.0.1:4321/")
# The family pages carry the same specimens as the all-in-one index at a
# fraction of its weight (layout 232KB, content 66KB, index 549KB); on a
# loaded host the index alone took 54s to reach DOMContentLoaded.
FORMS = URL.rstrip("/") + "/f/layout/"
ART = URL.rstrip("/") + "/f/content/"
FAILS = []



def wait_ready(page, expr, budget=180.0):
    # wait_for_function right after navigation has been measured to hang on
    # this host under load; poll the page's own state instead, and say what
    # never appeared if it times out.
    import time as _t
    end = _t.monotonic() + budget
    while _t.monotonic() < end:
        try:
            if page.evaluate(expr):
                return
        except Exception:
            pass
        _t.sleep(0.25)
    raise SystemExit(f"FAIL page never became ready: {expr}")

def check(name, ok, detail=""):
    print(("  ok  " if ok else "FAIL  ") + name + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILS.append(name)


def run(p, width, coarse):
    browser = p.webkit.launch()
    ctx = browser.new_context(viewport={"width": width, "height": 900}, has_touch=coarse, is_mobile=False)
    page = ctx.new_page()
    # The showcase is one large page; under a loaded host a 30s default
    # navigation budget timed out before the first paint.
    page.set_default_timeout(120000)
    page.goto(FORMS, wait_until="domcontentloaded")
    wait_ready(page, "() => !!(window.cliMono && document.querySelector('#num-cost ~ [data-cm-number-inc]'))")
    tag = f"{width}{' coarse' if coarse else ''}"
    print(f"--- {tag}")

    # ---- stepper
    s = page.evaluate("""() => {
        const inp = document.getElementById('num-cost');
        const wrap = inp.closest('.cm-number');
        const cs = getComputedStyle(inp), ws = getComputedStyle(wrap);
        const [dec, inc] = wrap.querySelectorAll('.cm-number__btn');
        return {
          inputBorder: cs.borderTopWidth, inputBg: cs.backgroundColor,
          inputW: inp.getBoundingClientRect().width, wrapW: wrap.getBoundingClientRect().width,
          parentW: wrap.parentElement.getBoundingClientRect().width,
          wrapBorder: ws.borderTopWidth,
          decDisabled: dec.disabled, incDisabled: inc.disabled,
          decW: dec.getBoundingClientRect().width, h: wrap.getBoundingClientRect().height,
        };
    }""")
    check(f"{tag}: stepper input has no border of its own", s["inputBorder"] == "0px", s["inputBorder"])
    check(f"{tag}: stepper frame has a border", s["wrapBorder"] == "1px", s["wrapBorder"])
    check(f"{tag}: stepper is not full width", s["wrapW"] < 0.6 * s["parentW"], f'{s["wrapW"]:.0f} of {s["parentW"]:.0f}')
    check(f"{tag}: stepper is at least 44px tall", s["h"] >= 44, f'{s["h"]:.1f}')
    check(f"{tag}: minus disabled at min=0", s["decDisabled"] is True)
    check(f"{tag}: plus enabled below max", s["incDisabled"] is False)
    if coarse:
        check(f"{tag}: coarse-pointer step button >= 44px wide", s["decW"] >= 44, f'{s["decW"]:.1f}')

    page.evaluate("""() => {
        window.__ev = [];
        const inp = document.getElementById('num-cost');
        inp.addEventListener('input', () => __ev.push('input'));
        inp.addEventListener('change', () => __ev.push('change'));
    }""")
    inc = page.locator("#num-cost ~ [data-cm-number-inc]")
    inc.click()
    st = page.evaluate("() => ({v: document.getElementById('num-cost').value, ev: __ev.slice(), dec: document.querySelector('#num-cost').previousElementSibling.disabled})")
    check(f"{tag}: plus steps 0 -> 1", st["v"] == "1", st["v"])
    check(f"{tag}: a step fires input and change", st["ev"] == ["input", "change"], json.dumps(st["ev"]))
    check(f"{tag}: minus re-enables above min", st["dec"] is False)
    for _ in range(14):
        if inc.is_disabled():
            break
        inc.click()
    st = page.evaluate("() => ({v: document.getElementById('num-cost').value, inc: document.querySelector('#num-cost').nextElementSibling.disabled})")
    check(f"{tag}: stepping stops at max=10", st["v"] == "10", st["v"])
    check(f"{tag}: plus disabled at max", st["inc"] is True)
    # typing past the bound re-syncs the buttons too
    page.fill("#num-cost", "3")
    st = page.evaluate("() => document.querySelector('#num-cost').nextElementSibling.disabled")
    check(f"{tag}: typing a value re-syncs the plus", st is False)

    # The clamp only matters off the step grid: stepping by 1 from 0 lands
    # on max exactly and disables itself, so it never needs the clamp. A
    # typed 9.5 plus one step must land on max, not on 10.5 (rounded to 11).
    page.fill("#num-cost", "9.5")
    inc.click()
    cl = page.evaluate("() => document.getElementById('num-cost').value")
    check(f"{tag}: a step from an off-grid value clamps to max", cl == "10", cl)

    page.locator("#num-weight ~ [data-cm-number-inc]").click()
    w = page.evaluate("() => document.getElementById('num-weight').value")
    check(f"{tag}: 0.1 step lands on a clean 0.6", w == "0.6", w)

    # ---- repeater
    rep = "#rep-demo"

    def state():
        return page.evaluate("""() => {
            const rep = document.getElementById('rep-demo');
            const items = [...rep.querySelector(':scope > [data-cm-repeater-list]').children];
            return {
              count: rep.querySelector(':scope > .cm-repeater__head [data-cm-repeater-count]').textContent,
              n: items.length,
              idx: items.map(i => i.querySelector('[data-cm-repeater-index]').textContent),
              labels: items.map(i => i.querySelector('.cm-repeater__label').textContent),
              upDisabled: items.map(i => i.querySelector(':scope > .cm-repeater__bar [data-cm-repeater-up]').disabled),
              downDisabled: items.map(i => i.querySelector(':scope > .cm-repeater__bar [data-cm-repeater-down]').disabled),
              rmDisabled: items.map(i => i.querySelector(':scope > .cm-repeater__bar [data-cm-repeater-remove]').disabled),
              rmLabel: items.map(i => i.querySelector(':scope > .cm-repeater__bar [data-cm-repeater-remove]').getAttribute('aria-label')),
              active: document.activeElement === document.body ? 'BODY' : (document.activeElement.getAttribute('aria-label') || document.activeElement.textContent.trim() || document.activeElement.tagName),
              emptyShown: getComputedStyle(rep.querySelector(':scope > .cm-repeater__empty')).display !== 'none',
            };
        }""")

    s0 = state()
    check(f"{tag}: repeater starts with 2 rows, count 2", s0["n"] == 2 and s0["count"] == "2", json.dumps([s0["n"], s0["count"]]))
    check(f"{tag}: first up / last down disabled", s0["upDisabled"] == [True, False] and s0["downDisabled"] == [False, True],
          json.dumps([s0["upDisabled"], s0["downDisabled"]]))
    check(f"{tag}: empty state hidden while rows exist", s0["emptyShown"] is False)

    # nested add on row 1 must not change the outer count
    page.locator(f"{rep} > ol > li:nth-child(1) .cm-repeater [data-cm-repeater-add]").click()
    inner = page.evaluate("""() => {
        const r = document.querySelector('#rep-demo > ol > li:nth-child(1) .cm-repeater');
        return {count: r.querySelector('[data-cm-repeater-count]').textContent,
                n: r.querySelector('[data-cm-repeater-list]').children.length,
                newStepperDecDisabled: r.querySelector('[data-cm-repeater-list] > li:last-child [data-cm-number-dec]').disabled,
                active: document.activeElement.closest('[data-cm-repeater-item]') === r.querySelector('[data-cm-repeater-list] > li:last-child')};
    }""")
    check(f"{tag}: nested add appends an inner row", inner["n"] == 2 and inner["count"] == "2", json.dumps(inner))
    check(f"{tag}: new row's stepper is synced (minus disabled at min=1)", inner["newStepperDecDisabled"] is True)
    check(f"{tag}: focus moves into the added row", inner["active"] is True)
    check(f"{tag}: nested add leaves the outer count at 2", state()["count"] == "2")

    # outer add
    page.locator(f"{rep} > [data-cm-repeater-add]").click()
    s1 = state()
    check(f"{tag}: outer add -> 3 rows, numbered 1..3", s1["n"] == 3 and s1["idx"] == ["1", "2", "3"] and s1["count"] == "3",
          json.dumps([s1["idx"], s1["count"]]))
    check(f"{tag}: ends re-synced after add", s1["downDisabled"] == [False, False, True], json.dumps(s1["downDisabled"]))
    # The outer add must clone the OUTER template. With scoping gone it
    # picked the first <template> in document order - the nested one - and
    # appended an effect row to the action list.
    check(f"{tag}: outer add clones the outer template (an action, not an effect)", s1["labels"][-1] == "new action", s1["labels"][-1])

    # move row 3 up
    page.locator(f"{rep} > ol > li:nth-child(3) > .cm-repeater__bar [data-cm-repeater-up]").click()
    s2 = state()
    check(f"{tag}: move up reorders", s2["labels"] == ["strike", "new action", "guard"], json.dumps(s2["labels"]))
    check(f"{tag}: move keeps focus on the moving tool", s2["active"] == "move action 2 up", s2["active"])

    # remove the middle row
    page.locator(f"{rep} > ol > li:nth-child(2) > .cm-repeater__bar [data-cm-repeater-remove]").click()
    s3 = state()
    check(f"{tag}: remove renumbers 1..2 and recounts", s3["idx"] == ["1", "2"] and s3["count"] == "2", json.dumps([s3["idx"], s3["count"]]))
    check(f"{tag}: aria-labels follow the position", s3["rmLabel"] == ["remove action 1", "remove action 2"], json.dumps(s3["rmLabel"]))
    check(f"{tag}: focus after remove is not <body>", s3["active"] != "BODY", s3["active"])

    # a cancelled remove leaves the DOM alone
    page.evaluate("() => document.getElementById('rep-demo').addEventListener('cm:repeater-remove', e => { if (e.target.id === 'rep-demo') e.preventDefault(); }, {once: true})")
    page.locator(f"{rep} > ol > li:nth-child(1) > .cm-repeater__bar [data-cm-repeater-remove]").click()
    check(f"{tag}: cancelled remove keeps both rows", state()["n"] == 2)

    # data-min=1: remove down to one row, then remove is disabled
    page.locator(f"{rep} > ol > li:nth-child(2) > .cm-repeater__bar [data-cm-repeater-remove]").click()
    s4 = state()
    check(f"{tag}: at data-min the remove is disabled", s4["n"] == 1 and s4["rmDisabled"] == [True], json.dumps([s4["n"], s4["rmDisabled"]]))
    check(f"{tag}: focus after removing the last row is not <body>", s4["active"] != "BODY", s4["active"])

    # data-max=3 on the nested list
    nadd = page.locator(f"{rep} > ol > li:nth-child(1) .cm-repeater [data-cm-repeater-add]")
    for _ in range(4):
        if nadd.is_disabled():
            break
        nadd.click()
    nn = page.evaluate("() => document.querySelector('#rep-demo > ol > li:nth-child(1) .cm-repeater [data-cm-repeater-list]').children.length")
    check(f"{tag}: nested add stops at data-max=3", nn == 3 and nadd.is_disabled(), str(nn))

    # empty state: remove every nested row
    for _ in range(4):
        b = page.locator(f"{rep} > ol > li:nth-child(1) .cm-repeater [data-cm-repeater-list] > li:first-child [data-cm-repeater-remove]")
        if b.count() == 0:
            break
        b.click()
    em = page.evaluate("""() => {
        const r = document.querySelector('#rep-demo > ol > li:nth-child(1) .cm-repeater');
        return {shown: getComputedStyle(r.querySelector('.cm-repeater__empty')).display !== 'none',
                count: r.querySelector('[data-cm-repeater-count]').textContent,
                active: document.activeElement === document.body ? 'BODY' : document.activeElement.textContent.trim()};
    }""")
    check(f"{tag}: empty state shows when the list is empty", em["shown"] and em["count"] == "0", json.dumps(em))
    check(f"{tag}: emptying the list puts focus on add", em["active"] == "+ effect", em["active"])

    ov = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
    check(f"{tag}: no sideways scroll", ov <= 0, str(ov))

    # ---- artwork pick
    page.goto(ART, wait_until="domcontentloaded")
    wait_ready(page, "() => !!(window.cliMono && document.querySelector('label.cm-artwork__pick'))")
    tiles = page.locator("label.cm-artwork__pick")
    check(f"{tag}: three pick tiles", tiles.count() == 3, str(tiles.count()))
    tiles.nth(0).click(position={"x": 30, "y": 60})

    def pick_state():
        return page.evaluate("""() => [...document.querySelectorAll('label.cm-artwork__pick')].map(l => {
            const it = l.querySelector('.cm-artwork__item');
            return {checked: l.querySelector('input').checked,
                    ring: getComputedStyle(it, '::before').boxShadow,
                    mark: getComputedStyle(it, '::after').display,
                    content: getComputedStyle(it, '::after').content};
        })""")

    ps = pick_state()
    check(f"{tag}: click on the picture checks its radio", ps[0]["checked"] and not ps[1]["checked"], json.dumps([x["checked"] for x in ps]))
    check(f"{tag}: chosen tile paints a ring", ps[0]["ring"] not in ("none", "") and ps[1]["ring"] in ("none", ""), f'{ps[0]["ring"]} | {ps[1]["ring"]}')
    check(f"{tag}: chosen tile shows the check mark only on itself", ps[0]["mark"] != "none" and ps[1]["mark"] == "none" and "\u2713" in ps[0]["content"],
          f'{ps[0]["mark"]}/{ps[0]["content"]} | {ps[1]["mark"]}')
    # The ring is an overlay; a computed box-shadow proves nothing unless the
    # overlay actually covers the tile it rings (an unpositioned tile would
    # anchor it to some outer box and the check above would still pass).
    g = page.evaluate("""() => { const it = document.querySelector('label.cm-artwork__pick .cm-artwork__item');
        const r = it.getBoundingClientRect(), b = getComputedStyle(it, '::before');
        return {w: r.width, h: r.height, bw: parseFloat(b.width), bh: parseFloat(b.height)}; }""")
    check(f"{tag}: the ring overlay covers its own tile", abs(g["bw"] - (g["w"] - 2)) <= 1 and abs(g["bh"] - (g["h"] - 2)) <= 1, json.dumps(g))
    page.keyboard.press("ArrowRight")
    ps = pick_state()
    check(f"{tag}: ArrowRight moves the choice", ps[1]["checked"] and not ps[0]["checked"], json.dumps([x["checked"] for x in ps]))
    # Keyboard focus is a separate signal from the choice. Reach the group
    # the way a keyboard user does - Tab in from the control before it - so
    # :focus-visible is the platform's own answer, not a scripted focus().
    page.evaluate("() => { const u = document.querySelector('label.cm-artwork__pick').closest('ul'); const b = document.createElement('button'); b.id = '__before'; b.textContent = 'x'; u.before(b); b.focus(); }")
    page.keyboard.press("Tab")
    fo = page.evaluate("""() => { const r = document.activeElement; return {
        radio: r.classList.contains('cm-artwork__radio'),
        outline: getComputedStyle(r.closest('label').querySelector('.cm-artwork__item')).outlineStyle,
        other: getComputedStyle(document.querySelectorAll('label.cm-artwork__pick .cm-artwork__item')[0]).outlineStyle }; }""")
    check(f"{tag}: Tab lands on the chosen radio", fo["radio"] is True, json.dumps(fo))
    check(f"{tag}: keyboard focus draws the outline on that tile only", fo["outline"] == "solid" and fo["other"] == "none", json.dumps(fo))

    browser.close()


with sync_playwright() as p:
    run(p, 390, True)
    run(p, 1280, False)

print(f"\n{'ALL BUILDER CHECKS PASSED' if not FAILS else str(len(FAILS)) + ' CHECK(S) FAILED'}")
sys.exit(1 if FAILS else 0)
