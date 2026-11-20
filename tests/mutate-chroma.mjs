#!/usr/bin/env node
/**
 * mutation: status colour (on by default, data-cm-chroma="off") and the stacked meter
 *
 * Every check in the "status chroma" block of tests/run.mjs is a guess
 * until it has been made to fail. Each mutant below breaks the one thing
 * a check guards, runs the suite, and requires THAT check to fail.
 *
 * "Fail" is read strictly: the suite prints `FAIL  <name>` for a failed
 * check and `  ok  <name>` for a passing one, so looking for the name
 * alone would call every mutant caught. The match is on the FAIL line.
 *
 * A pattern that no longer matches its file is a NO-OP, which is a
 * failure of this harness, never a pass: exit 2.
 *
 * Two mutants change what the showcase renders, and the check that
 * guards them reads the BUILT page, so those two rebuild first. The
 * build is restored at the end.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const p = (f) => join(root, f);
const TOK = 'src/styles/tokens.css';
const COMP = 'src/styles/components.css';
const SHOW = 'src/pages/[...family].astro';
const CHIP = 'src/astro/Chip.astro';
const README = 'README.md';

const C = {
	keys: 'chroma: every palette block declares all twelve tokens',
	mirror: 'chroma: the scoped and print blocks carry the theme they mirror',
	text: 'chroma: every hue is AA as text on every surface of its theme',
	tint: 'chroma: every hue is AA on its own tint, over every surface',
	same: 'chroma: a tint and its hairline are the hue of their text',
	hues: 'chroma: the four hues are hues, and no two are neighbours',
	gate: 'chroma: colour is on by default, and data-cm-chroma="off" puts a subtree back in grey',
	map: 'chroma: every named state takes its hue, and keeps its grey with colour off',
	lit: 'chroma: no component paints a literal hue',
	fall: 'chroma: a setter only sets, and a reader always has a grey to fall back to',
	shadow: 'chroma: each fallback is the grey of the rule it shadows',
	rank: 'chroma: a reader never out-ranks a state rule',
	alone: 'chroma: a tone class paints nothing by itself',
	chip: 'chroma: the chip has four severities, each with its own glyph',
	seg: 'chroma: a stacked segment draws its width from the number it prints',
	legend: 'chroma: a stacked meter is labelled in the order it is drawn',
	inherit: 'chroma: an untoned segment cannot inherit a hue',
	show: 'chroma: the showcase draws the same markup with colour on and off',
	readme: 'chroma: the README documents the switch, the tokens and the limit',
};

// `nth` picks which occurrence of a string pattern to replace (1-based).
const MUTATIONS = [
	{ name: 'the dark error hue is retuned below AA', file: TOK, nth: 1,
		from: '--chroma-err: #ff7b72;', to: '--chroma-err: #b3261e;', expectFail: C.text },
	{ name: 'the light warn tint is made heavy enough to swallow its text', file: TOK, nth: 1,
		from: '--chroma-warn-soft: rgba(133, 77, 14, 0.1);', to: '--chroma-warn-soft: rgba(133, 77, 14, 0.6);', expectFail: C.tint },
	{ name: 'the dark ok tint drifts to another hue', file: TOK, nth: 1,
		from: '--chroma-ok-soft: rgba(74, 222, 128, 0.14);', to: '--chroma-ok-soft: rgba(250, 204, 21, 0.14);', expectFail: C.same },
	{ name: 'the dark warn hue is retuned to grey', file: TOK, nth: 1,
		from: '--chroma-warn: #facc15;', to: '--chroma-warn: #c8c8c8;', expectFail: C.hues },
	{ name: 'warn is retuned to sit beside err', file: TOK, nth: 1,
		from: '--chroma-warn: #facc15;', to: '--chroma-warn: #ff8a5c;', expectFail: C.hues },
	{ name: 'the scoped dark block keeps an older ok', file: TOK, nth: 2,
		from: '--chroma-ok: #4ade80;', to: '--chroma-ok: #3fb950;', expectFail: C.mirror },
	{ name: 'print forgets the info hue', file: TOK, nth: 1,
		from: '\t\t--chroma-info: #1d4ed8;\n', to: '', expectFail: C.keys },
	{ name: 'print mirrors the dark theme', file: TOK, nth: 1,
		from: '\t\t--chroma-ok: #166534;', to: '\t\t--chroma-ok: #4ade80;', expectFail: C.mirror },
	{ name: 'the ok setter gains weight', file: COMP, nth: 1,
		from: ':where(.cm-tone--ok, .cm-chip--ok,', to: '.cm-tone--ok, :where(.cm-chip--ok,', expectFail: C.gate },
	{ name: 'the off switch covers the root but not the subtree', file: COMP, nth: 1,
		from: "[data-cm-chroma='off'],\n[data-cm-chroma='off'] * {", to: "[data-cm-chroma='off'] {", expectFail: C.gate },
	{ name: 'the off switch leaves the tint on', file: COMP, nth: 1,
		from: '\t--tone-soft: initial;\n', to: '', expectFail: C.gate },
	{ name: 'the warn toast drops out of the warn setter', file: COMP, nth: 1,
		from: '.cm-callout--warn, .cm-toast--warn, ', to: '.cm-callout--warn, ', expectFail: C.map },
	{ name: 'a create row is also in the err setter', file: COMP, nth: 1,
		from: ':where(.cm-tone--err, ', to: ":where(.cm-diff__row[data-op='create'], .cm-tone--err, ", expectFail: C.map },
	{ name: 'the field error falls back to the wrong grey', file: COMP, nth: 1,
		from: '\tfont-size: max(var(--min-font), var(--text-xs));\n\tcolor: var(--tone, var(--ink));',
		to: '\tfont-size: max(var(--min-font), var(--text-xs));\n\tcolor: var(--tone, var(--ink-dim));', expectFail: C.map },
	{ name: 'a done trace step goes back to grey only', file: COMP, nth: 1,
		from: '.cm-trace__item.is-done .cm-trace__icon { background: var(--tone, var(--ink));',
		to: '.cm-trace__item.is-done .cm-trace__icon { background: var(--ink);', expectFail: C.map },
	{ name: 'the warn log line goes back to a literal orange', file: COMP, nth: 1,
		from: '.cm-term__line--warn { border-inline-start: 2px solid var(--tone, var(--ink-faint));',
		to: '.cm-term__line--warn { border-inline-start: 2px solid #f59e0b;', expectFail: C.lit },
	{ name: 'the danger hover fills with a literal red', file: COMP, nth: 1,
		from: '.cm-btn--danger:hover { background: var(--tone, var(--ink));',
		to: '.cm-btn--danger:hover { background: #a4161a;', expectFail: C.lit },
	{ name: 'a reader names a chroma token directly', file: COMP, nth: 1,
		from: '{ border-block-start-color: var(--tone, var(--line)); }', to: '{ border-block-start-color: var(--chroma-ok); }', expectFail: C.gate },
	{ name: 'the chip reader loses its fallback', file: COMP, nth: 1,
		from: '\tcolor: var(--tone, var(--ink-dim));\n', to: '\tcolor: var(--tone);\n', expectFail: C.fall },
	{ name: 'a setter also paints', file: COMP, nth: 1,
		from: '\t--tone: var(--chroma-err);\n', to: '\t--tone: var(--chroma-err);\n\tcolor: var(--chroma-err);\n', expectFail: C.fall },
	{ name: 'the ok alert edge falls back to the wrong grey', file: COMP, nth: 1,
		from: '.cm-alert:where(.cm-alert--ok) { border-inline-start-color: var(--tone, var(--ink-dim)); }',
		to: '.cm-alert:where(.cm-alert--ok) { border-inline-start-color: var(--tone, var(--ink)); }', expectFail: C.shadow },
	{ name: 'the err chip glyph falls back to the wrong grey', file: COMP, nth: 1,
		from: '.cm-chip:where(.cm-chip--err)::before { color: var(--tone, var(--ink)); }',
		to: '.cm-chip:where(.cm-chip--err)::before { color: var(--tone, var(--ink-dim)); }', expectFail: C.shadow },
	{ name: 'the toned dot falls back to a hollow dot', file: COMP, nth: 1,
		from: '\tbackground: var(--tone, var(--ink));\n}', to: '\tbackground: var(--tone, transparent);\n}', expectFail: C.shadow },
	{ name: 'the chip reader is raised above the hover rule', file: COMP, nth: 1,
		from: '.cm-chip:where(.cm-tone--ok, .cm-tone--warn, .cm-tone--err, .cm-tone--info, .cm-chip--ok,',
		to: '.cm-chip:is(.cm-tone--ok, .cm-tone--warn, .cm-tone--err, .cm-tone--info, .cm-chip--ok,', expectFail: C.rank },
	{ name: 'a bare tone class paints', file: COMP, nth: 1,
		from: '.cm-meter__track--stack { display: flex; }',
		to: '.cm-tone--err { color: var(--tone, var(--ink)); }\n.cm-meter__track--stack { display: flex; }', expectFail: C.alone },
	{ name: 'the info chip loses its glyph', file: COMP, nth: 1,
		from: ".cm-chip--info::before { content: '\\2139\\00a0'; }", to: '.cm-chip--info::before { }', expectFail: C.chip },
	{ name: 'the info chip borrows the ok glyph', file: COMP, nth: 1,
		from: ".cm-chip--info::before { content: '\\2139\\00a0'; }", to: ".cm-chip--info::before { content: '\\25cf\\00a0'; }", expectFail: C.chip },
	{ name: '<Chip> forgets the fourth severity', file: CHIP, nth: 1,
		from: "variant?: 'ok' | 'warn' | 'err' | 'info' | 'set';", to: "variant?: 'ok' | 'warn' | 'err' | 'set';", expectFail: C.chip },
	{ name: 'a segment grows to fill the track', file: COMP, nth: 1,
		from: '\tflex: 0 1 var(--cm-meter-fill, 0%);', to: '\tflex: 1 1 0;', expectFail: C.seg },
	{ name: 'the stacked track is not a row', file: COMP, nth: 1,
		from: '.cm-meter__track--stack { display: flex; }', to: '.cm-meter__track--stack { display: block; }', expectFail: C.seg },
	{ name: 'the gap between shares is not the track colour', file: COMP, nth: 1,
		from: '.cm-meter__seg + .cm-meter__seg { border-inline-start: 1px solid var(--bg-3); }',
		to: '.cm-meter__seg + .cm-meter__seg { border-inline-start: 1px solid var(--ink); }', expectFail: C.seg },
	{ name: 'every segment reads the inherited tone', file: COMP, nth: 1,
		from: '\tbackground: var(--cm-seg-grey, var(--ink));', to: '\tbackground: var(--tone, var(--cm-seg-grey, var(--ink)));', expectFail: C.inherit },
	{ name: 'the legend stops wrapping', file: COMP, nth: 1,
		from: '.cm-meter__legend {\n\tdisplay: flex;\n\tflex-wrap: wrap;', to: '.cm-meter__legend {\n\tdisplay: flex;\n\tflex-wrap: nowrap;', expectFail: C.legend },
	{ name: 'the legend is listed out of order', file: SHOW, nth: 1, build: true,
		from: '<li><span class="cm-dot cm-tone--ok" aria-hidden="true"></span>done <span class="cm-meter__count">90</span></li>\n\t\t\t\t\t\t\t\t<li><span class="cm-dot cm-tone--info" aria-hidden="true"></span>in review <span class="cm-meter__count">15</span></li>',
		to: '<li><span class="cm-dot cm-tone--info" aria-hidden="true"></span>in review <span class="cm-meter__count">15</span></li>\n\t\t\t\t\t\t\t\t<li><span class="cm-dot cm-tone--ok" aria-hidden="true"></span>done <span class="cm-meter__count">90</span></li>', expectFail: C.legend },
	{ name: 'a share is drawn wider than its count', file: SHOW, nth: 1, build: true,
		from: '<span class="cm-meter__seg cm-tone--warn" style="--cm-meter-fill: 20%"></span>', to: '<span class="cm-meter__seg cm-tone--warn" style="--cm-meter-fill: 35%"></span>', expectFail: C.legend },
	{ name: 'the README section is deleted', file: README, nth: 1,
		from: /## Status colour\n[\s\S]*?\n(?=## Method badge\n)/, to: '', expectFail: C.readme },
	{ name: 'the README drops the limit on hue alone', file: README, nth: 1,
		from: '**A hue is never the state alone.**', to: '**A hue is a state.**', expectFail: C.readme },
	{ name: 'the section leaves the index', file: SHOW, nth: 1,
		from: "'states', 'chroma', 'surface',", to: "'states', 'surface',", expectFail: C.show },
	{ name: 'both columns get the off switch', file: SHOW, nth: 1, build: true,
		from: "data-cm-chroma={on ? undefined : 'off'}", to: 'data-cm-chroma="off"', expectFail: C.show },
	{ name: 'the README goes back to opt-in', file: README, nth: 1,
		from: 'It is on by default.', to: 'It is opt-in.', expectFail: C.readme },
	{ name: 'the README forgets what red means', file: README, nth: 1,
		from: 'red is bad, ', to: '', expectFail: C.readme },
	{ name: 'the specimen drops the untoned segment', file: SHOW, nth: 1, build: true,
		from: '\t\t\t\t\t\t\t\t<span class="cm-meter__seg" style="--cm-meter-fill: 10%"></span>\n', to: '', expectFail: C.show },
];

const replaceNth = (src, from, to, nth) => {
	if (from instanceof RegExp) return src.replace(from, to);
	let at = -1;
	for (let i = 0; i < nth; i++) { at = src.indexOf(from, at + 1); if (at === -1) return src; }
	return src.slice(0, at) + to + src.slice(at + from.length);
};
const runSuite = () => (spawnSync('node', [join(root, 'tests/run.mjs')], { encoding: 'utf8' }).stdout || '');
const build = () => spawnSync('npm', ['run', 'build'], { cwd: root, encoding: 'utf8' }).status === 0;

const only = process.argv[2];
let caught = 0, missed = 0, noop = 0, rebuilt = false;
for (const mut of MUTATIONS) {
	if (only && !mut.name.includes(only)) continue;
	const file = p(mut.file);
	const orig = readFileSync(file, 'utf8');
	const mutated = replaceNth(orig, mut.from, mut.to, mut.nth || 1);
	if (mutated === orig) {
		noop++;
		console.log(`NO-OP  ${mut.name}\n       pattern did not match ${mut.file} - FIX THE HARNESS`);
		continue;
	}
	writeFileSync(file, mutated);
	try {
		if (mut.build) { rebuilt = true; if (!build()) { missed++; console.log(`MISSED ${mut.name}\n       the mutant did not build, so the check never saw it`); continue; } }
		const out = runSuite();
		if (out.includes(`FAIL  ${mut.expectFail}\n`)) {
			caught++;
			const why = out.split(`FAIL  ${mut.expectFail}\n`)[1].split('\n')[0].trim();
			console.log(`caught ${mut.name}\n       -> ${mut.expectFail}\n          ${why.slice(0, 200)}`);
		} else {
			missed++;
			console.log(`MISSED ${mut.name}\n       expected: ${mut.expectFail}`);
		}
	} finally {
		writeFileSync(file, orig);
	}
}
if (rebuilt && !build()) { console.log('the restoring build FAILED - dist/ is stale'); process.exit(3); }
console.log(`\n${caught + missed + noop} mutations: ${caught} caught, ${missed} missed, ${noop} no-op`);
if (noop) process.exit(2);
process.exit(missed ? 1 : 0);
