#!/usr/bin/env node
/**
 * mutation: cmInitAgo, the relative-time runtime
 *
 * Every assertion added this cycle is a guess until it has been made to
 * fail. This harness breaks the exact thing each check guards, runs the
 * suite, and reports which check fired. The ago checks execute the
 * runtime source in a VM with an injectable clock and read the source
 * and the showcase by name, so skipBuild keeps the sweep fast - the
 * built page is measured separately by measure-ago-webkit.py.
 *
 * A pattern that no longer matches the source is a NO-OP - a failure of
 * THIS file, never a pass. The count reported in the cycle note must
 * have zero in it, or the harness itself is broken and the number is
 * worthless.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const p = (f) => join(root, f);
const JS = 'src/js/cli-mono.js';
const SHOW = 'src/pages/[...family].astro';

const MUTATIONS = [
	{
		// The sub-minute floor. Widening it from 10s to 60s makes a 45s
		// gap read "now" - the seconds row in the showcase would freeze
		// for a full minute after every reload.
		name: 'the ago sub-minute floor swallows the seconds case',
		file: JS,
		from: /\t\tif \(d < 10000\) return 'now';/,
		to: "\t\tif (d < 60000) return 'now';",
		expectFail: 'must read "45s ago"',
		skipBuild: true,
	},
	{
		// The week unit. Without it a 10-day gap cascades down to "10d
		// ago" - the unit ramp is the whole point of the pure form, and a
		// missing rung reads wrong at exactly the gaps posts age through.
		name: 'the ago week unit is deleted from the ramp',
		file: JS,
		from: /\t\t\t\[31557600000, 'y'\], \[2592000000, 'mo'\], \[604800000, 'w'\],\n\t\t\t\[86400000, 'd'\]/,
		to: "\t\t\t[31557600000, 'y'], [2592000000, 'mo'],\n\t\t\t[86400000, 'd']",
		expectFail: 'must read "1w ago"',
		skipBuild: true,
	},
	{
		// The future-date guard. Without it a future timestamp walks the
		// relative ramp with a negative gap, lands under the 10s floor,
		// and reads "now" - an inverted read the absolute branch exists
		// to prevent (timezone edges, scheduled posts).
		name: 'the ago future-date guard is deleted',
		file: JS,
		from: /\t\tif \(ts > now\) return cmAgoShort\(ts\);\n/,
		to: '',
		expectFail: 'the absolute form must carry a digit',
		skipBuild: true,
	},
	{
		// The title. The visible text is relative; the full date must ride
		// on title so hover or focus answers "which day exactly". A title
		// that copies the visible text answers neither question.
		name: 'the ago title copies the visible text instead of the full date',
		file: JS,
		from: /\t\t\t\t\tel\.setAttribute\('title', cmAgoShort\(ts\)\);/,
		to: "\t\t\t\t\tel.setAttribute('title', el.textContent);",
		expectFail: 'the full date (a 4-digit year is the fingerprint)',
		skipBuild: true,
	},
	{
		// The shared clock. The paint must read CM_AGNO_NOW() - the
		// injectable module clock - not Date.now() inline. A hard-coded
		// wall clock makes the pinned-clock test vacuous: the label
		// ignores the clock a consumer (or a test) swapped in.
		name: 'the ago paint hard-codes Date.now() instead of the shared clock',
		file: JS,
		from: /\t\t\t\t\tel\.textContent = cmAgoText\(ts, CM_AGNO_NOW\(\)\);/,
		to: "\t\t\t\t\tel.textContent = cmAgoText(ts, Date.now());",
		expectFail: 'the bound time must read "5m ago"',
		skipBuild: true,
	},
	{
		// The one-arm guard. Without it a re-init (watchForLateMarkup
		// arms, the consumer calls init again after a commit) stacks a
		// second interval on the first - two timers doing one job.
		name: 'the ago timer guard is deleted',
		file: JS,
		from: /\t\tif \(CM_AGNO_TIMER !== null\) return;\n/,
		to: '',
		expectFail: 'must be guarded so a re-init never arms a second interval',
		skipBuild: true,
	},
	{
		// The repeat. One-shot instead of repeating: the label paints
		// once and then stands still, which is the frozen-specimen
		// defect the shared 30s interval exists to prevent.
		name: 'the ago shared interval becomes one-shot',
		file: JS,
		from: /\t\tCM_AGNO_TIMER = setInterval\(function \(\) \{/,
		to: "\t\tCM_AGNO_TIMER = window.setTimeout(function () {",
		expectFail: 'must be one module-level setInterval',
		skipBuild: true,
	},
	{
		// The wiring. init() is the contract every consumer page gets; a
		// capability that exists but is never called is a library that
		// owns nothing.
		name: 'init never calls cmInitAgo',
		file: JS,
		from: /\t\tcmInitAgo\(root\);\n/,
		to: '',
		expectFail: 'init must call cmInitAgo(root)',
		skipBuild: true,
	},
	{
		// The demonstration. A runtime that is only ever read in the
		// source is a promise, not a product; the showcase specimen is
		// the proof it renders in its intended context.
		name: 'the relative-time specimen is removed from the showcase',
		file: SHOW,
		from: /<h3 class="cm-kicker">relative time<\/h3>[\s\S]*?<\/div>\s*\n\s*<h3 class="cm-kicker">media<\/h3>/,
		to: '<h3 class="cm-kicker">media</h3>',
		expectFail: 'relative-time specimens',
		skipBuild: true,
	},
];

const runSuite = () => {
	const r = spawnSync('node', [join(root, 'tests/run.mjs')], { encoding: 'utf8' });
	return r.stdout || '';
};

let caught = 0, missed = 0, noop = 0;
for (const mut of MUTATIONS) {
	const file = p(mut.file);
	const orig = readFileSync(file, 'utf8');
	const mutated = orig.replace(mut.from, mut.to);
	if (mutated === orig) {
		noop++;
		console.log(`NO-OP  ${mut.name}\n       pattern did not match ${mut.file} - FIX THE HARNESS`);
		continue;
	}
	writeFileSync(file, mutated);
	try {
		const out = runSuite();
		if (out.includes(mut.expectFail) && /FAIL/.test(out)) {
			caught++;
			console.log(`caught ${mut.name}\n       -> ${mut.expectFail}`);
		} else {
			missed++;
			console.log(`MISSED ${mut.name}\n       expected: ${mut.expectFail}`);
		}
	} finally {
		writeFileSync(file, orig);
	}
}
console.log(`\n${MUTATIONS.length} mutations: ${caught} caught, ${missed} missed, ${noop} no-op`);
if (noop) process.exit(2);
process.exit(missed ? 1 : 0);
