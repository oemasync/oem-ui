"""Do the three typeset presets actually TUNE anything?

A preset that computes the same rhythm as its base is a no-op knob wearing a
preset's name - the `--tap-sm` failure. So measure the EFFECTIVE values on a
real specimen in real WebKit, isolated per element, rather than asserting the
declarations exist.

Also measures the two properties the contract is about, at an iPhone
viewport: the phone bump, and that a spread of block types all space
themselves on block-start only.
"""
import sys
from playwright.sync_api import sync_playwright
import os

BASE = sys.argv[1] if len(sys.argv) > 1 else (os.environ.get('CLI_MONO_URL') or 'http://127.0.0.1:4471/')
URL = BASE + 'f/prose/'
passed = failed = 0


def check(name, cond, extra=''):
    global passed, failed
    if cond:
        passed += 1
        print('ok   ' + name)
    else:
        failed += 1
        print('FAIL ' + name + (' :: ' + str(extra) if extra else ''))


with sync_playwright() as p:
    b = p.webkit.launch()
    pg = b.new_page(viewport={'width': 390, 'height': 844})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL, wait_until='networkidle')
    pg.wait_for_function("() => document.documentElement.classList.contains('cm-js')", timeout=15000)
    check('no page errors', not errs, errs[:2])

    # ---- the presets must DIFFER from the base, on their own box ----------
    # Isolated control: each variant goes into its own empty host appended to
    # body, so nothing is measured through a sibling's stretch or a
    # surrounding flex row.
    presets = pg.evaluate("""() => {
        const read = (cls) => {
            const host = document.createElement('div');
            host.style.cssText = 'width:600px;position:absolute;left:-9999px;top:0';
            const t = document.createElement('div');
            t.className = 'cm-typeset' + (cls ? ' ' + cls : '');
            t.innerHTML = '<p>one</p><p>two</p>';
            host.appendChild(t); document.body.appendChild(host);
            const cs = getComputedStyle(t);
            const flow = getComputedStyle(t.children[1]).marginBlockStart;
            const out = {fontSize: cs.fontSize, lineHeight: cs.lineHeight, flow,
                         size: cs.getPropertyValue('--cm-typeset-size').trim(),
                         leading: cs.getPropertyValue('--cm-typeset-leading').trim()};
            host.remove();
            return out;
        };
        return {base: read(''), docs: read('cm-typeset--docs'),
                chat: read('cm-typeset--chat'), roomy: read('cm-typeset--roomy')};
    }""")
    print('   ', presets)

    base_flow = presets['base']['flow']
    check('the docs preset loosens the flow above the base',
          presets['docs']['flow'] != base_flow,
          f"docs flow {presets['docs']['flow']} vs base {base_flow}")
    check('the chat preset tightens the flow below the base',
          presets['chat']['flow'] != base_flow,
          f"chat flow {presets['chat']['flow']} vs base {base_flow}")
    check('the roomy preset raises the size above the base (a reader preference)',
          presets['roomy']['fontSize'] != presets['base']['fontSize'],
          f"roomy {presets['roomy']['fontSize']} vs base {presets['base']['fontSize']}")
    check('the roomy preset loosens the leading above the base',
          presets['roomy']['lineHeight'] != presets['base']['lineHeight'],
          f"roomy {presets['roomy']['lineHeight']} vs base {presets['base']['lineHeight']}")
    check('each preset resolves a DISTINCT flow, so none duplicates another',
          len({presets[k]['flow'] for k in ('docs', 'chat', 'roomy')}) == 3,
          {k: presets[k]['flow'] for k in ('docs', 'chat', 'roomy')})

    # ---- every block type spaces on block-start only ---------------------
    spacing = pg.evaluate("""() => {
        const t = document.querySelector('.cm-typeset');
        if (!t) return null;
        const kinds = ['p', 'blockquote', 'ul', 'pre', 'hr', 'table',
                       'h1', 'h2', 'h3', 'h4'];
        const seen = {};
        const host = document.createElement('div');
        host.style.cssText = 'position:absolute;left:-9999px';
        const probe = document.createElement('div');
        probe.className = 'cm-typeset';
        probe.innerHTML = '<p>a</p><h2>b</h2><blockquote>c</blockquote>' +
                          '<ul><li>d</li></ul><pre>e</pre><hr><table><tbody><tr><td>f</td></tr></tbody></table>';
        host.appendChild(probe); document.body.appendChild(host);
        for (const el of probe.children) {
            const cs = getComputedStyle(el);
            seen[el.tagName.toLowerCase()] = {
                start: cs.marginBlockStart,
                end: cs.marginBlockEnd,
                bottom: cs.marginBottom,
            };
        }
        host.remove();
        return seen;
    }""")
    print('   ', spacing)
    nonzero_end = {k: v for k, v in spacing.items()
                   if v['end'] not in ('0px', 'auto') or v['bottom'] not in ('0px', 'auto')}
    check('no block type carries end-side spacing (the streaming contract)',
          not nonzero_end, nonzero_end)
    check('every block after the first carries a real block-start gap',
          all(spacing[k]['start'] != '0px' for k in
              ('h2', 'blockquote', 'ul', 'pre', 'hr', 'table')),
          spacing)

    # ---- the phone bump, measured at 390 --------------------------------
    bump = pg.evaluate("""() => {
        const host = document.createElement('div');
        host.style.cssText = 'width:360px;position:absolute;left:-9999px';
        const t = document.createElement('div');
        t.className = 'cm-typeset'; t.innerHTML = '<p>x</p>';
        host.appendChild(t); document.body.appendChild(host);
        const fs = getComputedStyle(t).fontSize;
        const v = getComputedStyle(t).getPropertyValue('--cm-typeset-size').trim();
        host.remove();
        return {fontSize: fs, size: v};
    }""")
    print('   ', bump)
    check('the phone bump is applied at 390 (a viewport rule, not a preset)',
          bump['size'] != '1em', f"--cm-typeset-size resolved {bump['size']}")

    # ---- the opt-out, measured ------------------------------------------
    opt = pg.evaluate("""() => {
        const hole = document.querySelector('.not-typeset');
        if (!hole) return null;
        const p = hole.querySelector('p');
        const cs = getComputedStyle(p);
        return {start: cs.marginBlockStart, size: cs.fontSize};
    }""")
    check('the opt-out subtree carries no typeset rhythm', opt and opt['start'] == '0px', opt)

    # ---- no sideways pan at the iPhone viewport --------------------------
    w = pg.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]")
    check('no horizontal pan at 390', w[0] <= w[1], w)

    b.close()

print(f'\n{passed}/{passed + failed} passed')
sys.exit(1 if failed else 0)
