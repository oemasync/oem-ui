#!/usr/bin/env python3
"""
init() must be idempotent, and a listener must not outlive its element.

AGENTS.md rule 5: init() runs again on every astro:page-load, and a SPA calls
it after each route change. MEASURED on the showcase in Chromium before this
harness existed: every extra init() added 7 listeners to `window` (4 scroll,
3 resize) and constructed one more ResizeObserver, and nothing removed them.
Four binders had no guard at all: the header, the scroll spy, the navigation
menu's section spy and the measure readout. And after a client-side
navigation, every listener bound for the page that left was still attached.

The count is taken by wrapping addEventListener / removeEventListener before
the page's own scripts run. Only `window`, `document` and media query lists
are counted: a listener on an element dies with the element, and one on
`window` never does.
Identity is honoured the way the platform honours it, so adding the SAME
function twice counts once.

  1. boot, then init() three more times       -> no new listener, no new observer
  2. one astro:page-load event                -> the same
  3. replace the whole body with a fresh copy of itself (what a client-side
     navigation does), init(), then scroll, resize, click and press a key
     -> the count is back to boot, and the NEW header is live: it takes
     .is-scrolled when the page scrolls

Step 3 has its own control, or it could pass by binding nothing at all: the
old header must be out of the document, and the new one must react.

usage: OEM_UI_URL=http://127.0.0.1:4321/ python3 tests/verify-init-idempotent.py
"""
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness_wait import wait_boot  # noqa: E402

URL = os.environ.get('OEM_UI_URL', 'http://localhost:4321/')
# Set by tests/mutate-init-idempotent.py: the text to serve in place of the
# built runtime chunk, so a mutant is measured without touching the tree.
JS_OVERRIDE = None
QUIET = False

HOOK = r"""(() => {
  const reg = { listeners: {}, observers: {}, intervals: 0 };
  // A MediaQueryList is as long-lived as window: the burger subscribes to one.
  const name = t => t === window ? 'window' : t === document ? 'document'
    : (window.MediaQueryList && t instanceof MediaQueryList) ? 'mediaquery' : null;
  const seen = new WeakMap();
  const add = EventTarget.prototype.addEventListener, rem = EventTarget.prototype.removeEventListener;
  const cap = o => typeof o === 'boolean' ? o : !!(o && o.capture);
  EventTarget.prototype.addEventListener = function (type, fn, opts) {
    const n = name(this);
    if (n && fn) {
      let m = seen.get(this); if (!m) { m = new Map(); seen.set(this, m); }
      const k = type + '|' + cap(opts); let s = m.get(k); if (!s) { s = new Set(); m.set(k, s); }
      if (!s.has(fn)) { s.add(fn); const key = n + ' @' + type; reg.listeners[key] = (reg.listeners[key] || 0) + 1; }
    }
    return add.call(this, type, fn, opts);
  };
  EventTarget.prototype.removeEventListener = function (type, fn, opts) {
    const n = name(this);
    if (n && fn) {
      const m = seen.get(this), s = m && m.get(type + '|' + cap(opts));
      if (s && s.has(fn)) { s.delete(fn); reg.listeners[n + ' @' + type]--; }
    }
    return rem.call(this, type, fn, opts);
  };
  for (const kind of ['MutationObserver', 'ResizeObserver', 'IntersectionObserver']) {
    const O = window[kind]; if (!O) continue;
    window[kind] = class extends O { constructor(...a) { super(...a); reg.observers[kind] = (reg.observers[kind] || 0) + 1; } };
  }
  const si = window.setInterval; window.setInterval = function (...a) { reg.intervals++; return si.apply(this, a); };
  window.__reg = reg;
})();"""
SNAP = "() => JSON.parse(JSON.stringify(window.__reg))"
SWAP = """async () => {
  const old = document.querySelector('[data-cm-header]');
  const html = await (await fetch(location.href)).text();
  const fresh = new DOMParser().parseFromString(html, 'text/html');
  window.scrollTo({ top: 0, behavior: 'instant' });
  document.body.replaceChildren(...[...fresh.body.childNodes].map(n => document.adoptNode(n)));
  window.cliMono.init(document);
  const now = document.querySelector('[data-cm-header]');
  return { oldGone: !!old && old.isConnected === false, fresh: !!now && now !== old };
}"""
# `behavior: 'instant'` throughout. <html> sets scroll-behavior: smooth, so a
# bare scrollTo returns while the page is still travelling, and the first
# draft of this control read the header mid-journey and called a working
# header unbound.
STIR = """async () => {
  const frame = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  for (let i = 0; i < 2; i++) {
    window.scrollTo({ top: 400, behavior: 'instant' }); window.dispatchEvent(new Event('scroll')); await frame();
    window.dispatchEvent(new Event('resize')); await frame();
    document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 'Shift', bubbles: true }));
  }
  await new Promise(r => setTimeout(r, 250));
  const h = document.querySelector('[data-cm-header]');
  const scrolled = !!h && h.classList.contains('is-scrolled');
  window.scrollTo({ top: 0, behavior: 'instant' }); window.dispatchEvent(new Event('scroll')); await frame();
  await new Promise(r => setTimeout(r, 120));
  return { scrolled, cleared: !!h && !h.classList.contains('is-scrolled') };
}"""


