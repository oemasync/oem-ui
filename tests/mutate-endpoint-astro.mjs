#!/usr/bin/env node
/**
 * mutation: <Endpoint>, the API-docs method+path wrapper
 *
 * Every assertion added this cycle is a guess until it has been made to
 * fail. This harness breaks the exact thing each check guards, runs the
 * suite, and reports which check fired. The Endpoint.astro checks read
 * the component source and the showcase by name, so skipBuild keeps the
 * sweep fast - the component's rendered output (both {token} slots
 * wrapped, the method uppercased) is covered by the suite's own
 * built-dist check, which this sweep does not need to rebuild for.
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
const EP = 'src/astro/Endpoint.astro';
const SHOW = 'src/pages/[...family].astro';

const MUTATIONS = [
	{
		// The method badge. Without the prop interpolation every
		// endpoint renders as GET regardless of what the caller passed.
		name: 'the method badge class is hardcoded, ignoring the method prop',
		file: EP,
		from: '<span class={`cm-method cm-method--${method}`}>{method.toUpperCase()}</span>',
		to: '<span class="cm-method cm-method--get">{method.toUpperCase()}</span>',
		expectFail: 'Endpoint.astro does not derive the method badge class from the method prop',
		skipBuild: true,
	},
	{
		// The row. Without cm-endpoint the badge and the path lose the
		// centered flex row that lays them out on one line.
		name: 'the wrapper loses its cm-endpoint class',
		file: EP,
		from: '<div class="cm-endpoint">',
		to: '<div class="cm-endpoint-row">',
		expectFail: 'Endpoint.astro does not use the cm-endpoint class',
		skipBuild: true,
	},
	{
		// The path. Without cm-endpoint__path the path loses its mono
		// weight and its ability to break inside itself on a phone.
		name: 'the path element loses its cm-endpoint__path class',
		file: EP,
		from: '<span class="cm-endpoint__path">',
		to: '<span class="cm-endpoint-path">',
		expectFail: 'Endpoint.astro is missing the path element',
		skipBuild: true,
	},
	{
		// The slot. Without cm-endpoint__param a {token} renders at the
		// path's own full ink - a literal, not a thing to substitute.
		name: 'the slot span loses its cm-endpoint__param class',
		file: EP,
		from: '<span class="cm-endpoint__param">{part}</span>',
		to: '<span class="cm-endpoint-param">{part}</span>',
		expectFail: 'Endpoint.astro is missing the param-slot element',
		skipBuild: true,
	},
	{
		// The split. A pattern that cannot match a {token} boundary
		// leaves the whole path as one literal part - no slot ever
		// gets wrapped, whatever the caller passes.
		name: 'the split pattern no longer matches {token} boundaries',
		file: EP,
		from: 'path.split(/(\\{[^}]+\\})/g)',
		to: 'path.split(/(\\[[^}]+\\])/g)',
		expectFail: 'Endpoint.astro does not split the path on a {token} pattern',
		skipBuild: true,
	},
	{
		// The slot test's other half. Dropping endsWith('}') means a
		// literal segment that merely STARTS with a brace (there is
		// none today, but the next path author does not know that)
		// would be wrapped as a slot it is not.
		name: 'the slot test drops the closing-brace half of the check',
		file: EP,
		from: "part.startsWith('{') && part.endsWith('}')",
		to: "part.startsWith('{')",
		expectFail: 'Endpoint.astro does not test each part for being a {token} before wrapping it as a slot',
		skipBuild: true,
	},
	{
		// The label case. A lowercase method sits beside the five
		// uppercase treatments the method section already demonstrates
		// and reads as a sixth, unrelated thing.
		name: 'the method label is no longer uppercased',
		file: EP,
		from: '{method.toUpperCase()}',
		to: '{method}',
		expectFail: 'Endpoint.astro does not uppercase the method label',
		skipBuild: true,
	},
	{
		// The demonstration. A wrapper only ever read in its own file is
		// a promise, not a product - the showcase specimen is the proof
		// it composes correctly in the family it was built for.
		name: 'the showcase stops rendering <Endpoint>',
		file: SHOW,
		from: '<Endpoint method="patch" path="/v1/foxes/{id}/comments/{commentId}" />',
		to: '',
		expectFail: 'the showcase imports Endpoint.astro but never renders it',
		skipBuild: true,
	},
];

// --range a,b runs MUTATIONS[a..b] inclusive, so a slow full sweep (8
// full-suite runs, ~65s each) can be split across several tool calls
// that each stay comfortably under a hard wall-clock timeout. Every
// batch still pre-flights and restores on its own slice; running all
// batches in sequence is equivalent to one unsplit run.
const rangeArg = process.argv.find((a) => a.startsWith('--range='));
let RANGE = [0, MUTATIONS.length - 1];
if (rangeArg) {
	const [a, b] = rangeArg.slice('--range='.length).split(',').map(Number);
	RANGE = [a, b];
}
const ACTIVE = MUTATIONS.slice(RANGE[0], RANGE[1] + 1);

const runSuite = () => {
	const r = spawnSync('node', [join(root, 'tests/run.mjs')], { encoding: 'utf8' });
	return r.stdout || '';
};

let caught = 0, missed = 0, noop = 0;
/* A sweep this long sits inside the kill boundary: a timeout SIGKILLs
   the process and `finally` never runs, leaving the last mutant in the
   tree. So the current mutation is tracked and a restore handler is
   bound to every signal the process can receive; uncaughtException gets
   the same treatment. Re-entrancy guard: only one restore in flight. */
