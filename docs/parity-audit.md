# Live audit: shadcn/ui vs oem-ui (measured, 2026-10-12)

All shadcn numbers below are MEASURED in a real browser at a 1265px
viewport on `ui.shadcn.com/docs/components` and
`.../docs/components/base/button`, not read off screenshots or guessed
from class names.

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

Not done, and known:

- **one page per family.** The payload is still a single 316KB
  `index.astro`; shadcn splits by route. This is the remaining half of
  "the whole thing loads". It is not free: ~50 suite checks slice
  `index.astro` by section id, so splitting the page moves the fixtures
  those checks read.
- **a right-hand on-this-page TOC.** shadcn's content page carries a
  sticky ~288px TOC beside the ~640px measure; oem-ui has only the rail.
  The scroll-spy is already generic (it reads whatever `[data-cm-spy]`
  rows it is handed), so a TOC would get highlighting without new JS —
  but nothing renders one yet, so no JS was added for it. Wiring a TOC
  with no TOC in the page would be dead code that reads as live.
- **the non-component areas**: Blocks, Typeset, Directory, Create have
  no oem-ui equivalent at all.

A note on ordering, since it is the honest part: `content-visibility:
auto` was the cheap way to make one page behave like many, and it was
measured and rejected — it skips 49 of 51 sections but breaks in-page
anchors (jumps landed 1342–3586px past the target). Any future
lazy-loading has to preserve `href="#…"`.

