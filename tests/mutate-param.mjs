#!/usr/bin/env node
/**
 * mutation: cm-param, the API docs parameter row
 *
 * Every assertion added this cycle is a guess until it has been made to
 * fail. This harness breaks the exact thing each check guards, runs the
 * suite, and reports which check fired. The parameter checks read the
 * CSS source and the showcase by name, so skipBuild keeps the sweep fast
 * - the built page is measured separately in WebKit.
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
		// The wrap. Without it the description has nowhere to fall on
		// a phone, and the row overruns the viewport - the whole reason
		// the row wraps by height.
		name: 'the parameter row stops wrapping',
		file: CSS,
		from: 'display: flex;\n\tflex-wrap: wrap;\n\talign-items: baseline;',
		to: 'display: flex;\n\tflex-wrap: nowrap;\n\talign-items: baseline;',
		expectFail: 'the parameter row must wrap',
		skipBuild: true,
	},
	{
		// The separator. A parameter row without its hairline is a
		// paragraph, and the docs list stops reading as a list.
		name: 'the base row loses the hairline separator',
		file: CSS,
		from: 'padding: var(--space-2) 0;\n\tborder-bottom: 1px solid var(--line);',
		to: 'padding: var(--space-2) 0;',
		expectFail: 'the separator is the system hairline',
		skipBuild: true,
	},
	{
		// The doctrine half of the pair. Keeping the rule on the last
		// row draws a line that separates nothing - the panel reads as
		// cut off mid-component.
		name: 'the last row keeps its orphan rule',
		file: CSS,
		from: '.cm-param:last-child { border-bottom: 0; }',
		to: '.cm-param:last-child { border-bottom: 1px solid var(--line); }',
		expectFail: 'the last row\'s rule separates nothing',
		skipBuild: true,
	},
	{
		// The face. The name is an identifier: off the mono token it
		// reads as prose and the row loses its docs voice.
		name: 'the name leaves the mono token',
		file: CSS,
		from: 'font-family: var(--font-mono);\n\tfont-weight: 600;\n\tcolor: var(--ink);',
		to: "font-family: 'Helvetica Neue', Arial, sans-serif;\n\tfont-weight: 600;\n\tcolor: var(--ink);",
		expectFail: 'the parameter name must take the --font-mono token',
		skipBuild: true,
	},
	{
		// The weight. The name is the thing the reader looks for; at
		// ink-dim it reads as the same context as the type beside it.
		name: 'the name drops to ink-dim',
		file: CSS,
		from: 'font-family: var(--font-mono);\n\tfont-weight: 600;\n\tcolor: var(--ink);',
		to: 'font-family: var(--font-mono);\n\tfont-weight: 600;\n\tcolor: var(--ink-dim);',
		expectFail: 'the parameter name must read at full ink',
		skipBuild: true,
	},
	{
		// The required mark. Full ink makes the asterisk a second name,
		// not a mark; the form's own mark is faint, and that is the
		// one required signal the system carries.
		name: 'the required mark reads at full ink',
		file: CSS,
		from: '.cm-param__req { color: var(--ink-faint); }',
		to: '.cm-param__req { color: var(--ink); }',
		expectFail: 'the required mark must read at ink-faint',
		skipBuild: true,
	},
	{
		// The type's context. Full ink on the type makes it rival the
		// name it qualifies.
		name: 'the type reads at full ink instead of dim',
		file: CSS,
		from: 'font-size: max(var(--min-font), 0.85em);\n\tcolor: var(--ink-dim);',
		to: 'font-size: max(var(--min-font), 0.85em);\n\tcolor: var(--ink);',
		expectFail: 'the type must read at ink-dim',
		skipBuild: true,
	},
	{
		// The box. Without the border the in badge is a word, and the
		// four locations lose the mark that says "where, not what".
		name: 'the in badge loses its outline',
		file: CSS,
		from: 'padding: 0.1em 0.45em;\n\tborder: 1px solid var(--line);',
		to: 'padding: 0.1em 0.45em;',
		expectFail: 'the in badge must carry the line border',
		skipBuild: true,
	},
	{
		// The case. A lowercase location reads as a word, not a mark -
		// and the showcase specimens are uppercase, so the rule and
		// the demonstration would disagree.
		name: 'the in badge stops being uppercase',
		file: CSS,
		from: 'letter-spacing: 0.04em;\n\ttext-transform: uppercase;\n\tcolor: var(--ink-dim);\n}',
		to: 'letter-spacing: 0.04em;\n\ttext-transform: none;\n\tcolor: var(--ink-dim);\n}',
		expectFail: 'the in badge must be uppercase',
		skipBuild: true,
	},
	{
		// The legibility floor. A badge that can shrink under min-font
		// is unreadable on exactly the phone that reads docs pages.
		name: 'the in badge loses the min-font floor',
		file: CSS,
		from: 'font-size: max(var(--min-font), 0.72em);\n\tfont-weight: 600;',
		to: 'font-size: 0.72em;\n\tfont-weight: 600;',
		expectFail: 'the in badge must floor at --min-font',
		skipBuild: true,
	},
	{
		// The token discipline. A raw grey is a second palette - a
		// theme flip would leave the badge in the old theme's grey.
		name: 'the in badge paints a raw colour',
		file: CSS,
		from: 'text-transform: uppercase;\n\tcolor: var(--ink-dim);\n}',
		to: 'text-transform: uppercase;\n\tcolor: #7a7a7a;\n}',
		expectFail: 'no raw colour in the in badge',
		skipBuild: true,
	},
	{
		// The line-sharing. Without the 10rem basis the description
		// hugs the head, and a row that cannot fill its line stops
		// reading as a row.
		name: 'the description loses its flex basis',
		file: CSS,
		from: 'flex: 1 1 10rem;',
		to: 'flex: 0 0 auto;',
		expectFail: 'the description must carry a 10rem flex basis',
		skipBuild: true,
	},
	{
		// The shrink. min-width: 0 is what lets the description shrink
		// below its text; without it the flex item refuses to fall
		// under its content width and the row overruns the viewport
		// on a phone.
		name: 'the description keeps its text width',
		file: CSS,
		from: 'flex: 1 1 10rem;\n	min-width: 0;\n	color: var(--ink-dim);',
		to: 'flex: 1 1 10rem;\n	color: var(--ink-dim);',
		expectFail: 'the description needs min-width: 0',
		skipBuild: true,
	},
	{
		// The description's context. At full ink it reads as a second
		// name, not the explanation of the first.
		name: 'the description drops to full ink',
		file: CSS,
		from: 'flex: 1 1 10rem;\n\tmin-width: 0;\n\tcolor: var(--ink-dim);',
		to: 'flex: 1 1 10rem;\n\tmin-width: 0;\n\tcolor: var(--ink);',
		expectFail: 'the description must read at ink-dim',
		skipBuild: true,
	},
	{
		// The demonstration. A row only ever read in the source is a
		// promise, not a product; the showcase section is the proof it
		// renders in the endpoint context.
		name: 'the parameter section is removed from the showcase',
		file: SHOW,
		from: /<section id="param"[\s\S]*?<\/section>\n/,
		to: '',
		expectFail: 'no #param section in the showcase',
		skipBuild: true,
	},
	{
		// The required specimen. Deleting the asterisk from one row
		// leaves a single required specimen, and a family demonstrated
		// in one of its two states is a family that is half unproven.
		name: 'the body row loses its required mark',
		file: SHOW,
		from: '<span class="cm-param__name">body<span class="cm-param__req">*</span></span>',
		to: '<span class="cm-param__name">body</span>',
		expectFail: 'the required specimen appears once or never',
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
