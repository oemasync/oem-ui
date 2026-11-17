#!/usr/bin/env node
/**
 * mutation: <Param>, the API-docs parameter/response row wrapper
 *
 * Every assertion added this cycle is a guess until it has been made to
 * fail. This harness breaks the exact thing each check guards, runs the
 * suite, and reports which check fired. Like mutate-endpoint-astro.mjs,
 * every mutant here is source/regex-level (the component's REAL rendered
 * output - both modes reaching the DOM with the right marks - is proven
 * once by the suite's own built-dist check against a real `npm run
 * build`, which this sweep does not rebuild for).
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
const PA = 'src/astro/Param.astro';
const SHOW = 'src/pages/[...family].astro';

const MUTATIONS = [
	{
		// The row. Without cm-param the name/status mark and the
		// description lose the wrapping flex row and its hairline.
		name: 'the wrapper loses its cm-param class',
		file: PA,
		from: '<div class="cm-param">',
		to: '<div class="cm-param-row">',
		expectFail: 'Param.astro does not use the cm-param class',
	},
	{
		// Name mode's identity mark. Without it a parameter name
		// renders with no mono treatment at all.
		name: 'name mode loses its cm-param__name class',
		file: PA,
		from: '<span class="cm-param__name">',
		to: '<span class="cm-param-name">',
		expectFail: 'Param.astro name mode is missing the name element',
	},
	{
		// The required gate. Removing the condition renders the `*`
		// on EVERY parameter, required or not - the same regression
		// the form field's own required prop exists to prevent.
		name: 'the required mark is no longer gated on the required prop',
		file: PA,
		from: '{required && <span class="cm-param__req">*</span>}',
		to: '<span class="cm-param__req">*</span>',
		expectFail: 'Param.astro does not gate the required mark on the required prop',
	},
	{
		// The type gate's status half. Dropping `!status` means a
		// response row (which has no type) would render a stray type
		// badge whenever a caller happened to also pass `type`.
		name: 'the type badge is no longer gated on !status',
		file: PA,
		from: '{!status && type && <span class="cm-param__type">{type}</span>}',
		to: '{type && <span class="cm-param__type">{type}</span>}',
		expectFail: 'Param.astro does not gate the type element on both type AND !status',
	},
	{
		// The in-badge gate's status half, the same shape one level
		// down - a response row could end up with a stray in badge.
		name: 'the in badge is no longer gated on !status',
		file: PA,
		from: '{!status && inLoc && <span class="cm-param__in">{inLoc}</span>}',
		to: '{inLoc && <span class="cm-param__in">{inLoc}</span>}',
		expectFail: 'Param.astro does not gate the in badge on both inLoc AND !status',
	},
	{
		// Status mode's identity mark. A hardcoded tier means every
		// response row renders as "ok" regardless of what the caller
		// passed - a 500 would paint the same mark as a 201.
		name: 'the status-code tier is hardcoded, ignoring the tier prop',
		file: PA,
		from: 'class={`cm-status-code cm-status-code--${tier}`}',
		to: 'class="cm-status-code cm-status-code--ok"',
		expectFail: 'Param.astro status mode does not derive the status-code treatment from the tier prop',
	},
	{
		// The slot. A string prop here would render a live <code>
		// reference inside a description as literal angle brackets -
		// exactly the regression <SectionHead>'s sub slot prevents.
		name: 'the description slot is replaced with a string prop read',
		file: PA,
		from: '<span class="cm-param__desc"><slot /></span>',
		to: '<span class="cm-param__desc">{desc}</span>',
		expectFail: 'Param.astro does not emit <slot /> for the description',
	},
	{
		// The ambiguous-combination guard. Without it, passing both
		// name and status renders a row with no way to tell which
		// mode the caller meant - exactly the silent-drift shape the
		// guard exists to refuse outright.
		name: 'the name-and-status ambiguity guard is disabled',
		file: PA,
		from: 'if (name && status) {',
		to: 'if (false && name && status) {',
		expectFail: 'Param.astro does not guard against name AND status both being given',
	},
	{
		// The incomplete-combination guard. Without it, passing
		// neither renders a row with no identifying mark at all.
		name: 'the neither-name-nor-status guard is disabled',
		file: PA,
		from: 'if (!name && !status) {',
		to: 'if (false && !name && !status) {',
		expectFail: 'Param.astro does not guard against neither name nor status being given',
	},
	{
		// The tier-required guard. Without it, status mode can render
		// cm-status-code with an undefined tier - `cm-status-code--`
		// with nothing after the dashes, matching no rule at all.
		name: 'the status-without-tier guard is disabled',
		file: PA,
		from: 'if (status && !tier) {',
		to: 'if (false && status && !tier) {',
		expectFail: 'Param.astro does not guard against status without tier',
	},
	{
		// The demonstration. A wrapper only ever read in its own file
		// is a promise, not a product - the showcase specimen is the
		// proof it composes correctly in the family it was built for.
		// This is the only showcase specimen carrying `required`, so
		// removing it is caught by the required-mode check, not merely
		// the generic use-count check.
		name: 'the showcase stops rendering <Param> in name mode',
		file: SHOW,
		from: '<Param name="id" type="string" in="path" required>The fox\'s id.</Param>',
		to: '',
		expectFail: 'the showcase never renders <Param> with required',
	},
];

// --range a,b runs MUTATIONS[a..b] inclusive, so a slow full sweep can be
// split across several tool calls that each stay comfortably under a
// hard wall-clock timeout, the same device mutate-endpoint-astro.mjs uses.
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
