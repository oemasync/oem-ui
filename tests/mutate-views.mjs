#!/usr/bin/env node
/**
 * mutation: saved views — filter chips and view toggles (batch 39)
 *
 * Every assertion in the batch-39 block of tests/run.mjs is a guess
 * until it has been made to fail. This harness breaks the exact thing
 * each check guards, runs the suite, and reports which check fired.
 *
 * A pattern that no longer matches the source is a NO-OP — a failure of
 * THIS file, never a pass. Zero no-ops is required for the cycle's
 * caught-count to mean anything.
 *
 * Every pattern is anchored to the SAVED-VIEWS toolbar (its chip text,
 * its view labels, or its own class), because a bare class name in this
 * library matches an earlier component and the mutant silently changes
 * the wrong node.
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
		// The filters slot is the chip row; without it chips drop into
		// the toolbar's default centred flex and stop reading as state.
		name: 'the filters slot is deleted from the library',
		file: COMP,
		from: /\.cm-toolbar__filters \{[\s\S]*?\n\}\n/,
		to: '',
		expectFail: 'the cm-toolbar__filters rule is not defined in the library',
	},
	{
		// Whole-rule deletion: the class-existence check must fire. The
		// views slot is the half of the composition that keeps saved
		// views from stacking under the chips on a phone.
		name: 'the views slot rule is deleted from the library',
		file: COMP,
		from: /\.cm-toolbar__views \{[\s\S]*?\n\}\n/,
		to: '',
		expectFail: 'the cm-toolbar__views rule is not defined in the library',
	},
	{
		// The remove control is a REAL BUTTON per the family contract —
		// a clickable span has no keyboard, no focus ring, no name.
		name: 'the chip remove control stops being a real button',
		file: SHOW,
		from: /<button class="cm-chip__x" type="button" aria-label="Remove filter: status failing">/,
		to: '<span class="cm-chip__x" aria-hidden="true">',
		expectFail: 'a chip remove control is not a real button',
		skipBuild: true,
	},
	{
		// The accessible name is what tells a screen reader WHICH
		// filter a bare ✕ removes.
		name: 'the chip remove buttons lose their accessible names',
		file: SHOW,
		from: / aria-label="Remove filter:[^"]*"/g,
		to: '',
		expectFail: 'a chip remove control has no accessible name',
		skipBuild: true,
	},
	{
		// A pressed view must be a state, not a tint.
		name: 'the pressed view style rule is deleted',
		file: COMP,
		from: /\.cm-toolbar__view\[aria-pressed='true'\] \{[\s\S]*?\n\}\n/,
		to: '',
		expectFail: 'the pressed view has no visual state',
	},
	{
		// "Save this view" must stay a real button that opens the naming
		// step — a span with role=button is the slop this library bans.
		name: 'the save affordance stops being a real button',
		file: SHOW,
		from: /<button class="cm-toolbar__view cm-toolbar__view-save" type="button">/,
		to: '<span class="cm-toolbar__view-save">',
		expectFail: 'the save affordance is not a real button',
		skipBuild: true,
	},
	{
		// The save affordance must be VISIBLE as the dashed affordance,
		// not vanish into a normal view button.
		name: 'the save affordance loses its dashed style',
		file: COMP,
		from: /(\.cm-toolbar__view-save \{[\s\S]*?)border-style: dashed;/,
		to: '$1border-style: solid;',
		expectFail: 'the save affordance has no dashed styling',
	},
	{
		// Long view names must ellipsize, not widen the toolbar.
		name: 'the view label loses its ellipsis',
		file: COMP,
		from: /(\.cm-toolbar__view-label \{[\s\S]*?)text-overflow: ellipsis;/,
		to: '$1text-overflow: clip;',
		expectFail: 'the view label does not ellipsize',
	},
	{
		// A component the docs never name is one a consumer reinvents.
		name: 'the README saved-views section is renamed away',
		file: README,
		from: /saved views/gi,
		to: 'filters',
		expectFail: 'the README never documents saved views',
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
	const mutated = orig.replace(mut.from, mut.to);
	if (mutated === orig) {
		noop++;
		console.log(`NO-OP  ${mut.name}\n       pattern did not match ${mut.file} - FIX THE HARNESS`);
		continue;
	}
	writeFileSync(file, mutated);
	try {
		const out = runSuite();
		// The suite prints "FAIL  <check name>" with TWO spaces and puts
		// the assertion message on the NEXT line. A string expectation
		// may be either, so both lines of each FAIL block are tested.
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