def total(s):
	return sum(s['listeners'].values())


def grew(a, b):
	keys = set(a['listeners']) | set(b['listeners'])
	d = {k: b['listeners'].get(k, 0) - a['listeners'].get(k, 0) for k in keys}
	return ', '.join('%s %+d' % (k, v) for k, v in sorted(d.items()) if v) or 'nothing'


def run(engine, p):
	fails = []

	def check(ok, what, detail=''):
		if not QUIET:
			print('%s  %-8s %s%s' % ('ok  ' if ok else 'FAIL', engine, what, '' if ok else '  -> ' + detail))
		if not ok:
			fails.append(what)

	browser = getattr(p, engine).launch()
	ctx = browser.new_context(viewport={'width': 1280, 'height': 900})
	ctx.add_init_script(HOOK)
	if JS_OVERRIDE is not None:
		ctx.route('**/_astro/cli-mono.*.js', lambda route: route.fulfill(body=JS_OVERRIDE, content_type='text/javascript'))
	page = ctx.new_page()
	errors = []
	page.on('pageerror', lambda e: errors.append(str(e)[:200]))
	page.goto(URL, wait_until='load', timeout=90000)
	wait_boot(page)
	page.wait_for_timeout(1200)
	boot = page.evaluate(SNAP)
	check(total(boot) >= 10, 'the count sees the runtime (%d long-lived listeners at boot)' % total(boot),
		'only %d counted; the hook is not installed before the runtime' % total(boot))

	for _ in range(3):
		page.evaluate('() => window.cliMono.init(document)')
	page.wait_for_timeout(500)
	again = page.evaluate(SNAP)
	check(total(again) == total(boot), 'init() x3 adds no long-lived listener', grew(boot, again))
	check(again['observers'] == boot['observers'], 'init() x3 constructs no observer',
		'%s -> %s' % (boot['observers'], again['observers']))
	check(again['intervals'] == boot['intervals'], 'init() x3 arms no interval',
		'%d -> %d' % (boot['intervals'], again['intervals']))

	page.evaluate("() => document.dispatchEvent(new Event('astro:page-load'))")
	page.wait_for_timeout(500)
	nav = page.evaluate(SNAP)
	check(total(nav) == total(boot), 'astro:page-load adds no long-lived listener', grew(boot, nav))

	swap = page.evaluate(SWAP)
	check(swap['oldGone'] and swap['fresh'], 'control: the body swap replaced the header', str(swap))
	live = page.evaluate(STIR)
	check(live['scrolled'] and live['cleared'], 'control: the NEW header is bound (takes and drops .is-scrolled)', str(live))
	after = page.evaluate(SNAP)
	check(total(after) == total(boot), 'after a body swap + init(), the count is back to boot (%d)' % total(boot), grew(boot, after))
	check(not errors, 'no page error', '; '.join(errors[:3]))
	browser.close()
	return fails


def main():
	fails = []
	with sync_playwright() as p:
		for engine in ('chromium', 'webkit'):
			fails += run(engine, p)
	print('\n%s' % ('init() is idempotent and releases what it binds' if not fails else '%d check(s) failed' % len(fails)))
	return 1 if fails else 0


if __name__ == '__main__':
	sys.exit(main())
