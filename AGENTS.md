# AGENTS.md

Guidance for AI coding agents working in this repository.

## What this is

A zero-dependency mono/terminal design system: 3 CSS layers, 1 JS runtime,
optional Astro components (everything in `src/astro/`), and a contract test
suite. There is no build step required to *use* it. `npm run build` only
builds the showcase.

## Orientation

```
src/styles/tokens.css       the contract — all values, both themes
src/styles/base.css         element defaults, a11y, prose rhythm
src/styles/components.css   all .cm-* components
src/js/cli-mono.js          runtime: one IIFE on `window.cliMono`. `init()`
                            binds every component that needs script
src/astro/                  optional Astro components + config.ts
src/pages/[...family].astro  the showcase — renders everything
tests/run.mjs               contract tests
```

## Rules that are easy to break by accident

1. **Tokens are the only place values live.** No hex, px, or timing literals
   in `components.css`. A hardcoded value is a rebrand bug.
2. **Load order is `tokens → base → components`.** Each layer must work with
   only the layers above it present.
3. **Astro tree-shakes side-effect-only frontmatter imports.** The runtime
   must be loaded with `<script src="../js/cli-mono.js"></script>`. A
   frontmatter `import` compiles fine and silently does nothing at runtime —
   this is the single most likely way to "verify" a broken integration.
4. **The FOUC guard must come before any stylesheet** in `<head>`, inline.
5. **`init()` must stay idempotent, and must let go.** It is called again
   on every `astro:page-load`. Guard each binder per element. A listener on
   `window`, `document` or a media query that is bound for one element goes
   through `cmWhileConnected(owner, …)`, never a bare `addEventListener`, so
   it ends when the element leaves the page. `npm test` fails by name on a
   bare scroll or resize listener, and
   `tests/verify-init-idempotent.py` counts the real thing in two engines.
6. **The title never truncates in a list row; the description does.** Do not
   "fix" this the other way.
7. **No component hardcodes site identity.** It comes from
   `src/astro/config.ts` or props. A test enforces this.
8. **Prefer the platform element over a runtime.** `<dialog>` for a modal,
   `[popover]` for a menu, `:hover` / `:focus-within` for a tooltip. A
   hand-rolled version gets focus trapping, light dismiss and live-region
   behaviour subtly wrong, and the bug is invisible in a static
   screenshot. The only new script here is the roving tabindex, because
   the platform ships no tab widget. If you add JS, it must be
   progressive-enhancement-only and guarded with `data-cm-*-bound`.

9. **A state is never a fill alone in forced colors.** Windows High
   Contrast repaints every background and drops every box-shadow. A new
   selected state, or a new mark whose paint is its whole meaning (a fill, a
   bar, a dot), goes in the `@media (forced-colors: active)` block at the end
   of `components.css`, in system colours only, and gets a case in
   `tests/verify-forced-colors.py`.
10. **`outline: <colour>` draws nothing.** It is the shorthand and resets the
    style to `none`. To recolour a ring, set `outline-color`.

## Verifying your change

```bash
npm run build   # must compile the showcase; the suite reads dist/
npm test        # must be green
```

CI runs those two and nothing else. The checks that need a browser are run
by hand, and a change to the runtime or to a state needs them:

```bash
OEM_UI_PY=/path/to/python-with-playwright npm run test:browser
npm run test:browser -- --no-build verify-calendar   # one harness, current dist/
```

That builds, serves this checkout's `dist/` on a free loopback port, and runs
every harness listed in `tests/browser-harnesses.txt` against it (WebKit,
headless). A harness goes on that list only once it reads `OEM_UI_URL`; one
that falls back to its own default URL measures some other build. The other
`tests/*.py` harnesses still run by hand against `npm run preview` with
`OEM_UI_URL` set.

`npm test` is a real contract suite, not a smoke test. It computes WCAG
contrast from the actual hex values, parses the actual CSS rules, and
executes the actual runtime against a fake DOM. If you break the theme
default, the row layout, or contrast, it fails.

For visual work, also load the showcase in a browser and check **both
themes** — a contrast or truncation bug is invisible in a passing build.

Parity with shadcn is pinned, not fetched — the suite is offline on
purpose. `npm run parity:live` is the other half: it re-fetches shadcn's
list and diffs it against the pin. A pin cannot announce that the other
side moved (shadcn added `code-block` and `trace` while the pin read 64),
so run it when you touch the ledger and occasionally when you do not.

## Verifying a change in a *consumer* project

Do not stop at "the library builds". Prove the integration:

- copy the four files into the consumer, or link the package
- confirm the FOUC guard is before the stylesheet
- confirm the runtime actually bound: `typeof window.cliMono === 'object'`
- toggle the theme and reload, and confirm it persists
- check one real page, not just the homepage

## Style

- Comments explain **why**, never what. A line that needs a comment to say
  what it does needs a rename instead.
- CSS property order follows the existing files; match the surrounding style
  (tabs, one declaration per line, lowercase hex).
- Public API changes need a README update and a `CHANGELOG.md` entry under
  `[Unreleased]`.

## Do not

- Add a dependency. If something needs a library, solve it in 30 lines or
  leave it to the consumer.
- Add a build step to the published artifact.
- Change the look of an existing component without a changelog entry.
- Lower a test threshold to make a failing check pass. Fix the token.
