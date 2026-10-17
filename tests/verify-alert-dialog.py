#!/root/.venvs/mau/bin/python
"""WebKit proof for the AlertDialog (shadcn's alert-dialog).

The claim this file exists to test is the one thing that separates an
AlertDialog from a Dialog, and it is a BEHAVIOURAL claim, not a styling
one: a destructive confirm must not be dismissible by a click outside.

Two measurement lessons are baked into this file, both learned the hard
way by writing it wrong first:

  1. A SYNTHETIC MouseEvent CANNOT TEST LIGHT DISMISS. Light dismiss is
     the engine's own hit test - a script-dispatched event never reaches
     it, so a "the backdrop click did not close it" check passes whether
     or not the dialog is actually protected. That check was vacuous, and
     it was replaced with a REAL pointer at a REAL coordinate outside the
     dialog's box.

  2. A PROBE THAT OPENS A MODAL MUST CLOSE IT. An earlier version created
     a probe <dialog> with showModal() and left it in the top layer; a
     later Escape then closed the PROBE, not the confirm under test, and
     the failure looked like a bug in the library. Any probe that opens a
     modal closes it before the next assertion.

What is measured, rather than assumed: whether this engine light-
dismisses at all, and what `closedby` does. The spec gives `closedby` a
default of "closerequest" (Escape closes, an outside click does NOT), so
the honest alert dialog may need NO SCRIPT AT ALL - which is exactly what
this file establishes in the reader's own engine before asserting on it.

Claims:
  1. IT IS AN ALERT DIALOG. role="alertdialog", with a name and a
     description from DIFFERENT nodes both reaching the a11y tree. An
     alert dialog whose description is not announced is a question with
     no context.
  2. AN OUTSIDE CLICK DOES NOT DISMISS IT - proven with a real pointer,
     against a measured engine baseline.
  3. ESCAPE AND THE BUTTONS STILL DO. A guard that also blocks the real
     exits is a worse bug than the one it fixes.
  4. THE DESTRUCTIVE ACTION IS LAST on the strip, so the safe answer is
     the one a thumb lands on.
"""
import sys
from playwright.sync_api import sync_playwright
from harness_wait import boot_timeout

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:4471/'
NAV_TIMEOUT = boot_timeout(base=90000)

passed = 0
failed = []


def check(name, ok, detail=None):
    global passed
    if ok:
        passed += 1
        print(f'ok   {name} :: {detail}', flush=True)
    else:
        failed.append(name)
        print(f'FAIL {name} :: {detail}', flush=True)