let current = null;
let restoring = false;
function restoreNow(reason) {
	if (restoring) return;
	restoring = true;
	if (current) {
		try {
			writeFileSync(current.file, current.orig);
			const back = readFileSync(current.file, 'utf8');
			if (back !== current.orig) {
				console.log(`RESTORE FAILED for ${current.name} (${reason}) - verify the tree by hand`);
			}
		} catch (e) {
			console.log(`RESTORE ERROR for ${current.name} (${reason}): ${e.message}`);
		}
	}
	console.log(`restored (${reason})`);
	process.exit(130);
}
for (const sig of ['SIGINT', 'SIGTERM', 'SIGHUP']) {
	process.on(sig, () => restoreNow(sig));
}
process.on('uncaughtException', (e) => {
	console.log(`uncaughtException: ${e.message}`);
	restoreNow('uncaughtException');
});
/* Pre-flight: every pattern must match EXACTLY once, or the sweep would
   mutate the wrong rule or mutate nothing. A miss is reported before
   anything is written, not discovered mid-run. */
for (const mut of ACTIVE) {
	const src = readFileSync(p(mut.file), 'utf8');
	const n = src.split(mut.from).length - 1;
	if (n !== 1) {
		console.log(`PRE-FLIGHT FAIL  ${mut.name}\n       pattern matches ${n} time(s) in ${mut.file} - FIX THE HARNESS`);
		process.exit(2);
	}
}
for (const mut of ACTIVE) {
	const file = p(mut.file);
	const orig = readFileSync(file, 'utf8');
	const mutated = orig.replace(mut.from, mut.to);
	if (mutated === orig) {
		noop++;
		console.log(`NO-OP  ${mut.name}\n       pattern did not match ${mut.file} - FIX THE HARNESS`);
		continue;
	}
	writeFileSync(file, mutated);
	current = { file, orig, name: mut.name };
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
		const back = readFileSync(file, 'utf8');
		if (back !== orig) {
			console.log(`RESTORE MISMATCH after ${mut.name} - verify the tree by hand`);
			process.exit(3);
		}
		current = null;
	}
}
console.log(`\n${ACTIVE.length} mutation(s) in range [${RANGE[0]},${RANGE[1]}]: ${caught} caught, ${missed} missed, ${noop} no-op`);
if (noop) process.exit(2);
process.exit(missed ? 1 : 0);
