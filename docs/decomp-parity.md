# decomp-sh parity: every UI element, mapped

Measured 2026-10-21 against decomp-sh at `b83aa36`. Not a survey of what decomp-sh
might need — a class-by-class inventory of what its app actually emits, taken from
`app.css`, `index.html` and the template strings in `app.js`.

## What was counted

| source | count | how |
|---|---|---|
| classes emitted by decomp-sh | 286 | union of `class="..."` in index.html and app.js, plus every selector defined in app.css |
| regions those classes belong to | 15 | the `/* --- */` section each one is defined under |
| classes oem-ui already had | 759 | `.cm-*` in components.css + base.css |
| **new components this audit required** | **2** | `.cm-dropzone` (5 rules) and `.cm-mono` |

Four tokens were removed from the raw extraction as false positives: `false`, `n`,
`theme` and `toolFilter` are the second argument of `classList.toggle()` or an
interpolated expression inside `class="...${expr}"`, not class names. Counting them
would have inflated the inventory and produced four mappings to nothing.

**The result is not a gap list.** 284 of the 286 classes already had a component.
The work was deciding *which* one, and refusing the tempting wrong answer:

- `.mono` is not `.cm-inline-code` — that draws a box around an address the reader
  then assumes is clickable.
- `.legend` is not a new `.cm-legend` — the series colours belong to the chart, so it
  is `.cm-chart__legend`, and a standalone legend would let the two drift.
- `.danger-zone` is not a red box — severity here is glyph plus ink weight.

## The mapping

### base — text and layout utilities

- **decomp-sh (9):** `mono` `muted` `small` `grow` `row` `ok` `bad` `locked` `on`
- **oem-ui (8):** `cm-mono` `cm-hint` `cm-inline` `cm-btn-group` `cm-chip--ok` `cm-chip--err` `cm-chip--set` `cm-row--on`
- `.mono` is the one genuinely new utility: an address or a symbol inline in prose is TYPE, not a box, so `.cm-inline-code` is the wrong answer. `.muted small` is `.cm-hint` (opacity) plus `--text-sm`; oem-ui deliberately has no `.small` class, because a component owns its own size rather than inheriting one from the author.

### buttons — action buttons

- **decomp-sh (9):** `primary` `ghost` `small-btn` `icon` `danger` `as-btn` `link` `link-btn` `sm`
- **oem-ui (7):** `cm-btn` `cm-btn--primary` `cm-btn--ghost` `cm-btn--sm` `cm-icon-btn` `cm-btn--danger` `cm-inline-link`
- One base plus modifiers. `.sm` and `.small-btn` are the same variant; `.as-btn` is a link wearing button clothes, which is `.cm-btn` on an `<a>`.

### shell — app shell and sidebar rail

- **decomp-sh (26):** `app` `nav` `nav-top` `nav-scroll` `nav-foot` `nav-meta` `nav-item` `nav-label` `nav-badge` `nav-empty` `nav-new` `nav-proj` `nav-projects` `np-top` `np-name` `np-meta` `np-room` `np-bar` `up-notes` `brand` `hollow` `nav-shade` `nav-close` `nav-update` `mbar` `main`
- **oem-ui (15):** `cm-shell` `cm-sidebar` `cm-sidebar__header` `cm-sidebar__content` `cm-sidebar__footer` `cm-sidebar__item` `cm-sidebar__link` `cm-sidebar__label` `cm-sidebar__badge` `cm-sidebar__scrim` `cm-sidebar__action` `cm-rows` `cm-nav-toggle` `cm-header` `cm-state`
- decomp splits the rail into nav-top / nav-scroll / nav-foot, which is `__header` / `__content` / `__footer`. `.nav-shade` is `__scrim`; `.nav-close` and `.nav-update` are `__header` controls. A project entry in the rail is a `.cm-row`, and an empty rail is `.cm-state`.

### pages — page frame

