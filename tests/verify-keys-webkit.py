"""The keyboard layer, driven by REAL key presses in WebKit at an iPhone
viewport. A source scan cannot prove any of this: the runtime's handler can
exist, be registered, and still never fire because the scope was not focused,
the caret swallowed the key, or the sequence window had already lapsed.

Every check below is a measurement:
  - the aria form the platform exposes to assistive tech
  - the element that actually has focus after `/`
  - the page's scrollY / hash before and after a sequence
  - the caret's own text after typing `g` inside the field
  - the generated map's row count, labels and painted geometry
  - the dialog's computed border, so the BUILT css is proven, not the source

Run: /root/.venvs/mau/bin/python tests/verify-keys-webkit.py
"""
import os, sys
from playwright.sync_api import sync_playwright

# This host exports a PLAYWRIGHT_BROWSERS_PATH pointing at a NAS directory
# that no longer exists; playwright then hunts for webkit under the dead dir
# and refuses to launch. Browsers live in the local cache. Delete the var
# ONLY when the directory is genuinely gone - an unconditional delete would
# discard a restored cache.
if os.environ.get('PLAYWRIGHT_BROWSERS_PATH') and not os.path.isdir(
        os.environ['PLAYWRIGHT_BROWSERS_PATH']):
    del os.environ['PLAYWRIGHT_BROWSERS_PATH']

BASE = os.environ.get('CM_BASE', 'http://192.168.1.68:4321/')
passed = failed = 0


def check(name, cond, extra=''):
    global passed, failed
    if cond:
        passed += 1
        print('ok   ' + name)
    else:
        failed += 1
        print('FAIL ' + name + (' :: ' + extra if extra else ''))


