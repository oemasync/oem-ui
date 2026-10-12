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

- ONE page: `src/pages/index.astro`, 316 KB, 5740 lines, 55 `<section>`
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

   FIXED, measured (2026-10-12): `.cm-section` is no longer filled with
   `background: var(--panel)` + `border: var(--line)` on every section.
   The stack now owns children via `gap: var(--stack-gap)`, and 50 of 51
   sections lay their in-flow direct children on a single gap with no
   inline `margin-top` breaking the rhythm (measured at 20px in WebKit).
2. **Payload**: one page, everything in the initial HTML.

   NOTE: shadcn's component page for Button itself ships 942KB raw / 84KB gzip
   (102 chunks) — larger than our 437KB raw / 76KB gzip. The complaint is
   division, not bytes. `content-visibility: auto` on `.cm-section` was
   tested: it skips 49 of 51 sections but breaks in-page anchor jumps
   (lands 1342–3586px off in WebKit). REMOVED for now as it breaks the
   rail navigation; any lazy-loading must not break `href="#…"`.
3. **Navigation**: 52 flat links, no grouping, no on-this-page TOC.

## 5. Rebuild plan (matching shadcn's structure, keeping house tokens)

House identity is preserved (mono, sharp corners, no hue, dark default);
what changes is the STRUCTURE and the RHYTHM, which are what shadcn gets
right:

- a `DocsLayout` shell: sticky header, fixed left rail, constrained
  content measure, right-hand on-this-page TOC;
- **one page per component family** instead of one page for all 52
  sections, so a visit loads one family;
- a single section rhythm in CSS (no per-section background) with one
  filled surface reserved for demo/preview blocks;
- nav grouped by family, with the current family marked.
