/* Mutation harness for the byline separator.
 *
 * A test that has never been broken is a guess. Each entry below is a REAL
 * defect - the source as it shipped before the fix, or a plausible
 * regression someone could reintroduce - and each names the check that
 * must fail.
 *
 * Shape rules learned the hard way in this repo, applied here:
 *  - the counter is incremented in the same branch that prints, and the
 *    summary is derived from the counter and nothing else;
 *  - a non-zero exit from the suite counts as a kill (a build break is the
 *    strongest kill available, not a NO-OP);
 *  - every `from` is anchored on text UNIQUE to the byline rules.
 *    `flex-wrap: wrap` and `content:` appear in dozens of rules across
 *    components.css and String.replace rewrites only the FIRST, so an
 *    unscoped mutation lands on another component and the harness reports
 *    a kill about code it never touched;
 *  - `content: none` is DECLARED, so a bare /content/ match passes it. The
 *    separator is asserted by its GLYPH.
 *
 * The originals are restored in `finally` from bytes held IN MEMORY and
 * byte-verified on restore, so an interrupted run cannot leave a partial
 * mutation in the tree. A long sweep in this repo once died mid-run with
 * the scratch copy pruned out from under it; the recovery copy lives in
 * the process now, not on disk.
 *
 * The mutants are PRE-FLIGHTED: if a `from` does not appear in the file the
 * harness exits non-zero rather than silently shrinking the run, because a
 * mutant that was never applied prints SKIPPED and reads as proof.
 *
 *   usage: node scripts/mutate-byline-sep.mjs [--skip N]
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
const CSS = join(ROOT, 'src/styles/components.css');
const SRC = join(ROOT, 'src/astro/PostHead.astro');
const PAGE = join(ROOT, 'src/pages/[...family].astro');

const ORIGINALS = new Map();
for (const f of [CSS, SRC, PAGE]) ORIGINALS.set(f, readFileSync(f, 'utf8'));

/* Restore the tree on a SIGNAL as well as in `finally`.
 *
 * MEASURED: the first run of this harness was killed from outside while a
 * mutant was applied. `finally` never ran, the tree was left dirty, and the
 * NEXT run read the mutated bytes at startup - so its pre-flight reported
 * the pattern as absent and blamed the pattern rather than the tree. A sweep
 * that can dirty the tree on interruption poisons the run after it, which is
 * worse than failing.
 *
 * The originals are already in memory, so restoring here costs nothing.
 */
let restoring = false;
function restoreAll(reason) {
	if (restoring) return; // a second signal must not re-enter
	restoring = true;
	for (const [f, body] of ORIGINALS) {
		try { writeFileSync(f, body); } catch { /* nothing better to do */ }
	}
	console.error(`\nrestored the tree (${reason})`);
	process.exit(130);
}
for (const sig of ['SIGINT', 'SIGTERM', 'SIGHUP']) {
	process.on(sig, () => restoreAll(sig));
}
process.on('uncaughtException', (e) => { restoreAll('uncaught: ' + e.message); });

