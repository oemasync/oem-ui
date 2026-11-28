# QA integrated report — 2026-11-27

Measured on a **local build of commit `6e246eaa0a0d4af61cce195d26a6e9b348b91e82`** (worktree `redesign-w15-integration`),
served from `http://127.0.0.1:18765` (built with `npm run build`). Crawler: `scripts/qa-crawl.py`.
Engines: Chromium + WebKit. Viewports: 1440x900, 768x1024, 390x844. Themes: dark + light.

Raw JSON: `/tmp/oem-ui-final3/qa-report.json`. Log: `/tmp/oem-ui-final3/qa.log`.

## Summary

- Runs: **132** (2 engines × 3 viewports × 2 themes × 11 pages).
- Horizontal page overflow (scrollX probe): **0** on every page/engine/viewport/theme. `documentElement.scrollWidth` never exceeds viewport.
- JS errors: **0**. Console: 1 recurring deprecation warning (`Deprecated API for given entry type.`), all engines/viewports, both themes — 396 total lines, low severity.
- Failed requests / HTTP errors on local build: **0**.
- Layout shift (CLS + section-top delta): **0** on all measured runs (CLS max 0; shiftedSections 0).
- Text contrast (WCAG AA, computed): no real failures. Crawler flags transparent gradient text (`span.cm-grad-text`, `code.cm-shimmer`, `span.cm-marker__content.cm-shimmer`) because computed `color` is `rgba(0,0,0,0)`; these are `background-clip: text` decorations. 10 unique (page,section,selector) patterns, 60 total hits.
- Broken links: **0** (baseline had one `/somewhere-else/` 404 demo link; not present in this build's crawl).
- Broken in-page anchors: 4 unique (page,section,selector) patterns (baseline 21 unique), down sharply.
- Sticky header covers anchor targets: yes, across many sections (coveredAnchors: 69 unique patterns, baseline 68).
- Small interactive targets (<24px desktop, <44px mobile): 117 unique selectors (baseline 116); dominant `a.cm-header__link`, `input`, `button.cm-btn.cm-btn--sm`, etc.
- Media: broken images in 4 sections (artwork, mediablocks, msglist, surface); missing intrinsic dimensions in several. 4 unique media patterns (baseline 7).
- Viewport offenders: 121 unique (section,selector) patterns (baseline 122); 0 new patterns.
- Text clipped: 70 unique patterns (baseline 77); 2 new.
- Overlaps: 80 unique patterns (baseline 80); 0 new.

## RUNTIME

| severity | page | section | engine | viewport | theme | selector | what is wrong | screenshot |
|---|---|---|---|---|---|---|---|---|
| low | all | RUNTIME | all | all | all | (console) | `Deprecated API for given entry type.` warning in every run; no JS errors. | n/a |
| low | all | RUNTIME | all | all | both | (network) | No failed requests on local build. | n/a |

## SHELL

Dominant small-target selectors (counts across runs): `a.cm-header__link` 2776, `input` 1236, `button.cm-btn.cm-btn--sm` 848, `button.cm-icon-btn` 648, `button.cm-chip__x` 240, `a` 228, `button.cm-icon-btn.cm-icon-btn--bare` 224, `a.cm-tree__row` 160, `button.cm-toolbar__view` 160, `button.cm-number__btn` 160, `button.cm-toast__close` 120, `button.cm-seg__opt` 120, `a.cm-navmenu__trigger` 112, `summary.cm-disclosure__summary.cm-tree__row` 96, `a.cm-header__brand` 88. Sticky header covers anchor targets on scroll-to-top (no `scroll-margin-top`).

## Finding-category totals (all runs)

| category | total hits | runs with |
|---|---:|---:|
| viewportOffenders | 1256 | 92 |
| textClipped | 1392 | 132 |
| overlaps | 1241 | 132 |
| smallTargets | 8920 | 132 |
| media | 312 | 60 |
| brokenAnchors | 108 | 48 |
| coveredAnchors | 1288 | 40 |
| contrastIssues | 60 | 24 |

## Diff vs 7de27d4 baseline (same engines/viewports)

Baseline files: /tmp/oem-local-chromium.json, /tmp/oem-local-webkit-1440.json, /tmp/oem-local-webkit-768.json (commit 7de27d4). New report restricted to baseline (engine, viewport) combos: chromium×{1440,768,390}, webkit×{1440,768}. Pattern key = (section, selector) unless noted.

| category | old unique patterns | new unique patterns | new-only count |
|---|---:|---:|---:|
| viewportOffenders | 122 | 121 | 0 |
| textClipped | 77 | 70 | 2 |
| overlaps | 80 | 80 | 0 |
| smallTargets | 116 | 117 | 1 |
| media | 7 | 4 | 1 |
| brokenAnchors | 21 | 3 | 0 |
| coveredAnchors | 68 | 69 | 1 |
| contrastIssues | 5 | 5 | 0 |
| brokenLinks | 1 | 0 | 0 |
| shiftedSections | 0 | 0 | 0 |

### textClipped — NEW patterns (2)
- `(None, 'button.cm-chip__x')`
- `('surface', 'button.cm-toast__close')`

### smallTargets — NEW patterns (1)
- `('buttons', 'a.cm-btn.cm-btn--sm')`

### media — NEW patterns (1)
- `('artwork', 'img.cm-artwork__img', True, False)` — the broken flag is pre-existing (baseline flagged the same images broken with missingDims=True); only missingDims changed to false (W07 width/height fix).

### hover contrast
- probe: 275 -> 76 pairs below 3:1; the 76 are control fills against the row tint and the library's resting input borders (pre-existing base field styling). Probe: /tmp/oem-ui-final3/hover_contrast_probe.py.

### coveredAnchors — NEW patterns (1)
- `('cards', '#projects', '#projects')`

### Runtime (pageerrors / failedRequests / httpErrors / console)
- pageOverflow runs: old 0, new 0
- pageerrors: old 0, new 0
- failedRequests: old 0, new 0
- httpErrors: old 0, new 0
- CLS nonzero runs: old 0, new 0
- shiftedSections: old 0, new 0
