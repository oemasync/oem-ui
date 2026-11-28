#!/usr/bin/env node
// Measure WCAG 2.x contrast for every ink tier against every surface token
// in src/styles/tokens.css, per theme block. No dependencies.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const TOKENS = path.resolve(ROOT, 'src/styles/tokens.css');

const src = fs.readFileSync(TOKENS, 'utf8');

/* ---------- block discovery ---------- */
// A theme block is any rule block whose body declares --bg. This picks up
// the document themes, the scoped [data-cm-theme] blocks and the print block
// without naming them, so a new theme block is measured automatically.
const blocks = [];
for (const m of src.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
	const body = m[2].replace(/\/\*[\s\S]*?\*\//g, '');
	if (!/--bg\s*:/.test(body)) continue;
	const sel = m[1].replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/\s+/g, ' ').trim();
	let label;
	if (sel.includes("data-cm-theme='dark'")) label = 'dark (scoped)';
	else if (sel.includes("data-cm-theme='light'")) label = 'light (scoped)';
	else if (sel.includes("data-theme='light'") && sel.includes("data-theme='dark'")) label = 'print';
	else if (sel.includes("data-theme='light'")) label = 'light';
	else label = 'dark';

	const decls = {};
	for (const d of body.matchAll(/--([a-zA-Z0-9-]+)\s*:\s*([^;]+);/g)) {
		decls[d[1]] = d[2].trim();
	}
	blocks.push({ label, sel, decls });
}

// De-duplicate identical (label+body) blocks, keep first.
const seen = new Set();
const uniq = [];
for (const b of blocks) {
	const key = b.label + '|' + JSON.stringify(b.decls);
	if (seen.has(key)) continue;
	seen.add(key);
	uniq.push(b);
}
blocks.length = 0;
blocks.push(...uniq);

/* ---------- colour parsing ---------- */
function parseHex(h) {
	h = h.trim().replace(/^#/, '');
	if (h.length === 3) h = h.split('').map((c) => c + c).join('');
	if (h.length === 4) h = h.split('').map((c) => c + c).join('');
	if (h.length === 6) {
		return { r: parseInt(h.slice(0, 2), 16), g: parseInt(h.slice(2, 4), 16), b: parseInt(h.slice(4, 6), 16), a: 1 };
	}
	if (h.length === 8) {
		return { r: parseInt(h.slice(0, 2), 16), g: parseInt(h.slice(2, 4), 16), b: parseInt(h.slice(4, 6), 16), a: parseInt(h.slice(6, 8), 16) / 255 };
	}
	return null;
}

function parseRgbFn(v) {
	const m = /^rgba?\(\s*([^)]+)\)\s*$/.exec(v.trim());
	if (!m) return null;
	const parts = m[1].split(',').map((s) => s.trim());
	if (parts.length < 3) return null;
	const r = parseFloat(parts[0]), g = parseFloat(parts[1]), b = parseFloat(parts[2]);
	let a = 1;
	if (parts.length >= 4) a = parseFloat(parts[3]);
	if ([r, g, b].some((n) => Number.isNaN(n))) return null;
	return { r: Math.round(r), g: Math.round(g), b: Math.round(b), a: Number.isNaN(a) ? 1 : a };
}

