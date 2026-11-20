#!/usr/bin/env node
/**
 * mutation: <Diff>, the word-level diff row wrapper
 *
 * Every assertion added this cycle is a guess until it has been made to
 * fail. This harness breaks the exact thing each check guards, runs the
 * suite, and reports which check fired. Like mutate-tree-astro.mjs and
 * mutate-callout-astro.mjs, every mutant here is source/regex-level (the
 * component's REAL rendered output - reaching the DOM with the right
 * classes, fold and aria-labels - is proven once by the suite's own
 * built-dist check against a real `npm run build`, which this sweep does
 * not rebuild for). The fold-count-derivation and fold-filter mutants live
 * in tests/mutate-diff.mjs instead (batch 34's own sweep, which they were
 * folded into when the hand-typed markup moved into this wrapper).
 *
 * A pattern that no longer matches the source is a NO-OP - a failure of
 * THIS file, never a pass. The count reported in the cycle note must have
 * zero in it, or the harness itself is broken and the number is
 * worthless.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const p = (f) => join(root, f);
const DA = 'src/astro/Diff.astro';
const SHOW = 'src/pages/[...family].astro';

const MUTATIONS = [
	{
		// The from/to guard. Without it an update row with nothing to
		// compare renders an operator over a blank - a diff that lies
		// about having a new value.
		name: 'the missing from/to guard never fires',
		file: DA,
		from: "if (row.op === 'update' && (row.from === undefined || row.to === undefined)) {",
		to: 'if (false) {',
		expectFail: 'Diff.astro throws when an update row is missing from or to',
	},
	{
		// The shown-rows loop's aria-label drops the operation prefix -
		// a screen reader would hear only the field name, never told
		// whether it was created, changed or removed.
		name: "the shown-rows aria-label drops the op prefix",
		file: DA,
		from: '<li class="cm-diff__row" data-op={r.op} aria-label={`${r.op}: ${r.label}`}>\n\t\t\t<span class="cm-diff__op">{r.op}</span>\n\t\t\t<span class="cm-diff__val">\n\t\t\t\t{r.op === \'delete\' ? (',
		to: '<li class="cm-diff__row" data-op={r.op} aria-label={r.label}>\n\t\t\t<span class="cm-diff__op">{r.op}</span>\n\t\t\t<span class="cm-diff__val">\n\t\t\t\t{r.op === \'delete\' ? (',
		expectFail: "Diff.astro's aria-label template appears 1 time(s)",
	},
	{
		// A `set:html` slips into the TEMPLATE (not the doc comment,
		// which already names it in prose). A diff value is computed
		// from live state, never hand-authored prose, so this is the
		// exact regression the check exists to catch.
		name: 'a set:html slips into the template',
		file: DA,
		from: '<ul class="cm-diff">\n\t{shown.map((r) => (',
		to: '<ul class="cm-diff">\n\t{/* set:html would break escaping here */}\n\t{shown.map((r) => (',
		expectFail: 'Diff.astro never renders raw HTML',
	},
	{
		// The create row's <code> wrap is dropped - a created field's
		// literal value loses the treatment every other literal in the
		// library gets, and reads as prose instead of a value.
		name: "create's <code> wrap is dropped",
		file: DA,
		from: '{r.label}: <code>{r.value}</code>',
		to: '{r.label}: {r.value}',
		expectFail: "Diff.astro renders create wrapped in <code>, update as <del>/<ins>, delete and same as plain text",
	},
	{
		// The update row's del/ins pair is dropped for plain text - the
		// word-level diff semantics (what left, what arrived) vanish,
		// and <del>/<ins> is also what print and screen readers key off.
		name: "update's del/ins pair is dropped",
		file: DA,
		from: '{r.label}: <del class="cm-diff__del">{r.from}</del> → <ins class="cm-diff__ins">{r.to}</ins>',
		to: '{r.label}: {r.from} to {r.to}',
		expectFail: "Diff.astro renders create wrapped in <code>, update as <del>/<ins>, delete and same as plain text",
	},
	{
		// A delete row grows a value - there is nothing left to show a
		// value FOR once a field is gone, so this is the row that most
		// needs its value suppressed.
		name: "delete renders a value, not just its label",
		file: DA,
		from: "r.op === 'delete' ? (\n\t\t\t\t\tr.label\n\t\t\t\t) : r.op === 'update' ? (",
		to: "r.op === 'delete' ? (\n\t\t\t\t\t`${r.label}: ${r.value}`\n\t\t\t\t) : r.op === 'update' ? (",
		expectFail: "Diff.astro renders create wrapped in <code>, update as <del>/<ins>, delete and same as plain text",
	},
	{
		// The demonstration. A wrapper only ever read in its own file
		// is a promise, not a product.
		name: 'the showcase stops importing Diff.astro',
		file: SHOW,
		from: "import Diff from '../astro/Diff.astro';\n",
		to: '',
		expectFail: 'the showcase does not import Diff.astro',
	},
	{
		// The long-values specimen disappears - the one demo proving
		// the fold-less, no-foldLabel path (and the hanging-indent
		// wrap) is never exercised at all.
		name: 'the showcase drops its long-values <Diff> specimen',
		file: SHOW,
		from: "\t\t\t\t<Diff\n\t\t\t\t\trows={[\n\t\t\t\t\t\t{\n\t\t\t\t\t\t\top: 'update',\n\t\t\t\t\t\t\tlabel: '/config/rclone/remotes/prod-archive',\n\t\t\t\t\t\t\tfrom: 'rclone:securesync-legacy-prod',\n\t\t\t\t\t\t\tto: 'rclone:securesync-v2-prod',\n\t\t\t\t\t\t},\n\t\t\t\t\t]}\n\t\t\t\t/>\n",
		to: '',
		expectFail: 'expected exactly 2 (the create/update/delete/same+fold demo and the long-values demo)',
	},
];

// --range a,b runs MUTATIONS[a..b] inclusive, so a slow full sweep can be
// split across several tool calls that each stay comfortably under a
// hard wall-clock timeout, the same device mutate-tree-astro.mjs uses.
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
/* A sweep this long sits inside the kill boundary: a timeout SIGKILLs the
   process and `finally` never runs, leaving the last mutant in the tree.
   So the current mutation is tracked and a restore handler is bound to
   every signal the process can receive; uncaughtException gets the same
   treatment. Re-entrancy guard: only one restore in flight. */
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
