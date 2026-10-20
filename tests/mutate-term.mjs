#!/usr/bin/env node
/**
 * mutation: cm-term follow mode — the live log tail (batch 37)
 *
 * Every assertion in the batch-37 block of tests/run.mjs is a guess
 * until it has been made to fail. This harness breaks the exact thing
 * each check guards, runs the suite, and reports which check fired.
 *
 * A pattern that no longer matches the source is a NO-OP — a failure of
 * THIS file, never a pass. Zero no-ops is required for the cycle's
 * caught-count to mean anything.
 *
 * All mutations target files the batch-37 checks read directly
 * (components.css, the showcase, the runtime, the README), so no astro
 * build is needed between mutants.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const p = (f) => join(root, f);
const COMP = 'src/styles/components.css';
const SHOW = 'src/pages/[...family].astro';
const RUNTIME = 'src/js/cli-mono.js';
const README = 'README.md';

const MUTATIONS = [
	{
		// The follow toggle is a pressed-state control; without
		// aria-pressed its state is invisible to a screen reader.
		name: 'the follow toggle loses its aria-pressed state',
		file: SHOW,
		from: /data-cm-follow-toggle aria-pressed="true"/,
		to: 'data-cm-follow-toggle',
		expectFail: 'the follow toggle is a pressed-state button',
	},
	{
		// The status line must announce politely — a chatty log tail
		// that interrupts on every state flip is worse than silence.
		name: 'the follow status is no longer an aria-live region',
		file: SHOW,
		from: /class="cm-term__status" aria-live="polite"/,
		to: 'class="cm-term__status"',
		expectFail: 'the follow status is announced politely',
	},
	{
		// The jump-to-tail affordance is how a reader re-engages after
		// scrolling up; remove it and there is no way back.
		name: 'the jump-to-tail button is deleted from the specimen',
		file: SHOW,
		from: /<button type="button" class="cm-term__jump-tail"[^>]*data-cm-jump-tail>[\s\S]*?<\/button>/,
		to: '',
		expectFail: 'the specimen has no jump-to-tail button; re-engaging has no affordance',
		skipBuild: true,
	},
	{
		// Follow must be a state driven by scroll position: without a
		// scroll listener, scrolling up can never disengage it. Scoped
		// to the initTermFollow region — 13 other listeners in this
		// file use the same { passive: true } tail.
		name: 'initTermFollow does not listen for scroll',
		file: RUNTIME,
		region: true,
		from: /body\.addEventListener\(\s*'scroll'[\s\S]*?\}, \{ passive: true \}\);/,
		to: '/* scroll listener removed */',
		expectFail: 'the runtime listens for scroll (scroll-up disengages follow)',
	},
	{
		// The toggle must be wired; a decorative button that changes
		// nothing is exactly the "slop" the app must not ship.
		name: 'initTermFollow does not wire the toggle button',
		file: RUNTIME,
		region: true,
		from: /if \(toggle\) toggle\.addEventListener\('click'[\s\S]*?\}\);/,
		to: '/* toggle listener removed */',
		expectFail: 'the runtime wires the toggle button',
	},
	{
		// The jump button must be wired to re-engage.
		name: 'initTermFollow does not wire the jump-to-tail button',
		file: RUNTIME,
		region: true,
		from: /if \(jump\) jump\.addEventListener\('click'[^;]*;/,
		to: '/* jump listener removed */',
		expectFail: 'the runtime wires the jump-to-tail button',
	},
	{
		// The DOM must stay bounded: without the MAX_LINES window a
		// 100k-line buffer collapses the layout.
		name: 'the append bound is removed (no MAX_LINES window)',
		file: RUNTIME,
		region: true,
		from: /while \(pre\.children\.length > MAX_LINES\) pre\.removeChild\(pre\.firstChild\);/,
		to: '/* windowing removed */',
		expectFail: 'appends are bounded (virtualised window)',
	},
	{
		// The state machine must expose named transitions so follow is
		// re-engaged deliberately, not as an append side-effect.
		name: 'the engage/disengage state transitions are removed',
		file: RUNTIME,
		from: /function engage\(\) \{[\s\S]*?\n\t+\}\n/,
		to: '',
		expectFail: 'follow is re-engaged by the button, not by an append side-effect',
	},
	{
		// A component the docs never name is one a consumer reinvents.
		name: 'the README term section is deleted',
		file: README,
		from: /cm-term[^\n]*/g,
		to: 'cm-log',
		expectFail: 'the README never mentions cm-term',
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
	let mutated;
	if (mut.region) {
		// Scope the replacement to the initTermFollow block: these
		// patterns (passive:true, addEventListener) recur dozens of
		// times earlier in the file and would otherwise mutate the
		// wrong component while the suite stays green.
		const start = orig.indexOf('function initTermFollow');
		const end = orig.indexOf('/* ---------- measure');
		if (start < 0 || end < 0 || end <= start) {
			console.log(`NO-OP  ${mut.name}\n       initTermFollow region not found - FIX THE HARNESS`);
			noop++;
			continue;
		}
		const region = orig.slice(start, end);
		// Function replacements run per match inside the region, same as
		// the guide harness; guard against a non-string return.
		const newRegion = region.replace(mut.from, typeof mut.to === 'function'
			? (...a) => { const s = mut.to(...a); if (typeof s !== 'string') throw new TypeError(`to() returned ${typeof s}`); return s; }
			: mut.to);
		// Handle function replacements inside the region too (same branch logic as guide).
		mutated = newRegion === region ? orig : orig.slice(0, start) + newRegion + orig.slice(end);
	} else {
		mutated = orig.replace(mut.from, mut.to);
	}
	if (mutated === orig) {
		noop++;
		console.log(`NO-OP  ${mut.name}\n       pattern did not match ${mut.file} - FIX THE HARNESS`);
		continue;
	}
	writeFileSync(file, mutated);
	try {
		const out = runSuite();
		// String expectations anchor to the check NAME, which also
		// appears on passing "ok" lines — require the FAIL line (the
		// suite prints "FAIL  name", TWO spaces) or a passing check
		// would count as a catch. Regexes anchor to assertion messages,
		// which only FAIL lines carry.
		// A FAIL block spans TWO lines: "FAIL  <check name>" then the
		// indented assertion message. String expectations may be either
		// the name or the message, so test both lines of each block.
		const lines = out.split('\n');
		const hit = typeof mut.expectFail === 'string'
			? lines.some((ln, i) => ln.startsWith('FAIL')
				&& (ln.includes(mut.expectFail) || (lines[i + 1] || '').includes(mut.expectFail)))
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
