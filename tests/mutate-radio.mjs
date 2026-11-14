#!/usr/bin/env node
/**
 * mutation: the cm-radio row + group, the choice family's third member
 *
 * Every assertion added this cycle is a guess until it has been made to
 * fail. This harness breaks the exact thing each check guards, runs the
 * suite, and reports which check fired. The contract tests read the source
 * files (components.css, the showcase), so skipBuild keeps the sweep fast -
 * the build is verified separately in the normal cycle flow.
 *
 * A pattern that no longer matches the source is a NO-OP - a failure of
 * THIS file, never a pass. The count reported in the cycle note must have
 * zero in it, or the harness itself is broken and the number is worthless.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const p = (f) => join(root, f);
const COMP = 'src/styles/components.css';
const SHOW = 'src/pages/[...family].astro';

const MUTATIONS = [
	{
		// The tap floor. Without it the only target is the 17px disc and the
		// word beside it is dead space - the same defect cm-check fills for
		// the checkbox.
		name: 'the radio row loses its tap floor',
		file: COMP,
		from: /\.cm-radio \{\s*display: flex;\s*align-items: center;\s*gap: var\(--space-2\);\s*min-height: var\(--tap\);/,
		to: '.cm-radio {\n\tdisplay: flex;\n\talign-items: center;\n\tgap: var(--space-2);',
		expectFail: 'the row must carry the tap floor',
		skipBuild: true,
	},
	{
		// The optical line. The disc is a flex child; without align-self:
		// center a 17px circle sits above the 15px text instead of on it.
		name: 'the radio circle is no longer centred on the label line',
		file: COMP,
		from: /\.cm-radio > input\[type='radio'\] \{ align-self: center; \}/,
		to: '.cm-radio > input[type=\'radio\'] { }',
		expectFail: 'the circle must be centred on the label line',
		skipBuild: true,
	},
	{
		// The hover. Lightening only the circle leaves the affordance on the
		// part that is not the target; the LABEL must carry it.
		name: 'the radio hover no longer lightens the label',
		file: COMP,
		from: /\.cm-radio:hover \{ color: var\(--ink\); \}/,
		to: '.cm-radio:hover { color: var(--ink-dim); }',
		expectFail: 'hover must lighten the LABEL too',
		skipBuild: true,
	},
	{
		// The fieldset trap. cm-quiz__item measured it: min-inline-size: 0
		// does not override a fieldset's min-content default in WebKit the
		// way min-width: 0 does, so an over-long caption runs the page
		// sideways. The group must pin min-width.
		name: 'the radio group loses its fieldset min-width',
		file: COMP,
		from: /\.cm-radio__group \{\s*margin: 0;\s*padding: 0;\s*border: 0;\s*min-width: 0;/,
		to: '.cm-radio__group {\n\tmargin: 0;\n\tpadding: 0;\n\tborder: 0;',
		expectFail: 'the group must pin min-width: 0',
		skipBuild: true,
	},
	{
		// The row rhythm. Without display: grid the labels fall back to their
		// own margins, which are ad-hoc, not a step on the scale.
		name: 'the radio group stops laying its rows on a grid',
		file: COMP,
		from: /\.cm-radio__group \{[^}]*\}/,
		to: '.cm-radio__group {\n\tmargin: 0;\n\tpadding: 0;\n\tborder: 0;\n\tmin-width: 0;\n\tgap: var(--space-1);\n}',
		expectFail: 'the rows must sit on a uniform gap',
		skipBuild: true,
	},
	{
		// The caption. A field label reads at ink weight; the faint row colour
		// is what the OPTIONS use, not the thing that names them.
		name: 'the radio group legend drops its label weight',
		file: COMP,
		from: /\.cm-radio__group > legend \{[^}]*\}/,
		to: '.cm-radio__group > legend {\n\tdisplay: block;\n\tpadding: 0;\n\tmargin-block-end: var(--space-2);\n\tfont-size: var(--text-sm);\n\tcolor: var(--ink-dim);\n}',
		expectFail: 'the caption must read as the field label',
		skipBuild: true,
	},
	{
		// The rule itself, deleted. The component is gone; the suite must say
		// so by name, not read as a silent pass.
		name: 'the cm-radio rule is deleted',
		file: COMP,
		from: /\.cm-radio \{[^}]*\}/,
		to: '/* the cm-radio rule was deleted by the mutation sweep */',
		expectFail: '.cm-radio is not defined',
		skipBuild: true,
	},
	{
		// The demonstration, deleted. A component that is only ever read in the
		// CSS is a promise, not a product; the showcase specimen is the proof
		// it renders in its intended context.
		name: 'the radio group specimen is removed from the showcase',
		file: SHOW,
		from: /<fieldset class="cm-radio__group"[\s\S]*?<\/fieldset>/,
		to: '',
		expectFail: 'the showcase must render a cm-radio__group fieldset',
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
		if (out.includes(mut.expectFail) && /FAIL/.test(out)) {
			caught++;
			console.log(`caught ${mut.name}\n       -> ${mut.expectFail}`);
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
