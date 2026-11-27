# Design language — "terminal, refined"

oem-ui is monospace, dark by default, square-cornered, greyscale. Borders
do the lifting; colour is reserved for state, never decoration. This
document is the consumer-facing spec for the direction. Every value
below resolves to a token in `src/styles/tokens.css` — that file is the
source of truth, and this document never repeats a value, so the two
cannot drift.

## Surfaces — the ladder

Depth comes from a stack of surfaces, not from shadows. Each level is a
real step in both themes; the token names stay the same and the values
invert per theme. Consult `tokens.css` for the values of each step.

| Token | Role |
|---|---|
| `--bg` | page background |
| `--panel` | a card, a section, a modal body |
| `--panel-nested` | a tile inside a panel |
| `--surface-raised` | a control drawn on a card (chip, button) |
| `--bg-2` / `--bg-3` | inset wells, code bodies |

The machined highlight is the one shadow the system owns: `--shadow-1`
is an inset top hairline on a raised surface, giving it a machined
edge. It is not a drop shadow, and it disappears under forced colors
(see below). Its value lives in `tokens.css`.

Rules:

- A state is never a fill alone. Selected/active surfaces pair a fill
  with a border change or a glyph, and every new state ships a case in
  the `@media (forced-colors: active)` block at the end of
  `components.css`.
- Radius is zero on purpose: `--radius` and `--radius-sm` are both
  zero. Do not round. The tokens are the single place to change this.

## Type scale — dramatic, not flat

Headings:

- `--head-h1` — display head, page title.
- `--head-h2` — section head (resolves to a body-scale step, so the
  heading and its data stay distinct).

Body text, six steps, from largest to smallest:

- `--text-lg` — a value that is the point of its panel.
- `--text-md` — section heading step.
- `--text` — default reading size.
- `--text-sm` — secondary text, meta, a row's description.
- `--text-xs` — label, tag, chip.
- `--text-micro` — the uppercase tracked label, and the floor.

Eyebrows are wide-tracked uppercase at `--text-micro`. The `--min-font`
token is the smallest font size the system permits (a font-size floor,
not a tap-target floor — tap targets use `--tap`, 44px). `--text-micro`
is the smallest text step. Neither text step is below `--min-font`.
Their values live in `tokens.css`.

## Texture — the dot grid

A subtle dot grid sits behind panels to give the page a machined
surface. It is paint-only: dots on a regular spacing, low contrast
against `--bg`, and it must not affect layout or scrolling. Apply it to
the page or panel background, never to text containers. Spacing and
colour come from `tokens.css`.

## Frames — terminal windows

Specimens and demos are framed as terminal windows:

```
[ name ]
```

A frame is a bordered box (`--panel` fill, border from the border
token) with a title bar carrying `[ name ]` in `--text-micro`,
wide-tracked. Square corners. The frame holds the specimen; the
specimen inside keeps its own spacing.

## Section heads — indexed

Sections are numbered and ruled:

```
01 ── name
```

The index is zero-padded, followed by a box-drawing rule and the name
in the heading step. This is the `SectionHead` component; use it for
every top-level section of a page so the reading order is explicit.

## Interaction

- Inverted hover: on hover/focus, a control inverts (background becomes
  ink, text becomes background) rather than gaining a tint. No new
  hues are introduced for hover.
- The brand carries a blinking block caret (`cm-cursor`), animated
  with an opacity cycle. Respect `prefers-reduced-motion`: the system
  lists every animation in one block and disables them.
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
