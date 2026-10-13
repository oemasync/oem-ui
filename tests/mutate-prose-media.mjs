#!/usr/bin/env node
/* Mutation proof for batch 32: media in an article body.
 *
 * A test nobody has tried to break is a guess. This harness deletes or
 * inverts each half of the fix, rebuilds `dist` (the contract checks read
 * BUILT output, so a source-only mutation measures nothing), runs the
 * suite, and requires it to FAIL - by name, naming the defect.
 *
 * Rules this harness obeys, learned the hard way in this repo:
 *   - The recovery copy lives IN THE PROCESS. A cp into a scratch dir is
 *     deleted by the scratch pruner mid-run and the `finally` then dies
 *     holding a mutated tree.
 *   - Every restore is byte-verified the moment it happens, and the tree
 *     is asserted pristine before the next mutation.
 *   - A mutation pattern that does not match is a NO-OP reported as a
 *     pass. MUTANTS are pre-flighted; a miss exits instead of shrinking
 *     the run.
 *   - `git checkout --` is never used on a shared file.
 *
 * The mutation count is part of the evidence: if it changes between runs,
 * this file was edited and nobody meant to.
 */
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const BASE = join(ROOT, 'src/styles/base.css');
const COMP = join(ROOT, 'src/styles/components.css');

/* Each mutant: {name, file, from, to, expect}. `expect` is the substring
 * the suite's failure output must contain, so a mutation that fails for an
 * unrelated reason is not counted as a kill. */
const MUTANTS = [
	{
		name: 'video loses its max-width',
		file: BASE,
		from: 'video:not([class]) { max-width: 100%; height: auto; display: block; }',
		to: 'video:not([class]) { height: auto; display: block; }',
		expect: 'a bare <video> has no max-width',
	},
	{
		name: 'figure keeps the UA inline margin (off the rail)',
		file: BASE,
		from: 'video:not([class]) { max-width: 100%; height: auto; display: block; }\n\nfigure { margin: var(--space-6) 0; }',
		to: 'video:not([class]) { max-width: 100%; height: auto; display: block; }\n\nfigure { margin: var(--space-6) 40px; }',
		expect: 'figure does not zero its inline margin',
	},
	{
		name: 'figure img does not claim the column',
		file: BASE,
		from: '\nfigure img {\n	display: block;\n	width: 100%;',
		to: '\nfigure img {\n	display: block;\n	width: auto;',
		expect: 'figure img does not claim the column',
	},
	{
		name: 'figcaption loses its colour step',
		file: BASE,
		from: 'figcaption {\n\t/* `max(var(--min-font), …)`, not a bare em: a bare `0.9em` under the\n\t   library\'s own base font resolves below the 12px floor on a phone,\n\t   which is the reason `.cm-prose-table` carries the same pair. */\n\tfont-size: max(var(--min-font), 0.9em);\n\tcolor: var(--ink-dim);',
		to: 'figcaption {\n\tfont-size: max(var(--min-font), 0.9em);\n\tcolor: inherit;',
		expect: 'figcaption has no colour step',
	},
	{
		name: 'figcaption loses the --min-font floor',
		file: BASE,
		from: 'which is the reason `.cm-prose-table` carries the same pair. */\n	font-size: max(var(--min-font), 0.9em);',
		to: 'which is the reason `.cm-prose-table` carries the same pair. */\n	font-size: 0.9em;',
		expect: 'figcaption does not carry the --min-font floor',
	},
	{
		name: 'the SCOPED twin is dropped',
		file: BASE,
		from: ':where([data-cm-theme]) video { max-width: 100%; height: auto; display: block; }',
		to: '/* scratch-pruned by the mutant */',
		expect: 'the scoped prose block has no :where([data-cm-theme]) video twin',
	},
	{
		name: 'the media rule is scoped with :not([class]), dropping a classed figure',
		file: BASE,
		from: '\nfigure img {\n	display: block;',
		to: '\nfigure:not([class]) img {\n	display: block;',
		expect: 'figure img must stay a bare element rule',
	},
	{
		name: '.cm-media loses its own image rule',
		file: COMP,
		from: '.cm-media img {\n\tdisplay: block; width: 100%;',
		to: '.cm-media img {\n\tdisplay: block; width: auto;',
		expect: '.cm-media lost the image rule',
	},
	{
		name: 'typeset drops its figure rule (the :where(*) reset wins)',
		file: COMP,
		from: '.cm-typeset > :where(figure) img {',
		to: '.cm-typeset > figure img {',
		expect: '.cm-typeset states no figure img rule',
	},
	{
		name: 'the README drops the figcaption default from its section',
		file: join(ROOT, 'README.md'),
		from: 'figcaption { font-size: max(var(--min-font), 0.9em); color: var(--ink-dim); }',
		to: 'figcaption { color: var(--ink-dim); }',
		expect: 'the media section does not document the figcaption default',
	},
	{
		name: 'the README drops the figure default from its section',
		file: join(ROOT, 'README.md'),
		from: 'figure { margin: var(--space-6) 0; }',
		to: 'figure { margin: 1em 0; }',
		expect: 'the media section does not document the figure default, with its token',
	},
	{
		name: 'the README documents the figure frame without its tokens',
		file: join(ROOT, 'README.md'),
		from: 'figure img { display: block; width: 100%; border-radius: var(--radius-sm); border: 1px solid var(--line); }',
		to: 'figure img { display: block; width: 100%; }',
		expect: 'the media section does not document the figure img default, with its frame tokens',
	},
	{
		name: 'the README stops naming the probe',
		file: join(ROOT, 'README.md'),
		from: 'Verified by `tests/measure-prose-media-webkit.py`',
		to: 'Verified by the media probe',
		expect: 'the media section does not name the probe',
	},
];

