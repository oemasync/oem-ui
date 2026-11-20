#!/usr/bin/env python3
"""
Mutation sweep for init() idempotence and listener release.

tests/verify-init-idempotent.py says the runtime binds once and lets go.
This says each guard and each routed listener is what makes that true: it
removes them one at a time and requires the harness to fail by name.

  - the four re-bind guards (header, scroll spy, measure readout, nav menu)
  - the release itself, both ways: the sweep init() runs, and the listener
    that removes itself when it fires with its owner gone
  - every cmWhileConnected call site, put back to a bare addEventListener

A mutant is never written to disk. The source is edited in memory, wrapped
the way the build wraps it, and served in place of the built chunk.

Three mutants cannot be killed by the engine harness and are listed below
with the reason. Two are the fallbacks for a browser with no ResizeObserver,
and no engine this harness can launch lacks one. The third is the release on
fire, which the sweep in init() makes invisible on a page that re-inits.
`npm test` kills all three.

usage: OEM_UI_URL=http://127.0.0.1:4321/ python3 tests/mutate-init-idempotent.py
       (build first; OEM_UI_MUT_JOBS sets the worker count, default 4)
exit:  0 every mutant killed or expected, 1 otherwise, 2 the sweep could not run
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

# label fragment -> why the engine harness cannot kill it. Each one is killed
# by `npm test` instead, which is checked by hand when this list changes.
UNREACHABLE = {
	"cmWhileConnected(header, window, 'resize'": 'the header fallback for a browser with no ResizeObserver',
	"cmWhileConnected(box, window, 'resize'": 'the chart fallback for a browser with no ResizeObserver',
	'the release on fire is disabled': "init() sweeps first, so the page ends clean either way; npm test fires a listener for a removed element with no init() in between",
}


def harness():
	spec = importlib.util.spec_from_file_location('verify_init_idempotent', os.path.join(HERE, 'verify-init-idempotent.py'))
	mod = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(mod)
	return mod


def wrap(source):
	"""The source runtime, wrapped the way the build wraps it, under the same export name."""
	hits = glob.glob(os.path.join(ROOT, 'dist', '_astro', 'cli-mono.*.js'))
	if len(hits) != 1:
		sys.exit('expected exactly one built runtime chunk, found %d; run the build' % len(hits))
	m = re.search(r'export\{(\w+) as (\w+)\};?\s*$', open(hits[0]).read())
	if not m:
		sys.exit('the built chunk no longer ends in a single named export; the wrapper below is stale')
	return ('var __rt=((fn,m)=>()=>(m||(fn((m={exports:{}}).exports,m),fn=null),m.exports))'
		'((exports,module)=>{\n' + source + '\n});export{__rt as ' + m.group(2) + '};')


def once(source, old, new, label):
	if source.count(old) != 1:
		sys.exit('mutant %r: its pattern matches %d times, want exactly 1; the sweep is stale' % (label, source.count(old)))
	return label, source.replace(old, new)


def mutants(source):
	out = [
		once(source, "if (owner.isConnected === false) {\n\t\t\t\tcmRelease(rec);", "if (false) {\n\t\t\t\tcmRelease(rec);", 'the release on fire is disabled'),
		once(source, '\t\tcmReleaseGone();\n', '', 'init() no longer sweeps listeners whose owner is gone'),
		once(source, 'if (header.__cmHeaderBound) return;', '', 'drop the header re-bind guard'),
		once(source, 'if (nav.__cmSpyRefresh) {', 'if (false) {', 'drop the scroll-spy re-bind guard'),
		once(source, 'if (spec.__cmMeasure) {', 'if (false) {', 'drop the measure-readout re-bind guard'),
		once(source, 'if (bar.__cmNavSpied) {', 'if (false) {', 'drop the navigation-menu re-bind guard'),
	]
	call = re.compile(r'cmWhileConnected\(\s*([^,()]+),\s*([^,()]+(?:\|\|[^,()]+)?),\s*')
	sites = [m for m in call.finditer(source) if not source[:m.start()].rstrip().endswith('function')]
	for m in sites:
		target = m.group(2).strip()
		target = '(%s)' % target if '||' in target else target
		shown = re.sub(r'\s+', ' ', source[m.start():m.end() + 12])
		line = source[:m.start()].count('\n') + 1
		out.append(('bare listener at line %d: %s' % (line, shown),
			source[:m.start()] + target + '.addEventListener(' + source[m.end():]))
	return out, len(sites)


def run_one(job):
	label, source = job
	from playwright.sync_api import sync_playwright
	h = harness()
	h.JS_OVERRIDE = wrap(source)
	h.QUIET = True
	with sync_playwright() as p:
		fails = h.run('chromium', p)
	return label, fails


def main():
	source = open(os.path.join(ROOT, 'src', 'js', 'cli-mono.js')).read()
	jobs, sites = mutants(source)
	if sites < 15:
		print('only %d cmWhileConnected call sites found; the parser is not reading the runtime' % sites)
		return 2
	_, baseline = run_one(('baseline', source))
	if baseline:
		print('the unmutated source already fails through the override path: %s' % ', '.join(baseline))
		return 2
	print('baseline green through the override path; %d mutants (%d call sites), %d at a time\n' % (len(jobs), sites, JOBS))
	bad = 0
	with ProcessPoolExecutor(max_workers=JOBS) as pool:
		for label, fails in pool.map(run_one, jobs):
			reason = next((why for frag, why in UNREACHABLE.items() if frag in label), None)
			if fails and reason:
				bad += 1
				print('STALE     %s\n            listed as unreachable, but it was killed by: %s' % (label, ', '.join(fails)))
			elif fails:
				print('killed    %s\n            by: %s' % (label, ', '.join(fails)))
			elif reason:
				print('expected  %s\n            no engine reaches it: %s' % (label, reason))
			else:
				bad += 1
				print('SURVIVED  %s' % label)
	print('\n%d mutants, %d unaccounted for' % (len(jobs), bad))
	return 1 if bad else 0


if __name__ == '__main__':
	sys.exit(main())