- **decomp-sh (8):** `view` `page-head` `eyebrow` `pad` `cols` `stack-col` `section-title` `pane-title`
- **oem-ui (8):** `cm-stack--section` `cm-head` `cm-kicker` `cm-section--pad` `cm-cols` `cm-stack` `cm-section__title` `cm-head__title`
- `page-head` is `.cm-head` (kicker, title, sub). `.cols` and `.stack-col` are `.cm-cols` and `.cm-stack`.

### home — import surface

- **decomp-sh (39):** `hero` `lede` `how` `drop` `drop-idle` `drop-picked` `drop-busy` `drop-error` `drop-title` `cart` `plat-row` `plat-legend` `plat-status` `rom-card` `facts` `field` `check` `start-card` `starts` `cards` `sc-icon` `spinner` `joblog` `meter` `upbar` `privacy` `err-msg` `chip-s` `rec` `rec-mark` `meta` `one` `tall` `big` `accent` `beta` `over` `inline` `lz-custom`
- **oem-ui (25):** `cm-hero` `cm-lede` `cm-stepper` `cm-dropzone` `cm-dropzone--picked` `cm-dropzone--busy` `cm-dropzone--err` `cm-dropzone__mark` `cm-dropzone__title` `cm-dropzone__platforms` `cm-dropzone__note` `cm-card` `cm-kv` `cm-field` `cm-check` `cm-cards` `cm-spinner` `cm-term` `cm-meter` `cm-hint` `cm-alert__text` `cm-disclosure` `cm-chip` `cm-tag--accent` `cm-status`
- **The drop target is the one new component.** `.cm-dropzone` carries `--over`, `--picked`, `--busy` and `--err`, plus a `__platforms` row for the formats it accepts; decomp's four `drop-*` classes are exactly those four states. `.privacy` is `.cm-hint`, and `.lz-custom` is `.cm-disclosure`.

### phead — project header

- **decomp-sh (20):** `phead` `ph-row` `ph-title` `ph-actions` `ph-chips` `ph-progress` `ph-pct` `pill-btn` `count` `ptabs` `ptab` `pop-wrap` `popover` `notice` `warn` `off` `plat` `room` `together` `project`
- **oem-ui (13):** `cm-head` `cm-head-row` `cm-head-row__text` `cm-push-group` `cm-chip` `cm-meter` `cm-meter__top` `cm-chip--action` `cm-tag` `cm-tabs` `cm-tabs__panel` `cm-popover` `cm-alert`
- `ph-row` / `ph-title` / `ph-actions` are exactly `.cm-head-row` plus `__text` plus `.cm-push-group`. That component exists because hand-rolled versions of this row drift one block at a time; see its comment in components.css.

### overview — KPIs and the ROM map

- **decomp-sh (40):** `kpis` `kpi` `label` `num` `sub` `big-row` `progress` `bars` `area` `line` `stack` `legend` `sw` `map-panel` `map-wrap` `map-hint` `tip` `panel` `panel-head` `mini-list` `next` `next-text` `autopilot` `ap-icon` `ap-text` `now` `empty` `spin-dot` `star` `dot` `job` `job-top` `job-name` `job-who` `job-foot` `steps-line` `todo` `open` `fn` `who`
- **oem-ui (23):** `cm-stats` `cm-stat` `cm-stat__label` `cm-stat__val` `cm-stat__note` `cm-chart` `cm-chart__line` `cm-chart__area` `cm-chart__bar--stacked` `cm-chart__legend` `cm-chart__legend-dot` `cm-chart__legend-item` `cm-chart__legend-label` `cm-section` `cm-head-row` `cm-rows` `cm-alert` `cm-status` `cm-tooltip` `cm-state` `cm-spinner` `cm-tag--accent` `cm-dot`
- The map is a canvas plus `.cm-tooltip`. Every chart is one `.cm-chart` with `__line` / `__area` / `__bar--stacked`, and the legend is `.cm-chart__legend` - there is no standalone `.cm-legend`, and adding one would split the series colours away from the chart that owns them. `.autopilot` / `.ap-icon` / `.ap-text` are `.cm-status`; `.next` is `.cm-alert`.

