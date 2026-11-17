#!/usr/bin/env python3
"""
Forced colors: does every state and every painted mark survive the mode?

Windows High Contrast (and the other `forced-colors: active` modes) repaints
every `background-color` to the system canvas, drops every `box-shadow`, and
forces text and borders to the system text colour. A component that says
"selected" with a fill, or draws a meter as a filled box, says nothing at all
in that mode unless it also carries a border, a glyph, or a system colour.

MEASURED on the showcase before this harness existed: 86 elements whose paint
is the whole of their information rendered as nothing (meter and progress
fills, the reading bar, the burger icon, chart legend swatches), and the
selected tab, the pressed segment, the current pager link, the selected
table row and a checked radio were pixel-identical to their unselected
neighbours.

The oracle is a pixel difference, because that is what a person sees, and
because it holds however a state happens to be drawn: a fill, a border, a
glyph, a knob that moves. The harness never needs to know which.

  STATE  flip the state on a live specimen (clear aria-selected, uncheck the
         input, drop the modifier class) and require the picture to change.
  MARK   hide the mark and require the picture to change. A mark whose
         removal changes no pixel was never painted.
  OWN    the same, with the mark's children hidden first, for a mark that
         contains another one or is drawn by its own pseudo-elements.
  READ   a selected surface takes the system selection colours, so every
         piece of text on it is measured against what is behind it. Pixels
         cannot tell selection-coloured text on a plain canvas from the
         right pair; a contrast ratio can. Measured as rendered, and again
         with two children added that real content puts there and a specimen
         may not: text with a colour of its own, and a chip with a fill of
         its own.

Every case is controlled twice over. A NULL flip first: the specimen is
photographed until two consecutive pictures agree, and whatever still moves
is the case's noise floor, measured per case and never assumed. Then the whole sweep with forced colors OFF: a
flip that changes nothing there is a broken case, not a finding, and the run
stops on it. Only then forced colors ON, in a dark and a light system scheme.

A case with no visible specimen FAILS. A check that passes by not running is
how this class of defect stayed invisible.

usage: OEM_UI_URL=http://127.0.0.1:4321/ python3 tests/verify-forced-colors.py
Chromium only: it is the engine that implements forced-colors emulation.
"""
import io
import os
import sys

from PIL import Image, ImageChops
from playwright.sync_api import Error as PlaywrightError, sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness_wait import wait_boot  # noqa: E402

URL = os.environ.get('OEM_UI_URL', 'http://localhost:4321/')
# The full sweep is the default and the only one whose verdict counts. The
# two variables narrow it while iterating on one rule (a mutation sweep runs
# the harness once per mutant).
WIDTHS = tuple(int(w) for w in os.environ.get('OEM_UI_FC_WIDTHS', '1280,390').split(','))
SCHEMES = tuple(os.environ.get('OEM_UI_FC_SCHEMES', 'dark,light').split(','))
# Set by tests/mutate-forced-colors.py to a stylesheet's full text. Every
# .css request is then answered with it, so a mutant is measured without the
# working tree or the build being touched.
CSS_OVERRIDE = None
# Differing pixels needed to call two pictures different, on top of the
# case's own measured noise. A 1px hairline along a 20px control is 20px.
MIN_DIFF = 12
# Levels (0-255) a pixel must move to count, and it is bounded on both sides
# by a measurement. BELOW the faintest state the library draws: a selected
# table row under the pointer is --bg-3 against --panel in the dark theme, 5
# levels apart (two drafts set this bar at 24 and at 5, and each reported a
# working state as an unmeasurable case). ABOVE the rasteriser's own wobble:
# two consecutive pictures of an untouched, focused radio differ by exactly
# 1 level on 8 antialiased pixels of its round focus ring (a draft at 1
# counted those and refused the case as noisy).
LEVELS = 3

