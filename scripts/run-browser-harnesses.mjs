#!/usr/bin/env node
/* Run the registered browser harnesses against THIS checkout's build.
 *
 *   node scripts/run-browser-harnesses.mjs            # build, serve, run all
 *   node scripts/run-browser-harnesses.mjs --no-build # serve the dist/ there is
 *   node scripts/run-browser-harnesses.mjs verify-calendar verify-datepicker
 *
 * Why a manifest and not a glob: the harnesses in tests/ grew one at a time
 * and do not agree on how they are pointed at a page (a LAN address, three
 * ports, BASE_URL, RAIL_URL, or nothing at all). A harness that ignores the
 * URL it is given measures some other server's build and reports on that, so
 * a harness is listed in tests/browser-harnesses.txt only once it is known to
 * read OEM_UI_URL. Everything listed runs; nothing unlisted does.
 *
 * The page is served from dist/ on a free loopback port by a tiny static
 * server in this file, so the run needs no preview server, no fixed port and
 * no network. Python comes from OEM_UI_PY (a venv with playwright and its
 * WebKit installed), defaulting to `python3` on PATH.
 */
import { spawn, spawnSync } from 'node:child_process';
import { createReadStream, existsSync, readFileSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { extname, join, normalize, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)));
const DIST = join(ROOT, 'dist');
const MANIFEST = join(ROOT, 'tests', 'browser-harnesses.txt');
const PY = process.env.OEM_UI_PY || 'python3';
const TIMEOUT_S = Number(process.env.OEM_UI_HARNESS_TIMEOUT || 900);

const args = process.argv.slice(2);
const noBuild = args.includes('--no-build');
const only = args.filter((a) => !a.startsWith('--'));

const listed = readFileSync(MANIFEST, 'utf8').split('\n')
	.map((l) => l.replace(/#.*/, '').trim()).filter(Boolean);
for (const name of listed) {
	if (!existsSync(join(ROOT, 'tests', name + '.py'))) {
		console.error(`manifest lists ${name}, and tests/${name}.py does not exist`);
		process.exit(2);
	}
}
const unknown = only.filter((n) => !listed.includes(n));
if (unknown.length) {
	console.error(`not in the manifest: ${unknown.join(', ')}`);
	process.exit(2);
}
const run = only.length ? listed.filter((n) => only.includes(n)) : listed;

if (!noBuild) {
	const b = spawnSync('npm', ['run', 'build'], { cwd: ROOT, stdio: 'inherit' });
	if (b.status !== 0) process.exit(b.status || 1);
}
if (!existsSync(join(DIST, 'index.html'))) {
	console.error('dist/index.html is missing: build first, or drop --no-build');
	process.exit(2);
}

const TYPES = {
	'.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
	'.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8',
	'.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png',
	'.jpg': 'image/jpeg', '.webp': 'image/webp', '.ico': 'image/x-icon',
	'.woff2': 'font/woff2', '.mp4': 'video/mp4', '.wav': 'audio/wav', '.txt': 'text/plain',
};
const server = createServer((req, res) => {
	let path = decodeURIComponent(new URL(req.url, 'http://x').pathname);
	let file = normalize(join(DIST, path));
	if (file !== DIST && !file.startsWith(DIST + sep)) { res.writeHead(403); res.end(); return; }
	if (existsSync(file) && statSync(file).isDirectory()) file = join(file, 'index.html');
	if (!existsSync(file)) { res.writeHead(404); res.end('not found'); return; }
	const size = statSync(file).size;
	const type = TYPES[extname(file)] || 'application/octet-stream';
	// Ranges, because a <video preload="metadata"> asks for one.
	const m = /^bytes=(\d*)-(\d*)$/.exec(req.headers.range || '');
	if (m) {
		const start = m[1] ? Number(m[1]) : Math.max(0, size - Number(m[2]));
		const end = m[1] && m[2] ? Math.min(Number(m[2]), size - 1) : size - 1;
		if (start > end || start >= size) { res.writeHead(416, { 'Content-Range': `bytes */${size}` }); res.end(); return; }
		res.writeHead(206, { 'Content-Type': type, 'Content-Length': end - start + 1,
			'Content-Range': `bytes ${start}-${end}/${size}`, 'Accept-Ranges': 'bytes' });
		createReadStream(file, { start, end }).pipe(res);
		return;
	}
	res.writeHead(200, { 'Content-Type': type, 'Content-Length': size, 'Accept-Ranges': 'bytes' });
	createReadStream(file).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const url = `http://127.0.0.1:${server.address().port}/`;
console.log(`serving ${DIST} at ${url}; ${run.length} harness(es), python ${PY}`);

const results = [];
for (const name of run) {
	const t0 = Date.now();
	const env = { ...process.env, OEM_UI_URL: url, PYTHONUNBUFFERED: '1' };
	delete env.PYTHONPATH;
	const code = await new Promise((done) => {
		const p = spawn(PY, ['-W', 'ignore', join('tests', name + '.py')], { cwd: ROOT, env, stdio: ['ignore', 'pipe', 'pipe'] });
		let out = '';
		p.stdout.on('data', (d) => { out += d; });
		p.stderr.on('data', (d) => { out += d; });
		const kill = setTimeout(() => { out += `\nTIMEOUT after ${TIMEOUT_S}s`; p.kill('SIGKILL'); }, TIMEOUT_S * 1000);
		p.on('close', (c) => {
			clearTimeout(kill);
			const lines = out.trimEnd().split('\n');
			const fails = lines.filter((l) => /^(FAIL|BROKEN)/.test(l));
			for (const l of fails) console.log(`    ${l.slice(0, 220)}`);
			if (c !== 0 && !fails.length) for (const l of lines.slice(-8)) console.log(`    ${l.slice(0, 220)}`);
			console.log(`${c === 0 ? 'ok  ' : 'FAIL'}  ${name}  (${Math.round((Date.now() - t0) / 1000)}s)  ${lines[lines.length - 1].slice(0, 120)}`);
			done(c);
		});
	});
	results.push([name, code]);
}
server.close();
const failed = results.filter(([, c]) => c !== 0);
console.log(`\n${results.length - failed.length} of ${results.length} harnesses passed`);
process.exit(failed.length ? 1 : 0);
