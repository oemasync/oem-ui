# Live audit: shadcn/ui vs oem-ui (measured, 2026-10-12)

All shadcn numbers below are MEASURED in a real browser at a 1265px
viewport on `ui.shadcn.com/docs/components` and
`.../docs/components/base/button`, not read off screenshots or guessed
from class names.

## 0. The verdict, checked live and exactly

> **Superseded by section 7 (2026-10-13):** shadcn added `code-block` and
> `trace`; the live list is now 66 and parity had to be rebuilt, not just
> re-counted. The numbers below were true on the date they were taken.

The "All Components" list on `ui.shadcn.com/docs/components` enumerates
**64** names. oem-ui's README ledger enumerates **64**. Compared
name-by-name and in order, on 2026-10-12:

- missing from oem-ui: **none**
- present in oem-ui but not listed by shadcn: **none**
- **order identical** across all 64

So the catalogue half of "full parity" is complete and verifiable. What
remains is not components - it is the *shape of the site* (section 3) and
the non-component areas (section 1).

## 1. What shadcn actually ships

Two sources disagree, which matters for parity claims:

| source | count | notes |
|---|---|---|
| `/docs/components` page, "All Components" list | 64 | includes Data Table, Date Picker, Typography |
| `/r/index.json` (the registry, authoritative for what installs) | 63 | includes `form` and `sonner`; NO data-table/date-picker/typography |

The docs list is the navigation; the registry is the code. Parity must be
stated against ONE of them and the other named as different. Data Table and
Date Picker are documented **compositions** of Table + Calendar + Popover
plus a data-table extension, not registry items; `form` and `sonner` are
registry items that the components index does not list.

Those two were checked rather than dismissed, because "we skip the two the
other list has" is exactly the kind of claim that hides a gap:

- **`form`** is listed in the registry with `"files": []` and no
  dependencies - it is documents-only. It describes wiring React Hook Form
  to the Field components. oem-ui has `Field` (label/help/error wiring) and
  has no React, so the item is not portable and there is nothing to port.
- **`sonner`** wraps the third-party `sonner` npm package (its dependencies
  are `sonner` and `next-themes`) with React theming. oem-ui's Toast is
  hand-rolled and zero-dependency by design, so adopting it would mean
  taking on a dependency to replace working code.

Both exclusions are therefore deliberate and recorded, not oversights.

Beyond components, the site has sections oem-ui has no equivalent of at all:

- **Blocks** - full page sections (dashboards, login pages, sidebars)
- **Charts** - a chart area separate from the Chart component
- **Typeset** - typography for rendered markdown
- **Directory** - community registries
- **Create** - project scaffolder
- **Docs shell** - Introduction / Installation / Theming / CLI / Skills /
  Registry / Changelog

## 2. shadcn's docs shell (measured)

```
header    position sticky, top 0, z-index 50, height 64px, bg = background
grid      "288px 961px" at a 1265px viewport - fixed rail + flexible column
sidebar   width 288px, position sticky, top calc(header + ~10px), z 30
content   max-width 640px, margin auto, padding 32px 0, gap 24px between blocks
TOC       width 288px, sticky, height 90svh, hidden below the xl breakpoint
```

Rhythm inside the content column (measured on the button page):

```
h1   30px / 600 weight, y=112
h2   18.75px / 600, margin-top 32.8px
pre  border 1px, radius 18px, margin 16px 0 48px   <- code/example block
```

Every screenshot of the shell shows the SAME white background on the
header, the sidebar and the content column: **shadcn paints the page once
and outlines regions with hairline borders.** Only the demo/preview
surfaces carry a fill, and it is one fill (the muted surface) reused
everywhere.

## 3. What oem-ui is today

- ONE page: `src/pages/[...family].astro`, 316 KB, 5740 lines, 55 `<section>`
  elements, **52 of them top-level and individually linked in the nav**.
- The entire suite is in the initial HTML payload. Every visitor downloads
  and parses all 52 sections plus one 248 KB runtime before reading
  anything. That is the "the whole thing loads" complaint, and it is
  measurable rather than a matter of taste.

  MEASURED against the preview server, first visit, cache cold:

  | asset | bytes |
  |---|---|
  | `index.html` | 436,843 |
  | `_astro/...script...js` | 90,133 |
  | `_astro/index.css` | 129,630 |
  | **total** | **656,606** |

  54 `<section>` elements are in that HTML. A reader who came for one
  component pays for all of them.
