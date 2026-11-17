#!/usr/bin/env node
/**
 * mutation: hidden means hidden
 *
 * The five "hidden" checks in tests/run.mjs, each made to fail. The
 * match is on the suite's `FAIL  <name>` line, never on the name alone,
 * which the suite also prints for a pass. A pattern that does not match
 * its file is a NO-OP and exits 2.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const BASE = 'src/styles/base.css';
const COMP = 'src/styles/components.css';
const README = 'README.md';
const TWIN = "[class^='cm-'][hidden]:not([hidden='until-found']),\n[class*=' cm-'][hidden]:not([hidden='until-found']) { display: none !important; }";

const MUTATIONS = [
	{ name: 'the base rule loses its importance', file: BASE,
		from: "[hidden]:not([hidden='until-found']) { display: none !important; }", to: "[hidden]:not([hidden='until-found']) { display: none; }",
		expectFail: 'hidden: the base layer hides every [hidden] element, with importance' },
	{ name: 'the scoped twin is deleted', file: COMP, from: TWIN, to: '',
		expectFail: 'hidden: a scoped adoption gets the same rule, held to library classes' },
	{ name: 'the scoped twin misses a class that is not first', file: COMP, from: TWIN,
		to: "[class^='cm-'][hidden]:not([hidden='until-found']) { display: none !important; }",
		expectFail: 'hidden: a scoped adoption gets the same rule, held to library classes' },
	{ name: 'a component forces itself visible', file: COMP,
		from: '.cm-meter__track--stack { display: flex; }', to: '.cm-meter__track--stack { display: flex !important; }',
		expectFail: 'hidden: nothing in the library can out-rank it' },
	{ name: 'until-found is swallowed', file: BASE,
		from: "[hidden]:not([hidden='until-found']) { display: none !important; }", to: '[hidden] { display: none !important; }',
		expectFail: 'hidden: until-found is left to the platform' },
	{ name: 'the README section is renamed away', file: README,
		from: '### The `hidden` attribute', to: '### Attributes',
		expectFail: 'hidden: the README says the attribute is enough' },
];

let caught = 0, missed = 0, noop = 0;
for (const mut of MUTATIONS) {
	const file = join(root, mut.file);
	const orig = readFileSync(file, 'utf8');
	const at = orig.indexOf(mut.from);
	if (at === -1) { noop++; console.log(`NO-OP  ${mut.name}\n       pattern did not match ${mut.file} - FIX THE HARNESS`); continue; }
	writeFileSync(file, orig.slice(0, at) + mut.to + orig.slice(at + mut.from.length));
	try {
		const out = spawnSync('node', [join(root, 'tests/run.mjs')], { encoding: 'utf8' }).stdout || '';
		if (out.includes(`FAIL  ${mut.expectFail}\n`)) {
			caught++;
			console.log(`caught ${mut.name}\n       -> ${mut.expectFail}\n          ${out.split(`FAIL  ${mut.expectFail}\n`)[1].split('\n')[0].trim().slice(0, 200)}`);
		} else { missed++; console.log(`MISSED ${mut.name}\n       expected: ${mut.expectFail}`); }
	} finally { writeFileSync(file, orig); }
}
console.log(`\n${MUTATIONS.length} mutations: ${caught} caught, ${missed} missed, ${noop} no-op`);
if (noop) process.exit(2);
process.exit(missed ? 1 : 0);
