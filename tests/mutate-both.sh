#!/usr/bin/env bash
# Wrapper: run both mutation cycles from the repo no matter what the
# shell's startup cwd is. The shell's baked-in cd points at the
# pre-migration /mnt/pve/mrx-thunder path, which no longer exists.
set -u
cd /reiki/projects/oem-ui || exit 90

{
  echo "=== GUIDE ==="
  node tests/mutate-guide.mjs
  echo "GUIDE_RC=$?"
  echo "=== TERM ==="
  node tests/mutate-term.mjs
  echo "TERM_RC=$?"
  echo "=== STATUS ==="
  git status --short
} > /root/.hermes/cache/scratch/mutate.log 2>&1

echo "mutate done rc=$?"
