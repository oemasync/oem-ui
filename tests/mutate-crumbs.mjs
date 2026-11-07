#!/usr/bin/env node
import { readFileSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

const WRAP = 'src/astro/Crumbs.astro';

const mutants = [
  { name: 'drop the separator class entirely',
    from: '<span class="cm-crumbs__sep" aria-hidden="true">\n\t\t\t\t\t\t›\n\t\t\t\t\t</span>',
    to: '<span aria-hidden="true">\n\t\t\t\t\t\t›\n\t\t\t\t\t</span>' },
  { name: 'drop the current-page marker',
    from: '<span class="cm-crumbs__here" aria-current="page">',
    to: '<span class="cm-crumbs__here">' },
  { name: 'hand-roll the wrapper instead of using cm-crumbs',
    from: '<nav class="cm-crumbs" aria-label={ariaLabel}>',
    to: '<nav class="crumbs" aria-label={ariaLabel}>' },
];

function runSuite() {
  // A failing suite exits non-zero; catch and treat the thrown error as
  // the mutant being KILLED. A green run (796 passed, 0 failed) is the
  // only thing that counts as MISSED.
  try {
    return execFileSync('node', ['tests/run.mjs'], { cwd: process.cwd(), encoding: 'utf8' });
  } catch (e) {
    return e.stdout || e.message || '';
  }
}

let failures = 0;
let ran = 0;
const original = readFileSync(WRAP, 'utf8');

for (const m of mutants) {
  if (!original.includes(m.from)) {
    console.log(`SKIP (pattern absent): ${m.name}`);
    continue;
  }
  ran++;
  const snapshot = readFileSync(WRAP, 'utf8');
  writeFileSync(WRAP, original.replace(m.from, m.to));
  let result;
  try {
    result = runSuite();
  } finally {
    writeFileSync(WRAP, snapshot);
  }
  const ok = /796 passed, 0 failed/.test(result);
  if (ok) {
    failures++;
    console.log(`MISSED: ${m.name} — the suite stayed green`);
  } else {
    console.log(`KILLED: ${m.name}`);
  }
}

console.log(`\n${failures} mutant(s) missed, ${ran} run`);
process.exit(failures ? 1 : 0);