function parseColor(v) {
	v = v.trim();
	if (v.startsWith('#')) return parseHex(v);
	if (/^rgba?\(/i.test(v)) return parseRgbFn(v);
	return null;
}

function resolveVar(raw, block, depth = 0) {
	if (depth > 8) return null;
	raw = raw.trim();
	const varm = /^var\(\s*(--[\w-]+)\s*(?:,\s*(.+))?\)$/.exec(raw);
	if (varm) {
		const name = varm[1];
		let r = resolveToken(name, block, depth + 1);
		if (r) return r;
		if (varm[2]) return resolveVar(varm[2].trim(), block, depth + 1);
		return null;
	}
	const c = parseColor(raw);
	if (c) return c;
	return null;
}

const resolveCache = new Map();
function resolveToken(name, block, depth = 0) {
	const key = block.label + '|' + name;
	if (resolveCache.has(key)) return resolveCache.get(key);
	// find raw decl: block first, then any block, then whole file
	let raw = block.decls[name];
	if (raw === undefined) {
		for (const b of blocks) {
			if (b.decls[name] !== undefined) { raw = b.decls[name]; break; }
		}
	}
	if (raw === undefined) {
		const m = new RegExp(`--${name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}:\\s*([^;]+);`).exec(src);
		if (m) raw = m[1].trim();
	}
	if (raw === undefined) {
		resolveCache.set(key, null);
		return null;
	}
	const res = resolveVar(raw, block, depth);
	resolveCache.set(key, res);
	return res;
}

/* ---------- classification ---------- */
const SURFACE_NAME = /^(bg(-\d+)?|panel(-[a-z]+)?|surface-[a-z]+|header-bg|footer-bg|sidebar-background|sidebar-accent)$/;

function isSurface(name) {
	return SURFACE_NAME.test(name);
}

function isInk(name) {
	if (isSurface(name)) return false;
	if (/-(soft|line|glow|bg)$/.test(name)) return false;
	if (/^--/.test(name) === false) {}
	return /ink|accent|focus|^chroma-(ok|warn|err|info)$|foreground|selection-color|^cyan$|^green$|chart-c\d/.test(name);
}

function lum(c) {
	const f = (x) => (x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4);
	const [r, g, b] = [c.r, c.g, c.b].map((v) => f(v / 255));
	return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a, b) {
	const [l1, l2] = [lum(a), lum(b)].sort((x, y) => y - x);
	return (l1 + 0.05) / (l2 + 0.05);
}

function composite(fg, bg) {
	const a = fg.a;
	return {
		r: Math.round(fg.r * a + bg.r * (1 - a)),
		g: Math.round(fg.g * a + bg.g * (1 - a)),
		b: Math.round(fg.b * a + bg.b * (1 - a)),
		a: 1,
	};
}

function verdict(r) {
	if (r >= 4.5) return 'AA';
	if (r >= 3.0) return 'AA-large';
	return 'fail';
}

/* ---------- output ---------- */
const out = [];
// (No document title: the including document owns the H1.)

for (const block of blocks) {
	out.push(`## ${block.label} theme`);
	out.push('');
	out.push(`Selector: \`${block.sel}\``);
	out.push('');

	// Measure the tokens declared in this block (so a block that omits a
	// compat token is not scored against fallback values from another block),
	// plus global aliases such as --focus that live in the base :root block.
	const candidates = [...new Set([...Object.keys(block.decls), 'focus'])];
	const surfaces = candidates.filter(isSurface).sort();
	const inks = candidates.filter(isInk).sort();

	// resolve surfaces
	const surfResolved = {};
	for (const s of surfaces) {
		const c = resolveToken(s, block);
		if (c) surfResolved[s] = c;
	}
	const surfNames = Object.keys(surfResolved);

	out.push('| ink token | surface | ratio | verdict |');
	out.push('|---|---|---:|---|');
	const rows = [];
	const composited = [];
	for (const ink of inks) {
		const ic = resolveToken(ink, block);
		if (!ic) continue;
		// Paired foreground tokens (--X-foreground) are only meaningful
		// against their own --X surface; scoring them on every surface
		// produces meaningless rows.
		let targetSurfaces = surfNames;
		const paired = /^([\w-]+)-foreground$/.exec(ink);
		if (paired) {
			const base = paired[1];
			let own = null;
			if (block.decls[base] !== undefined) own = base;
			else if (block.decls[base + '-background'] !== undefined) own = base + '-background';
			else if (base === 'sidebar' && block.decls['sidebar-background'] !== undefined) own = 'sidebar-background';
			targetSurfaces = own && (block.decls[own] !== undefined || surfResolved[own]) ? [own] : [];
		}
		for (const surf of targetSurfaces) {
			const sc = surfResolved[surf] || resolveToken(surf, block);
			if (!sc) continue;
			let icUse = ic;
			if (ic.a < 1) {
				icUse = composite(ic, sc);
				composited.push(`--${ink} on --${surf}`);
			}
			const r = contrast(icUse, sc);
			rows.push(`| --${ink} | --${surf} | ${r.toFixed(2)}:1 | ${verdict(r)} |`);
		}
	}
	// inverted hover pair: --bg on --ink
	for (const ink of ['ink']) {
		const ic = resolveToken(ink, block);
		const bgc = resolveToken('bg', block);
		if (ic && bgc) {
			const r = contrast(bgc, ic);
			rows.push(`| --bg (on --${ink}, inverted hover) | --${ink} | ${r.toFixed(2)}:1 | ${verdict(r)} |`);
		}
	}
	out.push(...rows);
	out.push('');
	if (composited.length) {
		out.push('_Alpha ink tokens were composited over the surface they sit on before measuring._');
		out.push('');
	}
}

process.stdout.write(out.join('\n') + '\n');
