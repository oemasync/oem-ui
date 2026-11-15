#!/usr/bin/env node
/**
 * mutation: cm-method, the HTTP method badge
 *
 * Every assertion added this cycle is a guess until it has been made to
 * fail. This harness breaks the exact thing each check guards, runs the
 * suite, and reports which check fired. The method checks read the CSS
 * source and the showcase by name, so skipBuild keeps the sweep fast -
 * the built page is measured separately in WebKit.
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
		// The fill. POST is the primary action and the system's one
		// filled mark; demoting it to the raised surface makes POST
		// read as PUT and collapses the fill ramp to four marks.
		name: 'POST loses its ink fill',
		file: CSS,
		from: '.cm-method--post {\n	border-color: var(--ink);\n	background: var(--ink);\n	color: var(--bg);\n}',
		to: '.cm-method--post {\n	border-color: var(--ink);\n	background: var(--surface-raised);\n	color: var(--bg);\n}',
		expectFail: 'POST must fill on --ink',
		skipBuild: true,
	},
	{
		// The text on the fill. Ink-on-ink is the pair the check exists
		// to prevent: the box reads as a solid chip with nothing on it.
		name: 'POST reads ink on ink',
		file: CSS,
		from: '.cm-method--post {\n	border-color: var(--ink);\n	background: var(--ink);\n	color: var(--bg);\n}',
		to: '.cm-method--post {\n	border-color: var(--ink);\n	background: var(--ink);\n	color: var(--ink);\n}',
		expectFail: 'the filled POST must read the page background',
		skipBuild: true,
	},
	{
		// The raised step. Without it PUT has no box of its own and
		// reads as the outline GET.
		name: 'PUT loses the raised surface',
		file: CSS,
		from: '.cm-method--put {\n	border-color: var(--ink);\n	background: var(--surface-raised);\n	color: var(--ink);\n}',
		to: '.cm-method--put {\n	border-color: var(--ink);\n	background: transparent;\n	color: var(--ink);\n}',
		expectFail: 'PUT must sit on the raised surface',
		skipBuild: true,
	},
	{
		// The dashed set signal. A solid border makes PATCH a heavier
		// outline - the one treatment left is the one the chip family
		// already owns, and the signal it names goes with it.
		name: 'PATCH loses the dashed border',
		file: CSS,
		from: '.cm-method--patch { border-style: dashed; }',
		to: '.cm-method--patch { border-style: solid; }',
		expectFail: 'PATCH must carry the dashed border',
		skipBuild: true,
	},
	{
		// The destructive signal. cm-status-code--err owns the
		// underlined ink; DELETE dropping it is a verb that reads as
		// a neutral label.
		name: 'DELETE loses the destructive underline',
		file: CSS,
		from: '.cm-method--delete {\n	color: var(--ink);\n	text-decoration: underline;\n	text-underline-offset: 0.2em;\n}',
		to: '.cm-method--delete {\n	color: var(--ink);\n	text-underline-offset: 0.2em;\n}',
		expectFail: 'DELETE must carry the underline',
		skipBuild: true,
	},
	{
		// The other half of the pair. Underlined dim is a whisper, not
		// a warning: the status-code precedent is full ink UNDER the
		// line, and dim-plus-line is neither the rest mark nor the
		// destructive one.
		name: 'DELETE reads dim instead of ink',
		file: CSS,
		from: '.cm-method--delete {\n	color: var(--ink);\n	text-decoration: underline;',
		to: '.cm-method--delete {\n	color: var(--ink-dim);\n	text-decoration: underline;',
		expectFail: 'DELETE must read at full ink with the underline',
		skipBuild: true,
	},
	{
		// The resting box. GET is the outline - without the border the
		// base method is bare text and the five-mark ramp has no floor.
		name: 'the GET outline loses its border',
		file: CSS,
		from: 'padding: 0.1em 0.5em;\n\tborder: 1px solid var(--line);',
		to: 'padding: 0.1em 0.5em;\n\tborder: 0;',
		expectFail: 'the GET outline must carry the line border',
		skipBuild: true,
	},
	{
		// The case. A lowercase method reads as a word, not a verb -
		// and the showcase specimens are uppercase, so the rule and
		// the demonstration would disagree.
		name: 'the method badge stops being uppercase',
		file: CSS,
		from: 'letter-spacing: 0.04em;\n\ttext-transform: uppercase;',
		to: 'letter-spacing: 0.04em;\n\ttext-transform: none;',
		expectFail: 'the method badge must be uppercase',
		skipBuild: true,
	},
	{
		// The token discipline. A raw grey is a second palette - the
		// whole point of the fill vocabulary is that the system owns
		// every value, or a theme flip leaves the badge in the old
		// theme's grey.
		name: 'the base method paints a raw colour',
		file: CSS,
		from: 'text-transform: uppercase;\n\tcolor: var(--ink-dim);',
		to: 'text-transform: uppercase;\n\tcolor: #888888;',
		expectFail: 'no raw colour in the method badge base',
		skipBuild: true,
	},
	{
		// The face. The method is code, not prose: off the mono token
		// it reads as a label, and the token is what a scoped consumer
		// re-points at its own stack.
		name: 'the base method leaves the mono token',
		file: CSS,
		from: 'font-family: var(--font-mono);\n\tfont-size: max(var(--min-font), 0.72em);',
		to: "font-family: 'Courier New', monospace;\n\tfont-size: max(var(--min-font), 0.72em);",
		expectFail: 'the method badge must take the --font-mono token',
		skipBuild: true,
	},
	{
		// The demonstration. A badge only ever read in the source is a
		// promise, not a product; the showcase section is the proof it
		// renders in both contexts.
		name: 'the method section is removed from the showcase',
		file: SHOW,
		from: /<section id="method"[\s\S]*?<\/section>\n/,
		to: '',
		expectFail: 'no #method section in the showcase',
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
