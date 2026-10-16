#!/usr/bin/env node
/**
 * Is oem-ui still level with shadcn?
 *
 * The suite pins shadcn's component list ONCE, on purpose: a pin means an
 * update is a deliberate act with a diff, rather than a moving target that
 * silently redefines "parity" while nobody is looking. The cost of that
 * design is real and was paid: shadcn shipped `code-block` and `trace`
 * while the pin still said 64, and NOTHING here could announce it. The
 * drift was found by hand, which is not a process.
 *
 * So this is the other half. It is NOT part of `npm test` - the suite must
 * stay offline and hermetic, or a network blip becomes a red build and
 * people stop trusting red. This runs when someone asks, and it answers
 * one question: has shadcn's live list moved away from our pinned one?
 *
 *   node scripts/check-parity-live.mjs            # compare, exit 1 on drift
 *   node scripts/check-parity-live.mjs --list     # just print the live list
 *
 * WHY IT PARSES THE LEDGER OUT OF tests/run.mjs rather than restating it:
 * a second copy of the list is a second source of truth, and the whole
 * failure mode this tool exists to catch is two lists drifting apart. It
 * reads the pin where the pin actually lives.
 *
 * A real browser User-Agent is REQUIRED. A plain curl gets shadcn's bot
 * wall - 104 KB of shell with none of the list in it - so a naive fetch
 * would have compared our ledger against nothing and reported a clean
 * bill of health. That failure mode (0 items found, therefore no
 * differences) is guarded against explicitly below.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const UA =
	'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 ' +
	'(KHTML, like Gecko) Version/17.0 Safari/605.1.15';

/* The pin lives in the suite. Read it from there - never from a copy. */
function pinnedList() {
	const src = readFileSync(join(ROOT, 'tests', 'run.mjs'), 'utf8');
	const at = src.indexOf('const SHADCN = [');
	if (at === -1) throw new Error('the pinned SHADCN list is not in tests/run.mjs any more');
	const end = src.indexOf('];', at);
	const body = src.slice(at, end);
	const names = [...body.matchAll(/'([^']+)'/g)].map((m) => m[1]);
	if (names.length < 10) throw new Error(`only ${names.length} names parsed from the pin - the shape changed`);
	return names;
}

/* Title-case a slug the way shadcn writes it: `drop-down` -> `Drop Down`,
   with `and`/`of` style words kept... except shadcn does NOT do that:
   it writes "Data Table", "Date Picker", "Input OTP", "Toggle Group". So
   plain title-case per hyphen-separated word is right, and the exceptions
   are handled by comparing against the pin's own spelling. */
const IRREGULAR = {
	'input-otp': 'Input OTP',
	'kbd': 'Kbd',
	'otp': 'OTP',
};

function titleize(slug) {
	if (IRREGULAR[slug]) return IRREGULAR[slug];
	return slug
		.split('-')
		.map((w) => (w.length <= 3 && w === w.toUpperCase() ? w : w[0].toUpperCase() + w.slice(1)))
		.map((w) => w)
		.join(' ');
}

async function liveList() {
	const res = await fetch('https://ui.shadcn.com/docs/components', {
		headers: { 'user-agent': UA, accept: 'text/html' },
	});
	if (!res.ok) throw new Error(`shadcn returned HTTP ${res.status}`);
	const html = await res.text();
	/* Bot wall check: the real page is ~580 KB and carries the RSC payload.
	   A wall is smaller and carries none. */
	const ids = [...html.matchAll(/\\?"\$id\\?":\\?"components\/base\/([a-z0-9-]+)\.mdx\\?"/g)];
	const seen = new Set();
	const ordered = [];
	for (const m of ids) {
		if (seen.has(m[1])) continue;
		seen.add(m[1]);
		ordered.push(m[1]);
	}
	if (ordered.length === 0) {
		throw new Error(
			`parsed 0 components out of ${html.length} bytes - that is the bot wall, ` +
			'not the page. Refusing to report "no drift" from an empty measurement.',
		);
	}
	return ordered;
}

const args = process.argv.slice(2);
const listOnly = args.includes('--list');

const pin = pinnedList();
const live = await liveList();
const liveNames = live.map(titleize);

if (listOnly) {
	console.log(`live base/ namespace: ${live.length}`);
	for (const n of liveNames) console.log('  ' + n);
	process.exit(0);
}

const pinSet = new Set(pin);
const liveSet = new Set(liveNames);

const added = liveNames.filter((n) => !pinSet.has(n));
const removed = pin.filter((n) => !liveSet.has(n));

/* Order matters as much as membership: our ledger promises shadcn's ORDER,
   so a reordering on their side is drift even when the sets match. */
let firstOrderDiff = -1;
const n = Math.min(pin.length, liveNames.length);
for (let i = 0; i < n; i++) {
	if (pin[i] !== liveNames[i]) { firstOrderDiff = i; break; }
}

console.log(`pinned in tests/run.mjs : ${pin.length}`);
console.log(`live on ui.shadcn.com   : ${live.length}`);

if (!added.length && !removed.length && firstOrderDiff === -1 && pin.length === liveNames.length) {
	console.log('\nlevel: identical membership AND order.');
	process.exit(0);
}

console.log('');
if (added.length) {
	console.log(`shadcn has these, we do not (${added.length}):`);
	for (const a of added) console.log(`  + ${a}`);
}
if (removed.length) {
	console.log(`we list these, shadcn no longer does (${removed.length}):`);
	for (const r of removed) console.log(`  - ${r}`);
}
if (firstOrderDiff !== -1) {
	console.log(`order diverges from index ${firstOrderDiff}:`);
	console.log(`  ours: ${pin.slice(firstOrderDiff, firstOrderDiff + 4).join(', ')}`);
	console.log(`  live: ${liveNames.slice(firstOrderDiff, firstOrderDiff + 4).join(', ')}`);
}
console.log(
	'\nDRIFT. Update, in this order: the pinned SHADCN list in tests/run.mjs,\n' +
	'the README ledger (names + the "catalog is N" prose), the section index\n' +
	'and NAV_GROUP_SIZES in src/pages/[...family].astro, and the expected\n' +
	'counts in tests/verify-doc-toc.py. Then build the components: a name in\n' +
	'the list is a claim that the component exists.',
);
process.exit(1);
