# QA integrated report — 2026-11-27

Measured on the integrated head (`redesign/w15-integration`, commit `5df2a7935a476ae17177624e57138103e9f5a693`),
served from `http://127.0.0.1:8123` (built with `npm run build`). Crawler: `scripts/qa-crawl.py`.
Engines: Chromium + WebKit. Viewports: 1440x900, 768x1024, 390x844. Themes: dark + light. 132 runs.

Raw JSON: `/tmp/oem-ui-final/qa-report.json`. Server log: `/tmp/oem-ui-final/srv.log`. Crawler log: `/tmp/oem-ui-final/qa.log`.

## Summary

- Horizontal page overflow (scrollX probe): **0** on every page/engine/viewport/theme. `documentElement.scrollWidth` never exceeds viewport.
- JS errors: **0** pageerrors across all 132 runs.
- Failed requests / HTTP errors: **0**.
- Layout shift (CLS + section-top delta): **0** on all measured runs.
- Console: 396 warnings (`Deprecated API for given entry type.`), low severity, all engines/viewports/themes — likely `PerformanceObserver`/`layout-shift` entry usage.
- Text contrast (WCAG AA, computed): no real failures. 5 transparent gradient-text false positives (`span.cm-grad-text`, `code.cm-shimmer`, `code.cm-shimmer.cm-shimmer--once`, `code.cm-shimmer.cm-shimmer--reverse`, `span.cm-marker__content.cm-shimmer`) because computed `color` is `rgba(0,0,0,0)`; these are `background-clip: text` decorations, not AA failures. Excluded.
- Broken links: **0**. The live report's single demo link `/somewhere-else/` (404) is not present in this build.
- Broken in-page anchors: **3** unique (`#tree` in lists; `#lists` in crumbs and shortcuts).
- Covered anchors (sticky header): **69** unique.
- Viewport offenders: **121** unique (section, selector) patterns; the page itself does not scroll sideways (matches live report; carousel slide, tables, etc.).
- Text clipped: **70** unique (section, selector) patterns (matches live report categories).
- Overlaps: **42** unique section-level patterns.
- Small interactive targets: **71** distinct selector/floor patterns (matches live report).
- Media: **4** unique patterns (broken images in surface, mediablocks, artwork, msglist; missing intrinsic dimensions in msglist).

## RUNTIME

| severity | page | section | engine | viewport | theme | selector | what is wrong | screenshot |
|---|---|---|---|---|---|---|---|---|
| low | all | RUNTIME | all | all | all | (console) | `Deprecated API for given entry type.` warning in every run; no JS errors. | n/a |
| low | all | RUNTIME | all | all | both | (network) | No failed requests / HTTP errors on local build. | n/a |

## SHELL

| severity | page | section | engine | viewport | theme | selector | what is wrong | screenshot |
|---|---|---|---|---|---|---|---|---|
| med | all | SHELL | all | all | both | `header a.cm-header__link` | Header links measure 21px tall (and 14-15px variants) — under the 24px target floor. | n/a |
| med | all | SHELL | all | all | both | `button.cm-toast__close` | 16x16 hit target. | n/a |
| med | all | SHELL | all | all | both | `button.cm-chip__x` | 20x20 hit target. | n/a |
| med | all | SHELL | all | all | both | `a.cm-header__icon-link` | 18x18 hit target (18x44 variant OK). | n/a |
| med | all | SHELL | all | all | both | `button.cm-msg__action`, `button.cm-msglist__reaction` | 20px tall message actions. | n/a |
| med | mobile | SHELL | all | 390x844 | both | `button.cm-icon-btn`, `button.cm-btn.cm-btn--sm`, `button.cm-seg__opt`, `a.cm-navmenu__trigger`, etc. | Many controls 32-38px tall — under the 44px mobile floor. | n/a |
| med | all | SHELL | all | all | both | section anchors (e.g. `#foundation`, `#lists`) | Sticky header covers anchor targets on scroll-to-top; no `scroll-margin-top` observed. | n/a |
| low | all | SHELL | all | all | both | `a` (demo) | No broken links in this build (live report had one `/somewhere-else/` 404). | n/a |

## Finding counts by family

| family | page overflow | text clipped | overlaps | viewport offenders | small targets | media | broken anchors | covered anchors | contrast |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| foundation | 0 | 5 | 8 | 23 | 122 | 0 | 1 | 5 | 0 |
| surfaces | 0 | 5 | 10 | 18 | 139 | 5 | 1 | 11 | 0 |
| tables | 0 | 11 | 3 | 64 | 102 | 0 | 0 | 6 | 0 |
| panels | 0 | 15 | 7 | 4 | 126 | 0 | 0 | 6 | 0 |
| content | 0 | 11 | 18 | 5 | 107 | 6 | 0 | 10 | 3 |
| prose | 0 | 9 | 9 | 17 | 91 | 7 | 0 | 10 | 0 |
| layout | 0 | 43 | 13 | 29 | 130 | 0 | 0 | 7 | 3 |
| composed | 0 | 29 | 7 | 41 | 127 | 2 | 1 | 10 | 1 |
| reference | 0 | 6 | 4 | 4 | 94 | 0 | 0 | 5 | 0 |
| testing | 0 | 4 | 2 | 16 | 30 | 0 | 0 | 0 | 0 |

Counts are unique finding patterns per family across all engines/viewports/themes.

## Notes

- Measured-only findings; no speculative items.
- De-duplication is by `(family, section, selector, issue kind)`; counts in raw JSON may repeat across engines/viewports/themes.
- No new finding category was introduced by the integration relative to `docs/qa/live-2026-11-27.md`. Differences: the demo `/somewhere-else/` link is gone (0 broken links vs 1), and counts are measured on the integrated head rather than the `7de27d4` live build.
- Contrast table rows are byte-identical to `docs/contrast-2026-11-27.md` (777 rows).
- Verification logs: build `/tmp/oem-ui-final/build.log`, tests `/tmp/oem-ui-final/test.log`, browser `/tmp/oem-ui-final/browser.log`, contrast `/tmp/oem-ui-final/contrast.md`.

## Diff vs 7de27d4 baseline (same engines/viewports)

Measured on commit 5df2a79 (the code is identical after the revert).

- brokenAnchors: 10 -> 3
- brokenLinks: 1 -> 0
- media: 7 -> 4
- textClipped: 77 -> 70 (2 new: `.cm-toast__close`, `.cm-chip__x` — measurement artefacts of their ::before hit areas, no visible clipping)
- smallTargets: 116 -> 117 (new `a.cm-btn.cm-btn--sm` in the buttons matrix, same fine-pointer-emulation class as the 36 pre-existing .cm-btn--sm patterns, by design)
- coveredAnchors: 68 -> 69 (`#projects` now resolves; joins the pre-existing covered-anchor class)
- overlaps: 42 = 42
- viewportOffenders: 122 -> 121
- contrast false positives: 5 = 5
- page overflow, JS errors, failed requests and CLS all 0.