- Rhythm is per-section and hand-authored. `.cm-section` adds
  `background: var(--panel)` + `border: 1px solid var(--line)` +
  `padding: 1.1rem 1.2rem` to EVERYTHING, so a page that should have one
  surface has 52 competing ones. There is no single source for the
  section rhythm the way `--stack-*` is the single source for stacking.
- Spacing inside sections is a mix of literal rem values and `--space-N`.
  MEASURED: the layers ship **19 hand-written spacing literals across 15
  rules**, while `components.css`'s own header claims "no raw `rem`
  anywhere in the layers, not one":

  | line | rule | literal |
  |---|---|---|
  | 138 | `.cm-section--pad` | `padding: 1.1rem 1.2rem` |
  | 269 | `.cm-head-row .cm-head__title` | `margin: 0 0 0.6rem` |
  | 944 | `.cm-status` | `gap: 0.4rem 0.7rem` |
  | 945 | `.cm-status` | `padding: 0.8rem 1.1rem` |
  | 949 | `.cm-status` | `margin: 0 0 1.8rem` |
  | 1000 | `.cm-row` | `padding: 0.85rem 0.5rem` |
  | 1289 | `.cm-rows--stacked .cm-row` | `padding: 1rem 0.6rem` |
  | 1794 | `.cm-media` | `margin: 1rem 0 2rem` |
  | 1814 | `.cm-rule` | `margin: 2rem 0` |
  | 1832 | `.cm-term__bar` | `padding: 0.5rem 0.9rem` |
  | 1854 | `.cm-kv` | `gap: 0.55rem 1.2rem` |
  | 2565 | `.cm-footer__status` | `margin: 1.4rem auto 0` |
  | 2717 | `.cm-header__link` | `padding: 0 0.7rem` |
  | 2994 | `.cm-header__nav` | `padding: 0.55rem 0` |
  | 5500 | `.cm-select` | `padding: 0.55rem 0.7rem` |

  These are the "some have x spacing, others have y" complaint, stated
  exactly. Each is off the `--space-N` scale, so no two of these rules
  can be reasoned about together.
- Navigation is a single flat list of 52 ids with no grouping.

## 4. The three defects, stated as facts

1. **Uniformity**: 52 sections all carry the same card chrome, so nothing
   is emphasised and the page reads as a wall. shadcn outlines regions and
   fills only the demo surface.

   FIXED, measured (2026-10-12). `.cm-section` is `background: none;
   border: 0`; two neighbouring sections are divided by a
   `border-block-start: 1px solid var(--line)` scoped to `+ .cm-section`,
   so the first section draws no rule. The stack owns the space between a
   section's children via `gap: var(--stack-gap)`.

   MEASURED after, in WebKit, by tests/verify-section-rhythm.py:
   51 of 51 sections lay their in-flow direct children on ONE gap (20px),
   0 section children carry an inline margin any more (was 47), and the
   computed section background is `rgba(0, 0, 0, 0)`.
2. **Payload**: one page, everything in the initial HTML.

   NOTE: shadcn's component page for Button itself ships 942KB raw / 84KB gzip
   (102 chunks) — larger than our 437KB raw / 76KB gzip. The complaint is
   division, not bytes. `content-visibility: auto` on `.cm-section` was
   tested: it skips 49 of 51 sections but breaks in-page anchor jumps
   (lands 1342–3586px off in WebKit). REMOVED for now as it breaks the
   rail navigation; any lazy-loading must not break `href="#…"`.