# (kind, name, selector, flip). `flip` is JS run with `el` bound; STATE cases
# only. The picture is the element's nearest labelled container, so a control
# drawn by a sibling (the switch track, a custom radio) is inside the frame.
STATE = [
	('tab selected', ".cm-tabs__tab[aria-selected='true']", "el.setAttribute('aria-selected','false')"),
	('segment pressed', ".cm-seg__opt[aria-pressed='true']", "el.setAttribute('aria-pressed','false')"),
	('pager current page', ".cm-pager__link[aria-current='page']", "el.removeAttribute('aria-current')"),
	('table row selected', ".cm-table tbody tr[aria-selected='true']", "el.setAttribute('aria-selected','false')"),
	('list row on', '.cm-row--on', "el.classList.remove('cm-row--on')"),
	('calendar day selected', ".cm-cal__day[aria-selected='true']", "el.setAttribute('aria-selected','false')"),
	('status dot on', '.cm-dot--on', "el.classList.remove('cm-dot--on')"),
	('guild rail current', ".cm-guildrail__item[aria-current='true']", "el.removeAttribute('aria-current')"),
	('guide programme now', '.cm-guide__program--now', "el.classList.remove('cm-guide__program--now')"),
	('step current', '.cm-step.is-current', "el.classList.remove('is-current')"),
	('follow toggle pressed', ".cm-term__follow-toggle[aria-pressed='true']", "el.setAttribute('aria-pressed','false')"),
	('sidebar current page', ".cm-sidebar__link[aria-current='page']", "el.removeAttribute('aria-current')"),
	('radio checked', "input[type='radio']:checked", 'el.checked = false'),
	('checkbox checked', "input[type='checkbox']:checked:not(.cm-switch > input)", 'el.checked = false'),
	('switch on', '.cm-switch > input:checked', 'el.checked = false'),
	('timeline item now', '.cm-timeline__item--now', "el.classList.remove('cm-timeline__item--now')"),
	('carousel current page', ".cm-carousel__page[aria-current='true']", "el.removeAttribute('aria-current')"),
]
MARK = [
	('meter fill', '.cm-meter:not(.cm-meter--accent):not(.cm-meter--faint) .cm-meter__fill'),
	('meter fill, accent', '.cm-meter--accent .cm-meter__fill'),
	('meter fill, faint', '.cm-meter--faint .cm-meter__fill'),
	('progress fill', '.cm-progress__fill'),
	('reading bar fill', '.cm-readbar--spec .cm-readbar__fill'),
	('quiz progress bar', '.cm-quiz__bar'),
	('burger bar', '.cm-nav-toggle__bar'),
	('terminal cursor', '.cm-cursor'),
	('guide now line', '.cm-guide__now-line'),
	# 40 of its 64 px, not the default floor. Unpainted, this dot still
	# changed 13 px when hidden: it sits on the corner of its item and was a
	# canvas-coloured notch in the item's border. A notch is not a dot.
	('guild rail unread dot', '.cm-guildrail__unread', 40),
	('spacing specimen bar', '.cm-spec__bar'),
]
# A mark's OWN paint, with its children hidden first. The switch track holds
# the knob, so hiding the track alone always changes the picture (the knob
# goes with it) and says nothing about whether the track itself was drawn.
OWN = [
	('switch track frame, off', '.cm-switch > input:not(:checked) ~ .cm-switch__track'),
	('switch track frame, on', '.cm-switch > input:checked ~ .cm-switch__track'),
	# Two of the burger's three bars are pseudo-elements of this wrapper, 36
	# px each. The floor sits between one and two, so losing either fails.
	('burger edge bars', '.cm-nav-toggle__bars', 60),
]
# The surfaces that take the selection pair. Every text-bearing element on
# one, the surface included, must read at 4.5:1 against what is behind it.
READ = [
	('tab selected', ".cm-tabs__tab[aria-selected='true']"),
	('segment pressed', ".cm-seg__opt[aria-pressed='true']"),
	('pager current page', ".cm-pager__link[aria-current='page']"),
	('calendar day selected', ".cm-cal__day[aria-selected='true']"),
	('guide programme now', '.cm-guide__program--now'),
	('guild rail current', ".cm-guildrail__item[aria-current='true']"),
	('follow toggle pressed', ".cm-term__follow-toggle[aria-pressed='true']"),
	('step current marker', '.cm-step.is-current .cm-step__marker'),
	('list row on', '.cm-row--on'),
	('table row selected', ".cm-table tbody tr[aria-selected='true'] td"),
]
READ_PICK = """([sel]) => {
  document.querySelectorAll('[data-fc-read]').forEach(n => n.removeAttribute('data-fc-read'));
  for (const el of document.querySelectorAll(sel)) {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1 || el.closest('dialog:not([open]), [popover]:not(:popover-open), [hidden], [inert]')) continue;
    el.setAttribute('data-fc-read', '');
    el.scrollIntoView({ block: 'center', inline: 'nearest' });
    return true;
  }
  return false;
}"""
READ_JS = """([probe]) => {
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const rgb = s => { const m = s.match(/[\\d.]+/g).map(Number); return m.length > 3 && m[3] === 0 ? null : m; };
  const behind = e => { for (let n = e; n; n = n.parentElement) { const c = rgb(getComputedStyle(n).backgroundColor); if (c) return c; } return [255, 255, 255]; };
  const host = document.querySelector('[data-fc-read]');
  if (!host) return null;
  const added = [];
  if (probe) {
    // Text with an author colour (the host's own, so it reads with forced
    // colors off) and no fill; then an element with a fill of its own.
    const t = document.createElement('span'); t.textContent = 'probe'; t.style.color = getComputedStyle(host).color;
    host.appendChild(t); added.push(t);
    // <code> carries a fill of its own in base.css. With forced colors off
    // that is checked, so the probe cannot quietly stop being a filled one.
    const c = document.createElement('code'); c.textContent = 'probe'; host.appendChild(c); added.push(c);
    if (!matchMedia('(forced-colors: active)').matches && !rgb(getComputedStyle(c).backgroundColor)) {
      added.forEach(n => n.remove());
      return { ratio: 0, what: 'code probe', fg: 'has no fill of its own, so it probes nothing', bg: 'n/a' };
    }
  }
  let worst = null;
  for (const el of [host, ...host.querySelectorAll('*')]) {
    if (![...el.childNodes].some(n => n.nodeType === 3 && n.nodeValue.trim())) continue;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none') continue;
    const fg = rgb(s.color), bg = behind(el);
    if (!fg) continue;
    const a = lum(fg), b = lum(bg), ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    if (!worst || ratio < worst.ratio) worst = { ratio, what: el.tagName.toLowerCase() + (el.classList.length ? '.' + el.classList[0] : ''), fg: s.color, bg: 'rgb(' + bg.slice(0, 3).join(', ') + ')' };
  }
  added.forEach(n => n.remove());
  return worst;
}"""

