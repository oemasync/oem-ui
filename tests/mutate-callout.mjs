#!/usr/bin/env node
/**
 * mutation: cm-callout, the in-prose admonition
 *
 * Every check in the "callout" block of tests/run.mjs is a guess until it
 * has been made to fail. Each mutant below breaks the one thing a check
 * guards, runs the suite, and requires THAT check to fail.
 *
 * "Fail" is read strictly: the suite prints `FAIL  <name>` for a failed
 * check and `  ok  <name>` for a passing one, so looking for the name
 * alone would call every mutant caught. The match is on the FAIL line.
 *
 * A pattern that no longer matches its file is a NO-OP, which is a
 * failure of this harness, never a pass: exit 2.
 *
 * One mutant changes what the showcase renders in a way only visible on
 * the BUILT page (duplicating a variant class), so it rebuilds first.
 * The build is restored at the end.
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

const C = {
	shape: 'callout: the base rule, title and body carry the documented shape',
	glyph: 'callout: each variant glyph matches the one the rest of the library already uses for that tone',
	grey: 'callout: every variant falls back to the exact grey the README documents for that tone',
	gate: 'callout: the chroma gate lists all four callout selectors beside the alert ones',
	margin: 'callout: outside .cm-prose it carries no margin of its own, matching .cm-alert',
	showcase: 'callout: the showcase demonstrates all four variants inside .cm-prose, one with a multi-paragraph body',
	built: 'callout: the built page renders all four variants exactly once, each with its mark',
	readme: 'callout: the README documents the prose margin, the body reset and the chroma participation',
};

// `nth` picks which occurrence of a string pattern to replace (1-based).
const MUTATIONS = [
	{ name: 'the box stops being a column', file: COMP, nth: 1,
		from: '.cm-callout {\n\tdisplay: flex;\n\tflex-direction: column;',
		to: '.cm-callout {\n\tdisplay: flex;\n\tflex-direction: row;', expectFail: C.shape },
	{ name: 'the accent edge loses its weight', file: COMP, nth: 1,
		from: '.cm-callout {\n	display: flex;\n	flex-direction: column;\n	gap: var(--space-2);\n	padding: var(--space-4);\n	border: 1px solid var(--line);\n	border-inline-start-width: 3px;',
		to: '.cm-callout {\n	display: flex;\n	flex-direction: column;\n	gap: var(--space-2);\n	padding: var(--space-4);\n	border: 1px solid var(--line);\n	border-inline-start-width: 1px;', expectFail: C.shape },
	{ name: 'the body keeps a gap above its first paragraph', file: COMP, nth: 1,
		from: '.cm-callout__body > :first-child { margin-top: 0; }',
		to: '.cm-callout__body > :first-child { margin-top: 0.5em; }', expectFail: C.shape },
	{ name: 'the body keeps a gap below its last paragraph', file: COMP, nth: 1,
		from: '.cm-callout__body > :last-child { margin-bottom: 0; }',
		to: '.cm-callout__body > :last-child { margin-bottom: 0.5em; }', expectFail: C.shape },
	{ name: 'the ok mark borrows the warn glyph', file: COMP, nth: 1,
		from: ".cm-callout--ok .cm-callout__mark::before { content: '\\25cf\\00a0'; }",
		to: ".cm-callout--ok .cm-callout__mark::before { content: '\\25b2\\00a0'; }", expectFail: C.glyph },
	{ name: 'the info mark loses its glyph entirely', file: COMP, nth: 1,
		from: ".cm-callout--info .cm-callout__mark::before { content: '\\2139\\00a0'; }",
		to: ".cm-callout--info .cm-callout__mark::before { content: ''; }", expectFail: C.glyph },
	{ name: 'the err edge falls back to the wrong grey', file: COMP, nth: 1,
		from: '.cm-callout--err { border-inline-start-color: var(--tone, var(--ink)); }',
		to: '.cm-callout--err { border-inline-start-color: var(--tone, var(--ink-dim)); }', expectFail: C.grey },
	{ name: 'the warn edge falls back to ok\u2019s grey', file: COMP, nth: 1,
		from: '.cm-callout--warn { border-inline-start-color: var(--tone, var(--ink-faint)); }',
		to: '.cm-callout--warn { border-inline-start-color: var(--tone, var(--ink-dim)); }', expectFail: C.grey },
	{ name: 'the warn setter loses its gate', file: COMP, nth: 1,
		from: '[data-cm-chroma] :where(.cm-tone--warn, .cm-chip--warn, .cm-alert--warn, .cm-callout--warn),\n[data-cm-chroma]:where(.cm-tone--warn, .cm-chip--warn, .cm-alert--warn, .cm-callout--warn) {',
		to: '[data-cm-chroma] :where(.cm-tone--warn, .cm-chip--warn, .cm-alert--warn),\n[data-cm-chroma]:where(.cm-tone--warn, .cm-chip--warn, .cm-alert--warn) {', expectFail: C.gate },
	{ name: 'the info setter loses its gate', file: COMP, nth: 1,
		from: '[data-cm-chroma] :where(.cm-tone--info, .cm-chip--info, .cm-alert--info, .cm-callout--info),\n[data-cm-chroma]:where(.cm-tone--info, .cm-chip--info, .cm-alert--info, .cm-callout--info) {',
		to: '[data-cm-chroma] :where(.cm-tone--info, .cm-chip--info, .cm-alert--info),\n[data-cm-chroma]:where(.cm-tone--info, .cm-chip--info, .cm-alert--info) {', expectFail: C.gate },
	{ name: 'the prose rhythm drifts off the paragraph margin', file: COMP, nth: 1,
		from: '.cm-prose .cm-callout { margin: 0 0 1.1em; }',
		to: '.cm-prose .cm-callout { margin: 0 0 1.2em; }', expectFail: C.margin },
	{ name: 'the bare box grows its own margin', file: COMP, nth: 1,
		from: '.cm-callout {\n\tdisplay: flex;\n\tflex-direction: column;\n\tgap: var(--space-2);',
		to: '.cm-callout {\n\tdisplay: flex;\n\tflex-direction: column;\n\tmargin: 0 0 1em;\n\tgap: var(--space-2);', expectFail: C.margin },
	{ name: 'the Tip specimen loses its second paragraph', file: SHOW, nth: 1,
		from: '<p>The body is free-form: more than one paragraph is normal, and the box\'s own padding is the only space above the first line and below the last.</p>\n\t\t\t\t\t\t\t\t<p>This second paragraph proves the first/last-child margin reset: there is no doubled gap between it and the one above.</p>',
		to: '<p>The body is free-form: more than one paragraph is normal, and the box\'s own padding is the only space above the first line and below the last.</p>', expectFail: C.showcase },
	{ name: 'the err specimen is silently retyped as ok', file: SHOW, nth: 1, build: true,
		from: '<div class="cm-callout cm-callout--err">', to: '<div class="cm-callout cm-callout--ok">', expectFail: C.built },
	{ name: 'the README drops the chroma attribute', file: README, nth: 1,
		from: '`data-cm-chroma` colours the edge and the mark exactly the way it colours',
		to: 'something colours the edge and the mark exactly the way it colours', expectFail: C.readme },
	{ name: 'the README drops the reset wording', file: README, nth: 1,
		from: '**`.cm-callout__body > :first-child` / `:last-child` reset their own',
		to: '**`.cm-callout__body` handles its own', expectFail: C.readme },
];

const replaceNth = (src, from, to, nth) => {
	if (from instanceof RegExp) return src.replace(from, to);
	let at = -1;
	for (let i = 0; i < nth; i++) { at = src.indexOf(from, at + 1); if (at === -1) return src; }
	return src.slice(0, at) + to + src.slice(at + from.length);
};
const runSuite = () => (spawnSync('node', [join(root, 'tests/run.mjs')], { encoding: 'utf8', maxBuffer: 1024 * 1024 * 64 }).stdout || '');
const build = () => spawnSync('npm', ['run', 'build'], { cwd: root, encoding: 'utf8' }).status === 0;

const only = process.argv[2];
const range = process.argv.find((a) => a.startsWith('--range='));
let lo = 0, hi = MUTATIONS.length - 1;
if (range) { const [a, b] = range.split('=')[1].split(','); lo = Number(a) - 1; hi = Number(b) - 1; }

let caught = 0, missed = 0, noop = 0, rebuilt = false;
for (let idx = 0; idx < MUTATIONS.length; idx++) {
	if (idx < lo || idx > hi) continue;
	const mut = MUTATIONS[idx];
	if (only && !range && !mut.name.includes(only)) continue;
	const file = p(mut.file);
	const orig = readFileSync(file, 'utf8');
	const mutated = replaceNth(orig, mut.from, mut.to, mut.nth || 1);
	if (mutated === orig) {
		noop++;
		console.log(`NO-OP  [${idx + 1}] ${mut.name}\n       pattern did not match ${mut.file} - FIX THE HARNESS`);
		continue;
	}
	writeFileSync(file, mutated);
	try {
		if (mut.build) { rebuilt = true; if (!build()) { missed++; console.log(`MISSED [${idx + 1}] ${mut.name}\n       the mutant did not build, so the check never saw it`); continue; } }
		const out = runSuite();
		if (out.includes(`FAIL  ${mut.expectFail}\n`)) {
			caught++;
			const why = out.split(`FAIL  ${mut.expectFail}\n`)[1].split('\n')[0].trim();
			console.log(`caught [${idx + 1}] ${mut.name}\n       -> ${mut.expectFail}\n          ${why.slice(0, 200)}`);
		} else {
			missed++;
			console.log(`MISSED [${idx + 1}] ${mut.name}\n       expected: ${mut.expectFail}`);
		}
	} finally {
		writeFileSync(file, orig);
		const restored = readFileSync(file, 'utf8');
		if (restored !== orig) { console.log(`RESTORE FAILED on ${mut.file} - abandon this run`); process.exit(4); }
	}
}
if (rebuilt && !build()) { console.log('the restoring build FAILED - dist/ is stale'); process.exit(3); }
console.log(`\n${caught + missed + noop} mutations: ${caught} caught, ${missed} missed, ${noop} no-op`);
if (noop) process.exit(2);
process.exit(missed ? 1 : 0);
