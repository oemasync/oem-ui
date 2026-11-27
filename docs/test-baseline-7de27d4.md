# Test baseline — commit 7de27d4

Established by worker W15 (redesign/w15-integration) on 2026-11-27.

## Environment

- Node: v22+ (engines >=22.12.0), npm ci clean (200 packages).
- Python: python3 with Playwright (WebKit) at /usr/local/lib/python3.13.
- Port for browser harnesses: 4415 (loopback server inside harness runner).
- Commit under test: `7de27d4` (Merge pull request #4).

## npm ci / build / test

- `npm ci`: PASS (added 200 packages; 6 known vulnerabilities, not addressed).
- `npm run build`: PASS (11 pages built in ~1.9s).
- `npm test` (`node tests/run.mjs`): **942 passed, 0 failed**.

## Browser harnesses (`npm run test:browser`, full manifest)

All 8 listed in `tests/browser-harnesses.txt` passed:

| harness | result |
|---|---|
| verify-init-idempotent | PASS |
| verify-forced-colors | PASS (196/196 checks) |
| verify-calendar | PASS (34/34) |
| verify-calendar-multiple | PASS (24/24) |
| verify-datepicker | PASS (17/17) |
| verify-chart | PASS (68/68) |
| verify-chart-inherited-dir | PASS |
| measure-builder-webkit | PASS (ALL BUILDER CHECKS PASSED) |

## Additional browser probe (not in manifest)

- `tests/measure-testing-page-webkit.py` (run against local dist at 4415): PASS at 390/402/768/1280 (all regions present and visible, no sideways scroll, dropzone renders).
- Against live `https://ui.mrx.sh/testing`: 1 failure — at 390x844 the state chips carry hue (`matched` rgb(74,222,128), `working` rgb(250,204,21)); local build does not reproduce (chips render greyscale). Attributed to the older deployed build, not to `src/pages/testing.astro` in this checkout.

## Test infrastructure changes

None required — no runner, wait, or URL breakage found at baseline. `scripts/run-browser-harnesses.mjs` and `tests/browser-harnesses.txt` left untouched.

## Added

- `scripts/fold-changelog.mjs` — folds `changelog.d/*.md` fragments into `CHANGELOG.md` under `[Unreleased]` (sorted by file name) and deletes the fragments; no dependencies.

## Failing checks

None. Baseline is fully green; any failure after merging worker branches is a regression.