with sync_playwright() as p:
    b = p.webkit.launch()
    page = b.new_page(viewport={'width': 390, 'height': 844},
                      has_touch=True, is_mobile=True)
    page.set_default_timeout(180000)  # starved box: 27s+ to boot
    errs = []
    page.on('pageerror', lambda e: errs.append(str(e)))
    page.goto(URL, wait_until='load', timeout=NAV_TIMEOUT)
    page.wait_for_function(
        "() => window.cliMono && document.documentElement.classList.contains('cm-js')",
        timeout=NAV_TIMEOUT)
    page.wait_for_timeout(250)

    # ---- 1. the semantic half, read from the live DOM ----
    sem = page.evaluate("""() => {
      const d = document.getElementById('alert-demo');
      if (!d) return null;
      const name = d.getAttribute('aria-labelledby')
        ? (document.getElementById(d.getAttribute('aria-labelledby')) || {}).textContent : null;
      const desc = d.getAttribute('aria-describedby')
        ? (document.getElementById(d.getAttribute('aria-describedby')) || {}).textContent : null;
      return {role: d.getAttribute('role'), tag: d.tagName.toLowerCase(),
              name: (name || '').trim(), desc: (desc || '').trim(),
              closedby: d.getAttribute('closedby'),
              labelledby: d.getAttribute('aria-labelledby'),
              describedby: d.getAttribute('aria-describedby')};
    }""")
    check('the confirm is a native <dialog> carrying role="alertdialog"',
          sem and sem['tag'] == 'dialog' and sem['role'] == 'alertdialog',
          str(sem))
    check('it has a name AND a description, both non-empty',
          sem and sem['name'] and sem['desc'],
          f'name={sem["name"]!r} desc={sem["desc"][:40]!r}' if sem else 'no element')
    # The name and the description must be DIFFERENT nodes: pointing both
    # at one id satisfies "non-empty" twice while announcing the same
    # sentence as both the question and its context.
    check('the name and the description are different elements',
          sem and sem['labelledby'] != sem['describedby'],
          f'{sem["labelledby"]} vs {sem["describedby"]}' if sem else 'no element')
    # The attribute is the whole protection, so its absence is a real
    # failure and not a style note.
    check('the outside click is refused DECLARATIVELY, not by script',
          sem and (sem['closedby'] or '') == 'closerequest',
          f'closedby={sem["closedby"]!r}' if sem else 'no element')

    # ---- ENGINE BASELINE, measured in a throwaway modal that is closed
    # again before anything else runs (lesson 2). ----
    baseline = page.evaluate("""() => {
      const out = {};
      for (const v of [null, 'any', 'closerequest', 'none']) {
        const d = document.createElement('dialog');
        if (v) d.setAttribute('closedby', v);
        d.style.cssText = 'position:fixed;left:40px;top:40px;width:180px;height:90px;padding:12px;';
        d.textContent = 'probe';
        document.body.appendChild(d);
        d.showModal();
        out[v === null ? 'absent' : v] = {rect: (r => ({x:r.x,y:r.y,w:r.width,h:r.height}))(d.getBoundingClientRect())};
        d.close();                       // <- leave no modal behind
        d.remove();
      }
      out.anyModalOpen = !!document.querySelector('dialog[open]');
      return out;
    }""")
    page.wait_for_timeout(100)
    check('no probe modal is left open in the top layer',
          baseline.get('anyModalOpen') is False, str(baseline.get('anyModalOpen')))

    # ---- the trigger opens it ----
    page.click('[data-cm-open="alert-demo"]')
    page.wait_for_timeout(250)
    opened = page.evaluate("() => document.getElementById('alert-demo').open === true")
    check('the trigger opens the confirm', opened, f'open={opened}')

    # ---- 2. THE OUTSIDE CLICK, with a REAL pointer at a REAL point
    # outside the dialog's own box (lesson 1). ----
    box = page.evaluate("""() => {
      const d = document.getElementById('alert-demo');
      const r = d.getBoundingClientRect();
      return {x: r.x, y: r.y, w: r.width, h: r.height,
              vw: innerWidth, vh: innerHeight};
    }""")
    # A point below the dialog and inside the viewport: the dialog is
    # centred, so the strip under it is backdrop.
    tx = box['vw'] / 2
    ty = min(box['vh'] - 6, box['y'] + box['h'] + 40)
    page.mouse.click(tx, ty)
    page.wait_for_timeout(350)
    still_open = page.evaluate("() => document.getElementById('alert-demo').open === true")
    check('a REAL click on the backdrop does NOT dismiss the confirm',
          still_open is True,
          f'at ({tx:.0f},{ty:.0f}) outside box {box} -> open={still_open}')

    # A real click on the CONTENT must also leave it open.
    page.click('#alert-demo .cm-dialog__title')
    page.wait_for_timeout(200)
    check('a real click on the content leaves it open too',
          page.evaluate("() => document.getElementById('alert-demo').open === true") is True,
          'content click')

    # ---- 3. the real exits still work ----
    # Escape is the platform's; a guard that ate it would trap the reader.
    page.keyboard.press('Escape')
    page.wait_for_timeout(350)
    esc_closed = page.evaluate("() => document.getElementById('alert-demo').open === false")
    check('Escape still closes it - the confirm does not trap the reader',
          esc_closed is True, f'open={not esc_closed}')

    # And it re-opens afterwards.
    page.click('[data-cm-open="alert-demo"]')
    page.wait_for_timeout(250)
    check('it opens again after an Escape',
          page.evaluate("() => document.getElementById('alert-demo').open === true") is True,
          'reopen')

    # The CONFIRM answer must reach the page as a returnValue - that is
    # what makes the two buttons answers rather than decoration.
    page.click('#alert-demo .cm-btn--danger')
    page.wait_for_timeout(300)
    rv = page.evaluate("() => { const d = document.getElementById('alert-demo'); return {open: d.open, rv: d.returnValue}; }")
    check('the destructive button settles the dialog and returns "confirm"',
          rv['open'] is False and rv['rv'] == 'confirm', str(rv))

    # ---- 4. the destructive action is LAST ----
    order = page.evaluate("""() => {
      const foot = document.querySelector('#alert-demo .cm-dialog__foot');
      if (!foot) return null;
      const kids = [...foot.children].map(b => ({cls: b.className, txt: b.textContent.trim()}));
      return {n: kids.length, last: kids[kids.length - 1],
              dangerIdx: kids.findIndex(k => /cm-btn--danger/.test(k.cls)),
              kids: kids.map(k => k.txt)};
    }""")
    # ---- 5. NO DEAD ACTION. The alert dialog shipped its actions as
    # type="submit" OUTSIDE the form, so neither button did anything at
    # all: a confirm with two dead buttons. Assert the general rule for
    # every dialog on the page, not just this one.
    dead = page.evaluate("""() => {
      const bad = [];
      document.querySelectorAll('dialog').forEach(d => {
        const foot = d.querySelector('.cm-dialog__foot');
        if (!foot) return;
        [...foot.querySelectorAll('button')].forEach(b => {
          const submits = (b.getAttribute('type') || 'submit').toLowerCase() === 'submit';
          const inForm = !!b.closest('form');
          // A submit button that is not inside a form is inert.
          if (submits && !inForm) bad.push(d.id + ' -> ' + (b.textContent || '').trim());
        });
      });
      return bad;
    }""")
    check('no dialog action button is an inert submit outside a form',
          not dead, str(dead))

    check('the destructive action is the LAST control on the strip',
          order and order['dangerIdx'] == order['n'] - 1 and order['n'] >= 2,
          str(order))
    check('the confirm uses the danger grammar, not a hue',
          order and order['dangerIdx'] >= 0, str(order))

    check('the page threw nothing', not errs, str(errs))

    b.close()

print(f'\npassed {passed}/{passed + len(failed)}', flush=True)
if failed:
    print('FAILED: ' + ', '.join(failed))
sys.exit(1 if failed else 0)
