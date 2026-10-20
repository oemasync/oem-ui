#!/usr/bin/env node
/**
 * mutation: the keyboard layer (batch 41)
 *
 * Every batch-41 assertion is a guess until it has been made to fail. This
 * breaks the exact thing each check guards, runs the suite, and reports which
 * check fired.
 *
 * Three rules are baked in, each one a defect this repo has already eaten:
 *
 *  1. A pattern that does not match is a NO-OP - a failure of THIS file, never
 *     a pass. The whole list is pre-flighted before anything is mutated.
 *  2. A tree that already CONTAINS a mutant (a sweep killed from outside
 *     leaves one behind) is detected first: `!src.includes(from) &&
 *     src.includes(to)` is not a design decision, it is an interrupted run.
 *  3. The recovery copy lives IN THE PROCESS. A SIGKILL cannot run `finally`,
 *     so SIGINT/SIGTERM/SIGHUP and uncaughtException restore from memory, and
 *     every write is verified against the bytes it replaced.
 *
 * Most mutants are runtime or source and need no rebuild; the suite's batch-41
 * checks read the source and drive the runtime, so a build would only churn
 * dist/ mid-cycle.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const p = (f) => join(root, f);
const RT = 'src/js/cli-mono.js';
const COMP = 'src/styles/components.css';
const SHOW = 'src/pages/[...family].astro';
const README = 'README.md';

const MUTATIONS = [
	// ---- the three guards -------------------------------------------------
	{
		// The typing guard is the difference between a shortcut layer and a
		// keyboard that steals what you type.
		name: 'a plain key fires from a caret',
		file: RT,
		from: /if \(typing\) return;/,
		to: 'if (typing && false) return;',
		expectFail: 'a plain sequence fired from inside a text field',
	},
	{
		// A modified chord must pass the SAME guard. Reading only mod/was
		// enough; treating Alt as "typing" hides Alt-based jumps.
		name: 'the typing guard ignores a modified chord',
		file: RT,
		from: /var typing = cmKeyEditable\(e\.target\) &&\s*\n\s*!\(e\.metaKey \|\| e\.ctrlKey \|\| e\.altKey\);/,
		to: 'var typing = cmKeyEditable(e.target) &&\n\t\t\t\t!(e.metaKey || e.altKey);',
		expectFail: 'a modified chord was swallowed by the typing guard',
	},
	{
		// The scope gate: without it every specimen shares one keyboard.
		name: 'a local scope fires with no focus inside it',
		file: RT,
		from: /if \(!cmKeyScopeActive\(scope\)\) continue;/,
		to: 'if (false) continue;',
		expectFail: 'a local scope fired with no focus inside it',
	},
	{
		// WebKit lays a closed drawer's links out; only checkVisibility()
		// says a person cannot see them.
		name: 'an invisible control is in the map',
		file: RT,
		from: /if \(typeof el\.checkVisibility === 'function'\) return el\.checkVisibility\(\);/,
		to: 'return true;',
		expectFail: 'a control that is not visible is in the map',
	},
	{
		name: 'a disabled control publishes a shortcut and enters the map',
		file: RT,
		from: /if \(el\.hasAttribute && el\.hasAttribute\('disabled'\)\) return false;\n\t\tif \(el\.getAttribute\('aria-disabled'\) === 'true'\) return false;/,
		to: "if (el.getAttribute('aria-disabled') === 'true') return false;",
		expectFail: 'a disabled control published a shortcut',
	},

	// ---- the sequence machine --------------------------------------------
	{
		// Every chord must be compared at the DEPTH the sequence has reached.
		name: 'the sequence always compares its first chord',
		file: RT,
		from: /cmKeyMatches\(b\.seq\[st\.depth\], e\)/,
		to: 'cmKeyMatches(b.seq[0], e)',
		expectFail: 'g then l did not fire',
	},
	{
		// A consumed prefix is the only thing stopping the browser from also
		// acting on `/` (quick-find) on its way to focusing the field.
		name: 'the sequence prefix is not consumed',
		file: RT,
		from: /\/\* a prefix is ours:[\s\S]*?e\.preventDefault\(\);/,
		to: '/* prefix left to the browser */',
		expectFail: 'the prefix was not consumed',
	},
	{
		// Abandoned sequences must not complete minutes later.
		name: 'the sequence window never expires',
		file: RT,
		from: /if \(st\.depth && now - st\.at > CM_KEY_SEQ_MS\) \{/,
		to: 'if (false) {',
		expectFail: 'a chord outside the window still completed the sequence',
	},

	// ---- what reaches assistive tech -------------------------------------
	{
		// aria-keyshortcuts has no syntax for a sequence; publishing one
		// announces a shortcut nobody can press.
		name: 'a SEQUENCE publishes an aria-keyshortcuts',
		file: RT,
		from: /if \(seq\.length !== 1\) return;/,
		to: 'if (!seq.length) return;',
		expectFail: 'a SEQUENCE published an aria-keyshortcuts',
	},
	{
		name: 'a chord publishes its bare key instead of the platform modifier',
		file: RT,
		from: /if \(c\.mod\) out\.push\(cmIsMac\(\) \? 'Meta' : 'Control'\);/,
		to: 'if (c.mod) out.push(c.key);',
		expectFail: 'mod+ must publish the PLATFORM modifier',
	},

	// ---- the map is derived ---------------------------------------------
	{
		name: 'the map is created but never filled',
		file: RT,
		from: /list\.forEach\(function \(b\) \{\n\t\t\tvar li = document\.createElement\('li'\);/,
		to: "list.slice(0, 0).forEach(function (b) {\n\t\t\tvar li = document.createElement('li');",
		// The row COUNT fires before the labels do, so that is the check this
		// mutant actually kills. An expectation naming the assertion you WISH
		// had fired reads exactly like a missed mutant.
		expectFail: 'expected 4 rows',
	},
	{
		// A renamed part is dead CSS the reachability list would otherwise
		// hide - the proof names the class AND its assignment.
		name: 'the row label class is renamed in the runtime',
		file: RT,
		from: /lab\.className = 'cm-keys__label';/,
		to: "lab.className = 'cm-keys__labl';",
		expectFail: 'no longer creates it',
	},
	{
		name: 'the map never opens',
		file: RT,
		// BOTH paths: the platform call and the fallback the fake document
		// takes. Mutating only showModal() left the fake green, because a
		// fake has no showModal and lands in the else branch - the mutant
		// has to remove what the harness actually runs.
		from: /if \(typeof dlg\.showModal === 'function'\) \{\n\t\t\tif \(!dlg\.open\) dlg\.showModal\(\);\n\t\t\} else if \(!dlg\.open\) \{\n\t\t\tdlg\.setAttribute\('open', ''\);\n\t\t\}/,
		to: '/* opened by nobody */',
		expectFail: 'the map was built but never opened',
	},

	// ---- the library defines every part it renders -----------------------
	{
		name: 'the title rule is renamed in the library',
		file: COMP,
		from: /\.cm-keys__title \{/,
		to: '.cm-keys__heading {',
		expectFail: 'components.css never defines .cm-keys__title',
	},
	{
		name: 'the list rule is deleted from the library',
		file: COMP,
		from: /\.cm-keys__list \{[\s\S]*?\n\}\n/,
		to: '',
		expectFail: 'components.css never defines .cm-keys__list',
	},

	// ---- the specimen ----------------------------------------------------
	{
		name: 'the specimen loses the map trigger',
		file: SHOW,
		from: / data-cm-keys-help/,
		to: '',
		expectFail: 'nothing in the specimen opens the map',
	},
	{
		name: 'a binding loses its label, so the map shows element text',
		file: SHOW,
		from: /data-cm-key-label="Go to the lists section"/,
		to: '',
		expectFail: 'every binding needs its own label',
	},
	{
		name: 'the focus action names an element that is not there',
		file: SHOW,
		from: /data-cm-key-focus="#kbd-q"/,
		to: 'data-cm-key-focus="#kbd-nope"',
		expectFail: 'which the specimen does not contain',
	},

	// ---- the docs --------------------------------------------------------
	{
		name: 'the README stops naming the binding attribute',
		file: README,
		from: /data-cm-key=/g,
		to: 'data-cm-shortcut=',
		expectFail: 'the README never mentions data-cm-key',
	},
];

const runSuite = () => {
	const r = spawnSync('node', [join(root, 'tests/run.mjs')], { encoding: 'utf8' });
	return r.stdout || '';
};

/* ---- pre-flight: no pattern may be a no-op, and no mutant may be live ---- */
const originals = new Map();
for (const mut of MUTATIONS) {
	if (!originals.has(mut.file)) originals.set(mut.file, readFileSync(p(mut.file), 'utf8'));
	const src = originals.get(mut.file);
	const out = src.replace(mut.from, mut.to);
	// `String.includes` refuses a RegExp, and `.test()` on a /g/ pattern
	// carries lastIndex between calls - so the probe builds a fresh
	// non-global copy of the pattern for the question it asks.
	const hasFrom = typeof mut.from === 'string' ? src.includes(mut.from)
		: new RegExp(mut.from.source, mut.from.flags.replace('g', '')).test(src);
	if (!hasFrom && src.includes(mut.to)) {
		console.log(`POISONED  ${mut.name}\n       ${mut.file} already contains the mutant's replacement, so a ` +
			`killed sweep (or a wrong pattern) is in play - diff it against HEAD before continuing`);
		process.exit(3);
	}
	if (out === src) {
		console.log(`NO-OP  ${mut.name}\n       pattern did not match ${mut.file} - FIX THE HARNESS`);
		process.exit(2);
	}
}

/* ---- restore-from-memory: a SIGKILL cannot run `finally` ---------------- */
let dirty = null;
const restore = () => {
	if (!dirty) return;
	writeFileSync(p(dirty), originals.get(dirty));
	if (readFileSync(p(dirty), 'utf8') !== originals.get(dirty)) {
		console.error(`RESTORE FAILED for ${dirty}`);
		process.exit(9);
	}
	dirty = null;
};
for (const sig of ['SIGINT', 'SIGTERM', 'SIGHUP']) {
	process.on(sig, () => { restore(); process.exit(130); });
}
process.on('uncaughtException', (e) => { restore(); console.error(e); process.exit(1); });

let caught = 0, missed = 0;
for (const mut of MUTATIONS) {
	const file = p(mut.file);
	const orig = originals.get(mut.file);
	writeFileSync(file, orig.replace(mut.from, mut.to));
	dirty = mut.file;
	try {
		const out = runSuite();
		// The suite prints "FAIL  <name>" and the assertion on the NEXT line;
		// an expectation may be either, so both are tested.
		const lines = out.split('\n');
		const hit = lines.some((ln, i) => ln.startsWith('FAIL')
			&& (ln.includes(mut.expectFail) || (lines[i + 1] || '').includes(mut.expectFail)));
		if (hit) {
			caught++;
			console.log(`caught ${mut.name}`);
		} else {
			missed++;
			console.log(`MISSED ${mut.name}\n       expected: ${mut.expectFail}`);
		}
	} finally {
		restore();
	}
}
console.log(`\n${MUTATIONS.length} mutations: ${caught} caught, ${missed} missed, 0 no-op`);
process.exit(missed ? 1 : 0);
