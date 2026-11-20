#!/usr/bin/env node
/**
 * mutation: <Callout>, the in-prose admonition wrapper
 *
 * Every assertion added this cycle is a guess until it has been made to
 * fail. This harness breaks the exact thing each check guards, runs the
 * suite, and reports which check fired. Like mutate-tree-astro.mjs, every
 * mutant here is source/regex-level (the component's REAL rendered output
 * - reaching the DOM with the right classes, mark and title - is proven
 * once by the suite's own built-dist check against a real `npm run
 * build`, which this sweep does not rebuild for).
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
const CA = 'src/astro/Callout.astro';
const SHOW = 'src/pages/[...family].astro';

const MUTATIONS = [
	{
		// The no-default guard. A silent default would hide a caller
		// forgetting to name a tone - every real admonition names one.
		name: 'variant gains a default value',
		file: CA,
		from: "const { variant, title, id, class: className } = Astro.props;",
		to: "const { variant = 'info', title, id, class: className } = Astro.props;",
		expectFail: 'Callout.astro defaults variant to a literal tone',
	},
	{
		// The variant-to-class interpolation. Without it every callout
		// renders the same tone regardless of the variant prop passed.
		name: 'the variant is hardcoded into the class list',
		file: CA,
		from: "class:list={['cm-callout', `cm-callout--${variant}`, className]}",
		to: "class:list={['cm-callout', 'cm-callout--info', className]}",
		expectFail: 'Callout.astro does not interpolate the variant prop',
	},
	{
		// The mark's aria-hidden. Without it, a screen reader announces
		// the decorative glyph (or whatever text ends up in the span)
		// before the sentence that names what is empty.
		name: 'the mark span loses aria-hidden',
		file: CA,
		from: '<span class="cm-callout__mark" aria-hidden="true"></span>{title}',
		to: '<span class="cm-callout__mark"></span>{title}',
		expectFail: 'Callout.astro does not render an empty, aria-hidden cm-callout__mark span',
	},
	{
		// A second way to set the glyph. The whole point of the prop-free
		// mark is that it can never drift from the CSS ::before rule for
		// the variant - a mark prop would give a caller exactly that.
		name: 'Props gains a mark prop',
		file: CA,
		from: '\t/** The one-line label after the glyph, e.g. "Note" or "Warning". */\n\ttitle: string;',
		to: '\t/** The one-line label after the glyph, e.g. "Note" or "Warning". */\n\ttitle: string;\n\t/** Glyph override - should not exist. */\n\tmark?: string;',
		expectFail: "Callout.astro's Props interface declares a mark prop",
	},
	{
		// The title row's own class. Without it the title paragraph is
		// unstyled and unfindable by anything that reads .cm-callout__title.
		name: 'the title paragraph loses its class',
		file: CA,
		from: '<p class="cm-callout__title">',
		to: '<p>',
		expectFail: 'Callout.astro does not render a cm-callout__title paragraph',
	},
	{
		// The title interpolation. Without it every callout reads "Note"
		// regardless of what the caller actually passed.
		name: 'the title prop is no longer interpolated',
		file: CA,
		from: '></span>{title}',
		to: '></span>Note',
		expectFail: 'Callout.astro does not interpolate the title prop',
	},
	{
		// The body wrapper's own class. Without it .cm-callout__body's
		// first/last-child margin reset never applies to the slotted content.
		name: 'the body wrapper loses its class',
		file: CA,
		from: '<div class="cm-callout__body">',
		to: '<div>',
		expectFail: 'Callout.astro does not render a cm-callout__body wrapper',
	},
	{
		// The slot itself. Without it, nothing the caller passes as
		// children ever reaches the page - a silent content loss.
		name: 'the slot is removed from the body wrapper',
		file: CA,
		from: '\t\t<slot />\n',
		to: '',
		expectFail: 'Callout.astro does not render <slot /> inside the cm-callout__body wrapper',
	},
	{
		// The demonstration. A wrapper only ever read in its own file is a
		// promise, not a product.
		name: 'the showcase stops importing Callout.astro',
		file: SHOW,
		from: "import Callout from '../astro/Callout.astro';\n",
		to: '',
		expectFail: 'the showcase does not import Callout.astro',
	},
	{
		// One of the four variants disappears from the showcase entirely -
		// the count check (exactly 4) and the per-variant check should
		// both notice.
		name: 'the showcase drops its "ok" (Tip) <Callout> specimen',
		file: SHOW,
		from: '\t\t\t\t\t\t<Callout variant="ok" title="Tip">\n\t\t\t\t\t\t\t<p>The body is free-form: more than one paragraph is normal, and the box\'s own padding is the only space above the first line and below the last.</p>\n\t\t\t\t\t\t\t<p>This second paragraph proves the first/last-child margin reset: there is no doubled gap between it and the one above.</p>\n\t\t\t\t\t\t</Callout>\n',
		to: '',
		expectFail: 'expected exactly 4 (info/ok/warn/err)',
	},
	{
		// The multi-paragraph specimen loses its second paragraph - without
		// it, the first/last-child margin reset is never exercised by the
		// showcase at all.
		name: 'the "Tip" specimen loses its second paragraph',
		file: SHOW,
		from: "\t\t\t\t\t\t\t<p>This second paragraph proves the first/last-child margin reset: there is no doubled gap between it and the one above.</p>\n",
		to: '',
		expectFail: 'no callout specimen passes a multi-paragraph body',
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
