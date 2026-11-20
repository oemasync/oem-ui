#!/usr/bin/env node
/**
 * mutation: <Trace>/<TraceStep>, the cm-trace wrapper pair
 *
 * Every assertion added this cycle is a guess until it has been made to
 * fail. This harness breaks the exact thing each check guards, runs the
 * suite, and reports which check fired. Like mutate-diff-astro.mjs and
 * mutate-callout-astro.mjs, every mutant here is source/regex-level (the
 * component's REAL rendered output - the right glyphs and trigger wiring
 * reaching the DOM - is proven once by the suite's own built-dist check
 * against a real `npm run build`, which this sweep does not rebuild for,
 * and separately by a real WebKit measurement taken outside this sweep).
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
const TA = 'src/astro/Trace.astro';
const TS = 'src/astro/TraceStep.astro';
const SHOW = 'src/pages/[...family].astro';

const MUTATIONS = [
	{
		// idle picks up a stray modifier class - the showcase's idle
		// specimen would paint a spurious is-* state it never asked for.
		name: 'idle state gains a stray modifier class',
		file: TS,
		from: "\tidle: '',\n\trunning: 'is-running',",
		to: "\tidle: 'is-idle',\n\trunning: 'is-running',",
		expectFail: 'batch 40: the idle state renders with NO state modifier class',
	},
	{
		// running loses its modifier - a running step would render
		// indistinguishably from idle in the DOM.
		name: "running state loses its modifier class",
		file: TS,
		from: "\trunning: 'is-running',\n\tdone: 'is-done',",
		to: "\trunning: '',\n\tdone: 'is-done',",
		expectFail: 'batch 40: the idle state renders with NO state modifier class',
	},
	{
		// error's glyph collapses onto done's - a finished step and a
		// failed one would be visually identical.
		name: "error's glyph duplicates done's",
		file: TS,
		from: "\tdone: '\\u2713',\n\terror: '\\u2717',",
		to: "\tdone: '\\u2713',\n\terror: '\\u2713',",
		expectFail: 'batch 40: each state maps to a DISTINCT glyph, no two alike',
	},
	{
		// The GLYPH map loses an entry outright - a state with no
		// glyph at all would render the icon slot empty.
		name: 'the GLYPH map loses an entry',
		file: TS,
		from: "\trunning: '\\u25cf',\n\tdone: '\\u2713',",
		to: "\tdone: '\\u2713',",
		expectFail: 'batch 40: each state maps to a DISTINCT glyph, no two alike',
	},
	{
		// The dead-trigger guard is loosened to "id alone is enough" -
		// a step given an id but no detail would render a trigger
		// pointing at a body with nothing in it.
		name: 'collapsible drops its hasBody half of the guard',
		file: TS,
		from: 'const collapsible = hasBody && Boolean(id);',
		to: 'const collapsible = Boolean(id);',
		expectFail: 'batch 40: a step with no body renders no trigger and no desc',
	},
	{
		// hasBody is hardcoded true - every step, even one with no
		// slot content, would be treated as carrying a body.
		name: 'hasBody is hardcoded true',
		file: TS,
		from: "const hasBody = Astro.slots.has('default');",
		to: 'const hasBody = true;',
		expectFail: 'batch 40: a step with no body renders no trigger and no desc',
	},
	{
		// aria-expanded is pinned to false - an initially-open step
		// (trace-detail-2) would tell assistive tech it is closed.
		name: "aria-expanded is pinned to 'false'",
		file: TS,
		from: "aria-expanded={open ? 'true' : 'false'}",
		to: 'aria-expanded="false"',
		expectFail: 'batch 40: a collapsible step wires aria-expanded/aria-controls and hides its body by default',
	},
	{
		// aria-controls stops pointing at the step's own id - the
		// trigger would control nothing, or the wrong panel.
		name: 'aria-controls no longer points at id',
		file: TS,
		from: 'aria-controls={id}',
		to: 'aria-controls="static"',
		expectFail: 'batch 40: a collapsible step wires aria-expanded/aria-controls and hides its body by default',
	},
	{
		// The body's hidden-by-default logic is dropped entirely - a
		// closed step's detail would be visible on first paint.
		name: 'the body loses its hidden-by-default logic',
		file: TS,
		from: '<div class="cm-trace__body" id={id} {...(!open && { hidden: true })}>',
		to: '<div class="cm-trace__body" id={id}>',
		expectFail: 'batch 40: a collapsible step wires aria-expanded/aria-controls and hides its body by default',
	},
	{
		// The demonstration. A wrapper only ever read in its own file
		// is a promise, not a product.
		name: 'the showcase stops importing Trace.astro',
		file: SHOW,
		from: "import Trace from '../astro/Trace.astro';\n",
		to: '',
		expectFail: 'the showcase does not import Trace.astro',
	},
	{
		name: 'the showcase stops importing TraceStep.astro',
		file: SHOW,
		from: "import TraceStep from '../astro/TraceStep.astro';\n",
		to: '',
		expectFail: 'the showcase does not import TraceStep.astro',
	},
	{
		// The no-body idle specimen disappears - the empty-slot path
		// (no trigger, no desc) would never be exercised at all.
		name: 'the showcase drops its no-body idle specimen',
		file: SHOW,
		from: '\t\t\t\t\t<TraceStep state="idle" title="author the two components" />\n',
		to: '',
		expectFail: 'the showcase lost its no-body idle specimen',
	},
	{
		// The second collapsible specimen loses its `open` prop - the
		// initially-open path would never be exercised, only closed.
		name: "the showcase's open collapsible specimen loses its open prop",
		file: SHOW,
		from: '\t\t\t\t\t\tid="trace-detail-2"\n\t\t\t\t\t\topen\n',
		to: '\t\t\t\t\t\tid="trace-detail-2"\n',
		expectFail: "no longer carries the open prop",
	},
];

// --range a,b runs MUTATIONS[a..b] inclusive, so a slow full sweep can be
// split across several tool calls that each stay comfortably under a
// hard wall-clock timeout, the same device mutate-diff-astro.mjs uses.
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
