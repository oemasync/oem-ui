#!/usr/bin/env node
/**
 * mutation: cm-endpoint, the API endpoint row
 *
 * Every assertion added this cycle is a guess until it has been made to
 * fail. This harness breaks the exact thing each check guards, runs the
 * suite, and reports which check fired. The endpoint checks read the CSS
 * source and the showcase by name, so skipBuild keeps the sweep fast -
 * the built page is measured separately in WebKit (measure-endpoint-
 * webkit.py).
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
const CSS = 'src/styles/components.css';
const SHOW = 'src/pages/[...family].astro';

const MUTATIONS = [
	{
		// The face. The path is an identifier, not prose: off the mono
		// token it reads as a label, and the token is what a scoped
		// consumer re-points at its own stack.
		name: 'the endpoint path leaves the mono token',
		file: CSS,
		from: '.cm-endpoint__path {\n\tfont-family: var(--font-mono);\n\tfont-weight: 600;',
		to: ".cm-endpoint__path {\n\tfont-family: 'Courier New', monospace;\n\tfont-weight: 600;",
		expectFail: 'the endpoint path must take the --font-mono token',
		skipBuild: true,
	},
	{
		// The weight. The identifier's own weight is 600; plain 400
		// reads as a path the reader skims, not the thing the entry
		// is about.
		name: 'the endpoint path drops to the plain weight',
		file: CSS,
		from: '.cm-endpoint__path {\n\tfont-family: var(--font-mono);\n\tfont-weight: 600;',
		to: '.cm-endpoint__path {\n\tfont-family: var(--font-mono);\n\tfont-weight: 400;',
		expectFail: 'the endpoint path must read at 600',
		skipBuild: true,
	},
	{
		// The ink. Dim is the slot's step; the path's own ink is the
		// literal. Flipping them makes the whole path read as context
		// and the slot read as the headline - the pair inverted.
		name: 'the endpoint path reads dim instead of ink',
		file: CSS,
		from: 'color: var(--ink);\n\t/* A path is one token',
		to: 'color: var(--ink-dim);\n\t/* A path is one token',
		expectFail: 'the endpoint path must read at full ink',
		skipBuild: true,
	},
	{
		// The break. A path is one token with no spaces; without a
		// break rule it cannot wrap, so a long endpoint overruns the
		// viewport on a phone and the row scrolls.
		name: 'the endpoint path can no longer break',
		file: CSS,
		from: "URL cells were written to avoid. */\n	min-width: 0;\n	overflow-wrap: break-word;\n}",
		to: "URL cells were written to avoid. */\n	min-width: 0;\n	overflow-wrap: normal;\n}",
		expectFail: 'the path must be able to break',
		skipBuild: true,
	},
	{
		// The shrink. Without min-width: 0 the flex item will not
		// shrink below its text, so even with a break rule the item
		// overruns the viewport before it is allowed to wrap.
		name: 'the endpoint path keeps its text width',
		file: CSS,
		from: "URL cells were written to avoid. */\n	min-width: 0;\n	overflow-wrap: break-word;\n}",
		to: "URL cells were written to avoid. */\n	min-width: auto;\n	overflow-wrap: break-word;\n}",
		expectFail: 'the path needs min-width: 0',
		skipBuild: true,
	},
	{
		// The slot. The {param} token is one step DOWN from the path;
		// full ink makes the slot read as a literal and erases the
		// mark that links it to the parameter row below.
		name: 'the endpoint param token reads ink instead of dim',
		file: CSS,
		from: "the parameter row's type already carries, not a new colour. */\n\tcolor: var(--ink-dim);",
		to: "the parameter row's type already carries, not a new colour. */\n\tcolor: var(--ink);",
		expectFail: 'the endpoint param token must read at ink-dim',
		skipBuild: true,
	},
	{
		// The centre. The badge sits on the path's own line, the way
		// the method section composes it; flex-start would pin it to
		// the top of a wrapping path, off the first line's baseline.
		name: 'the endpoint row stops centering the badge',
		file: CSS,
		from: '.cm-endpoint {\n\tdisplay: flex;\n\talign-items: center;',
		to: '.cm-endpoint {\n\tdisplay: flex;\n\talign-items: flex-start;',
		expectFail: 'the endpoint row must center the badge',
		skipBuild: true,
	},
	{
		// The gap. The badge and the path are separate marks; with no
		// gap they read as one fused token and the badge's border
		// touches the path's first character.
		name: 'the endpoint row drops the gap',
		file: CSS,
		from: 'align-items: center;\n\tgap: var(--space-2);\n}\n.cm-endpoint__path',
		to: 'align-items: center;\n\tgap: 0;\n}\n.cm-endpoint__path',
		expectFail: 'the endpoint row must keep the system gap',
		skipBuild: true,
	},
	{
		// The token discipline. A raw grey is a second palette - the
		// whole point of the token is that a theme flip repoints it.
		name: 'the endpoint path paints a raw colour',
		file: CSS,
		from: "URL cells were written to avoid. */\n	min-width: 0;\n	overflow-wrap: break-word;\n}",
		to: "URL cells were written to avoid. */\n	min-width: 0;\n	overflow-wrap: break-word;\n	color: #888888;\n}",
		expectFail: 'no raw colour in the endpoint path',
		skipBuild: true,
	},
	{
		// The demonstration. A row only ever read in the source is a
		// promise, not a product; the showcase section is the proof
		// it renders with the slot marked.
		name: 'the endpoint section is removed from the showcase',
		file: SHOW,
		from: /<section id="endpoint"[\s\S]*?<\/section>\n/,
		to: '',
		expectFail: 'no #endpoint section in the showcase',
		skipBuild: true,
	},
];

const runSuite = () => {
	const r = spawnSync('node', [join(root, 'tests/run.mjs')], { encoding: 'utf8' });
	return r.stdout || '';
};

let caught = 0, missed = 0, noop = 0;
/* A sweep this long sits inside the kill boundary: a timeout SIGKILLs
   the process and `finally` never runs, leaving the last mutant in the
   tree (this exact failure mode happened to the house sweeps). So the
   current mutation is tracked and a restore handler is bound to every
   signal the process can receive; uncaughtException gets the same
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
   mutate the wrong rule (a twice-matching pattern hits the first
   occurrence, which may be another component's) or mutate nothing.
   A miss is reported before anything is written, not discovered mid-run. */
for (const mut of MUTATIONS) {
	const src = readFileSync(p(mut.file), 'utf8');
	const n = mut.from instanceof RegExp
		? (src.match(mut.from) || []).length
		: src.split(mut.from).length - 1;
	if (n !== 1) {
		console.log(`PRE-FLIGHT FAIL  ${mut.name}\n       pattern matches ${n} time(s) in ${mut.file} - FIX THE HARNESS`);
		process.exit(2);
	}
}
for (const mut of MUTATIONS) {
	const file = p(mut.file);
	const orig = readFileSync(file, 'utf8');
	const mutated = mut.from instanceof RegExp
		? orig.replace(mut.from, mut.to)
		: orig.replace(mut.from, mut.to);
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
console.log(`\n${MUTATIONS.length} mutations: ${caught} caught, ${missed} missed, ${noop} no-op`);
if (noop) process.exit(2);
process.exit(missed ? 1 : 0);
