#!/usr/bin/env node
/**
 * Mutation sweep for the Code Block body features and Trace.
 *
 * A check that no mutation can break is not a check. Each mutant breaks
 * exactly one behaviour the harness claims to verify, the harness runs
 * against the rebuilt page, and a mutant that SURVIVES means the harness
 * is lying about that property.
 *
 * The sweep measures through the WEBKIT HARNESS (tests/verify-codeblock-trace.py),
 * not the static suite, because half of these properties are computed
 * values in a real engine - a `white-space` that is declared and a
 * `white-space` that computes are different claims.
 *
 * Refuses to run on a dirty tree: a sweep over uncommitted work measures
 * the work, not the mutants.
 */
import { execFileSync, execSync } from 'node:child_process';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

// Resolve from THIS file, never a hardcoded worktree path: a sweep that
// names a sibling checkout measures someone else's tree (and refuses to
// run at all when that checkout is dirty).
const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const PY = '/root/.venvs/mau/bin/python';
const HARNESS = join(ROOT, 'tests', 'verify-codeblock-trace.py');

const MUTANTS = [
	{
		name: 'the gutter is left on the clipboard',
		why: 'extractCopyText stops stripping .cm-code__ln, so copied code arrives with numerals in it',
		file: 'src/js/cli-mono.js',
		from: "if (!src.querySelector || !src.querySelector('.cm-code__ln')) {",
		to: 'if (true) {',
	},
	{
		name: 'the start line is ignored and every block begins at 1',
		why: 'startAt stops being added to the numeral',
		file: 'src/astro/CodeBlock.astro',
		from: 'const n = startAt + i;',
		to: 'const n = 1 + i;',
	},
	{
		name: 'wrap is declared but never reaches the engine',
		why: 'the data-wrap attribute is never emitted, so the CSS branch is dead',
		file: 'src/astro/CodeBlock.astro',
		from: "data-wrap={wrap ? 'true' : undefined}",
		to: 'data-wrap={undefined}',
	},
	{
		name: 'highlight marks nothing',
		why: 'the highlight set is emptied, so data-highlight never lands',
		file: 'src/astro/CodeBlock.astro',
		from: 'data-highlight={marked.has(n) ? \'\' : undefined}',
		to: 'data-highlight={undefined}',
	},
	{
		name: 'the disclosure is inert',
		why: 'the runtime never flips aria-expanded, so the button is dead UI',
		file: 'src/js/cli-mono.js',
		from: "btn.setAttribute('aria-expanded', open ? 'false' : 'true');",
		to: "btn.setAttribute('aria-expanded', open ? 'false' : 'false');",
	},
	{
		name: 'the disclosure opens but never reveals',
		why: 'the panel is never un-hidden, so aria-expanded lies about the body',
		file: 'src/js/cli-mono.js',
		from: 'else panel.removeAttribute(\'hidden\');',
		to: 'else panel.setAttribute(\'hidden\', \'\');',
	},
	{
		name: 'the floating action is not a button',
		why: 'the control becomes a span, which no keyboard can reach',
		file: 'src/astro/CodeBlock.astro',
		from: '\t\t\t<button\n\t\t\t\tclass="cm-btn cm-btn--sm cm-copy cm-codebar__float"',
		to: '\t\t\t<span\n\t\t\t\tclass="cm-btn cm-btn--sm cm-copy cm-codebar__float"',
	},
];

function sh(cmd, opts = {}) {
	return execSync(cmd, { cwd: ROOT, encoding: 'utf8', ...opts });
}

function dirty() {
	const out = sh('git status --porcelain -- src tests');
	return out.trim();
}

function build() {
	sh('npm run build > /dev/null 2>&1');
}

function runHarness() {
	try {
		const out = execFileSync(PY, [HARNESS], {
			cwd: ROOT,
			encoding: 'utf8',
			timeout: 300000,
		});
		return { ok: true, out };
	} catch (err) {
		return { ok: false, out: (err.stdout || '') + (err.stderr || '') };
	}
}

const dirt = dirty();
if (dirt) {
	console.error('the working tree is NOT clean under src/ or tests/:');
	console.error(dirt.split('\n').map((l) => '  ' + l).join('\n'));
	console.error('A sweep over a dirty tree measures the dirt. Commit or restore, then re-run.');
	process.exit(2);
}

console.log('baseline (unmutated):');
build();
let base = runHarness();
if (!base.ok) {
	console.error('  the harness is already red before any mutant - fix that first');
	console.error(base.out.split('\n').slice(-12).join('\n'));
	process.exit(2);
}
const total = /(\d+)\/(\d+) passed/.exec(base.out);
console.log(`  green: ${total ? total[0] : 'ran'}`);

let killed = 0;
let survived = 0;
let broken = 0;
const survivors = [];
const brokenMuts = [];

for (const m of MUTANTS) {
	const path = join(ROOT, m.file);
	const orig = readFileSync(path, 'utf8');
	if (!orig.includes(m.from)) {
		console.log(`\n  BROKEN  ${m.name}\n    the anchor is no longer in ${m.file} - the mutant cannot be applied`);
		broken++;
		brokenMuts.push(m.name);
		continue;
	}
	writeFileSync(path, orig.replace(m.from, m.to));
	try {
		build();
	} catch {
		console.log(`\n  KILLED  ${m.name} (does not build)`);
		killed++;
		writeFileSync(path, orig);
		continue;
	}
	const r = runHarness();
	if (r.ok) {
		console.log(`\n  SURVIVED  ${m.name}\n    ${m.why}\n    the harness still reports green, so it does NOT check this`);
		survived++;
		survivors.push(m.name);
	} else {
		const which = (r.out.match(/^FAIL .*$/gm) || []).slice(0, 3).map((s) => s.trim());
		console.log(`\n  KILLED  ${m.name}`);
		for (const w of which) console.log(`    ${w}`);
		killed++;
	}
	writeFileSync(path, orig);
}

// Restore and rebuild so the tree is left exactly as found.
build();

console.log(`\n${killed}/${MUTANTS.length} killed, ${broken} broken, ${survived} survived`);
if (survivors.length) console.log('survivors: ' + survivors.join('; '));
if (brokenMuts.length) console.log('broken: ' + brokenMuts.join('; '));
process.exit(survived || broken ? 1 : 0);
