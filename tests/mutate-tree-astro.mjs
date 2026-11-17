#!/usr/bin/env node
/**
 * mutation: <Tree>, the nested file/record tree wrapper
 *
 * Every assertion added this cycle is a guess until it has been made to
 * fail. This harness breaks the exact thing each check guards, runs the
 * suite, and reports which check fired. Like mutate-param-astro.mjs,
 * every mutant here is source/regex-level (the component's REAL rendered
 * output - the recursion, the root-only attrs and the href fallback all
 * reaching the DOM correctly - is proven once by the suite's own
 * built-dist check against a real `npm run build`, which this sweep does
 * not rebuild for).
 *
 * A pattern that no longer matches the source is a NO-OP - a failure of
 * THIS file, never a pass. The count reported in the cycle note must
 * have zero in it, or the harness itself is broken and the number is
 * worthless.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const p = (f) => join(root, f);
const TA = 'src/astro/Tree.astro';
const SHOW = 'src/pages/[...family].astro';

const MUTATIONS = [
	{
		// The root gate on the class. Without it, every nested <ul> a
		// branch recurses into would also carry cm-tree--root.
		name: 'cm-tree--root is no longer gated on root',
		file: TA,
		from: "class:list={['cm-tree', root && 'cm-tree--root']}",
		to: "class:list={['cm-tree', 'cm-tree--root']}",
		expectFail: 'Tree.astro does not conditionally add cm-tree--root on root',
	},
	{
		// The root gate on the binding attribute and label. Without it,
		// every nested <ul> repeats data-cm-tree and the root's own
		// aria-label - the exact bug a naive recursive render makes.
		name: 'data-cm-tree/aria-label are no longer gated on root',
		file: TA,
		from: "{...root && { 'data-cm-tree': true, 'aria-label': label }}",
		to: "{{ 'data-cm-tree': true, 'aria-label': label }}",
		expectFail: 'Tree.astro does not gate data-cm-tree/aria-label on root',
	},
	{
		// The branch/leaf decision itself. Without it every node (even a
		// leaf) would be read as a branch, or vice versa.
		name: 'the branch/leaf decision no longer reads node.children',
		file: TA,
		from: 'node.children ? (',
		to: 'node.open ? (',
		expectFail: 'Tree.astro does not branch on node.children to decide branch vs leaf',
	},
	{
		// The branch's open state. Dropping node.open means every branch
		// defaults OPEN (the platform default for a bare <details>),
		// stranding a page expanded the author asked to keep collapsed.
		name: "a branch's open state no longer reads node.open",
		file: TA,
		from: '<details class="cm-disclosure" open={node.open}>',
		to: '<details class="cm-disclosure">',
		expectFail: 'Tree.astro does not render a branch as a cm-disclosure, or does not pass node.open through',
	},
	{
		// The recursive call. Without root={false}, every nested <ul> is
		// itself treated as a root and re-adds the gated attrs one level
		// down - caught by the SAME check as the two gates above, which
		// is the point: the gates and the call that could defeat them
		// are two different ways to the same bug.
		name: 'the recursive call no longer passes root={false}',
		file: TA,
		from: '<Tree nodes={node.children} root={false} />',
		to: '<Tree nodes={node.children} />',
		expectFail: 'Tree.astro does not recurse into itself with root={false}',
	},
	{
		// The href fallback. Without it, a leaf given no href renders a
		// dead, unfocusable, untappable row instead of a real link.
		name: 'the href fallback to # is removed',
		file: TA,
		from: "href={node.href ?? '#'}",
		to: 'href={node.href}',
		expectFail: 'Tree.astro does not fall back href to "#" for a leaf with none',
	},
	{
		// The root-label guard. Without it, a root call with no label
		// renders a tree that reads as an anonymous nested list to a
		// screen reader, with nothing to catch the mistake at build time.
		name: 'the root-label guard is disabled',
		file: TA,
		from: 'if (root && !label) {',
		to: 'if (false && root && !label) {',
		expectFail: 'Tree.astro does not guard the root call against a missing label',
	},
	{
		// The demonstration. A wrapper only ever read in its own file is
		// a promise, not a product - the showcase specimen is the proof
		// it composes correctly, with a closed branch and an href-less
		// leaf actually exercised, not merely an all-defaults happy path.
		name: 'the showcase stops rendering <Tree>',
		file: SHOW,
		from: "import Tree from '../astro/Tree.astro';",
		to: '',
		expectFail: 'the showcase does not import Tree.astro',
	},
	{
		// The closed-branch specimen. Giving every branch `open: true`
		// would leave the "a branch given no open prop defaults closed"
		// claim completely unexercised in the showcase/built-page checks.
		name: "the showcase's \"tests/\" branch specimen is given open: true",
		file: SHOW,
		from: "label: 'tests/',\n\t\t\t\t\t\t\t\t\tchildren: [{ label: 'run.mjs', href: '#tree' }],",
		to: "label: 'tests/',\n\t\t\t\t\t\t\t\t\topen: true,\n\t\t\t\t\t\t\t\t\tchildren: [{ label: 'run.mjs', href: '#tree' }],",
		expectFail: 'the showcase specimen gives its "tests/" branch open: true - without a closed branch, the wrapper never proves a <details> with no open attribute',
	},
	{
		// The href-less-leaf specimen. Giving LICENSE an href would leave
		// the href-fallback path completely unexercised by the showcase.
		name: "the showcase's LICENSE leaf specimen is given an href",
		file: SHOW,
		from: "{ label: 'LICENSE' },",
		to: "{ label: 'LICENSE', href: '#tree' },",
		expectFail: 'the showcase specimen gives every leaf an href - without one, the href-fallback-to-# path is unproven',
	},
];

// --range a,b runs MUTATIONS[a..b] inclusive, so a slow full sweep can be
// split across several tool calls that each stay comfortably under a
// hard wall-clock timeout, the same device mutate-param-astro.mjs uses.
const rangeArg = process.argv.find((a) => a.startsWith('--range='));
let RANGE = [0, MUTATIONS.length - 1];
if (rangeArg) {
	const [a, b] = rangeArg.slice('--range='.length).split(',').map(Number);
	RANGE = [a, b];
}
const ACTIVE = MUTATIONS.slice(RANGE[0], RANGE[1] + 1);

const runSuite = () => {
	const r = spawnSync('node', [join(root, 'tests/run.mjs')], { encoding: 'utf8' });
	return r.stdout || '';
};

let caught = 0, missed = 0, noop = 0;
/* A sweep this long sits inside the kill boundary: a timeout SIGKILLs the
   process and `finally` never runs, leaving the last mutant in the tree.
   So the current mutation is tracked and a restore handler is bound to
   every signal the process can receive; uncaughtException gets the same
   treatment. Re-entrancy guard: only one restore in flight. */