PICK = """([sel]) => {
  for (const el of document.querySelectorAll(sel)) {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    if (el.checkVisibility && !el.checkVisibility({ visibilityProperty: true, opacityProperty: false })) continue;
    if (el.closest('dialog:not([open]), [popover]:not(:popover-open), [hidden], [inert]')) continue;
    document.querySelectorAll('[data-fc-pick]').forEach(n => n.removeAttribute('data-fc-pick'));
    document.querySelectorAll('[data-fc-frame]').forEach(n => n.removeAttribute('data-fc-frame'));
    el.setAttribute('data-fc-pick', '');
    // The frame is what gets photographed. An input is drawn by its label
    // (or by a sibling inside it); a mark is photographed with its parent so
    // the place it SHOULD occupy is in the picture.
    let frame = el.matches('input') ? (el.closest('label') || el.parentElement) : el;
    if (frame === el && el.parentElement && (el.matches('span, div') && r.width * r.height < 40000)) frame = el.parentElement;
    frame.setAttribute('data-fc-frame', '');
    frame.scrollIntoView({ block: 'center', inline: 'nearest' });
    return true;
  }
  return false;
}"""


def diff_pixels(a, b):
	ia = Image.open(io.BytesIO(a)).convert('RGB')
	ib = Image.open(io.BytesIO(b)).convert('RGB')
	if ia.size != ib.size:
		return max(ia.size[0] * ia.size[1], ib.size[0] * ib.size[1])
	box = ImageChops.difference(ia, ib).convert('L').point(lambda v: 255 if v >= LEVELS else 0)
	return box.histogram()[255]


def stable_shot(page, frame):
	"""Photograph until two consecutive pictures agree. Returns (png, noise).

	A fixed wait guessed wrong in both directions here: a specimen scrolled
	into view for the first time was still painting (22,049 px moved between
	two shots of an untouched timeline row), and a longer fixed wait only
	moved which case caught it. Waiting for the picture to stop changing is
	the only wait that is right on a busy box and a fast one alike. A picture
	that never settles returns its last difference, and the control refuses
	the case on it.
	"""
	a = frame.screenshot(animations='disabled', caret='hide')
	n = 0
	for _ in range(12):
		b = frame.screenshot(animations='disabled', caret='hide')
		n = diff_pixels(a, b)
		if n == 0:
			return b, 0
		a = b
		page.wait_for_timeout(80)
	return a, n


