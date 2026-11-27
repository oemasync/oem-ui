# redesign/w09-layout

- Restyled the layout family to the terminal-refined language: form fields as crisp hairline boxes on the panel surface with eyebrow labels, strong rule on focus/invalid/disabled; calendar as a tight tabular grid with inverted selected day, underlined today and panel-nested range fill; scroll area with a machined thumb and track in both engines; charts with framed plot, eyebrow axes, tabular numerals and square legend swatches.
- Fixed slider thumb vertical centering; derived from local custom properties --cm-slider-track-h / --cm-slider-thumb-h.
- Fixed chart spec value overflow on narrow viewports (break-word).
- Added inset top highlight (--shadow-1) to calendar and chart containers.
- Field focus now uses the strong border rule instead of a heavier ring.
