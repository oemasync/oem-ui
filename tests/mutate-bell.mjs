#!/usr/bin/env node
/**
 * mutation: cm-bell — the topbar notification trigger (batch 40)
 *
 * Every assertion in the batch-40 block of tests/run.mjs is a guess
 * until it has been made to fail. This harness breaks the exact thing
 * each check guards, runs the suite, and reports which check fired.
 *
 * A pattern that no longer matches the source is a NO-OP — a failure of
 * THIS file, never a pass. Zero no-ops is required for the cycle's
 * caught-count to mean anything.
 *
 * Two lesson-driven rules are baked in here:
 *  1. Every pattern is UNIQUE to the bell (anchored on a bell class or
 *     the bell's own aria-label). A bare class in this library matches
 *     an earlier component and the mutant silently changes the wrong
 *     node — that is how the artwork dot mutant missed on its first run.
 *  2. Specimen mutants set skipBuild: the checks read the SOURCE, and a
 *     rebuild would overwrite dist/ mid-cycle for no reason.
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
		// The badge must leave the flow to sit ON the corner; position:
		// static is the composition this family exists to replace.
		name: 'the count badge returns to the flow, so it cannot overflow',
		file: COMP,
		from: /(\.cm-bell__count \{[\s\S]*?)position: absolute;/,
		to: '$1position: static;',
		expectFail: 'the count badge is not absolutely positioned, so it cannot overflow',
	},
	{
		// Anchoring decides WHICH corner. Without it the badge floats
		// wherever the absolute box lands and covers the icon.
		name: 'the count badge loses its corner anchor',
		file: COMP,
		from: /(\.cm-bell__count \{[\s\S]*?)inset-inline-end: 0;/,
		to: '$1inset-inline-end: auto;',
		expectFail: 'the count badge is not anchored to the inline end',
	},
	{
		// Disconnected has no hue vocabulary; the dashed border is the
		// whole marker. A solid border makes it a normal bell.
		name: 'the disconnected state loses its dashed marker',
		file: COMP,
		from: /(\.cm-bell--off \{[\s\S]*?)border-style: dashed;/,
		to: '$1border-style: solid;',
		expectFail: 'the disconnected state has no dashed provisional border',
	},
	{
		// The cap must pin a width or 9 -> 100 reflows the whole topbar.
		name: 'the capped count stops pinning its width',
		file: COMP,
		from: /(\.cm-bell__count\[data-overflow\] \{[\s\S]*?)inline-size: 1\.75rem;/,
		to: '$1inline-size: auto;',
		expectFail: 'the capped count does not pin its width',
	},
	{
		// Whole-rule deletion: the class-existence check must fire.
		name: 'the disconnected rule is deleted from the library',
		file: COMP,
		from: /\.cm-bell--off \{[\s\S]*?\n\}\n/,
		to: '',
		expectFail: 'the cm-bell--off rule is not defined in the library',
	},
	{
		// The specimen must demonstrate every state; drop the all-read
		// trigger and two states remain.
		name: 'the all-read trigger is deleted from the specimen',
		file: SHOW,
		from: /<button class="cm-bell" type="button" aria-label="Notifications, none unread">[\s\S]*?<\/button>\n/,
		to: '',
		expectFail: 'all three states must render: unread, all-read, disconnected',
		skipBuild: true,
	},
	{
		// The a11y bar: a badge is not a button name.
		name: 'the bell buttons lose their accessible names',
		file: SHOW,
		from: / aria-label="Notifications,[^"]*"/g,
		to: '',
		expectFail: 'each bell button needs an accessible name that includes its count/state',
		skipBuild: true,
	},
	{
		// The connected bell must not carry the disconnected modifier --
		// otherwise "disconnected is drawn" passes on a bell that is not.
		name: 'the disconnected modifier is dropped from the specimen',
		file: SHOW,
		from: /class="cm-bell cm-bell--off" type="button" aria-label="Notifications, disconnected"/,
		to: 'class="cm-bell" type="button" aria-label="Notifications, disconnected"',
		expectFail: 'the disconnected state is not demonstrated',
		skipBuild: true,
	},
	{
		// The unread state's badge is the count channel.
		name: 'the unread badge is deleted from the specimen',
		file: SHOW,
		from: /<span class="cm-bell__count">3<\/span>\n/,
		to: '',
		expectFail: 'the unread state shows no count badge',
		skipBuild: true,
	},
	{
		// Capping is demonstrated, not just styled.
		name: 'the capped count loses its marker attribute',
		file: SHOW,
		from: /<span class="cm-bell__count" data-overflow>99\+<\/span>/,
		to: '<span class="cm-bell__count">99+</span>',
		expectFail: 'the capped count is not demonstrated',
		skipBuild: true,
	},
	{
		// A component the docs never name is one a consumer reinvents.
		name: 'the README bell section is renamed away',
		file: README,
		from: /cm-bell/g,
		to: 'cm-notifications',
		expectFail: 'the README never mentions cm-bell',
		skipBuild: true,
	},
	{
		// The recorded DECISION is the point of this gap; losing it
		// re-opens a question that was answered once.
		name: 'the README stops recording why the bell is a family',
		file: README,
		from: /Gap 7/g,
		to: 'the gap',
		expectFail: 'the README never records why the bell is a family',
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
