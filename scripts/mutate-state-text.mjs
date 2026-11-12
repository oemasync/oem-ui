/* Mutation harness for .cm-state__text, the documented empty-state
 * one-liner.
 *
 * A test that has never been broken is a guess. Each entry below is a
 * plausible regression someone could reintroduce in the rule, its
 * specimen or the README contract it answers to, and each names the
 * check that must fail. The suite prints `FAIL  <name>\n        <msg>`;
 * `expect` is the unique assertion message, not the check name (check
 * names repeat, assertion messages do not).
 *
 * The `from` anchors are the FULL rule string (unique in components.css)
 * and the verbatim specimen line (unique in the page and in the README),
 * so a drifted pattern is a loud error, never a phantom survivor.
 *
 * The originals are restored in `finally` from bytes read BEFORE the
 * edit, so an interrupted run cannot leave a partial mutation behind.
 * Do NOT run this while editing the same files: a kill between the
 * edit and the restore leaves the mutation in the tree.
 *
 *   usage: node scripts/mutate-state-text.mjs
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
const CSS = join(ROOT, 'src/styles/components.css');
const PAGE = join(ROOT, 'src/pages/[...family].astro');
const README = join(ROOT, 'README.md');

const RULE =
	'.cm-state__text { margin: 0 auto; max-width: var(--measure-narrow); color: var(--ink-faint); }';
const SPECIMEN =
	'<p class="cm-state__text">One line on what would fill this.</p>';

const MUTATIONS = [
	{
		name: 'the rule is deleted - the documented name goes ghost',
		file: CSS,
		from: RULE,
		to: '',
		expect: '.cm-state__text has no rule',
	},
	{
		name: 'the tier flips to --ink-dim - the one-liner reads as body copy',
		file: CSS,
		from: RULE,
		to: RULE.replace('--ink-faint', '--ink-dim'),
		expect: 'must resolve to the faint tier',
	},
	{
		name: 'the narrow measure is dropped - the line runs the panel wide',
		file: CSS,
		from: RULE,
		to: '.cm-state__text { margin: 0 auto; color: var(--ink-faint); }',
		expect: 'must take the narrow measure',
	},
	{
		name: 'the specimen loses the class - the demonstration goes unstyled',
		file: PAGE,
		from: SPECIMEN,
		to: '<p>One line on what would fill this.</p>',
		expect: 'the page does not demonstrate the documented mark -> title -> text shape',
	},
	{
		name: 'the README renames the class - the contract points at a ghost',
		file: README,
		from: SPECIMEN,
		to: '<p class="cm-state__note">One line on what would fill this.</p>',
		expect: "the README's States example names .cm-state__note, which has no rule",
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