### functions — sortable table

- **decomp-sh (17):** `desc` `dim` `fn-table` `fn-table-wrap` `sorted` `list-tools` `list-foot` `search` `seg` `sel` `matched` `tried` `working` `st` `name` `none` `r`
- **oem-ui (11):** `cm-table` `cm-table-wrap` `cm-table__sort` `cm-toolbar` `cm-list-more` `cm-search` `cm-seg` `cm-seg__opt` `cm-chip--ok` `cm-chip--warn` `cm-chip`
- `sorted` is `aria-sort` on `.cm-table__sort`, never a colour class: the direction is drawn from the attribute, so a screen reader hears it as well as seeing it.

### agents — agent launcher and sessions

- **decomp-sh (24):** `agents-grid` `sessions` `session` `session-top` `agent-row` `ar-head` `launcher` `stepper` `lz-body` `lz-fields` `lz-kind` `lz-kinds` `lz-row` `ep-card` `ep-pick` `model-chips` `tag` `state` `err` `ext` `work` `wide` `last` `facts-line`
- **oem-ui (16):** `cm-split` `cm-rows` `cm-row` `cm-rows--stacked` `cm-row__body` `cm-row__meta` `cm-stepper` `cm-field` `cm-field-row` `cm-select` `cm-card` `cm-check` `cm-chip` `cm-tag` `cm-status` `cm-alert--err`
- A session is `.cm-rows--stacked` (title over detail over meta); the launcher is `.cm-stepper` driving `.cm-field` rows.

### activity — feeds

- **decomp-sh (7):** `activity-cols` `feed` `feed-panel` `thoughts` `fresh` `placeholder` `score`
- **oem-ui (6):** `cm-cols` `cm-timeline` `cm-timeline__item` `cm-timeline__body` `cm-msglist` `cm-section`
- The chronological feed is `.cm-timeline`; agent chatter carrying an author and a timestamp is `.cm-msglist`, which already owns grouped messages, reactions and unread rails.

### settings — settings panes

- **decomp-sh (11):** `chip` `chips` `cmd` `danger-zone` `line-item` `ok-mark` `port` `setup-group` `src-line` `src-state` `txt`
- **oem-ui (7):** `cm-chip` `cm-code` `cm-alert--err` `cm-row` `cm-alert__mark` `cm-field-row` `cm-status`
- `danger-zone` is a `.cm-section` whose action is `.cm-btn--danger`. There is no red-bordered box, on purpose: the system carries severity by glyph and weight, never by hue.

### catalog — public decomps and tools

- **decomp-sh (20):** `badge` `broken` `busy-step` `cat-card` `cat-grid` `cat-note` `cat-tools` `tool-grid` `tool-card` `cc-top` `tc-top` `repo-row` `logbox` `readme` `policy-line` `fork-setup` `fs-main` `fs-side` `fs-remove` `steps`
- **oem-ui (12):** `cm-tag` `cm-alert--err` `cm-stepper` `cm-card` `cm-cards` `cm-hint` `cm-toolbar` `cm-input-group` `cm-disclosure` `cm-typeset` `cm-cols` `cm-split`
- Both card grids are `.cm-cards`; a repo-URL row with a trailing button is `.cm-input-group`.

### drawer — function inspector