3. **Navigation**: 52 flat links, no grouping, no on-this-page TOC.

   FIXED, measured (2026-10-12). The rail is divided into **9 labelled
   groups** as contiguous `SECTION_ORDER.slice()` ranges, so there is
   still ONE section index and the groups cannot drift from it. MEASURED
   on the built page in WebKit at 1280x577: 9 `cm-header__group-label`
   elements render, 52 links, all 52 carry `data-cm-spy`, and the rail
   list is a scroll container (2641px of rows in a 426px viewport) whose
   last link is reachable by scrolling it — the same arrangement shadcn
   uses for its 64-item component list.

   A boundary that overshoots would DROP sections off the rail while they
   still render in the page: present, anchorable, unreachable from the
   nav. The derivation asserts its own coverage at module scope, and the
   suite re-checks the property (the slices must sum to `SECTION_ORDER`).
   Mutation-proven: setting the first group's size 5 -> 3 reports
   "the rail groups sum to 50 rows against 52 sections, so 2 section(s)
   are unreachable from the nav".

   Still missing vs shadcn's IA (measured from its own sidebar, 8 groups):
   a **right-hand on-this-page TOC** (shadcn's content page carries one
   sticky TOC at ~288px alongside the ~640px content column), and the
   non-component areas — Blocks, Typeset, Directory, Create — which have
   no oem-ui equivalent at all.

## 5. Status against that plan (measured 2026-10-12)

Done:

- **one rhythm, one surface** — `.cm-section` carries no fill and no
  border; neighbours are divided by a hairline. 51 of 51 sections lay
  their children on a single 20px gap (was 32 of 51 mixed).
- **nav grouped** — 9 labelled groups, derived as contiguous slices of
  `SECTION_ORDER` so there is still one section index. 52 links, all 52
  with scroll-spy, rail scrollable (2641px of rows in a 426px viewport).
- **every spacing declaration is off the `--space-N` scale** — the 19
  raw rem literals across 15 rules are gone, plus one in the markup, and
  the suite now fails on any new one.
- **one document per family** — `src/pages/[...family].astro` emits `/`
  (all 52 specimens) and `/f/<family>/` (9 routes) from the same markup,
  wrapped in `shows(family)`. Gzipped: `/` 76.2 KB, `/f/foundation/`
  12.6 KB (-83%), `/f/content/` 11.8 KB. The 9 pages partition the 52
  sections exactly, 5/7/6/6/3/6/7/8/4. Doing it this way (rather than
  extracting 52 files) kept all 59 suite reads slicing one file, so no
  fixture had to move and nothing is duplicated between routes.

Not done, and known:
- **a right-hand on-this-page TOC** — **done** on the family routes. It
  renders at 288px (the `--doc-toc-w` token already existed), sticky, and
  lists only the sections of the document it is in; the whole-page build
  renders none. Verified in a browser by `tests/verify-doc-toc.py` (54
  checks), including that every row resolves and that the spy marks the
  row the reader is actually in.

  The first version of it was wrong in a way worth keeping: the CSS keyed
  the active state off `[aria-current]` while the runtime's spy toggles
  `is-active`. The highlight would simply never have appeared, and nothing
  would have failed — caught only by driving the page. shadcn's own
  sidebar uses `data-active`, which is where the wrong assumption came
  from.
- **the non-component areas**: Blocks, Typeset, Directory, Create.
  **Typeset is now done** — `docs/typeset` is not a component but a styling
  system (three controls, container-relative size, streaming stability, an
  opt-out), and `.cm-prose` had none of those four properties. `.cm-typeset`
  implements all four; see *Typeset* in the README and the seven contract
  checks in the suite (three mutation-proven). Blocks, Directory and Create
  remain out of scope and are named as such: Blocks are React app pages
  (`app/dashboard/page.tsx` wiring a sidebar, charts and a data table
  together), Directory is a registry browser, and Create is a project
  scaffolder — none of the three is CSS a framework-free library can ship.

A note on ordering, since it is the honest part: `content-visibility:
auto` was the cheap way to make one page behave like many, and it was
measured and rejected — it skips 49 of 51 sections but breaks in-page
anchors (jumps landed 1342–3586px past the target). Any future
lazy-loading has to preserve `href="#…"`.

## 6. Re-measured 2026-10-13, against shadcn's whole docs nav

The claim in section 0 is a claim about someone else's site, so it was
re-measured against the live pages rather than re-read from this file.
The suite's ledger check cannot re-fetch (it runs offline), so this is
the measurement that keeps the pinned list honest.

The full route list was extracted from shadcn's own sidebar — **105
distinct `/docs/*` routes** in 8 nav groups. The components are now
namespaced (`/docs/components/base/*`, plus `radix/` and `aria/`
variants of the same components), and the `base/` namespace enumerates
exactly the same **64** names, in the same order, as the pinned ledger:

