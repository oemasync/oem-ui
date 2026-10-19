#!/usr/bin/env node
/**
 * mutation: cm-revert — the countdown-undo banner (batch 35)
 *
 * Every assertion in the batch-35 block of tests/run.mjs is a guess
 * until it has been made to fail. This harness breaks the exact thing
 * each check guards, runs the suite, and reports which check fired.
 *
 * A pattern that no longer matches the source is a NO-OP - a failure of
 * THIS file, never a pass. The count reported in the cycle note must
 * have zero in it, or the harness itself is broken and the number is
 * worthless.
 *
 * All mutations target files the batch-35 checks read directly
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
		// The glyph is the "not colour alone" backbone for the banner.
		// There are 7 rules with the same glyph; the regex must scope to
		// the revert rule's body, or the mutant edits a different rule.
		name: "the revert banner loses its warning glyph",
		file: COMP,
		from: /\.cm-revert::before \{\s+content: '\\25b2\\00a0'/,
		to: ".cm-revert::before {\n	content: ''",
		expectFail: "the banner carries a glyph, so it is not a bare box",
		skipBuild: true,
	},
	{
		// The countdown must be real text with a starting value, not a CSS counter.
		name: 'the countdown slot has no literal starting value',
		file: SHOW,
		from: /data-cm-revert-countdown aria-live="polite">10s</,
		to: 'data-cm-revert-countdown aria-live="polite"></',
		expectFail: "the countdown slot has no literal starting value in the markup",
		skipBuild: true,
	},
	{
		// aria-live must be polite, not assertive (a countdown that interrupts
		// on every tick is worse than a silent one).
		name: 'the countdown is aria-live="assertive" instead of polite',
		file: SHOW,
		from: /data-cm-revert-countdown aria-live="polite"/,
		to: 'data-cm-revert-countdown aria-live="assertive"',
		expectFail: 'the countdown slot is not aria-live="polite"',
		skipBuild: true,
	},
	{
		// The runtime must pause on focusin — a reader inside must not be rushed.
		name: 'initRevert does not listen for focusin',
		file: RUNTIME,
		from: /addEventListener\('focusin', stop\)/,
		to: "/* focusin listener removed */",
		expectFail: "initRevert does not listen for focusin",
		skipBuild: true,
	},
	{
		// The runtime must resume on focusout — otherwise it stays paused forever.
		name: 'initRevert does not listen for focusout',
		file: RUNTIME,
		from: /addEventListener\('focusout'/,
		to: "/* focusout listener removed */",
		expectFail: "initRevert does not listen for focusout",
		skipBuild: true,
	},
	{
		// stop() must clearInterval, not just set a flag — a flag still burns
		// wall-clock and still expires.
		name: 'initRevert does not clearInterval on pause',
		file: RUNTIME,
		from: /clearInterval\(timer\);/,
		to: "/* timer cleared */",
		expectFail: "initRevert does not clearInterval on pause",
		skipBuild: true,
	},
	{
		// Undo must stop the timer — otherwise expire fires after undo.
		name: 'initRevert has no Undo handling',
		file: RUNTIME,
		from: /if \(undo\) undo\.addEventListener\('click', function \(\) \{ resolve\('undo'\); \}\);?/,
		to: "/* undo listener removed */",
		expectFail: "initRevert has no Undo handling",
		skipBuild: true,
	},
	{
		// Apply must stop the timer — otherwise expire fires after apply.
		name: 'initRevert has no Apply handling',
		file: RUNTIME,
		from: /if \(apply\) apply\.addEventListener\('click', function \(\) \{ resolve\('apply'\); \}\);?/,
		to: "/* apply listener removed */",
		expectFail: "initRevert has no Apply handling",
		skipBuild: true,
	},
	{
		// The README must document the component — a component the docs never
		// name is one a consumer will reinvent locally.
		name: 'the README section is deleted',
		file: README,
		from: /### Revert banner — `cm-revert`[\s\S]*?(?=\n### )/,
		to: '',
		expectFail: 'the README documents the revert banner and its runtime',
		skipBuild: true,
	},
	{
		// Dead-CSS direction: kill the status rule entirely.
		// The rule may be followed by a comment, so match to the next section or EOF.
		name: 'the cm-revert__status rule is deleted',
		file: COMP,
		from: /\.cm-revert__status \{[^}]*\}/,
		to: '',
		expectFail: 'every cm-revert class is defined in the library',
		skipBuild: true,
	},
	{
		// Demonstration direction: the countdown class leaves the markup
		// while its CSS remains - "defined but never rendered".
		name: 'the countdown class is dropped from the specimen markup',
		file: SHOW,
		from: /class="cm-revert__countdown" data-cm-revert-countdown/,
		to: 'data-cm-revert-countdown',
		expectFail: 'every cm-revert class is DEMONSTRATED on the page',
		skipBuild: true,
	},
	{
		// The runtime must tick — no setInterval means no countdown at all.
		name: 'initRevert does not setInterval for the countdown',
		file: RUNTIME,
		from: /setInterval\(tick, 1000\)/,
		to: "/* timer never starts */",
		expectFail: "initRevert does not setInterval for the countdown",
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