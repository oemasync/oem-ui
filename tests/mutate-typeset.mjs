/* Mutation sweep for the typeset contract (batch 32).
 *
 * Every check in the typeset block is only worth shipping if it can FAIL.
 * Each mutant below breaks ONE documented property of the system, and the
 * suite must go red with a line that names the defect.
 *
 * Shaped after tests/mutate-hero.mjs, including its two hard rules: a
 * mutation whose pattern matches nothing is BROKEN (never a silent pass),
 * and the tree must be pristine before the sweep starts.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

// Resolve the repo root from THIS file's location rather than hardcoding a
// worktree. A hardcoded absolute path made the sweep measure whichever tree
// happened to sit at that path - so on any other worktree it swept someone
// else's uncommitted edits and refused to run at all. It is a test of THIS
// tree, so it must find THIS tree.
const ROOT = fileURLToPath(new URL('..', import.meta.url)).replace(/\/$/, '');
const p = (f) => `${ROOT}/${f}`;

function rebuild() {
	const b = spawnSync('npm', ['run', 'build'], { cwd: ROOT, encoding: 'utf8' });
	return b.status === 0;
}

const CSS = 'src/styles/components.css';
const TOKENS = 'src/styles/tokens.css';
const PAGE = 'src/pages/[...family].astro';

const MUTATIONS = [
	// ---- 1. the rhythm DERIVES from the controls -------------------------
	['a derivation is replaced by a literal, so the block stops being a system',
		CSS,
		(s) => s.replace(
			'.cm-typeset > :where(li) + :where(li) {\n\tmargin-block-start: calc(var(--cm-typeset-flow) * 0.25);',
			'.cm-typeset > :where(li) + :where(li) {\n\tmargin-block-start: 0.3125em;')],
	['the second derivation goes too, leaving one calc() and a presence-shaped pass',
		CSS,
		(s) => s.replace(
			'.cm-typeset > :where(h1, h2, h3, h4, h5, h6) + :where(*) {\n\tmargin-block-start: calc(var(--cm-typeset-flow) * 0.5);',
			'.cm-typeset > :where(h1, h2, h3, h4, h5, h6) + :where(*) {\n\tmargin-block-start: 0.625em;')
			.replace(
				'.cm-typeset > :where(li) + :where(li) {\n\tmargin-block-start: calc(var(--cm-typeset-flow) * 0.25);',
				'.cm-typeset > :where(li) + :where(li) {\n\tmargin-block-start: 0.3125em;')],

	// ---- 2. every control is a DECLARED token ----------------------------
	['a control is read but never declared, so its declaration dangles',
		TOKENS,
		(s) => s.replace('\t--cm-typeset-flow: 1.25em;\n', '')],

	// ---- 3. spacing flows in ONE direction -------------------------------
	['a block takes end-side spacing, so an appended block moves what is on screen',
		CSS,
		(s) => s.replace(
			'.cm-typeset > :where(* + *) {\n\tmargin-block-start: var(--cm-typeset-flow);\n}',
			'.cm-typeset > :where(* + *) {\n\tmargin-block-start: var(--cm-typeset-flow);\n\tmargin-block-end: var(--cm-typeset-flow);\n}')],
	['a structural selector enters a layout rule, so a sibling restyles a block',
		CSS,
		(s) => s.replace(
			'.cm-typeset > :where(blockquote) {',
			'.cm-typeset > :where(blockquote):not(:last-child) {')],

	// ---- 4. container-relative size --------------------------------------
	['the size becomes absolute, so the same markup is one size everywhere',
		TOKENS,
		(s) => s.replace('\t--cm-typeset-size: 1em;\n', '\t--cm-typeset-size: 16px;\n')],

	// ---- 5. the opt-out --------------------------------------------------
	// replaceAll, not replace: the opt-out is TWO rules and a single-shot
	// replace only rewrites the first, so the check's string test still found
	// the attribute in the second and the mutant "survived" - a bad mutant
	// reported as a hole in the test.
	['the opt-out loses its data-attribute form',
		CSS,
		(s) => s.replaceAll('[data-not-typeset]', '')],
	['the hole stops resetting its own children, so the rhythm applies inside it',
		CSS,
		(s) => s.replace(
			'.cm-typeset :where(.not-typeset, [data-not-typeset]) > :where(*) {\n\tmargin-block-start: 0;\n}',
			'')],

	// ---- 6. zero specificity --------------------------------------------
	['a rule takes real specificity, so it beats a consumer class',
		CSS,
		(s) => s.replace('.cm-typeset > :where(h2) { font-size: calc(1em * 1.35); }',
			'.cm-typeset > h2 { font-size: calc(1em * 1.35); }')],

	// ---- 6b. the preset and the viewport bump COMPOSE --------------------
	// Both halves of the split, plus the wiring. A preset that writes
	// `--cm-typeset-size` directly is the exact defect measured at 390:
	// the media query is later in source at the same specificity, so it
	// silently overrides the preset on the one viewport a phone uses.
	['the roomy preset writes an absolute size, which the phone bump overrides',
		CSS,
		(s) => s.replace('.cm-typeset--roomy {\n	--cm-typeset-scale: 1.0625;',
			'.cm-typeset--roomy {\n	--cm-typeset-size: 1.0625em;')],
	['the roomy preset scales by 1, so the reader preference is a no-op',
		CSS,
		(s) => s.replace('.cm-typeset--roomy {\n	--cm-typeset-scale: 1.0625;',
			'.cm-typeset--roomy {\n	--cm-typeset-scale: 1;')],
	['the phone bump takes the reader scale, which belongs to the reader',
		CSS,
		(s) => s.replace('@media (max-width: 640px) {\n	.cm-typeset {\n		--cm-typeset-size-lane: 1.0625em;',
			'@media (max-width: 640px) {\n	.cm-typeset {\n		--cm-typeset-scale: 1.0625;')],
	['the composition is collapsed to the lane alone, so a preset cannot tune it',
		CSS,
		(s) => s.replace('	--cm-typeset-size: calc(var(--cm-typeset-size-lane) * var(--cm-typeset-scale));',
			'	--cm-typeset-size: var(--cm-typeset-size-lane);')],
	['the scale is read but never declared, so its declaration dangles',
		TOKENS,
		(s) => s.replace('	--cm-typeset-scale: 1;\n', '')],

	// ---- 7. demonstrated, and every preset rendered ----------------------
	['the showcase section is renamed away, so the component is undemonstrated',
		PAGE,
		(s) => s.replace('<section id="typeset" class="cm-section cm-section--pad">',
			'<section id="typesetX" class="cm-section cm-section--pad">')],
	['a preset ships in the sheet but no specimen renders it',
		PAGE,
		(s) => s.replace(
			'<div class="cm-typeset cm-typeset--chat">',
			'<div class="cm-typeset">')],
	['the scroll wrapper ships but no specimen renders it',
		PAGE,
		(s) => s.replace('<div class="cm-typeset-scroll">', '<div>')],
	['the opt-out ships but no specimen demonstrates it',
		PAGE,
		(s) => s.replace('<div class="not-typeset">', '<div>')],
];

let killed = 0;
let broken = 0;
const survivors = [];
const BASELINE_FAILS = new Set();

console.log('baseline (unmutated):');
{
	const dirty = spawnSync('git', ['status', '--porcelain', '--', 'src/', 'tests/'], { cwd: ROOT, encoding: 'utf8' })
		.stdout.trim().split('\n').filter(Boolean);
	if (dirty.length) {
		console.log('   the working tree is NOT clean under src/ or tests/:');
		for (const d of dirty) console.log(`     ${d}`);
		console.log('   A sweep over a dirty tree measures the dirt. Commit or restore, then re-run.');
		process.exit(2);
	}
	rebuild();
	const b = spawnSync('node', ['tests/run.mjs'], { cwd: ROOT, encoding: 'utf8' });
	const fails = (b.stdout.match(/^FAIL .*$/gm) || []).map((s) => s.trim().slice(5));
	for (const f of fails) BASELINE_FAILS.add(f);
	for (const f of fails) console.log(`   already failing: ${f}`);
	if (fails.length) console.log(`   ^ ${fails.length} pre-existing failure(s); NOT credited to any mutant`);
	if (b.status !== 0 && !fails.length) {
		console.log('   the suite failed with no FAIL line - refusing to sweep against an unreadable baseline');
		process.exit(2);
	}
}

for (const [name, file, mutate] of MUTATIONS) {
	const path = p(file);
	const orig = readFileSync(path, 'utf8');
	const mutated = mutate(orig);
	if (mutated === orig) {
		console.log(`  BROKEN MUTATION  ${name} - the pattern matched nothing in ${file}`);
		broken++;
		continue;
	}
	writeFileSync(path, mutated);
	let killedNow = false;
	let why = '';
	const built = rebuild();
	if (!built) {
		killedNow = true;
		why = 'the build itself failed - the strongest kill available';
	} else {
		const r = spawnSync('node', ['tests/run.mjs'], { cwd: ROOT, encoding: 'utf8' });
		killedNow = r.status !== 0;
		const fails = (r.stdout.match(/^FAIL .*$/gm) || []).map((s) => s.trim().slice(5));
		const fresh = fails.filter((f) => !BASELINE_FAILS.has(f));
		why = (fresh.length ? fresh : fails).map((f) => `FAIL ${f}`).join('\n          ');
	}
	// Restore from the in-process copy, byte-verified. On-disk snapshots can
	// be pruned by another subsystem mid-run; the bytes in this process are
	// the authority.
	writeFileSync(path, orig);
	if (readFileSync(path, 'utf8') !== orig) {
		console.log(`  RESTORE FAILED  ${name} - the tree is not byte-identical to the original`);
		process.exit(2);
	}
	if (killedNow) {
		killed++;
		console.log(`  KILLED  ${name}`);
		console.log(`          ${why}`);
	} else {
		survivors.push(name);
		console.log(`  SURVIVED  ${name}  <-- the test cannot see this`);
	}
}

console.log(`\n${killed}/${MUTATIONS.length} killed, ${broken} broken, ${survivors.length} survived`);
process.exit(survivors.length || broken ? 1 : 0);
