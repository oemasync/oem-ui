# W12 runtime changelog

- `src/js/cli-mono.js`: `init()` now defaults a missing root to `document`, so a bare `cliMono.init()` call (documented public API) no longer throws on `root.querySelectorAll`.
- `src/js/cli-mono.js`: `cmInitNavmenu`, `cmClampHovercards`, `cmInitCal`, `cmInitResize`, `cmInitScroller`, `cmInitQuiz`, `cmInitForms` now tolerate a null/undefined root the same way the already-guarded binders do.
- `src/js/cli-mono.js`: `cmApplySort` now skips `[data-cm-empty]` rows (and keeps them at the end of the body) instead of sorting/moving them, which crashed `r.cells[idx]` access on the colspan empty-state row.
- `tests/verify-table-sort.py`: filter `[data-cm-empty]` rows in the load/click assertions so the empty-state row is never read as a data row.
- `src/js/cli-mono.js`: removed the now-redundant `(root || document)` leftover in `init()` after `root = root || document;`.
- `tests/run.mjs`: added contract checks proving `cliMono.init()` with no argument does not throw, and that sorting a table with a `[data-cm-empty]` row never reads that row's cells, keeps it in the body, and sorts data rows.
- `tests/verify-table-sort.py`: scope assertions to the non-paginated sort table so per-tbody/per-table sorting is checked without cross-table flattening.
- Bug list: see final report. No out-of-scope fixes applied.
