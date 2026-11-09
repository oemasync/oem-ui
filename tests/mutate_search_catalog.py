"""The mutation catalog, as data.

Each entry is (file, description, needs_rebuild, [(old, new), ...]).
A pair that does not occur is a NO-OP and the runner says so loudly.
"""
Q = chr(34)
NL = chr(10)
TAB = chr(9)

COMP = 'src/styles/components.css'
TOK = 'src/styles/tokens.css'
PAGE = 'src/pages/[...family].astro'
BASE = 'src/styles/base.css'

# The shipped rule is 2px. It used to be 1px, which the suite's own
# assertion correctly rejected ("a 1px ring against a 1px border is not a
# focus indicator a reader can see") - and the mutation sweep then showed the
# 1px->2px mutant SURVIVED, because the check that catches it asserts the
# WIDTH, not the presence of the rule. So the fix is the value, and the
# mutant now goes the other way (2px -> 1px) where the width assertion kills
# it. One constant, the one that is in the source.
FOCUS_RULE = ('.cm-search__input:focus-visible { outline: 2px solid var(--focus); '
              'outline-offset: 1px; }')

MUTATIONS = [
    (COMP, 'the search focus ring drops to a 1px hairline', False, [
        (FOCUS_RULE,
         '.cm-search__input:focus-visible { outline: 2px solid var(--focus); outline-offset: 1px; }'),
    ]),
    (COMP, 'the search focus ring stops referencing --focus', False, [
        (FOCUS_RULE,
         '.cm-search__input:focus-visible { outline: 1px solid var(--ink); outline-offset: 1px; }'),
    ]),
    (COMP, 'the search field loses the 16px form-text floor', False, [
        ('font-size: max(var(--min-font), 1rem);' + NL + TAB + 'color: var(--ink);',
         'font-size: max(var(--min-font), var(--text-sm));' + NL + TAB + 'color: var(--ink);'),
    ]),
    (TOK, '--focus is deleted (the exact bug that shipped)', False, [
        (TAB + '--focus: var(--accent-dim);' + NL, ''),
    ]),
    (COMP, 'the end gutter stops deriving from --search-clear', False, [
        ('padding-inline-end: calc(var(--space-3) + var(--search-clear) + var(--space-2));',
         'padding-inline-end: var(--space-4);'),
    ]),
    (COMP, 'the clear button stops taking --search-clear', False, [
        ('width: var(--search-clear);' + NL + TAB + 'height: var(--search-clear);',
         'width: 32px;' + NL + TAB + 'height: 32px;'),
    ]),
    (TOK, '--search-clear aliases --tap (a knob that cannot be turned)', False, [
        ('--search-clear: 32px;', '--search-clear: var(--tap);'),
    ]),
    (COMP, 'the coarse clear button loses the tap floor', False, [
        ('@media (pointer: coarse) {' + NL + TAB + '.cm-search__clear {' + NL
         + TAB + TAB + 'width: var(--tap);' + NL + TAB + TAB + 'height: var(--tap);' + NL
         + TAB + '}' + NL + '}', ''),
    ]),
    (COMP, 'the search glyph stops being sized (replaced-element default)', False, [
        (TAB + 'width: 1em;' + NL + TAB + 'height: 1em;' + NL + '}' + NL
         + '.cm-search__clear {',
         TAB + 'width: 24px;' + NL + TAB + 'height: 24px;' + NL + '}' + NL
         + '.cm-search__clear {'),
    ]),
    (BASE, 'base.css drops its .cm-search__input exclusion', True, [
        (':not(.cm-search__input)', ''),
    ]),
    (PAGE, 'the showcase stops rendering cm-search--wide', True, [
        ('<Search id="q-filled" wide', '<Search id="q-filled"'),
    ]),
    (PAGE, 'the clear button loses its accessible name in the showcase', True, [
        ('clearLabel="clear filter"', 'clearLabel="clear"'),
    ]),
    (PAGE, 'the search glyph stops being aria-hidden in the showcase', True, [
        ('<span class="cm-search__icon" aria-hidden="true">',
         '<span class="cm-search__icon">'),
    ]),
    (PAGE, 'the section index drops the search entry (scroll-spy skips it)', True, [
        ("'quiz', 'search', 'auth'", "'quiz', 'auth'"),
    ]),
    (PAGE, 'the find bar reverts to hand-written markup', True, [
        ('<Search id="q-find" placeholder="find in this room…" value="receipt" autocomplete="off" />',
         '<div class="cm-search"><span class="cm-search__icon" aria-hidden="true">'
         '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
         'stroke-linecap="round"><circle cx="11" cy="11" r="7" />'
         '<line x1="16.5" y1="16.5" x2="21" y2="21" /></svg></span>'
         '<input id="q-find" type="search" placeholder="find in this room…" '
         'value="receipt" autocomplete="off" /></div>'),
    ]),
    ('src/astro/Search.astro', 'the wrapper hand-writes the markup with a foreign glyph', True, [
        ('<div class="cm-search" class:list={wide && \'cm-search--wide\'}>',
         '<div class="cm-search"><span class="cm-search__icon" aria-hidden="true">'
         '<svg viewBox="0 0 16 16"><path d="M0 0h16v16H0z"/></svg>'
         '</span>'),
    ]),
    ('src/astro/Search.astro', 'the wrapper ships an always-visible clear button', True, [
        ('{value !== undefined && value !== \'\' && (',
         '{true && ('),
    ]),
    ('src/astro/Search.astro', 'the wrapper drops the library search glyph', True, [
        ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">\n      <circle cx="11" cy="11" r="7" />\n      <line x1="16.5" y1="16.5" x2="21" y2="21" />\n    </svg>',
         '<svg viewBox="0 0 16 16"><path d="M0 0h16v16H0z"/></svg>'),
    ]),
    ('src/astro/Search.astro', 'the wrapper makes the wide modifier a no-op', True, [
        ('class="cm-search" class:list={wide && \'cm-search--wide\'}',
         'class="cm-search"'),
    ]),
]