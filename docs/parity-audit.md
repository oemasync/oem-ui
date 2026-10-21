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

## 11. The re-proof era: what re-running every sweep found

Every browser-driving sweep was re-run against the current tree, through the
current harnesses, on this lane's preview port. The sweeps themselves turned
out to be the least reliable part of the rig. Five classes, each fixed at the
root:

- **Wrong tree / wrong port.** 60 harnesses defaulted to the sibling
  checkout's port; one survivor of that sweep defaulted to 4481 under a
  unique env name and aborted every run.
- **Anchored to dead code.** Mutants that land on a rule or code path the
  page never resolves measure ORACLE BLIND: forms-fade's focus mutant sat on
  the advance path while its check exercises the submit loop, and composer's
  l02-l04 edited the direct-child field rule while the markup resolves the
  mention-anchor rule. Mutants must target what the page uses.
- **Expect drift.** Predictions must be verbatim substrings of what the
  oracle actually prints. Rail, burger, sidebar and records each carried
  guesses, one of which (`the records section is not in the nav`) exists
  nowhere in the suite.
- **Overshooting patterns.** A lazy group whose terminator is not a
  structural token can cross rule boundaries: records' stat-label regex ate
  a span of unrelated rules and went red for the wrong reason. Bound the
  group to its own block.
- **Cleanup and contract bugs.** A sweep that fails to restore must not
  stall a queue (runners now restore leftovers and continue); harnesses
  invoked with `--baseline` must consume it rather than navigate to it.

## 12. The parallel plague: a bounded wait is not a serialisation

