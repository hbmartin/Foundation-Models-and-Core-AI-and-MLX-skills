"""GitHub heading-anchor slugs, shared by the guide tooling.

Single source of truth for the anchor algorithm: scripts/extract-callouts.py
and scripts/verify-snippets.py both import this module so their anchors always
agree (they previously kept byte-identical private copies).

The algorithm mirrors github-slugger over the rendered heading text: lowercase,
drop every character that is not a Unicode letter, mark, number, connector
punctuation, space, or hyphen, then turn spaces into hyphens. GitHub does not
collapse repeated hyphens and keeps leading and trailing ones, so a heading
"3. Incident — the break" anchors at #3-incident--the-break and "⚠️ Trap"
anchors at #️-trap: the warning sign U+26A0 is dropped as a symbol while its
variation selector U+FE0F survives as a mark.

Slugs are computed from source Markdown rather than rendered HTML, so inline
formatting is approximated. Code-span content is rendered verbatim, keeping
`_version:` and `strip_debug_info` underscores as GitHub does; outside code
spans, underscores at word edges are emphasis markers that render away (GFM
has no intraword _emphasis_, so bare snake_case also survives). Emphasis
asterisks and the backtick delimiters themselves need no special handling —
the category filter drops them as punctuation and symbols.
"""

import re
import unicodedata

_LINK_TEXT = re.compile(r'\[([^\]]*)\]\([^)]*\)')
_CODE_SPAN = re.compile(r'(`+)(.+?)\1')
_EMPHASIS_UNDERSCORE = re.compile(r'\b_|_\b')


def _render_away_emphasis(text):
    while True:
        stripped = _EMPHASIS_UNDERSCORE.sub('', text)
        if stripped == text:
            return text
        text = stripped


def unique_slug(base, used, next_suffix):
    """Return GitHub's first-unsuffixed, then -1, -2, ... heading anchor."""
    candidate = base
    if candidate in used:
        suffix = next_suffix[base] or 1
        candidate = f"{base}-{suffix}"
        while candidate in used:
            suffix += 1
            candidate = f"{base}-{suffix}"
        next_suffix[base] = suffix + 1
    else:
        next_suffix[base] = 1
    used.add(candidate)
    return candidate


def slugify(heading):
    text = _LINK_TEXT.sub(r'\1', heading)  # [text](url) -> text, as GitHub slugs do
    parts = []
    position = 0
    for span in _CODE_SPAN.finditer(text):
        parts.append(_render_away_emphasis(text[position:span.start()]))
        parts.append(span.group(2))
        position = span.end()
    parts.append(_render_away_emphasis(text[position:]))
    text = ''.join(parts).strip().lower()
    out = []
    for ch in text:
        if ch == ' ':
            out.append('-')
            continue
        category = unicodedata.category(ch)
        if ch == '-' or category[0] in 'LMN' or category == 'Pc':
            out.append(ch)
    return ''.join(out)