- missing from the pinned list: **none**
- extra in the pinned list: **none**
- **order identical** (ignoring one duplicate `button` link in the page
  context, which is a nav artifact, not a second component)

Two areas the earlier gap list named were re-checked rather than
restated, and both came back **different from the earlier note**:

- **`/docs/create` is a 404.** The nav's "Create" points at
  `/create` — a project scaffolder app, not a docs page. There is no
  "Create" docs area to reach parity with. The earlier list named it as
  a gap; it is not a target.
- **`/docs/utils/*` exists and IS portable CSS**, and this library
  already ships both of them:

  | shadcn | oem-ui | variants |
  |---|---|---|
  | `shimmer` | `.cm-shimmer` | base, `--once`, `--reverse`, `--none`, plus `--shimmer-duration`/`-spread`/`-angle` |
  | `scroll-fade` | `.cm-scroll-fade` | base, `-y`, `-x`, `--t`, `--b`, `--l`, `--r`, `--s`, `--e`, `--none` |

  Both were built with the rest of the utilities work and carry
  `prefers-reduced-motion` kill-switches. They were missing from the
  earlier gap list, so the list under-reported what we had.

Still genuinely out of scope, and now measured rather than asserted:

- **Blocks** (`/blocks`, 2.29 MB): 36 `use client` markers, 12 React
  imports, `app/dashboard/page.tsx` plus a component tree
  (`app-sidebar.tsx`, `data-table.tsx`, `chart-area-interactive.tsx`,
  …). shadcn ships it with `npx shadcn add dashboard-01`. It is a React
  application, not CSS.
- **Directory** (`/docs/directory`): a browser for community registries
  built into the CLI. Tooling, not a visual surface.
- **The docs shell** (Introduction / Installation / Theming / CLI /
  Skills / Registry / Changelog, `components.json`, `package-imports`,
  `monorepo`, `javascript`, `figma`, `legacy`): prose about using a
  React CLI. `js`, `cli` and `registry` are not classes a framework-free
  stylesheet can implement — a reader of this library copies CSS or
  links a stylesheet, they do not run `npx shadcn add`.

So the portable half of parity is closed: 64 components in order, the
Typeset system, and both documented utilities. What is left on the
other site is a React app, a CLI, and documentation *about* that CLI.



## 7. Re-measured — parity had DRIFTED, and the pin could not see it (2026-10-13)

Section 6's "64 = 64" was true when measured and became false without
anything here changing. That is not a flaw in the pinned check — the pin
is a deliberate design so that an update is an act with a diff — it is the
known cost of that design: **a pin cannot announce that the other side
moved.**

Re-fetched from the live site (Safari UA; plain `curl` returns the bot
wall), parsed out of shadcn's own RSC payload (`$id` entries, ordered and
de-duped):

- the live `base/` namespace now enumerates **66** components, not 64
- the registry (`r/index.json`) now carries **65** items, not 63
- both new names have real docs pages (HTTP 200 with proper titles):
  - **`code-block`** — after `chart`, in shadcn's alphabetical order
  - **`trace`** — after `tooltip`, in shadcn's alphabetical order
- registry types: both `registry:ui`;
  `code-block` deps: `button` + `use-highlighted-code`;
  `trace` deps: `collapsible`

**Both were then BUILT, not just counted:**

- `.cm-codebar` gained the Code Block **body** — line numbers, start line,
  wrap, highlighted lines, floating action — via five new `CodeBlock`
  props. The gutter is markup, not a CSS counter, because typed `attr()`
  is unimplemented in WebKit; and the copy path strips it, because
  `innerText` reflects rendered text rather than selectable text.
- `.cm-trace` is a new component: a run's steps, state by fill and glyph
  (never hue), detail expanded by one delegated listener that moves
  `aria-expanded` and `hidden` together.

Evidence: suite **678/0**; `tests/verify-codeblock-trace.py` **20/20** in
WebKit (computed `white-space`, the actual clipboard payload, the
disclosure toggling both ways, a revealed panel with real height);
`tests/mutate-codeblock-trace.mjs` **7/7 killed, 0 survived**;
`verify-doc-toc` **54/54** at 55 sections.

The pinned list, the README prose ("the catalog is 66"), the section index
and the TOC harness expectations all moved together — 66 names, in
shadcn's order, checked name-by-name.

