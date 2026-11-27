# Design language — "terminal, refined"

oem-ui is monospace, dark by default, square-cornered, greyscale. Borders
do the lifting; colour is reserved for state, never decoration. This
document is the consumer-facing spec for the direction. Every value
below resolves to a token in `src/styles/tokens.css`; never hardcode
the literals.

## Surfaces — the ladder

Depth comes from a stack of surfaces, not from shadows. Each level is a
real step in both themes; the names stay the same, the hex values
invert.

| Token | Dark | Light | Use |
|---|---|---|---|
| `--bg` | `#0a0a0a` | `#fafafa` | page background |
| `--panel` | `#111111` | `#f5f5f5` | a card, a section, a modal body |
| `--panel-nested` | `#1a1a1a` | `#ececec` | a tile inside a panel |
| `--surface-raised` | `#222222` | `#f5f5f5` | a control drawn on a card (chip, button) |
| `--bg-2` / `--bg-3` | `#101010` / `#161616` | `#ffffff` / `#f0f0f0` | inset wells, code bodies |

The machined highlight is the one shadow the system owns:
`--shadow-1` is a 1px inset top line (`rgba(255,255,255,0.03)` dark /
`rgba(0,0,0,0.04)` light). It is applied to raised surfaces to give
them a machined edge; it is not a drop shadow and it disappears under
forced colors (see below).

Rules:

- A state is never a fill alone. Selected/active surfaces pair a fill
  with a border change or a glyph, and every new state ships a case in
  the `@media (forced-colors: active)` block at the end of
  `components.css`.
- Radius is zero on purpose: `--radius: 0`, `--radius-sm: 0`. Do not
  round.

## Type scale — dramatic, not flat

Headings:

- `--head-h1: 2rem` — display head, page title.
- `--head-h2: var(--text-md)` (1.25rem) — section head.

Body text, five steps:

- `--text-lg: 1.35rem` — a value that is the point of its panel.
- `--text-md: 1.25rem` — section heading step.
- `--text: 1rem` — default reading size.
- `--text-sm: 0.875rem` — secondary text, meta, a row's description.
- `--text-xs: 0.8125rem` — label, tag, chip.
- `--text-micro: 0.75rem` — the uppercase tracked label, and the floor.

Eyebrows are wide-tracked uppercase at `--text-micro` (letter-spacing
around 0.18–0.28em). The `--min-font` floor is 12px and matches
`--text-xs`; nothing renders below it.

## Texture — the dot grid

A subtle dot grid sits behind panels to give the page a machined
surface. It is paint-only: small dots on a regular spacing, low
contrast against `--bg`, and it must not affect layout or scrolling.
Apply it to the page or panel background, never to text containers.

## Frames — terminal windows

Specimens and demos are framed as terminal windows:

```
[ name ]
```

A frame is a bordered box (`--panel` fill, `--border` 1px) with a title
bar carrying `[ name ]` in `--text-micro`, wide-tracked. Square
corners. The frame holds the specimen; the specimen inside keeps its
own spacing.

## Section heads — indexed

Sections are numbered and ruled:

```
01 ── name
```

The index is zero-padded, followed by an em dash rule and the name in
the heading step. This is the `SectionHead` component; use it for every
top-level section of a page so the reading order is explicit.

## Interaction

- Inverted hover: on hover/focus, a control inverts (background becomes
  ink, text becomes background) rather than gaining a tint. No new
  hues are introduced for hover.
- The brand carries a blinking block caret (`cm-cursor`), animated
  with a 1.2s opacity cycle. Respect `prefers-reduced-motion`: the
  system lists every animation in one block and disables them.
- Focus rings are recoloured with `outline-color`, never the
  `outline: <colour>` shorthand (which resets style to `none`).
- Tooltips use `:hover` / `:focus-within`, menus use `[popover]`,
  modals use `<dialog>` — prefer the platform element over a runtime.

## Forced colors

Windows High Contrast repaints every background and drops every
box-shadow. Any new mark whose paint is its whole meaning (a fill, a
bar, a dot) must also be added to the forced-colors block at the end
of `components.css`, in system colours only, with a case in
`tests/verify-forced-colors.py`.
