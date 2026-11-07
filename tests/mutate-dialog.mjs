#!/usr/bin/env node
// Mutation harness for the <Dialog> Astro wrapper.
// Usage: node tests/mutate-dialog.mjs
import { readFileSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

const ROOT = process.cwd();
const DIALOG = 'src/astro/Dialog.astro';
const SHOWCASE = 'src/pages/[...family].astro';

const MUTANTS = [
  { name: 'M1 drops the native <dialog>', target: 'dialog',
    apply: (s) => s.replace(/<dialog\s+class/, '<div class'),
    expect: 'Dialog.astro does not render a native <dialog>' },
  { name: 'M2 drops the head element', target: 'dialog',
    apply: (s) => s.replace(/cm-dialog__head/, 'cm-dialog__head--gone'),
    expect: 'Dialog.astro is missing the head element' },
  { name: 'M3 drops the body element', target: 'dialog',
    apply: (s) => s.replace(/cm-dialog__body/, 'cm-dialog__body--gone'),
    expect: 'Dialog.astro is missing the body element' },
  { name: 'M4 drops the foot element', target: 'dialog',
    apply: (s) => s.replace(/cm-dialog__foot/, 'cm-dialog__foot--gone'),
    expect: 'Dialog.astro is missing the foot element' },
  { name: 'M5 drops the alert variant', target: 'dialog',
    apply: (s) => s.replace(/cm-dialog--\$\{variant\}/, 'cm-dialog--gone'),
    expect: 'Dialog.astro does not expose the alert variant' },
  { name: 'M6 drops aria-label', target: 'dialog',
    apply: (s) => s.replace(/aria-label=/, 'aria-labelx='),
    expect: 'Dialog.astro is missing the accessible name' },
  { name: 'M7 drops role="dialog"', target: 'dialog',
    apply: (s) => s.replace(/role="dialog"/, 'role="region"'),
    expect: 'Dialog.astro is missing role="dialog"' },
  { name: 'M8 stops rendering <Dialog> in the showcase', target: 'showcase',
    apply: (s) => s.replace(/<Dialog\b/g, '<div class="gone">'),
    expect: 'the showcase never renders <Dialog>' },
  { name: 'M9 stops importing <Dialog> in the showcase', target: 'showcase',
    apply: (s) => s.replace(/import Dialog from/, '// Dialog removed'),
    expect: 'is shipped but the showcase never imports it' },
];

function runContract() {
  try { execFileSync('node', ['tests/run.mjs'], { cwd: ROOT, encoding: 'utf8' }); return { ok: true }; }
  catch (e) { return { ok: false, out: (e.stdout || '') + (e.stderr || '') }; }
}

function main() {
  const snap = {
    dialog: readFileSync(ROOT + '/' + DIALOG, 'utf8'),
    showcase: readFileSync(ROOT + '/' + SHOWCASE, 'utf8'),
  };
  let killed = 0, survived = 0;
  for (const m of MUTANTS) {
    const target = m.target === 'dialog' ? DIALOG : SHOWCASE;
    const snapSrc = m.target === 'dialog' ? snap.dialog : snap.showcase;
    if (m.apply(snapSrc) === snapSrc) { console.log(`  SKIP ${m.name}: no-op`); continue; }
    writeFileSync(ROOT + '/' + target, m.apply(snapSrc), 'utf8');
    const r = runContract();
    if (r.ok) { console.log(`  SURVIVED ${m.name}`); survived++; }
    else if (r.out.includes(m.expect)) { console.log(`  killed  ${m.name}`); killed++; }
    else { console.log(`  killed  ${m.name} (msg: ${r.out.split('\n').find(l=>l.includes('FAIL'))})`); killed++; }
    writeFileSync(ROOT + '/' + target, snapSrc, 'utf8');
  }
  console.log(`\n${killed} killed, ${survived} survived of ${MUTANTS.length}`);
  if (survived) process.exit(1);
}
main();