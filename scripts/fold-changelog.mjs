#!/usr/bin/env node
// Fold changelog.d/*.md fragments into CHANGELOG.md under [Unreleased].
import { readdirSync, readFileSync, writeFileSync, unlinkSync, existsSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const CHANGELOG = join(ROOT, 'CHANGELOG.md');
const DIR = join(ROOT, 'changelog.d');

if (!existsSync(DIR)) process.exit(0);

const fragments = readdirSync(DIR)
  .filter((f) => f.endsWith('.md'))
  .sort();
if (!fragments.length) process.exit(0);

const body = fragments
  .map((f) => readFileSync(join(DIR, f), 'utf8').trim())
  .filter(Boolean)
  .join('\n\n');

let changelog = existsSync(CHANGELOG) ? readFileSync(CHANGELOG, 'utf8') : '';

const headingRe = /^##\s*\[?Unreleased\]?[^\n]*$/m;
const match = changelog.match(headingRe);
if (match && match.index !== undefined) {
  const insertAt = match.index + match[0].length;
  changelog =
    changelog.slice(0, insertAt) +
    '\n\n' +
    body +
    changelog.slice(insertAt);
} else {
  changelog = '## [Unreleased]\n\n' + body + '\n\n' + changelog;
}

writeFileSync(CHANGELOG, changelog);
for (const f of fragments) unlinkSync(join(DIR, f));
console.log(`folded ${fragments.length} fragment(s) into CHANGELOG.md`);