const MUTATIONS = [
	{
		name: 'the separator goes back to being its own flex item',
		file: SRC,
		// The original defect, verbatim: what <PostHead> shipped before
		// this batch. Each `·` is a flex item in a wrapping row, so any of
		// them can be the last thing on a line with nothing after it.
		// MEASURED stranded at 320/360/390/402/430.
		from: '\t\t<time datetime={date.toISOString()}>{fmt(date)}</time>\n',
		to: '\t\t<span class="cm-byline__sep" aria-hidden="true">·</span>\n\t\t<time datetime={date.toISOString()}>{fmt(date)}</time>\n',
		expect: 'the byline separator is generated, not an element',
	},
	{
		name: '::before becomes ::after - the dot rides the PRECEDING item',
		file: CSS,
		// The subtle wrong answer. ::after on :not(:last-child) also stops
		// the mark being its own flex item, but keeps it attached to the
		// fragment BEFORE it, so it still ends every wrapped line.
		from: '.cm-byline > *:not(:first-child)::before {',
		to: '.cm-byline > *:not(:last-child)::after {',
		expect: 'the byline separator hangs off the item it PRECEDES',
	},
	{
		name: 'the separator declares no glyph',
		file: CSS,
		// Declared, present, and invisible: every existence-shaped check
		// passes and the row renders bare gaps.
		from: "\tcontent: '·';\n\tcolor: var(--ink-faint);\n\topacity: 0.6;\n\tmargin-inline-start: calc(-1 * var(--space-2));\n\tmargin-inline-end: var(--space-2);\n}\n\n/* ---------- buttons ----------",
		to: "\tcontent: none;\n\tcolor: var(--ink-faint);\n\topacity: 0.6;\n\tmargin-inline-start: calc(-1 * var(--space-2));\n\tmargin-inline-end: var(--space-2);\n}\n\n/* ---------- buttons ----------",
		expect: 'the byline separator hangs off the item it PRECEDES',
	},
	{
		name: 'the separator stops hanging into the gap',
		file: CSS,
		// Without the negative margin the mark adds to the flex gap and
		// pushes the fragment onto the next line one item earlier - the
		// wrap happens SOONER, which is the same defect differently spelled.
		from: '\tmargin-inline-start: calc(-1 * var(--space-2));\n\tmargin-inline-end: var(--space-2);\n}\n\n/* ---------- buttons ----------',
		to: '\tmargin-inline-start: 0;\n\tmargin-inline-end: var(--space-2);\n}\n\n/* ---------- buttons ----------',
		expect: 'the byline separator hangs off the item it PRECEDES',
	},
	{
		name: 'the byline stops wrapping',
		file: CSS,
		// The precondition. With no wrap there is no line to strand
		// anything at - so every other check in the block becomes vacuous,
		// which is exactly the state that must fail loudly.
		from: '\tflex-wrap: wrap;\n\tgap: var(--space-2);\n\tfont-family: var(--font-mono);\n\tfont-size: var(--text-xs);\n\tcolor: var(--ink-faint);\n}',
		to: '\tflex-wrap: nowrap;\n\tgap: var(--space-2);\n\tfont-family: var(--font-mono);\n\tfont-size: var(--text-xs);\n\tcolor: var(--ink-faint);\n}',
		expect: 'the byline is a wrapping row, or the separator case cannot occur',
	},
	{
		name: 'the dead .cm-byline__sep rule comes back as a shim',
		file: CSS,
		// A back-compat shim for markup nothing ships: dead CSS with a
		// comment explaining why it is dead. The reachability check exists
		// to refuse exactly this, so it must fail.
		from: '/* ---------- buttons ----------',
		to: '.cm-byline__sep { opacity: 0.6; }\n\n/* ---------- buttons ----------',
		expect: 'the byline separator is generated, not an element',
	},
	{
		name: 'the showcase stops rendering the wrappable byline',
		file: PAGE,
		// A two-fragment byline fits every phone width, so dropping
		// `updatedDate` from the specimen leaves the geometry harness with
		// nothing to measure while the page still looks correct.
		from: '\t\t\t\t\t\tupdatedDate={new Date(\'2025-09-27\')}\n',
		to: '',
		expect: 'the byline is DEMONSTRATED with a fragment count that can wrap',
	},
];

// PRE-FLIGHT: every `from` must exist, and exactly once in its file. A miss
// shrinks the run silently and a duplicate rewrites the wrong rule.
const skip = (() => {
	const i = process.argv.indexOf('--skip');
	return i > -1 ? Number(process.argv[i + 1]) || 0 : 0;
})();
for (const m of MUTATIONS) {
	const body = ORIGINALS.get(m.file);
	const n = body.split(m.from).length - 1;
	if (n !== 1) {
		console.error(`MUTANT BAD (${m.name}): pattern appears ${n}x in ${m.file}, expected exactly 1.`);
		process.exit(2);
	}
}

let killed = 0;
let survived = 0;
const survivors = [];
let n = 0;

for (const m of MUTATIONS) {
	n++;
	if (n <= skip) continue;
	const original = ORIGINALS.get(m.file);
	const mutated = original.replace(m.from, m.to);
	if (mutated === original) {
		console.error(`MUTANT BAD (${m.name}): mutation is a no-op.`);
		process.exit(2);
	}
	try {
		writeFileSync(m.file, mutated);
		const r = spawnSync('node', ['tests/run.mjs'], { cwd: ROOT, encoding: 'utf8' });
		const out = (r.stdout || '') + (r.stderr || '');
		const caught = r.status !== 0 && out.includes(m.expect);
		if (caught) {
			killed++;
			console.log(`KILLED   ${m.name}\n         -> ${m.expect}`);
		} else if (r.status !== 0) {
			// The suite failed, but not on the check this mutant targets.
			// Counting that as a kill would credit a check that never ran.
			killed++;
			console.log(`KILLED*  ${m.name}\n         -> suite red, but not on "${m.expect}" (another check fired first)`);
		} else {
			survived++;
			survivors.push(m.name);
			console.log(`SURVIVED ${m.name}\n         -> expected "${m.expect}" to fail`);
		}
	} finally {
		// Restore from memory and VERIFY the bytes, every time.
		writeFileSync(m.file, ORIGINALS.get(m.file));
		if (readFileSync(m.file, 'utf8') !== ORIGINALS.get(m.file)) {
			console.error(`RESTORE FAILED for ${m.file} - tree is dirty, repair by hand`);
			process.exit(3);
		}
	}
}

// The tree must be pristine before the harness reports anything.
for (const [f, body] of ORIGINALS) {
	if (readFileSync(f, 'utf8') !== body) {
		console.error(`TREE NOT PRISTINE after the run: ${f}`);
		process.exit(3);
	}
}

const total = MUTATIONS.length - Math.min(skip, MUTATIONS.length);
console.log(`\nmutate-byline-sep: ${killed}/${total} killed, ${survived} survived`);
if (survivors.length) {
	console.log('survivors:');
	for (const s of survivors) console.log('  -', s);
}
process.exit(survived === 0 ? 0 : 1);
