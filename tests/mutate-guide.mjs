#!/usr/bin/env node
/**
 * mutation: cm-guide — the EPG guide grid (batch 36)
 *
 * Every assertion in the batch-36 block of tests/run.mjs is a guess
 * until it has been made to fail. This harness breaks the exact thing
 * each check guards, runs the suite, and reports which check fired.
 *
 * A pattern that no longer matches the source is a NO-OP — a failure of
 * THIS file, never a pass. The cycle note must report zero no-ops, or
 * the harness is broken and its caught-count is worthless.
 *
 * All mutations target files the batch-36 checks read directly
 * (components.css, the showcase, the README), so no astro build is
 * needed between mutants — which is what keeps the cycle quick.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const p = (f) => join(root, f);
const COMP = 'src/styles/components.css';
const SHOW = 'src/pages/[...family].astro';
const README = 'README.md';

const MUTATIONS = [
	{
		// The grid must be a real CSS grid — a table or flex fallback
		// cannot place a program across fractional time columns.
		name: 'the guide grid stops using display: grid',
		file: COMP,
		from: /\.cm-guide \{[^}]*display: grid;/,
		to: (m) => m.replace(/display: grid;/, 'display: block;'),
		expectFail: '.cm-guide does not use display: grid',
		skipBuild: true,
	},
	{
		// The now-line must be a LOGICAL property, or it breaks in RTL.
		// The check reads the whole file, so the mutant must remove the
		// last logical declaration, not merely add a physical one.
		name: 'the now-line uses a physical left instead of logical',
		file: COMP,
		from: /inset-inline-start:\s*var\(--guide-now-x[^;]*;\s*/g,
		to: 'left: var(--guide-now-x, 9.5rem);\n	',
		expectFail: 'the now-line uses a physical directional property (left/right) instead of logical',
		skipBuild: true,
	},
	{
		// A missing runtime var must not delete the line entirely.
		name: 'the now-line loses its fallback for a missing var',
		file: COMP,
		from: /var\(--guide-now-x,\s*[^)]+\)/,
		to: 'var(--guide-now-x)',
		expectFail: '--guide-now-x has no fallback; a missing runtime var breaks the now-line',
		skipBuild: true,
	},
	{
		// One program cell proves nothing about grid geometry; there
		// must be at least two so columns and rows are exercised. The
		// /g flag is load-bearing: without it only ONE cell is removed
		// and the check still sees ten substrings.
		name: 'the specimen drops all the program cells',
		file: SHOW,
		from: /<div class="cm-guide__program[^>]*>[\s\S]*?<\/div>/g,
		to: '',
		expectFail: /the specimen has only \d+ program cell\(s\); the grid geometry is unproven/,
		skipBuild: true,
	},
	{
		// The --now variant is what carries "you are here"; without a
		// specimen using it the variant is unproven.
		name: 'the specimen has no --now program',
		file: SHOW,
		// /g: there are two --now cells; removing one leaves the other.
		from: /cm-guide__program cm-guide__program--now/g,
		to: 'cm-guide__program',
		expectFail: 'the specimen has no cm-guide__program--now; the variant is unproven',
		skipBuild: true,
	},
	{
		// The mobile agenda fallback must engage at the phone
		// breakpoint; without it the grid is squeezed on a phone.
		name: 'the mobile fallback breakpoint is removed',
		file: COMP,
		// /g: the file's first 640px block belongs to another component;
		// hitting every one guarantees the guide's own block goes too,
		// which is what the (scoped) batch-36 check reads.
		from: /@media[^{]*max-width:\s*640px[^{]*\{/g,
		to: '@media (max-width: 9999px) {',
		expectFail: 'the mobile fallback is not at 640px, so the grid is squeezed on a phone',
		skipBuild: true,
	},

	{		// A class the app styles against must be rendered, or the
		// specimen is lying about what ships.
		name: 'the now-line is dropped from the specimen markup',
		file: SHOW,
		from: /class="cm-guide__now-line"/,
		to: 'class="guide-now-line"',
		expectFail: /\.cm-guide__now-line is defined but never rendered|defined but never rendered in the specimen/,
		skipBuild: true,
	},
	{
		// A component the docs never name is one a consumer reinvents.
		name: 'the README guide section is deleted',
		file: README,
		from: /cm-guide[^\n]*/g,
		to: 'cm-grid',
		expectFail: 'the README never mentions cm-guide',
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
	// A function `to` is invoked by String.replace with the match and its
	// captures, so it can edit a captured group. Guard against a capture
	// being undefined: writing "undefined" into the source would corrupt
	// it silently instead of counting as a harness error.
	const mutated = orig.replace(mut.from, typeof mut.to === 'function'
		? (...a) => { const s = mut.to(...a); if (typeof s !== 'string') throw new TypeError(`to() returned ${typeof s}`); return s; }
		: mut.to);
	if (mutated === orig) {
		noop++;
		console.log(`NO-OP  ${mut.name}\n       pattern did not match ${mut.file} - FIX THE HARNESS`);
		continue;
	}
	writeFileSync(file, mutated);
	try {
		const out = runSuite();
		const hit = typeof mut.expectFail === 'string'
			? out.includes(mut.expectFail)
			: mut.expectFail.test(out);
		if (hit && /FAIL/.test(out)) {
			caught++;
			console.log(`caught ${mut.name}`);
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
