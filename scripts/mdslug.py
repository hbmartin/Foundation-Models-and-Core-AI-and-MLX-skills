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
formatting is approximated. Code-span content is protected before links and
emphasis are rendered, keeping both link-like text and identifiers such as
`_version:` and `strip_debug_info` verbatim. Outside code spans, only paired
underscore emphasis delimiters render away; unmatched edge underscores and
bare snake_case remain visible. Emphasis asterisks and backtick delimiters need
no special handling after rendering — the category filter drops them as
punctuation and symbols.
"""

import re
import unicodedata

_LINK_TEXT = re.compile(r'\[([^\]]*)\]\([^)]*\)')
_CODE_SPAN = re.compile(
    r'(?<!`)(?P<delimiter>`+)(?!`)(?P<content>.+?)'
    r'(?<!`)(?P=delimiter)(?!`)'
)
_BACKSLASH_ESCAPE = re.compile(
    r'''\\([!"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])'''
)
_ESCAPE_PLACEHOLDER = re.compile(r'\x00e(\d+)\x00')
_CODE_PLACEHOLDER = re.compile(r'\x00c(\d+)\x00')
_MATCHED_UNDERSCORE_EMPHASIS = re.compile(
    r'(?<!\w)(?P<delimiter>_+)(?=\S)(?P<content>[^\n]*?\S)'
    r'(?P=delimiter)(?!\w)'
)


def _render_away_emphasis(text):
    while True:
        stripped = _MATCHED_UNDERSCORE_EMPHASIS.sub(r'\g<content>', text)
        if stripped == text:
            return text
        text = stripped


def slugify(heading):
    code_spans = []
    escaped_characters = []

    def protect_escape(match):
        escaped_characters.append(match.group(1))
        return f'\x00e{len(escaped_characters) - 1}\x00'

    def protect_code_span(match):
        # Backslash escapes do not render inside code spans. Restore their
        # original two-character source spelling before protecting the span.
        content = _ESCAPE_PLACEHOLDER.sub(
            lambda escaped: '\\' + escaped_characters[int(escaped.group(1))],
            match.group('content'),
        )
        code_spans.append(content)
        return f'\x00c{len(code_spans) - 1}\x00'

    # CommonMark replaces NUL before inline parsing. Doing the same also
    # reserves NUL-delimited placeholders exclusively for spans we create.
    text = heading.replace('\x00', '\ufffd')
    text = _BACKSLASH_ESCAPE.sub(protect_escape, text)
    text = _CODE_SPAN.sub(protect_code_span, text)
    text = _LINK_TEXT.sub(r'\1', text)  # [text](url) -> text, as GitHub slugs do
    text = _render_away_emphasis(text)
    text = _ESCAPE_PLACEHOLDER.sub(
        lambda match: escaped_characters[int(match.group(1))], text
    )
    text = _CODE_PLACEHOLDER.sub(
        lambda match: code_spans[int(match.group(1))], text
    ).strip().lower()
    out = []
    for ch in text:
        if ch == ' ':
            out.append('-')
            continue
        category = unicodedata.category(ch)
        if ch == '-' or category[0] in 'LMN' or category == 'Pc':
            out.append(ch)
    return ''.join(out)
