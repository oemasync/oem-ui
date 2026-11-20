#!/usr/bin/env python3
"""
Mutation sweep for the forced-colors rules.

tests/verify-forced-colors.py says the rules work. This says each one is
load-bearing: it removes every selector, every declaration and every
`!important` from the forced-colors blocks, one at a time, and requires the
harness to fail BY NAME for each. A rule nothing fails without is a rule
nothing proves, and it does not belong in the sheet.

The mutant is never written to disk. The built stylesheet is read from dist,
edited in memory, and handed to the browser in place of the real one, so the
working tree is not touched and the mutants can run side by side.

usage: OEM_UI_URL=http://127.0.0.1:4321/ python3 tests/mutate-forced-colors.py
       (build first; OEM_UI_MUT_JOBS sets the worker count, default 4)
       OEM_UI_MUT_ONLY=text runs only the mutants whose label contains it,
       for iterating on one rule; the verdict is the full sweep.
exit:  0 every mutant killed, 1 a mutant survived, 2 the sweep could not run
"""
import glob
import importlib.util
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
JOBS = int(os.environ.get('OEM_UI_MUT_JOBS', '4'))


def harness():
	spec = importlib.util.spec_from_file_location('verify_forced_colors', os.path.join(HERE, 'verify-forced-colors.py'))
	mod = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(mod)
	return mod


def built_css():
	hits = [p for p in glob.glob(os.path.join(ROOT, 'dist', '_astro', '*.css')) if 'forced-colors' in open(p).read()]
	if len(hits) != 1:
		sys.exit('expected exactly one built stylesheet with a forced-colors block, found %d; run the build' % len(hits))
	return open(hits[0]).read()


def blocks(css):
	"""[(start, end)] of the BODY of every forced-colors media block."""
	out = []
	for m in re.finditer(r'@media\s*\(forced-colors:\s*active\)\s*\{', css):
		depth, i = 1, m.end()
		while depth:
			depth += {'{': 1, '}': -1}.get(css[i], 0)
			i += 1
		out.append((m.end(), i - 1))
	return out


def split_top(text, sep):
	"""Split on sep, ignoring any inside (), [] or quotes."""
	parts, depth, quote, cur = [], 0, '', ''
	for ch in text:
		if quote:
			quote = '' if ch == quote else quote
		elif ch in '"\'':
			quote = ch
		elif ch in '([':
			depth += 1
		elif ch in ')]':
			depth -= 1
		if ch == sep and not depth and not quote:
			parts.append(cur)
			cur = ''
		else:
			cur += ch
	parts.append(cur)
	return parts


def mutants(css):
	"""[(label, mutated css)]. One edit each, all inside a forced-colors block."""
	out = []
	for start, end in blocks(css):
		for rule in re.finditer(r'([^{}]+)\{([^{}]*)\}', css[start:end]):
			sels = split_top(rule.group(1), ',')
			decls = [d for d in split_top(rule.group(2), ';') if d.strip()]
			a, b = start + rule.start(), start + rule.end()

			def emit(label, new_sels, new_decls):
				body = (','.join(new_sels) + '{' + ';'.join(new_decls) + '}') if new_sels and new_decls else ''
				out.append((label, css[:a] + body + css[b:]))

			for i, sel in enumerate(sels):
				emit('drop selector  %s' % sel.strip(), sels[:i] + sels[i + 1:], decls)
				# `:where(a, b, c) rest` is one selector to the comma split
				# above and ten surfaces to a reader. Drop each one in turn.
				inner = re.match(r'^(\s*:where\()(.*)(\).*)$', sel, re.S)
				if inner:
					args = split_top(inner.group(2), ',')
					for j, arg in enumerate(args):
						if len(args) > 1:
							emit('drop from :where()  %s' % arg.strip(),
								sels[:i] + [inner.group(1) + ','.join(args[:j] + args[j + 1:]) + inner.group(3)] + sels[i + 1:], decls)
			for i, decl in enumerate(decls):
				emit('drop declaration  %s  (%s ...)' % (decl.strip(), sels[0].strip()), sels, decls[:i] + decls[i + 1:])
				if '!important' in decl:
					emit('drop !important  %s  (%s ...)' % (decl.strip(), sels[0].strip()), sels,
						decls[:i] + [decl.replace('!important', '')] + decls[i + 1:])
	return out


def run_one(job):
	label, css = job
	from playwright.sync_api import sync_playwright
	h = harness()
	h.CSS_OVERRIDE = css
	h.SCHEMES = ('dark',)
	with sync_playwright() as p:
		browser = p.chromium.launch()
		got = h.sweep(browser, forced=True, scheme='dark')
		browser.close()
	failed = sorted(n for n in got if not h.differs(got[n], n))
	return label, failed, [n for n in failed if got[n] is None]


def main():
	css = built_css()
	jobs = mutants(css)
	only = os.environ.get('OEM_UI_MUT_ONLY')
	if only:
		# Iterating on one rule. A partial sweep is never the verdict.
		jobs = [j for j in jobs if only in j[0]]
		print('PARTIAL sweep, %d mutant(s) matching %r' % (len(jobs), only))
	elif len(jobs) < 20:
		print('only %d mutants generated; the parser is not reading the block' % len(jobs))
		return 2
	# The unmutated sheet through the SAME path, first. The only cases it may
	# fail are the ones with nothing to measure (a table row cannot take
	# focus), and a mutant is killed only by a case that passes here.
	_, baseline, absent = run_one(('baseline', css))
	real = [n for n in baseline if n not in absent]
	if real:
		print('the unmutated build already fails: %s' % ', '.join(real))
		return 2
	print('baseline green through the override path; %d mutants, %d at a time\n' % (len(jobs), JOBS))
	survived = 0
	with ProcessPoolExecutor(max_workers=JOBS) as pool:
		for label, failed, _ in pool.map(run_one, jobs):
			killers = [n for n in failed if n not in baseline]
			if killers:
				print('killed    %s\n            by: %s' % (label, ', '.join(killers[:6]) + (' (+%d more)' % (len(killers) - 6) if len(killers) > 6 else '')))
			else:
				survived += 1
				print('SURVIVED  %s' % label)
	print('\n%d mutants, %d killed, %d survived' % (len(jobs), len(jobs) - survived, survived))
	return 1 if survived else 0


if __name__ == '__main__':
	sys.exit(main())