def settle(page):
	page.evaluate('() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(r, 60))))')


SNAP = """() => {
  const el = document.querySelector('[data-fc-pick]');
  window.__fc = { attrs: Object.fromEntries(el.getAttributeNames().map(n => [n, el.getAttribute(n)])), checked: el.checked,
                  kids: [...el.children].map(c => c.getAttribute('style')) };
}"""
RESTORE = """() => {
  const el = document.querySelector('[data-fc-pick]');
  for (const n of el.getAttributeNames()) if (!(n in window.__fc.attrs)) el.removeAttribute(n);
  for (const [n, v] of Object.entries(window.__fc.attrs)) el.setAttribute(n, v);
  if (typeof window.__fc.checked === 'boolean') el.checked = window.__fc.checked;
  [...el.children].forEach((c, i) => { const v = window.__fc.kids[i]; if (v == null) c.removeAttribute('style'); else c.setAttribute('style', v); });
}"""


def run_case(page, kind, sel, flip, pose=None):
	"""Returns (noise, differing_pixels), or None with nothing to measure.

	pose is None, 'hover' or 'focus': the state is measured while the
	specimen is pointed at or keyboard-focused. A hover rule is usually a
	longer selector than the state rule, so it is where a state that
	survives at rest gets repainted away.
	"""
	if not page.evaluate(PICK, [sel]):
		return None
	settle(page)
	frame = page.locator('[data-fc-frame]').first
	page.evaluate(SNAP)
	if pose == 'hover':
		# Clipped by its own scroller at this width (the sidebar specimen on
		# a phone): the pointer cannot reach it, so there is no hover to
		# measure here. The other width still has to.
		try:
			page.locator('[data-fc-pick]').first.hover(force=True, timeout=5000)
		except PlaywrightError:
			return None
	elif pose == 'focus':
		# Not focusable (a table row, a list item): nothing to measure.
		if not page.evaluate('() => { const el = document.querySelector("[data-fc-pick]"); el.focus({ preventScroll: true }); return document.activeElement === el; }'):
			return None
	if kind == 'own':
		page.evaluate('() => { for (const c of document.querySelector("[data-fc-pick]").children) c.style.setProperty("visibility", "hidden", "important"); }')
	# After the pose, not before it: the focus ring arrives a frame late, and
	# without this the null flip caught it mid-arrival (12 px of "noise" on a
	# focused radio) and the control refused the case.
	settle(page)
	before, noise = stable_shot(page, frame)
	if kind == 'state':
		page.evaluate('(js) => { const el = document.querySelector("[data-fc-pick]"); (new Function("el", js))(el); }', flip)
	else:
		page.evaluate('() => { document.querySelector("[data-fc-pick]").style.setProperty("visibility", "hidden", "important"); }')
	settle(page)
	after, moving = stable_shot(page, frame)
	noise = max(noise, moving)
	# Put the specimen back: the page is shared by every case at this width.
	page.evaluate(RESTORE)
	if pose == 'hover':
		page.mouse.move(0, 0)
	elif pose == 'focus':
		page.evaluate('() => document.activeElement && document.activeElement.blur()')
	return noise, diff_pixels(before, after)


def read_case(page, sel, probe, pose):
	"""The worst text contrast on the surface, or None with nothing to measure."""
	if not page.evaluate(READ_PICK, [sel]):
		return None
	host = page.locator('[data-fc-read]').first
	if pose == 'hover':
		try:
			host.hover(force=True, timeout=5000)
		except PlaywrightError:
			return None
	elif pose == 'focus':
		if not host.evaluate('el => { el.focus({ preventScroll: true }); return document.activeElement === el; }'):
			return None
	settle(page)
	got = page.evaluate(READ_JS, [probe])
	if pose == 'hover':
		page.mouse.move(0, 0)
	elif pose == 'focus':
		page.evaluate('() => document.activeElement && document.activeElement.blur()')
	return got