## 8. Re-measured 2026-10-16 — layout at every width, and three instruments that had stopped measuring

The catalogue re-checked against the live site at this commit: **66 pinned,
66 live on ui.shadcn.com, identical membership AND order** — no drift since
section 7. What follows is the rest of the design: the page shape.

A new instrument drives it — `tests/audit-demos.py` walks every demo control
in WebKit at 1280px and 390px (touch) and reports what escapes its box, what
a click cannot reach, and what sits under the touch floor. It opened at **40
triaged findings**; it now reports **0 failing findings** (30 informational
below-touch notes: small buttons that clear the AA floor for their named
size). The defects that survived triage were all one shape — a child naming
its measure in a way its container could not afford:

- **`.cm-row__desc` contributes nothing to its ancestors' intrinsic width
  now** (`contain: inline-size`), with `contain: none` opt-outs in the two
  variants that SIZE from it (`--column` measured 0px, `--inline` 67px
  against 169px with containment on). Twelve items in `#proselists-order`
  forced 297/351px bodies inside a 270px row: **87px of sideways scroll**.
- **Thirteen captions were `<p class="cm-row__meta">`** — a value slot's
  `nowrap` + `overflow: hidden` on a sentence; every one lost its tail, the
  worst **513px on a phone**. They are `.cm-caption` now, and their stray
  inline margins went with them.
- **`.cm-shell--rail > *` caps at `min(var(--maxw), 100%)`**: auto margins
  size a flex child to fit-content BEFORE the cap, so the 860px prose body
  overflowed a 440px box at 1000px (right=1112) across **1000-1111**.
- **The sidebar rail sits flush** (`inset-inline-end: 0`; the panel measured
  sw=261 in a cw=255 box), the attach `--sm/--xs` width re-freeze is gone (a
  20px box for 21.6px of ink), and below 680px the inline title wraps — its
  nowrap floor (339px: pad, a 42px index, the 250px label) escaped viewports
  under 379px.

Sweeps, not samples: **300-1200px at 10px steps plus 1024/1280/1440, and
three iPhone device passes (SE 320, Pro 393, Pro Max 430) — 0 escaping
elements at every width**; 0 sideways scroll at 390/375/320/1440.

Three instruments had stopped measuring, and were repaired rather than
trusted: a harness with a hardcoded URL was reading a DIFFERENT checkout's
build; a `42ch` expectation typed as 404.578125px was really tracking the
box's fonts (it resolves 403.265625px after a host font change — measured
identically on both checkouts, and the specimen matched the page's own 42ch
to the digit); and a `:scope >` selector counted zero rail links after the
rail was divided into labelled groups (56 links, every one at x=8, so the
harness reported a rail that "wrapped" and an index that "lost one"). The
mutation machinery had the same rot at scale: **49 harnesses read the page
path the rename retired** and had stopped proving anything before mutating.
45 are repointed; `mutate-inline-rows.mjs` is re-proved end to end —
**17/17 caught, 0 NO-OP, restore byte-identical (sha256)** — and the rest are
swept serially, since each mutates shared source.

**The mutation fleet now has a census, and the census now has teeth.**
`tests/preflight-mutations.py` reads every Python harness's pattern table in
a sandboxed subprocess and reports what no longer matches; it speaks in
shapes - `NO-OP` (absent), `AMBIGUOUS` (several sites when the sweep asserts
one), `TOO-NARROW` (a `count='all'` sweep down to one site). Eight
ambiguous patterns were re-anchored to the site each mutant names, and one
too-narrow avatar sweep restored to the six it was written for. The fleet
reads **100 harnesses, 0 stale patterns, exit 0**. Every anchor the census
cannot read (`.mjs`, `.sh`) pre-checks its own patterns when it runs, and
the sweeps are serialized in a queue that stops on dirt.

Evidence: `npm run parity:live` 66/66 identical; audit **0 failing
findings**; suite **687/0** (four new pins, each mutation-proven);
`verify-no-sideways-scroll.py` 0 sideways at 390/375/320/1440;
`verify-showcase-nowrap-webkit.py` clean at 375/402/430/1440;
`verify-sidebar.py` 34/34; `verify-attach-quiz.py` 14/14;
`verify-doc-toc.py` 81/81; `verify-section-rhythm.py` 6/6.