- **decomp-sh (47):** `drawer` `drawer-card` `drawer-head` `drawer-body` `dh` `dh-title` `tabs` `tab` `fn-tabs` `fn-chart` `fn-chart-note` `diff` `diff-sum` `diff-key` `dfold` `dfolded` `bestline` `problems` `xref` `code` `code-cols` `col-title` `editor` `edit-bar` `try-msg` `note` `note-box` `toasts` `pin` `addr` `match` `mov` `op` `kw` `k` `lbl` `arg` `axis` `grid` `cm` `dn` `dm` `dr` `fail` `repl` `errlog` `narrow`
- **oem-ui (21):** `cm-dialog` `cm-dialog__head` `cm-dialog__body` `cm-dialog__title` `cm-tabs` `cm-tabs__tab` `cm-tabs__list` `cm-chart` `cm-diff` `cm-diff__row` `cm-diff__fold` `cm-rows` `cm-code` `cm-codebar` `cm-code-input` `cm-alert` `cm-field` `cm-toast-region` `cm-kv` `cm-table` `cm-btn--ghost`
- decomp's inspector card is `.cm-dialog` (head, body, title). The editor is `.cm-code-input`: a textarea over a highlighted `pre`, which is exactly what decomp hand-rolls with `.editor` plus `.edit-bar`. `.dfolded` is `.cm-diff__fold`.

### responsive — phone breakpoints

- **decomp-sh (3):** `nav-open` `err-text` `credit`
- **oem-ui (3):** `cm-nav-scrim` `cm-alert__text` `cm-hint`
- No class of its own: these are the app's own media-query behaviours, and every oem-ui component here already carries its own breakpoints. Porting them as classes would duplicate the system's responsive decisions in the consumer.

### js-templates — classes only app.js emits

- **decomp-sh (6):** `asm` `board` `btn` `c` `hero-text` `online`
- **oem-ui (5):** `cm-code` `cm-rows` `cm-btn` `cm-prose-measure` `cm-chip--ok`
- Markup fragments the JS builds at runtime. Each resolves to the component above rather than to a class of its own.

## The one component that had to be built

`.cm-dropzone` exists because decomp-sh's home page is a file target, and the
system had only `.cm-attach` — a file that is *already chosen*. The empty target
that chooses one did not exist. It is a state machine, not a box:

```html
<div class="cm-dropzone" role="button" tabindex="0" aria-label="Import a ROM">
  <span class="cm-dropzone__mark" aria-hidden="true">&#8595;</span>
  <p class="cm-dropzone__title">Drop a ROM to start</p>
  <p class="cm-dropzone__text">or press Enter to pick a file</p>
  <ul class="cm-dropzone__platforms">
    <li class="cm-chip">N64</li><li class="cm-chip">PSX</li>
  </ul>
  <p class="cm-dropzone__note">Read locally. Nothing is uploaded.</p>
</div>
```
The frame is **dashed at rest and solid while a drag is over it** — that is the
whole affordance, because a solid box reads as a container you cannot drop into.
`--over`, `--picked`, `--busy` and `--err` keep the frame: only the mark and the
copy change, so the page does not jump when a drop starts or fails.

`.cm-mono` is a two-line type utility. It exists so an address inline in prose
does not have to borrow the code-span box.

## Adopting it

The mapping is class-to-class, so adoption is substitution, not a rewrite. Order
that survives review:

1. Add the oem-ui layer (tokens, base, components) *before* the app's own rules,
   so app CSS still wins while the port is in progress and nothing half-ported
   ships looking right for the wrong reason.
2. Port region by region — `shell`, then `pages`, then the panels — and delete the
   decomp-sh rule as each region lands. A region is done when its classes are gone
   from `app.css`, not when both rule sets coexist.
3. `app.css` should lose its `tokens` block last: it is shared with decomp.wtf, and
   it is the only thing keeping the site coherent if the port stops halfway.

Two things this mapping deliberately does **not** claim:

- It does not claim decomp-sh and oem-ui share a *look*. They do not: decomp-sh has
  its own palette and rhythm. The mapping is structural — the same element, in the
  system's vocabulary — and adopting it changes the site's appearance unless the
  token layer is pointed at decomp-sh's own values.
- It does not claim `.cm-dropzone` is proven in a browser. It is proven to exist,
  to declare each state, and to come off the spacing scale. Geometry is unmeasured.

