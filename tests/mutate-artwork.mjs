#!/usr/bin/env node
/**
 * mutation: cm-artwork fixed-aspect tiles (batch 38)
 *
 * Every assertion in the batch-38 block of tests/run.mjs is a guess
 * until it has been made to fail. This harness breaks the exact thing
 * each check guards, runs the suite, and reports which check fired.
 *
 * A pattern that no longer matches the source is a NO-OP — a failure of
 * THIS file, never a pass. Zero no-ops is required for the cycle's
 * caught-count to mean anything.
 *
 * All mutations target files the batch-38 checks read directly
 * (components.css, the showcase, the README). Those checks read SOURCE,
 * not dist/, so no astro build is needed between mutants — every mutant
 * carries skipBuild.
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

/* The artwork CSS block. Several mutants scope to this region so a
   pattern that recurs elsewhere in a 6000-line stylesheet cannot be
   mutated by accident while the suite stays green. */
const comp = readFileSync(p(COMP), 'utf8');
const AW_START = comp.indexOf('/* ---------- artwork');
const AW_END = comp.indexOf('/* ---------- cards ----------');

const MUTATIONS = [
	{
		// The whole point of the family: a ratio on the img still lets the
		// frame collapse to 0 height before the image loads, which is the
		// layout shift the component exists to prevent.
		name: 'the poster variant loses its aspect-ratio (the layout shift returns)',
		file: COMP,
		region: [AW_START, AW_END],
		from: /(\.cm-artwork__frame--poster \{[\s\S]*?)aspect-ratio: 2 \/ 3;/,
		to: '$1',
		expectFail: 'the poster variant does not enforce aspect-ratio',
		skipBuild: true,
	},
	{
		name: 'the backdrop variant is given the poster ratio',
		file: COMP,
		region: [AW_START, AW_END],
		from: /(\.cm-artwork__frame--backdrop \{[\s\S]*?)aspect-ratio: 16 \/ 9;/,
		to: '$1aspect-ratio: 2 / 3;',
		expectFail: 'the backdrop variant does not enforce aspect-ratio',
		skipBuild: true,
	},
	{
		name: 'the square variant loses its aspect-ratio',
		file: COMP,
		region: [AW_START, AW_END],
		from: /(\.cm-artwork__frame--square \{[\s\S]*?)aspect-ratio: 1 \/ 1;/,
		to: '$1',
		expectFail: 'the square variant does not enforce aspect-ratio',
		skipBuild: true,
	},
	{
		// Without absolute positioning the fallback flows INSIDE the frame
		// instead of covering it, so a no-art row still exposes the frame's
		// empty box (and on a real <img> miss, the browser's glyph).
		name: 'the fallback stops covering the frame',
		file: COMP,
		region: [AW_START, AW_END],
		from: /\.cm-artwork__fallback \{[^}]*position: absolute;/,
		to: '.cm-artwork__fallback {',
		expectFail: 'the fallback does not cover the frame',
		skipBuild: true,
	},
	{
		// position:absolute is not enough — with no inset it collapses to
		// its content and covers nothing.
		name: 'the fallback loses its inset, so it covers nothing',
		file: COMP,
		region: [AW_START, AW_END],
		from: /\.cm-artwork__fallback \{[^}]*inset: 0;/,
		to: '.cm-artwork__fallback {',
		expectFail: 'the fallback does not cover the frame',
		skipBuild: true,
	},
	{
		name: 'the fallback loses its designed background',
		file: COMP,
		region: [AW_START, AW_END],
		from: /(\.cm-artwork__fallback \{[^}]*?)background:[^;]*;/,
		to: '$1',
		expectFail: 'the fallback has no designed background',
		skipBuild: true,
	},
	{
		// The overlay slot is the composition point; delete it from one
		// tile and the count drops below three.
		name: 'one tile loses its overlay slot',
		file: SHOW,
		from: /<span class="cm-artwork__overlay" aria-hidden="true">\n\t\t\t\t\t\t\t\t\t<span class="cm-chip cm-chip--ok">1080p<\/span>/,
		to: '<span><span class="cm-chip cm-chip--ok">1080p</span>',
		expectFail: 'the overlay slot is not demonstrated on all three tiles',
		skipBuild: true,
	},
	{
		// "Not colour alone" / not decoration alone: the overlay must carry
		// each composed child the README promises.
		name: 'the overlay stops composing a progress strip',
		file: SHOW,
		from: /<span class="cm-progress" style="--cm-progress:62%"><span class="cm-progress__fill"><\/span><\/span>/,
		to: '',
		expectFail: 'the overlay never composes a progress strip',
		skipBuild: true,
	},
	{
		// "Not colour alone" / not decoration alone: the overlay must carry
		// each composed child the README promises. Anchored to the artwork
		// tile by its SD chip — a bare cm-dot pattern hits the two earlier
		// cm-dot spans (lines 1618/1632) and the artwork tile keeps its dot.
		name: 'the overlay stops composing a status dot',
		file: SHOW,
		from: /<span class="cm-chip cm-chip--warn">SD<\/span>\n	+<span class="cm-dot cm-dot--on" aria-hidden="true"><\/span>/,
		to: '<span class="cm-chip cm-chip--warn">SD</span>',
		expectFail: 'the overlay never composes a status dot',
		skipBuild: true,
	},
	{
		// An eager poster wall fetches every tile on first paint.
		name: 'an artwork image is no longer lazy',
		file: SHOW,
		from: /class="cm-artwork__img" src="data:image\/svg\+xml,%3Csvg%20xmlns='http:\/\/www\.w3\.org\/2000\/svg'%20viewBox='0%200%20200%20300'[^>]*loading="lazy"/,
		to: (m) => m.replace(' loading="lazy"', ''),
		expectFail: 'an artwork image is not lazy',
		skipBuild: true,
	},
	{
		// A component the docs never name is one a consumer reinvents.
		name: 'the README artwork section is renamed away',
		file: README,
		from: /cm-artwork[^\n]*/g,
		to: 'cm-poster',
		expectFail: 'the README never mentions cm-artwork',
		skipBuild: true,
	},
	{
		// Class presence is the cheapest guarantee and still worth killing:
		// a variant markup ships with no matching rule.
		name: 'the square frame rule is deleted from the library',
		file: COMP,
		region: [AW_START, AW_END],
		from: /\.cm-artwork__frame--square \{[\s\S]*?\n\}/,
		to: '',
		expectFail: 'the cm-artwork__frame--square rule is not defined',
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
	let mutated;
	if (mut.region) {
		const [start, end] = mut.region;
		if (start < 0 || end < 0 || end <= start) {
			console.log(`NO-OP  ${mut.name}\n       region not found - FIX THE HARNESS`);
			noop++;
			continue;
		}
		const regionText = orig.slice(start, end);
		const newRegion = regionText.replace(mut.from, typeof mut.to === 'function'
			? (...a) => { const s = mut.to(...a); if (typeof s !== 'string') throw new TypeError(`to() returned ${typeof s}`); return s; }
			: mut.to);
		mutated = newRegion === regionText ? orig : orig.slice(0, start) + newRegion + orig.slice(end);
	} else {
		mutated = orig.replace(mut.from, typeof mut.to === 'function' ? mut.to : mut.to);
	}
	if (mutated === orig) {
		noop++;
		console.log(`NO-OP  ${mut.name}\n       pattern did not match ${mut.file} - FIX THE HARNESS`);
		continue;
	}
	writeFileSync(file, mutated);
	try {
		const out = runSuite();
		// The suite prints the check name on passing "ok" lines too, so a
		// string expectation must anchor to the FAIL line ("FAIL  name",
		// TWO spaces) or the indented assertion message on the next line.
		const lines = out.split('\n');
		const hit = typeof mut.expectFail === 'string'
			? lines.some((ln, i) => ln.startsWith('FAIL')
				&& (ln.includes(mut.expectFail) || (lines[i + 1] || '').includes(mut.expectFail)))
			: mut.expectFail.test(out);
		if (hit && /FAIL/.test(out)) {
			caught++;
			console.log(`caught ${mut.name}`);
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