let current = null;
let restoring = false;
function restoreNow(reason) {
	if (restoring) return;
	restoring = true;
	if (current) {
		try {
			writeFileSync(current.file, current.orig);
			const back = readFileSync(current.file, 'utf8');
			if (back !== current.orig) {
				console.log(`RESTORE FAILED for ${current.name} (${reason}) - verify the tree by hand`);
			}
		} catch (e) {
			console.log(`RESTORE ERROR for ${current.name} (${reason}): ${e.message}`);
		}
	}
	console.log(`restored (${reason})`);
	process.exit(130);
}
for (const sig of ['SIGINT', 'SIGTERM', 'SIGHUP']) {
	process.on(sig, () => restoreNow(sig));
}
process.on('uncaughtException', (e) => {
	console.log(`uncaughtException: ${e.message}`);
	restoreNow('uncaughtException');
});
/* Pre-flight: every pattern must match EXACTLY once, or the sweep would
   mutate the wrong rule or mutate nothing. A miss is reported before
   anything is written, not discovered mid-run. */
for (const mut of ACTIVE) {
	const src = readFileSync(p(mut.file), 'utf8');
	const n = src.split(mut.from).length - 1;
	if (n !== 1) {
		console.log(`PRE-FLIGHT FAIL  ${mut.name}\n       pattern matches ${n} time(s) in ${mut.file} - FIX THE HARNESS`);
		process.exit(2);
	}
}
for (const mut of ACTIVE) {
	const file = p(mut.file);
	const orig = readFileSync(file, 'utf8');
	const mutated = orig.replace(mut.from, mut.to);
	if (mutated === orig) {
		noop++;
		console.log(`NO-OP  ${mut.name}\n       pattern did not match ${mut.file} - FIX THE HARNESS`);
		continue;
	}
	writeFileSync(file, mutated);
	current = { file, orig, name: mut.name };
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
		const back = readFileSync(file, 'utf8');
		if (back !== orig) {
			console.log(`RESTORE MISMATCH after ${mut.name} - verify the tree by hand`);
			process.exit(3);
		}
		current = null;
	}
}
console.log(`\n${ACTIVE.length} mutation(s) in range [${RANGE[0]},${RANGE[1]}]: ${caught} caught, ${missed} missed, ${noop} no-op`);
if (noop) process.exit(2);
process.exit(missed ? 1 : 0);
