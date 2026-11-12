/* Mutation harness for the <Field> Astro wrapper.
 *
 * A test that has never been broken is a guess. Each entry below is a
 * plausible regression someone could reintroduce in the wrapper or its
 * specimen, and each names the check that must fail: `cm-field: the Astro
 * wrapper ships and renders the library classes`.
 *
 * The `from` anchors are on text unique to Field.astro (the wrapper) and to
 * the one specimen in the forms section (the showcase), so a drifted pattern
 * is a loud error, never a phantom survivor.
 *
 * The originals are restored in `finally` from bytes read BEFORE the edit, so
 * an interrupted run cannot leave a partial mutation behind. Do NOT run this
 * while editing the same files: a kill between the edit and the restore
 * leaves the mutation in the tree.
 *
 *   usage: node scripts/mutate-field.mjs
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
const WRAP = join(ROOT, 'src/astro/Field.astro');
const PAGE = join(ROOT, 'src/pages/[...family].astro');

// Every mutant breaks the same check, but the check NAME starts with
// `cm-field:` and the suite prints `FAIL  <name>` - a name-capture regex
// would truncate at that colon. Match the unique ASSERTION MESSAGE instead;
// each assertion below is one that only this check throws.
const MUTATIONS = [
	{
		name: 'the wrapper root loses its class - the whole shape is unstyled',
		file: WRAP,
		from: '<div class="cm-field">',
		to: '<div class="cm-field-broken">',
		expect: 'Field.astro does not emit the cm-field wrapper',
	},
	{
		name: 'the required marker loses its class - the * is an unstyled asterisk',
		file: WRAP,
		from: '{required && <span class="cm-field__req">*</span>}',
		to: '{required && <span>*</span>}',
		expect: 'Field.astro is missing the required marker',
	},
	{
		name: 'the error ships visible - a fine value paints a bare "!"',
		file: WRAP,
		from: '<span class="cm-field__error" hidden>{error}</span>',
		to: '<span class="cm-field__error">{error}</span>',
		expect: 'Field.astro ships the error visible',
	},
	{
		name: 'the control becomes a fixed <input> - the select and textarea are hidden',
		file: WRAP,
		from: '<slot />',
		to: '<input type="text" />',
		expect: 'Field.astro is missing the control slot',
	},
	{
		name: 'the label loses its for= wiring - clicking it never focuses the control',
		file: WRAP,
		from: '<label class="cm-field__label" {...htmlFor && { for: htmlFor }}>',
		to: '<label class="cm-field__label">',
		expect: 'Field.astro does not wire the label for= to the control',
	},
	{
		name: 'the specimen drops the required marker - the branch goes unproven',
		file: PAGE,
		from: '<Field label="handle" for="wf-name" required help="lowercase, no spaces.">',
		to: '<Field label="handle" for="wf-name" help="lowercase, no spaces.">',
		expect: 'the specimen does not demonstrate the required marker',
	},
];

// Bytes read BEFORE any edit, so the restore cannot depend on a mutation
// having been undone cleanly.
const ORIGINALS = new Map(MUTATIONS.map((m) => [m.file, readFileSync(m.file, 'utf8')]));

const run = () => spawnSync('node', [join(ROOT, 'tests/run.mjs')], {
	cwd: ROOT, encoding: 'utf8',
});
const suiteFailed = (r) => r.status !== 0;
const out = (r) => `${r.stdout}\n${r.stderr}`;

let killed = 0;
const survivors = [];

try {
	for (const m of MUTATIONS) {
		const before = ORIGINALS.get(m.file);
		const occurrences = before.split(m.from).length - 1;
		if (occurrences !== 1) {
			survivors.push(`${m.name} -- PATTERN MATCHES ${occurrences} TIMES, NOT 1 (fix the anchor before trusting this run)`);
			continue;
		}
		writeFileSync(m.file, before.replace(m.from, m.to));

		const r = run();
		writeFileSync(m.file, before);

		if (!suiteFailed(r)) {
			survivors.push(`${m.name} -- suite stayed GREEN`);
			continue;
		}
		// The suite is red; now prove it is red on THIS mutant's assertion,
		// not on an unrelated check. The message is unique to this check.
		if (!out(r).includes(m.expect)) {
			survivors.push(`${m.name} -- suite went red but not on "${m.expect}"; the mutation may have broken the wrong thing`);
			continue;
		}
		killed++;
		console.log(`  KILLED  ${m.name}`);
	}
} finally {
	for (const [file, body] of ORIGINALS) writeFileSync(file, body);
}

console.log(`\n${killed}/${MUTATIONS.length} killed`);
if (survivors.length) {
	console.log('\nSURVIVORS:');
	for (const s of survivors) console.log(`  ${s}`);
	process.exit(1);
}
if (killed !== MUTATIONS.length) {
	console.log('\nkill count does not match the mutation count - the summary is lying');
	process.exit(1);
}
console.log('every mutation was killed by the check that owns it');