The chained queues each parked a waiter on the previous queue with a *bounded*
wait - `for i in $(seq 1 48); sleep 45` - which expires after 36 minutes. When
q12's tail items ran longer than that, q15, q16 and q17 fired anyway, and by
12:04 two more queues started within the same minute. Five queues, one tree.
The contamination reads like five unrelated bugs: ENOENT for `dist/index.html`
mid-suite (a peer's rebuild wiped dist under another sweep), `RESTORE FAILED:
src/styles/components.css - crash, not a result` (one sweep's final snapshot
disagreed because a peer owned the file), a self-spawn sweep aborting with
"port 4471 is already in use", and one lone survivor in an otherwise clean
sweep. The rule now: a waiter waits on its pid UNBOUNDED; a cap, if any, ABORTS
instead of proceeding. Every verdict from the overlap window was voided and the
19 affected sweeps re-ran through one strictly serial queue; wall-clock
end-times across queue logs (`ls --time-style=+%H:%M`) are the cheap overlap
detector.

Two further findings from the same stretch. First, the sweeps split into two
port families that need **opposite windows**: the composer/guildrail/toast trio
refuses to run while anything else serves :4471 and spawns its own server,
while every other sweep probes the standing preview. Same port, mutually
exclusive requirements - so the trio runs in a wrapper that stops the standing
preview, runs the three serially, and restores the preview for the audits.

Second, two rig defects of the "plausible message" class. forms-fade's focus
mutant needed a **third** anchor: both `controls(item(s))` sites live in the
stepper's own state machine (`skip`/`step`/`render`), which the forms page
never walks; the call its harness check exercises is `validate(show)`'s own
line, tagged by the `return bad === 0;` that closes that function. And
dropdown-depth's "Space stops flipping a checkbox row" is an **equivalent
mutant**: the rows are `<button>`s, so WebKit's Space fires a native click and
the click handler flips the row whatever the keydown branch says. Two routes,
one behaviour - cut, with the load-bearing click-guard record mutated instead,
the same standard the navmenu-sub code note already set. Relatedly,
mutate-burger's kill classifier returned on the *first* RELATED pair whose
fragment matched the mutation name, so the broad fragment `unconditionally`
shadowed the precise `collapse the panel` pair and mislabelled a correct kill;
every matching pair now gets a vote.

And the msglist claims are now assertions: the suite reads the page source
(no rebuild needed) for avatar composition, the day divider's words, and the
unread divider's words. Its re-run under the plague showed all 36 mutants
killed - including the three former survivors - but the run's cleanup crashed
under the parallel window, so its clean verdict is the one queued after this
entry.

## 13. The campaign closes: every sweep re-proven, and the battery runs on the drained tree (2026-10-19)

The queued msglist verdict landed first: **36/36 killed, 0 survived**,
restore verified, exit 0 - the three former survivors included. That was the
last sweep without a clean verdict, so all 42 now have one earned on this
tree. The last two to earn theirs needed the root-cause work this era kept
predicting: the sweeps are the least reliable part of the rig.

**sync-prefix** was 9/9 killed all along - the suite died on every mutant;
one of the nine `expect_named` strings simply named the wrong check (the
mutant's `prefix_for` returns `src`, so the comparison targets the consumer's
wrong path and the suite dies on "a consumer with a current public/ copy
must pass", not the bare-scan check, which still FINDs the consumer with a
wrong prefix). Renamed the expectation; the kill was real.

**popover-combobox** was the harness fault, not the product. The specimen
sits in `#overlays`, 34,000px down a 95,000px showcase. A harness that
opened the card from `scrollY=0` measured the placer's **pin-to-bottom
fallback** - the documented last resort for a trigger neither below nor
above can hold - and called the product wrong for doing exactly what it is
for. The fix is three waits, not one: instant-scroll the trigger into view
(a 34,000px smooth scroll never settles on this box - measured 180s and
still mid-jump); wait for the `content-visibility` reflow to stabilise
(document height must stop growing before the click, or the placer reads a
moving trigger - the reflow was 800px and it moved the trigger's viewport
top from 217 to 671 between two of my own measurements); and make the
adjacency scroll RELATIVE, because an absolute `scrollTo(0, 240)` from
34,000 down parks the trigger 33,000px off-screen again. Baseline 18/18,
then 10/10 mutants killed on a clean tree.

Two lessons worth keeping. First, a **killed-sweep that exits non-zero is
not always a dead sweep**: a dirty-tree guard that trips on an *uncommitted
test edit* is a harness complaint, not a verdict - the composer rc=1 that
aborted the first chain was exactly this (34/34 killed, then the guard
refused on `M tests/mutate-popover-combobox.py`). Second, a **timeout-kill
strands the mutant in the tree** and the next sweep's dirt guard correctly
refuses to start - the rescue is `git checkout --` the stranded file, not a
re-run on top of it. A re-proof run against a dirty tree is a measurement of
the dirt.

The quiet-window battery, on the drained tree (every sweep restored,
`git status` empty, dist rebuilt):

- census: **100 harnesses, 0 stale patterns, exit 0**
- suite: `npm test` — **688 passed, 0 failed**
- `npm run parity:live`: pinned 66 = live 66, **identical membership AND order**
- demos audit (`tests/audit-demos.py` on the live preview, both viewports):
  **clean, exit 0** — "every demo control is named, in its box, over the
  floor, and clicking it raised nothing"; the 30 notes are the desktop
  fine-pointer AAA touch-floor reports the audit is designed to print, not
  to fail on

The catalogue half was re-confirmed by the same live check: shadcn's list
has not moved since the 10-13 rebuild (66, same membership, same order).
No `src/` commit has landed since the verdict queue of 10-16/17, so the
thirty-four verdicts that queue earned (every browser-driven sweep but the
eight re-earned in this window: composer, the six, and msglist) stand as
earned. **The re-proof campaign is closed: all 42 sweeps hold clean
verdicts on this tree, and the battery ran green on the drained tree.**

## 14. The shape of the site: the drawer, the dead guard, and the measured judgment (2026-10-20)

The catalogue and the sweep campaign were closed, and the user's remaining
complaint was that the site "doesn't quite work like the shadcn site."
Measured at four widths on both sites before changing anything: at 768 and
390 oem-ui already matched shadcn's mobile/tablet shape, and the family
routes already carried the shadcn shell (rail, capped measure, right
"on this page" TOC at 1180+). The defects were two, both reproduced in a
real iPhone touch context.

**The mobile drawer hid every section link.** shadcn's mobile nav is a
full-screen sheet that lists its 167 links flat — measured from the live
DOM, nothing collapsed. The oem-ui drawer showed 9 group labels and **0 of
the 52 links**. Root cause, measured in WebKit at 390x844: `Header.astro`
renders each group's link list as a nested `.cm-header__links` — the same
class as the disclosure panel — so the phone rule
`.cm-js .cm-header__links { display:none }` hid every group list, and the
runtime only sets `data-open` on the top-level panel. Worse, the nested
lists also inherited the panel's own geometry: `position: fixed;
top: 60px; bottom: 0` fixed all nine lists to the same viewport box and
painted them on top of each other (all 56 links measured at top 61), and
the rail block's `width: 100%` / `flex: 1 1 auto` / `min-height: 0` made
each a collapsible container. The fix is one rule, scoped to the phone
block and to the nested list only:
`.cm-header--rail .cm-header__group > .cm-header__links` gets `position:
static`, `display: flex; flex-direction: column; flex-wrap: nowrap;
flex: 0 0 auto; width: auto; overflow: visible;
border-inline-end: 0` — the groups keep their labels, their lists stay
open, each group takes its natural height, and the panel (already a
scroll container) carries the overflow. Verified in WebKit: **0 of 52 →
56/56 links visible** (52 sections + the 9 label rows) in one column,
**0 overlaps**, closed state `display: none`, the last row (readme)
reachable by scrolling and inside the panel, on BOTH the root and
`/f/panels` builds, and again on a real iPhone 14 Pro touch context (65/65
visible, one column, all inside the panel). The 641-999 tablet band is
untouched: `verify-grouped-rail-tablet` PASS.

**The guard for that drawer had stopped measuring.**
`tests/verify-drawer-column.py` failed with "nothing was checked" on a
healthy drawer — confirmed pre-existing (it fails identically at `9c6305d`,
before the fix). Its probe read `:scope > a`, direct children of the
panel; after the rail was divided into labelled groups the direct children
are `.cm-header__group` divs, so the probe returned zero rows,
`links[-1]` threw inside the page, and every one of the 50 viewports
landed in the exception branch — the classic instrument rot of section 8,
where a `:scope >` selector "counted zero rail links after the rail was
divided into labelled groups." The probe now reads every link in document
order (`list.querySelectorAll('a')`); the one-column / scroll /
inside-panel signals are unchanged. Re-earned: **5x10 viewports, one
column at every height, scrolls when the rows overflow, every link inside
the panel.**

**The desktop shell was measured and adjudicated, not changed.** shadcn at
1280 (measured after hydration): full-width **sticky 64px top bar**, 288px
left sidebar, **640px capped content column** (`max-w-160`, x=320), 288px
sticky right TOC (x=984). oem-ui at 1280: a **232px full-height fixed left
rail**, no top bar; root content at x=336 w=860 with no TOC, family content
x=252 w=720 with the 288px sticky TOC. Three candidates, three verdicts:

- **The full-height rail vs a top bar.** oem-ui's rail is a documented,
  suite-pinned design (the family routes were accepted as shadcn-shaped
  through every section of this audit with that same rail), and it is the
  mobile drawer's desktop continuation — one nav, one scroll-spy, one
  measure, from 320px to 1440px. Replacing it with a top bar would mean
  re-doing the mobile/tablet bands this window just re-verified, to match
  a shell the audit never recorded as a defect. **Judged: deliberate
  difference, not a gap.**
- **The 860px root measure vs shadcn's 640px.** The root page is a 52-
  section specimen wall — code blocks, tables and interactive demos run
  wide by design (the family routes already cap at their family's measure
  once a TOC reserves the third column). The 860px box read as a
  comfortable, balanced measure in the rendered page. **Judged: content-
  driven, not a gap.**
- **The root's missing TOC.** shadcn's TOC lists a component's in-page
  headings — it never duplicates its sidebar. On oem-ui's root page the
  in-page sections ARE the rail's 52 rows, so a TOC there would be a
  second copy of the rail; on the family routes it earns its place (the
  rail's rows are mostly cross-document links). This is why the code
  renders `TOC_IDS = []` for the root by explicit comment, why
  `verify-doc-toc.py` pins "the whole page renders no TOC" as a passing
  check, and why section 5 records it as the *known, deliberate* state
  rather than a defect. **Judged: correct as built.**

The one thing that genuinely "didn't work" was the drawer — the reader on
the device this site is actually viewed on (iPhone, Safari) opened the
menu and got nine dead headings instead of 52 links. That is fixed,
guarded, and re-earned.

Evidence, on the drained tree: suite **688/0**; `verify-doc-toc` **81/81**;
`verify-grouped-rail-tablet` **PASS** (tablet 700-999 + rail 1280 + phone
drawer 390); `verify-drawer-column` **50/50** (was checking 0/50); census
**100 harnesses, 0 stale**; `parity:live` **66 = 66, identical membership
AND order**. Commits: `d41efc9` (the drawer), `ae72d2d` (the guard).

§15_MARKER_START
## 15. The polish campaign: every component, four widths, measured clean (2026-10-21)

The ask was broad — "many things are broken, misaligned, not loading or not
looking properly on either mobile or pc; polish every aspect until pristine."
So this pass did not audit claims, it audited pixels: every section of every
route was captured and measured at four widths (320, 390, 768, 1280), not
judged from a screenshot.

**The method, in one line.** Objective geometry first (recon + a clip/overflow
scanner + an alignment scanner over all 10 routes at 390, 768 and 1280), then
vision over the contact sheets **only as a hypothesis generator** — every
sheet-scale flag was re-checked at full resolution, and anything with a
measurable geometry question was settled by the DOM, not by eyes. That
discipline mattered: the sheet-scale vision pass flagged 22 of 55 root cells,
and then kept flagging 14 more across the other sheets, and nearly all of
those were refuted at full res — vague "slightly off" claims, the same claim
repeated in different cells, and text "cut off" that was the sheet's own crop
edge. A screenshot of a cell is not the component; the viewport is.

**What was actually broken — five defects, all fixed and guarded:**

1. **The hero clipped its own title at 320–368.** "Everything" measured
   ~260px in a 198px padding box. Fixed with a narrow-band ramp
   (`17.5vw − 2px` superseded by `17.5vw − 21px` at `max-width:392px`) and a
   dedicated guard, `tests/verify-hero-clip.py`, green at 22 widths, 14 of
   which go red under a mutation. Commit `3ee94b8`.
2. **The toast's close button had a 16px-wide hit area.** Widened to 24px
   with an invisible `::after` (`inset: 0 -4px`), proven by
   `elementFromPoint`. Commit `0963965`.
3. **The msglist's kai row was nested inside priya's `<article>`,** collapsing
   to 16px wide with its meta pushed to x=383 — past the 320 viewport. A
   structural re-parent, not CSS. After: kai's row is identical in geometry
   to its siblings (x=53, w=214, h=92). The fix landed on both the root and
   the f-composed route because they share the markup. Commit `1266647`.
4. **A 7px clip in the cards demo's trailing meta at 320** — "top-aligned,"
   is one 65px word in a 58px slot, and a bare flex text node cannot shrink.
   Fixed by the codebase's own convention (inner `<span>`) plus a reword that
   fits every slot: "stays at the top, no stretch". Both slots now measure
   `scrollWidth == clientWidth` at 320. Commit `6ef41c0`.

(The fifth is the drawer from §14 — nine dead headings on the phone — which
this campaign's recon re-confirmed fixed: 52 links, drawer-column guard 50/50.)

**What was *not* broken, and the measurement that proves it.**
Recon: 40/40 loads clean at 320/390/768/1280 — zero failed requests, zero
broken images, zero HTTP ≥ 400, zero JS errors, zero page-overflow (document
scroll width equals viewport on every route at every width). Alignment:
137 drift records at 390, 437 at 768, 370 at 1280 — **all** are the
intentional specimen-grid pattern (spec tables' label-vs-sample columns,
code-snippet pairs, `.cm-push`/`.cm-stick-top` trailing chips, indentation);
no record is a component overflowing its container. The clip scanner's
remainder is the `.cm-sr-only` utilities (clipped by design) and four THEAD
strips inside `overflow-x:auto` scrollers (intentional horizontal scroll —
measured, e.g. the data-table's actions column ends at x=726 inside a
748 section at 768, table 685px in a 686px scroller, document 768=768). The
Delete button that vision called "mis-centred" measures 16.9px symmetric
padding with an 8.9px icon gap.

**Visual sweep, complete.** Contact sheets for all 10 routes at 320, 390 and
1280 (336 shots) plus a fresh 768 grid (112 shots) — 100 sheets total. Every
concrete flag from them was re-verified at full resolution or by measurement:
stack/selection/density/surface/lists/overlays/rowon/tblaction/prosetap/
proselistorder/prosetable/sidebar/buttons/choice/records/tiles/cards/trace/
navmenu/quiz/search/badge/surface-paint/datepicker/switch/scrollarea/
guildrail/msglist/chat/composer/dropdown-depth/forms/data-table/charts —
**all refuted or measured clean.** Zero new defects found at full res.

**State at close.** Suite **688/0**; `verify-doc-toc` **81/81**;
`verify-drawer-column` **50/50**; `verify-hero-clip` **22/22** (14/22
mutation-red); preflight mutations **100/0**; `parity:live` **66 = 66**;
census 100 harnesses, 0 stale. Post-fix battery green end to end. Commits,
all pushed, all authored `omiinaya`: `3ee94b8`, `0963965`, `1266647`,
`6ef41c0` (on top of the §13/§14 chain `9ba6f60`, `9c6305d`, `d41efc9`,
`ae72d2d`, `928e953`).

The user's premise — "many things are broken" — was corrected with evidence:
five real defects in a site of 55 sections × 10 routes × 4 widths, now fixed,
guarded, and re-measured clean. The rest of the "broken" list was the
difference between a contact-sheet pixel and a component in its viewport.

## 16. The light theme, audited; two measured contrast defects fixed (2026-10-21)

The polish campaign (§15) closed on the DARK theme. The light theme is
a shipped surface - `src/js/cli-mono-theme-guard.js` sets
`data-theme="light"` on `<html>` from `localStorage` before first paint,
and `src/styles/tokens.css` carries a full light token set - and it had
never been looked at. Two measured defects came out of looking.

### The audit

A WCAG contrast walker (`/tmp/polish/contrast.py`) visits every
text-bearing element on all 10 routes at 390px, resolves the effective
background by walking ancestors for the first opaque paint, and computes
the ratio. It ran in both themes. Dark theme: **0 flags**. Light theme:
**45 flags, every one of them the same token** - `--ink-faint`.

Separately, a non-text (graphics) audit walked every SVG geometry
element and resolved the real stroke/fill against the nearest opaque
background. That one is dominated by decorative chrome (grid lines,
ticks, spokes) that is deliberately low-contrast in both themes, so the
signal had to be separated from the noise: the question is not "is this
line under 3:1" but "is a DATA MARK under 3:1".

### Defect 1 - `--ink-faint` below the AA text floor (light theme)

`--ink-faint: #6d6d6d` on `--panel-nested: #ececec` measures **4.38:1**.
WCAG 1.4.3 wants 4.5:1 for text under 18.66px, and this token paints
captions, help lines, stamps and period separators at 12px. 45
rendered elements were under the floor.

`--ink-faint` is now `#616161`: **5.24:1** on `--panel-nested` and
5.4-6.2 on every other light surface, so the tier still reads as
visibly faint without being unreadable. The dark theme's `#8b8b8b` was
already clean and is untouched.

Re-measured after the change: **0 flags on all 10 routes in both
themes.**

### Defect 2 - the chart series scale broke the promise its own comments make

Two source comments state the contract:

- `src/styles/tokens.css`: "five greys from --ink down to a floor that
  still clears 3:1 on --panel and --panel-nested, which is the WCAG
  figure for a non-text mark."
- `src/js/cli-mono.js`: "Five tones, because --chart-c1..5 are five... A
  sixth grey would not be - it could not clear 3:1 on the surface it is
  drawn on."

MEASURED: the promise was broken, in BOTH themes. The faintest tone is
the one that has to clear the floor, and it did not:

- dark `c5 #525252` - **2.23:1** on `--panel-nested`
- light `c5 #999999` - **2.41:1** on `--panel-nested`

A consumer writing a five-series chart got a series that was nearly
invisible against the card it was drawn on. The shipped specimens only
ever render two series (`CHART_SERIES` in `[...family].astro` has
`tone: 1` and `tone: 2`), so **nothing on screen ever showed the
defect** - this is a defect in the LIBRARY, found by reading the
contract rather than by looking at a screenshot.

The ramp was re-spaced by solving for the constraint set (every tone
>= 3.0:1 on `--panel` and `--panel-nested`, adjacent tones still
>= 1.30 apart, monotonic in each theme's direction), moving the
shipped c1/c2 as little as the constraint allows:

- dark: `#8c8c8c` / `#787878` / `#666666` (5.18, 3.94, 3.03:1)
- light: `#747474` / `#878787` (3.96, 3.04:1)

In-situ re-measurement after the change: every rendered series mark
measures **>= 8.9:1** against its real background in both themes. (The
1.08:1 entries in the graphics log are the intentional 1px
surface-coloured seam between stacked bars and the slice outline, not
data marks.) Full-resolution light-theme chart sheets confirm all
series, axes, labels and heatmap cells are visible and the two series
are clearly distinguishable.

### The guards

`tests/verify-chart-contrast.py` reads the real token values out of
`tokens.css` (no hardcoded copies) and asserts: the 3:1 floor against
both surfaces, the adjacent separation, the monotonicity, and that all
four ramp blocks (document dark, document light, scoped dark, scoped
light) agree with each other - a scoped container must not ship a
different scale from the document root.

`tests/mutate-chart-contrast.py` reverts each tone to its pre-fix value
in turn and asserts the guard goes **red**. A guard that has never been
seen red is not a guard. Result: **3/3 mutants red, green after
restore.**

Both are wired into `package.json` as `test:chart-contrast` and
`test:chart-contrast:mutate`.

### Verification

- suite 688/0
- hero-clip 22/22, doc-toc 81/81, drawer-column 50/50
- chart-contrast guard green; mutation 3/3 red
- parity:live 66=66
- live text-contrast audit: **0 flags** on 10 routes x 2 themes
- in-situ series marks: all >= 8.9:1 in both themes
- 768px sweep: every family sheet's claims refuted at full res or by
  measurement (f-surfaces, f-tables, f-prose closed out)

### The 768px sweep, closed

The remaining 768px claims from the last window were all refuted:

- f-tables: the "size column cut off" is the documented scrollable
  table pattern - measured, the actions column ends at x=726 inside a
  748px section boundary and the table (685px) fits its 686px scroller.
- f-surfaces: selection, surface, stack, density, lists, states and the
  "Dead Hosts" page head were all checked at full res or by
  measurement - the page-head title measures clean against its
  line-height, and the avatar-group "+2" chip has 11px of clearance.
- f-prose: the "Moderate," table cell is fully inside its column.

### What is still open

Nothing measured. The campaign's honest status: 7 real defects found
and fixed across the whole sweep (§15's five, plus this window's two),
and every other flag was refuted by measurement or by full-resolution
pixels. The corpus behind that claim:

- 448 dark-theme shots + 224 light-theme shots (320/390/768/1280)
- 60 contact sheets (40 dark, 20 light)
- 292 alignment section-records carrying 1296 drift entries
  (131 @390, 88 @768, 73 @1280) - every one an intentional
  specimen-grid or flex-row pattern
- 20 contrast passes (10 routes x 2 themes), 0 flags after the fix
