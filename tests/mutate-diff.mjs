#!/usr/bin/env node
/**
 * mutation: cm-diff — the word-level diff rows (batch 34)
 *
 * Every assertion in the batch-34 block of tests/run.mjs is a guess
 * until it has been made to fail. This harness breaks the exact thing
 * each check guards, runs the suite, and reports which check fired.
 *
 * A pattern that no longer matches the source is a NO-OP - a failure of
 * THIS file, never a pass. The count reported in the cycle note must
 * have zero in it, or the harness itself is broken and the number is
 * worthless.
 *
 * All mutations target files the batch-34 checks read directly
 * (components.css, the showcase, the README, the runtime), so no astro
 * build is needed between mutants - which is also what keeps the cycle
 * under a minute.
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
const RUNTIME = 'src/js/cli-mono.js';

const MUTATIONS = [
	{
		// The glyph mapping is the "not colour alone" backbone: blank
		// create's prefix and the row renders with an empty gutter.
		name: "create's glyph prefix is removed",
		file: COMP,
		from: /\.cm-diff__row\[data-op='create'\]::before \{ content: '\+'/,
		to: ".cm-diff__row[data-op='create']::before { content: ' '",
		expectFail: 'each op maps to a DISTINCT glyph prefix, no two alike',
		skipBuild: true,
	},
	{
		// Two ops, one glyph - the mutant a palette swap slips past.
		name: "delete borrows create's glyph",
		file: COMP,
		from: /\.cm-diff__row\[data-op='delete'\]::before \{ content: '−'/,
		to: ".cm-diff__row[data-op='delete']::before { content: '+'",
		expectFail: 'each op maps to a DISTINCT glyph prefix, no two alike',
		skipBuild: true,
	},
	{
		// The decoration half of the a11y rule: delete loses its strike
		// and now differs from create only by hue.
		name: 'delete loses its line-through (hue-only op)',
		file: COMP,
		from: /\.cm-diff__row\[data-op='delete'\] \.cm-diff__val \{ text-decoration: line-through;/,
		to: ".cm-diff__row[data-op='delete'] .cm-diff__val {",
		expectFail: 'each op carries a distinct TEXT DECORATION, not just a hue',
		skipBuild: true,
	},
	{
		name: 'create loses its underline (hue-only op)',
		file: COMP,
		from: /\.cm-diff__row\[data-op='create'\] \.cm-diff__val \{ text-decoration: underline;/,
		to: ".cm-diff__row[data-op='create'] .cm-diff__val {",
		expectFail: 'each op carries a distinct TEXT DECORATION, not just a hue',
		skipBuild: true,
	},
	{
		// The app writes the count; the check ties it to the rows that
		// actually collapsed.
		name: 'the fold summary count drifts from its rows',
		file: SHOW,
		from: /<summary>3 unchanged<\/summary>/,
		to: '<summary>4 unchanged</summary>',
		expectFail: 'the fold counts unchanged rows exactly',
		skipBuild: true,
	},
	{
		// The defect the fold exists to prevent: an unchanged row
		// rendered inline, where the reader must wade through it.
		name: 'a same row leaks outside the fold',
		file: SHOW,
		from: /<h3 class="cm-kicker" style="margin-top:var\(--space-4\)">long values<\/h3>/,
		to: '<li class="cm-diff__row" data-op="same"><span class="cm-diff__op">same</span><span class="cm-diff__val">leaked</span></li>\n				<h3 class="cm-kicker" style="margin-top:var(--space-4)">long values</h3>',
		expectFail: 'the fold counts unchanged rows exactly',
		skipBuild: true,
	},
	{
		// The platform rule: a chevron keyed off a class instead of
		// [open] means the component owns state <details> already has.
		name: 'the fold chevron keys off a class, not [open]',
		file: COMP,
		from: /\.cm-diff__fold\[open\] > summary::after \{ content: '▾'; \}/,
		to: ".cm-diff__fold.is-open > summary::after { content: '▾'; }",
		expectFail: 'the fold is platform expansion — a <details>, not runtime',
		skipBuild: true,
	},
	{
		// The runtime creeping in: a cm-diff reference in cli-mono.js
		// means JS owns what <details> gives away for free.
		name: 'the runtime grows a cm-diff init',
		file: RUNTIME,
		from: /function initYears\(\) \{/,
		to: "function initDiff(root) { /* cm-diff */ }\n\tfunction initYears() {",
		expectFail: 'the fold is platform expansion — a <details>, not runtime',
		skipBuild: true,
	},
	{
		// The fixture discipline: a short-only specimen proves nothing
		// about wrapping, so shrink the long value below the floor.
		name: 'the long value fixture is shortened below the wrap',
		file: SHOW,
		from: /\/config\/rclone\/remotes\/prod-archive: <del class="cm-diff__del">rclone:securesync-legacy-prod<\/del> → <ins class="cm-diff__ins">rclone:securesync-v2-prod<\/ins>/,
		to: 'a: <del class="cm-diff__del">x</del> → <ins class="cm-diff__ins">y</ins>',
		expectFail: 'the specimen exercises a LONG value, or the hanging indent is unproven',
		skipBuild: true,
	},
	{
		// Docs are part of the bar: a component the README never names
		// is one a consumer will reinvent locally.
		name: 'the README section is deleted',
		file: README,
		from: /### Diff rows — `cm-diff`[\s\S]*?(?=\n### JS API)/,
		to: '',
		expectFail: 'the README documents the diff rows',
		skipBuild: true,
	},
	{
		// Dead-CSS direction: kill a rule entirely; the "every cm-diff
		// class is defined" check must fire.
		name: 'the ins span rule is deleted',
		file: COMP,
		from: /\.cm-diff__ins \{[^}]*\}\n/,
		to: '',
		expectFail: 'every cm-diff class is defined in the library',
		skipBuild: true,
	},
	{
		// Demonstration direction: the fold class leaves the markup
		// while its CSS remains - "defined but never rendered".
		name: 'the fold class is dropped from the specimen markup',
		file: SHOW,
		from: /<li class="cm-diff__fold">/,
		to: '<li class="diff-fold">',
		expectFail: 'every cm-diff class is DEMONSTRATED, so none is dead CSS',
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