const originals = new Map();
for (const f of [BASE, COMP, join(ROOT, 'README.md')]) originals.set(f, readFileSync(f));

function restoreAll() {
	for (const [f, text] of originals) writeFileSync(f, text);
	// Byte-verify every restore the moment it happens.
	for (const [f, text] of originals) {
		if (readFileSync(f).toString() !== text.toString()) {
			throw new Error('RESTORE FAILED for ' + f);
		}
	}
}

let killed = 0;
const survived = [];
let restoring = false;
function emergencyRestore() {
	if (restoring) return;
	restoring = true;
	try {
		for (const [f, text] of originals) writeFileSync(f, text);
		console.error('\nRESTORED after an external kill - the tree is pristine again.');
	} catch (e) {
		console.error('\nEMERGENCY RESTORE FAILED: ' + e.message);
	}
	process.exit(130);
}
/* `finally` does not run for a SIGKILL, and this harness is run under a cron
 * timeout. A sweep killed from outside leaves its mutant in the tree - that
 * has already happened here once (a `nowrap` mutant sat for four hours). Bind
 * the signals we CAN catch, and re-verify the tree in the next run. */
for (const sig of ['SIGINT', 'SIGTERM', 'SIGHUP']) process.on(sig, emergencyRestore);
process.on('uncaughtException', (e) => { console.error(e); emergencyRestore(); });

try {
// Pre-flight: a tree that already holds a mutant is an INTERRUPTED run,
// not a design decision. Diagnose it before touching anything.
for (const m of MUTANTS) {
	const src = readFileSync(m.file, 'utf8');
	if (!src.includes(m.from) && src.includes(m.to)) {
		console.error(`POISONED TREE: "${m.name}" - ${m.file} already holds the muted value.`);
		console.error('An earlier sweep was killed from outside. Restore the file first.');
		process.exit(3);
	}
}
// Pre-flight: every pattern must match, or the run shrinks silently.
for (const m of MUTANTS) {
		const src = readFileSync(m.file, 'utf8');
		if (!src.includes(m.from)) {
			console.error(`PREFLIGHT MISS: "${m.name}" - pattern absent in ${m.file}`);
			console.error('A pattern that does not match is a NO-OP reported as a pass.');
			process.exit(2);
		}
	}
	console.log(`${MUTANTS.length} mutants pre-flighted\n`);

	for (const m of MUTANTS) {
		restoreAll();
		const src = readFileSync(m.file, 'utf8');
		// Uniqueness: a pattern matching twice mutates more than it says.
		if (src.split(m.from).length !== 2) {
			console.error(`PREFLIGHT: "${m.name}" matches ${src.split(m.from).length - 1} times`);
			process.exit(2);
		}
		writeFileSync(m.file, src.replace(m.from, m.to));
		if (readFileSync(m.file, 'utf8') === src) {
			console.error(`MUTATION DID NOT APPLY: ${m.name}`);
			process.exit(2);
		}
		// The contract checks read BUILT output, so a source-only mutation
		// would measure the previous build and report everything passing.
		let out = '';
		try {
			execFileSync('npm', ['run', 'build'], { cwd: ROOT, stdio: 'pipe', encoding: 'utf8' });
		} catch (e) {
			out = 'BUILD FAILED';
		}
		try {
			out += execFileSync('node', ['tests/run.mjs'], { cwd: ROOT, stdio: 'pipe', encoding: 'utf8' });
		} catch (e) {
			out += (e.stdout || '') + (e.stderr || '');
		}
		const failed = /FAIL/.test(out);
		const named = out.includes(m.expect);
		if (failed && named) {
			killed++;
			console.log(`KILLED   ${m.name}`);
		} else if (failed) {
			// A fail for the WRONG reason is not a kill.
			survived.push(m.name + ' (failed, but not on its own claim)');
			console.log(`MISKILL  ${m.name} - failed without naming: ${m.expect}`);
		} else {
			survived.push(m.name);
			console.log(`SURVIVED ${m.name}`);
		}
	}
} finally {
	restoreAll();
	try { execFileSync('npm', ['run', 'build'], { cwd: ROOT, stdio: 'pipe' }); } catch {}
}

console.log(`\n${killed}/${MUTANTS.length} killed`);
if (survived.length) {
	console.log('not killed:\n  ' + survived.join('\n  '));
	process.exit(1);
}