def sweep(browser, forced, scheme):
	"""name -> (noise, px) from the width where the flip shows most, or None if never seen."""
	best = {}
	for width in WIDTHS:
		ctx = browser.new_context(viewport={'width': width, 'height': 900}, reduced_motion='reduce',
			forced_colors='active' if forced else 'none', color_scheme=scheme)
		if CSS_OVERRIDE is not None:
			ctx.route('**/*.css', lambda route: route.fulfill(body=CSS_OVERRIDE, content_type='text/css'))
		page = ctx.new_page()
		page.goto(URL, wait_until='load', timeout=90000)
		wait_boot(page)
		for kind, cases, pose in PLAN:
			for name, sel, flip in cases:
				name = name + (' (%s)' % pose if pose else '')
				got = run_case(page, kind, sel, flip, pose)
				if got is None:
					best.setdefault(name, None)
				elif best.get(name) is None or got[1] - got[0] > best[name][1] - best[name][0]:
					best[name] = got
		# Posed as well as at rest, for the reason the states are: a hover
		# rule that outranks the selection takes the text colour with it.
		for probe, prefix, pose in ((False, 'reads: ', None), (True, 'reads with content: ', None),
				(False, 'reads: ', 'hover'), (False, 'reads: ', 'focus')):
			for name, sel in READ:
				# The WORST ratio across the widths is the verdict: text has
				# to read at every width, where a state only has to show at one.
				name = prefix + name + (' (%s)' % pose if pose else '')
				got = read_case(page, sel, probe, pose)
				if got is None:
					best.setdefault(name, None)
				elif best.get(name) is None or got['ratio'] < best[name]['ratio']:
					best[name] = got
		ctx.close()
	return best


PLAN = (
	('state', STATE, None),
	('state', STATE, 'hover'),
	('state', STATE, 'focus'),
	('mark', [(m[0], m[1], None) for m in MARK], None),
	('own', [(m[0], m[1], None) for m in OWN], None),
)


FLOOR = {m[0]: m[2] for m in MARK + OWN if len(m) > 2}


def differs(got, name=''):
	if isinstance(got, dict):
		return got['ratio'] >= 4.5
	return got is not None and got[1] - got[0] >= FLOOR.get(name, MIN_DIFF)


def describe(got):
	if got is None:
		return 'no visible specimen'
	if isinstance(got, dict):
		return '%.2f:1 worst, %s %s on %s' % (got['ratio'], got['what'], got['fg'], got['bg'])
	return '%d px differ' % got[1]


def main():
	failures = 0
	with sync_playwright() as p:
		browser = p.chromium.launch()
		control = sweep(browser, forced=False, scheme='dark')
		# A resting case with no specimen is broken. A posed case with none
		# (a table row cannot take focus) is simply not applicable, and is
		# dropped here, by the control, before any verdict is read.
		names = [n for n in control if not (control[n] is None and n.endswith(')'))]
		skipped = sorted(n for n in control if n not in names)
		noisy = lambda g: isinstance(g, tuple) and g[0] >= MIN_DIFF
		broken = [n for n in names if not differs(control.get(n), n) or noisy(control[n])]
		if broken:
			for n in broken:
				got = control.get(n)
				why = ('no visible specimen on the page' if got is None else
					'unreadable with forced colors OFF: ' + describe(got) if isinstance(got, dict) else
					'two pictures of the untouched specimen differ by %d px' % got[0] if noisy(got) else
					'the flip changes %d px with forced colors OFF' % got[1])
				print('BROKEN CASE  %-34s %s' % (n, why))
			print('\n%d case(s) cannot measure anything; fix the harness or the specimen before reading a verdict' % len(broken))
			browser.close()
			return 2
		print('control (forced colors off): all %d cases measure, noise floor %d px' % (
			len(names), max(control[n][0] for n in names if isinstance(control[n], tuple))))
		print('not applicable (cannot take that pose): %s' % (', '.join(skipped) or 'none'))
		for scheme in SCHEMES:
			got = sweep(browser, forced=True, scheme=scheme)
			for n in names:
				ok = differs(got.get(n), n)
				failures += 0 if ok else 1
				print('%s  forced/%-5s %-34s %s' % ('ok  ' if ok else 'FAIL', scheme, n, describe(got.get(n))))
		browser.close()
	total = len(SCHEMES) * len(names)
	print('\n%d/%d forced-colors checks passed' % (total - failures, total))
	return 1 if failures else 0


if __name__ == '__main__':
	sys.exit(main())
