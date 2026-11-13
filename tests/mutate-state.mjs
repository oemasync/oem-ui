#!/usr/bin/env node
/**
 * mutation: the <State> empty-state wrapper
 *
 * Every assertion added in this cycle is a guess until it has been made
 * to fail. This harness breaks the exact thing each check guards, runs
 * the suite, and reports which check fired.
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
const COMP = 'src/styles/components.css';
const SHOW = 'src/pages/[...family].astro';
const WRAP = 'src/astro/State.astro';

const MUTATIONS = [
	{
		// The bug from the previous cycle, back again: the documented
		// one-liner loses its rule. A consumer copying the README
		// example renders a bare <p> on UA margins.
		name: 'the cm-state__text rule is deleted entirely',
		file: COMP,
		from: /\.cm-state__text \{ margin: 0 auto; max-width: var\(--measure-narrow\); color: var\(--ink-faint\); \}/,
		to: '',
		expectFail: '.cm-state__text has no rule',
		skipBuild: true,
	},
	{
		// The tier drift: the rule still exists and still says
		// something, just not the right thing. A presence-only check
		// passes this forever; only the token assertion can see it.
		name: 'the one-liner climbs one tier to --ink-dim',
		file: COMP,
		from: /\.cm-state__text \{ margin: 0 auto; max-width: var\(--measure-narrow\); color: var\(--ink-faint\); \}/,
		to: '.cm-state__text { margin: 0 auto; max-width: var(--measure-narrow); color: var(--ink-dim); }',
		expectFail: 'must resolve to the faint tier',
		skipBuild: true,
	},
	{
		// The tap floor is the only reason the way out of an empty
		// state is reachable by a thumb on a coarse pointer. Zero is
		// declared, so a property-presence test passes the mutant.
		name: 'the coarse-pointer tap floor on the actions row is zeroed',
		file: COMP,
		from: /\.cm-state__actions \.cm-btn \{ min-height: var\(--tap\); \}/,
		to: '.cm-state__actions .cm-btn { min-height: 0; }',
		expectFail: 'min-height: var(--tap)',
		skipBuild: true,
	},
	{
		// The mark without its flag reads "circle slash" out loud,
		// before the sentence that says what is empty.
		name: 'the wrapper mark loses its aria-hidden',
		file: WRAP,
		from: /class="cm-state__mark" aria-hidden="true"/,
		to: 'class="cm-state__mark"',
		expectFail: 'must hide the mark from assistive tech',
		skipBuild: true,
	},
	{
		// class:list is the composition surface: a bare class literal
		// drops the extra-classes prop and the modifier path with it.
		// The doc comment still names the class, so a bare-name check
		// stays green.
		name: 'the wrapper degrades from class:list to a bare class',
		file: WRAP,
		from: /class:list=\{\['cm-state', className\]\}/,
		to: 'class="cm-state"',
		expectFail: 'does not emit the cm-state wrapper',
		skipBuild: true,
	},
	{
		// The escape trap. A slot in place of the string prop lets a
		// live <a> into the one-liner, where it resolves to --ink-dim
		// at 1.24:1 against the faint text - invisible in both themes.
		name: 'the one-liner becomes a slot a link can hide in',
		file: WRAP,
		from: /\{text && <p class="cm-state__text">\{text\}<\/p>\}/,
		to: '{text && <p class="cm-state__text"><slot name="text" /></p>}',
		expectFail: 'must render the one-liner from a string prop',
		skipBuild: true,
	},
	{
		// The invisible-specimen trap: the actions specimen loses its
		// content, so the section still builds and the heading is still
		// there. Only the specimen assertion can see it.
		name: 'the actions specimen loses its button',
		file: SHOW,
		from: /					<a slot="actions" class="cm-btn cm-btn--sm" href="#states">create the first one<\/a>\n/,
		to: '',
		expectFail: 'the wrapper body + actions specimen is missing from the states section',
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