with sync_playwright() as p:
    b = p.webkit.launch()
    pg = b.new_page(viewport={'width': 390, 'height': 844},
                    device_scale_factor=3, is_mobile=True, has_touch=True)
    pg.emulate_media(reduced_motion='reduce')
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    # `wait_until='load'` and `'domcontentloaded'` both HANG on this document
    # in WebKit (measured: goto times out at 30s while `document.readyState`
    # already reads 'complete'). The lifecycle event is missed on this large,
    # fast, same-origin document - and a verifier whose first line cannot
    # load the page proves nothing. 'commit' returns in 0.03s, and the real
    # readiness signal is the one the runtime itself publishes: the `cm-js`
    # class. networkidle can fire BEFORE the bundle executes, which is why
    # that mark - not a timer - is what this file waits for.
    pg.goto(BASE, wait_until='commit')
    # networkidle can fire before the bundle executes; the runtime marks
    # itself, and that mark is the only readiness signal worth waiting for.
    # MEASURED: `pg.wait_for_function("() => document.documentElement
    # .classList.contains('cm-js')")` TIMES OUT (10.9s) on this page while
    # `className` already reads 'cm-js' and `cliMono` is an object - and so
    # does the trivial `() => true`, on the FIRST call after a 'commit'
    # navigation, whichever polling mode is used. The next call resolves in
    # 0.06s. So the gate polls `evaluate` itself: same doctrine (wait for the
    # runtime's own mark, never a timer), no dependence on the broken path.
    for _ in range(150):
        if pg.evaluate("document.documentElement.classList.contains('cm-js')"):
            break
        pg.wait_for_timeout(100)
    else:
        raise SystemExit('FAIL the runtime never marked the document (cm-js)')
    pg.wait_for_timeout(300)

    scope_sel = '[data-cm-keys]'
    check('the specimen is on the page and is a real scope',
          pg.evaluate(f"() => !!document.querySelector('{scope_sel}')"))

    # ---- what assistive tech is told -----------------------------------
    aria = pg.evaluate(f"""() => {{
      const s = document.querySelector('{scope_sel}');
      const out = {{}};
      s.querySelectorAll('[data-cm-key]').forEach(el => {{
        out[el.getAttribute('data-cm-key')] = el.getAttribute('aria-keyshortcuts');
      }});
      return out;
    }}""")
    check('a plain chord publishes its own aria form',
          aria.get('/') == '/', str(aria))
    check('a SEQUENCE publishes nothing (the attribute has no syntax for one)',
          aria.get('g l') is None, str(aria))
    check('a disabled control publishes nothing',
          aria.get('x') is None, str(aria))

    # ---- the map ---------------------------------------------------------
    pg.evaluate(f"() => document.querySelector('{scope_sel}').focus()")
    check('focusing the scope puts focus ON it (tabindex="0")',
          pg.evaluate(f"() => document.activeElement === document.querySelector('{scope_sel}')"))
    pg.keyboard.press('?')
    pg.wait_for_timeout(150)
    rows = pg.evaluate("""() => {
      const d = document.querySelector('dialog.cm-keys');
      if (!d) return null;
      const cs = getComputedStyle(d);
      return {
        open: d.open,
        height: d.getBoundingClientRect().height,
        top: d.getBoundingClientRect().top,
        rows: [...d.querySelectorAll('.cm-keys__row')].map(r => ({
          label: r.querySelector('.cm-keys__label').textContent,
          keys: [...r.querySelectorAll('.cm-kbd')].map(k => k.textContent),
          border: getComputedStyle(r).borderTopWidth,
        })),
        barBorder: cs.borderBottomWidth,
        listOverflow: getComputedStyle(d.querySelector('.cm-keys__list')).overflowY,
      };
    }""")
    check('? builds AND opens the map', bool(rows) and rows['open'], str(rows))
    check('the map is painted, not a zero-height dialog',
          rows and rows['height'] > 120, str(rows and rows['height']))
    check('the map is on screen', rows and 0 <= rows['top'] < 844,
          str(rows and rows['top']))
    labels = [r['label'] for r in (rows or {}).get('rows', [])]
    check('one row per USABLE binding, the disabled one excluded',
          labels == ['Focus the search field', 'Go to the lists section',
                     'Open this keyboard map'], str(labels))
    seq = [r['keys'] for r in (rows or {}).get('rows', [])]
    check('a sequence renders as two keys, not one glued string',
          seq[1] == ['G', 'L'], str(seq))
    check('a chord renders as its keys (mod has no binding here)',
          seq[0] == ['/'], str(seq))
    check('the built CSS keeps the bar rule (minifier check)',
          rows and rows['barBorder'] == '1px', str(rows and rows['barBorder']))
    check('rows after the first carry the hairline',
          rows and rows['rows'][1]['border'] == '1px' and rows['rows'][0]['border'] == '0px',
          str(rows and [r['border'] for r in rows['rows']]))
    check('the list is its own scrollport', rows and rows['listOverflow'] == 'auto',
          str(rows and rows['listOverflow']))

    # The platform owns Escape and focus return; the layer only has to not
    # fight them.
    pg.keyboard.press('Escape')
    pg.wait_for_timeout(120)
    check('Escape closes the map (the platform dialog, not our keys)',
          pg.evaluate("() => !document.querySelector('dialog.cm-keys').open"))

    # ---- the sequence ----------------------------------------------------
    pg.evaluate(f"() => document.querySelector('{scope_sel}').focus()")
    before = pg.evaluate("() => ({y: window.scrollY, h: location.hash})")
    pg.keyboard.press('KeyG')
    pg.wait_for_timeout(60)
    mid = pg.evaluate("() => ({y: window.scrollY, h: location.hash})")
    check('the prefix alone does nothing', mid == before, f'{before} -> {mid}')
    pg.keyboard.press('KeyL')
    pg.wait_for_timeout(600)
    after = pg.evaluate("() => ({y: window.scrollY, h: location.hash})")
    check('g then l followed the binding (hash + a real scroll)',
          after['h'] == '#lists' and abs(after['y'] - before['y']) > 200,
          f'{before} -> {after}')

    # ---- the focus action ------------------------------------------------
    pg.evaluate(f"() => document.querySelector('{scope_sel}').focus()")
    pg.keyboard.press('/')
    pg.wait_for_timeout(80)
    check('/ focused the field by data-cm-key-focus',
          pg.evaluate("() => document.activeElement.id") == 'kbd-q',
          pg.evaluate("() => document.activeElement.id || document.activeElement.tagName"))

    # ---- the caret guard, on the same keys ------------------------------
    pg.evaluate("""() => { const i = document.getElementById('kbd-q');
                   i.value = ''; i.focus(); }""")
    y0 = pg.evaluate("() => window.scrollY")
    pg.keyboard.type('g')
    pg.keyboard.press('KeyL')
    pg.keyboard.type('/')
    pg.wait_for_timeout(120)
    state = pg.evaluate("""() => ({
      y: window.scrollY, hash: location.hash,
      val: document.getElementById('kbd-q').value,
      active: document.activeElement.id,
    })""")
    check('a caret keeps its plain keys: g, l and / all typed, nothing jumped',
          state['y'] == y0 and state['hash'] == '#lists'
          and state['val'] == 'gl/' and state['active'] == 'kbd-q',
          str(state))

    # ---- the scope guard: no stealing outside the panel ------------------
    pg.evaluate("() => { document.getElementById('kbd-q').value = ''; document.activeElement.blur(); }")
    y1 = pg.evaluate("() => window.scrollY")
    pg.keyboard.press('KeyG')
    pg.keyboard.press('KeyL')
    pg.wait_for_timeout(150)
    check('a LOCAL scope does not fire when focus is outside it',
          pg.evaluate("() => window.scrollY") == y1,
          'the page jumped with no focus in the panel')

    # ---- geometry: the sheet fits a phone -------------------------------
    pg.evaluate(f"() => document.querySelector('{scope_sel}').focus()")
    pg.keyboard.press('?')
    pg.wait_for_timeout(150)
    box = pg.evaluate("""() => {
      const d = document.querySelector('dialog.cm-keys');
      const r = d.getBoundingClientRect();
      return {l: r.left, r: r.right, w: r.width, iw: innerWidth,
              docW: document.documentElement.scrollWidth};
    }""")
    check('the map fits the viewport with a gutter on both sides',
          box['l'] >= 8 and box['r'] <= box['iw'] - 8, str(box))
    check('no horizontal overflow from the sheet',
          box['docW'] <= box['iw'], str(box))
    pg.keyboard.press('Escape')

    # ---- 320px: the narrowest phone Omar checks ------------------------
    pg.set_viewport_size({'width': 320, 'height': 640})
    pg.wait_for_timeout(200)
    pg.evaluate(f"() => document.querySelector('{scope_sel}').focus()")
    pg.keyboard.press('?')
    pg.wait_for_timeout(200)
    narrow = pg.evaluate("""() => {
      const d = document.querySelector('dialog.cm-keys');
      const r = d.getBoundingClientRect();
      const row = d.querySelector('.cm-keys__row');
      const lab = row.querySelector('.cm-keys__label').getBoundingClientRect();
      const keys = row.querySelector('.cm-keys__keys').getBoundingClientRect();
      return {l: r.left, rr: r.right, iw: innerWidth,
              rowOverflow: row.scrollWidth - row.clientWidth,
              keysRight: keys.right, labelLeft: lab.left,
              docW: document.documentElement.scrollWidth};
    }""")
    check('at 320 the sheet still fits', narrow['l'] >= 4 and narrow['rr'] <= narrow['iw'] - 4,
          str(narrow))
    check('at 320 a row does not overflow its own box',
          narrow['rowOverflow'] <= 1, str(narrow))
    check('at 320 the two columns do not overlap',
          narrow['keysRight'] <= narrow['labelLeft'] + 1, str(narrow))
    check('at 320 the document does not overflow', narrow['docW'] <= narrow['iw'],
          str(narrow))
    pg.keyboard.press('Escape')

    check('no page errors on any of it', not errs, str(errs))

    pg.screenshot(path='/tmp/keys-320.png', full_page=False)
    pg.set_viewport_size({'width': 390, 'height': 844})
    b.close()

print(f'\n{passed} passed, {failed} failed')
sys.exit(1 if failed else 0)