## 9. The sweep that measured the other checkout (2026-10-16)

The attach-quiz sweep came back `killed=13 survived=9`, and the nine were not
a weak-harness story: they were the mutants only a *browser* can see. Sixty
harnesses in this worktree defaulted to `:4321` - the framework's default
port - and `/proc/<pid>/cwd` on the server answering there read
`/root/projects/oem-ui`, the sibling checkout. Every browser verdict in
every sweep was a measurement of another tree's dist. The local suite still
caught what it could, which is why the number looked plausible.

So the proof surface was repaired before the proofs were trusted again:

- **One tree per URL.** Every `:4321` in `tests/` and `scripts/` now reads
  `:4471`, the port this lane's preview serves (`CLI_MONO_URL`, `BASE_URL`,
  `OEM_UI_URL`, `GUILDRAIL_URL` still override). 64 files, 33 further URLs.
- **A boot wait that cannot fire on a healthy run.** This page needs 27s+ to
  reach `window.cliMono` when a spec campaign shares the box; the 30s default
  made slow loads look like detections. 67 harnesses now set 180s right after
  opening their page, so a timeout can never be booked as a catch.
- **Two more census verdicts.** `AMBIGUOUS`: a pattern matching several sites
  where the sweep replaces the first and asserts exactly one - measured when
  the sidebar sweep aborted a whole batch on an unindented pattern that had
  quietly grown a second occurrence. `TOO-NARROW`: a `count='all'` sweep
  narrowed to one site, measured when an over-anchored avatar sweep stopped
  sweeping six. Eight ambiguities re-anchored; the census reads
  **100 harnesses, 0 stale, exit 0**.
- **Every affected sweep re-earned.** A kill measured against another
  checkout's build was never a kill: the sweeps that decided on a browser
  verdict are re-queued in a strict pid chain and re-run serially against
  this tree. `verify-drawer-field.py` 21/21 killed, 0 survived is the first
  clean post-fix full catch.

## 10. The re-proof campaign, and the machinery that carries it (2026-10-16)

42 sweeps — every browser-driving mutation sweep in `tests/` — re-earn
their verdicts serially against this tree. Verified by enumeration, not
memory: a python pass over `tests/mutate-*.py` (HARNESS_CMD referencing a
verify harness) plus the three `.mjs`/`.sh` sweeps that spawn a browser
found none outside the 42.

The carriers, and why each exists:

- **A strict pid chain.** Each queue's waiter holds a pid, the next waits
  on it, and `setsid` detaches the chain from any shell that might reap
  it. Nothing starts on a dirty `src/` — that guard refused three queues
  in a row tonight when a killed sweep stranded its mutant, and was right
  to: the restore, not the launch, was the missing piece.
- **A timeout-kill watcher.** `timeout` sends SIGTERM, which skips a
  sweep's finally-restore, so the mutant stays and the next dirt guard
  aborts. The watcher restores when the shape is "pipeline alive, no
  sweep running, tree dirty, on two consecutive checks" — and its sweep
  detection reads `/proc` for every runner type, because the version that
  matched only `python tests/...` restored a live `node` sweep's mutant
  out from under it and voided that run.
- **A quiet-window battery.** Census, `npm test`, `parity:live` and the
  demos audit, chained off the last waiter: the end-to-end proof runs on
  the drained tree, never between mutants.
- **Verdict digest, then per-sweep triage.** `q10-digest.sh` collapses 42
  verdicts to one page; a survivor is traced statically against the
  harness's own checks before any check is written — the attach-quiz
  "nine survivors" traced to the wrong tree and to checks that already
  name those exact behaviours, not to gaps.

The machinery lives in the campaign scratch dir, not the repo: it is how
this re-proof was driven, not how the suite is delivered.

Expect-name drift, audited statically across every remaining sweep: the
class is closed. Only rail, burger and sidebar key expectations against
oracle output, and all three were re-anchored. The other "the ..." strings
living in sweep tables were each traced to their consuming unpack and are
non-matchers: `why` notes (tree-resize, calendar), `name` descriptions
(otp-palette), and `_claim` prose (msglist). Alert, chart and direction
predict which oracle kills a pattern and measure it by running both, so a
wrong guess is recorded, not broken.
