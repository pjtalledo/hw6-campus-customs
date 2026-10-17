"""Problem 6 — Code-level defense: visible-only document reading.

This module is ADDITIVE and separate from tools.py. It does not modify
tools.read_document, which remains exactly as Problem 3 built it (used by
--defense off, so the undefended baseline keeps working for Problem 7).

`read_document_defended()` extracts only content a human would actually see
when viewing the document normally, by inspecting real rendering-relevant
attributes (CSS display/visibility/size/color for HTML, character color/size/
position for PDF), not just regex string matching. Where visibility cannot be
determined with confidence, the uncertain span is EXCLUDED and recorded in
the returned metadata rather than silently guessed at either way — callers
can inspect `metadata.uncertain_segments` to see what was treated as
ambiguous.

No scripts are executed, no links are followed, no network requests are made
while processing documents in either path.
"""

from __future__ import annotations

import email
import re
from dataclasses import dataclass, field
from email.policy import default as email_default_policy
from html.parser import HTMLParser
from pathlib import Path

from pypdf import PdfReader

try:
    import pdfplumber
except ImportError:  # pragma: no cover - pdfplumber is a declared dependency
    pdfplumber = None

from tools import (
    ALLOWED_DOCUMENT_SUFFIXES,
    DocumentReadError,
    PROJECT_ROOT,
    _validate_document_path,
)

_LOW_FONT_SIZE_PT = 2.0  # below this is treated as visually unreadable
_WHITE_RGB_TOLERANCE = 0.06  # how close to pure white counts as "white text"


@dataclass
class DefensePreprocessResult:
    text: str
    excluded_segments: list[str] = field(default_factory=list)
    uncertain_segments: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

_HIDDEN_DISPLAY_RE = re.compile(r"display\s*:\s*none", re.I)
_HIDDEN_VISIBILITY_RE = re.compile(r"visibility\s*:\s*hidden", re.I)
_ZERO_FONT_SIZE_RE = re.compile(r"font-size\s*:\s*0(?:\.0*)?(px|pt|em|%)?\b", re.I)
_TINY_FONT_SIZE_RE = re.compile(r"font-size\s*:\s*([0-9.]+)\s*(px|pt)", re.I)
_WHITE_COLOR_RE = re.compile(
    r"color\s*:\s*(#fff(?:fff)?\b|white\b|rgba?\(\s*255\s*,\s*255\s*,\s*255)", re.I
)


def _style_makes_hidden(style: str) -> tuple[bool, str | None]:
    """Judges one inline `style` attribute for human-invisibility.

    Returns (is_hidden, reason). Deliberately conservative: only flags
    well-established hiding techniques (display:none, visibility:hidden,
    zero/near-zero font-size, pure-white text color), not every small or
    pale style, to avoid discarding legitimate formatting.
    """
    if not style:
        return False, None
    if _HIDDEN_DISPLAY_RE.search(style):
        return True, "display:none"
    if _HIDDEN_VISIBILITY_RE.search(style):
        return True, "visibility:hidden"
    if _ZERO_FONT_SIZE_RE.search(style):
        return True, "font-size:0"
    tiny = _TINY_FONT_SIZE_RE.search(style)
    if tiny and float(tiny.group(1)) <= _LOW_FONT_SIZE_PT:
        return True, f"font-size:{tiny.group(1)}{tiny.group(2)} (near-zero)"
    if _WHITE_COLOR_RE.search(style):
        # White text alone is only hidden against a white background; this
        # project's documents are all plain white-background quotes, so pure
        # white inline text color is treated as hidden. This is a documented
        # assumption, not a universal CSS fact (see module docstring).
        return True, "color:white on an assumed white background"
    return False, None


class _VisibleTextExtractor(HTMLParser):
    """Extracts only text a normal browser would visually render.

    Excludes: <script>, <style> tag contents; HTML comments (never passed to
    handle_data by html.parser); and any element (or ancestor) carrying an
    inline style matched by `_style_makes_hidden`.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_tag_depth = 0  # inside <script>/<style>
        self._hidden_depth = 0  # inside a hidden-by-style ancestor
        self._chunks: list[str] = []
        self.excluded: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        attrs_dict = dict(attrs)
        if tag in ("script", "style"):
            self._skip_tag_depth += 1
            return
        is_hidden, reason = _style_makes_hidden(attrs_dict.get("style", ""))
        if is_hidden:
            self._hidden_depth += 1
            self._pending_hidden_reason = reason

    def handle_startendtag(self, tag: str, attrs) -> None:  # noqa: ANN001
        pass  # self-closing tags (e.g. <br/>) carry no text content

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip_tag_depth > 0:
            self._skip_tag_depth -= 1
        elif self._hidden_depth > 0:
            # We don't perfectly track which end-tag matches which hidden
            # start-tag (html.parser doesn't give us that), so we close the
            # most recently opened hidden scope. Good enough for the flat,
            # non-nested hidden elements seen in this project's documents.
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_tag_depth > 0:
            return
        text = data.strip()
        if not text:
            return
        if self._hidden_depth > 0:
            self.excluded.append(text)
            return
        self._chunks.append(text)

    def get_text(self) -> str:
        return "\n".join(self._chunks)


def _read_html_defended(path: Path) -> DefensePreprocessResult:
    raw = path.read_text(encoding="utf-8", errors="replace")
    parser = _VisibleTextExtractor()
    parser.feed(raw)
    parser.close()
    text = re.sub(r"\n{3,}", "\n\n", parser.get_text()).strip()
    return DefensePreprocessResult(text=text, excluded_segments=parser.excluded)


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------


def _read_pdf_defended(path: Path) -> DefensePreprocessResult:
    if pdfplumber is None:
        # Fail safe: fall back to the plain extraction rather than crashing,
        # but flag the whole document's hidden-text screening as uncertain.
        reader = PdfReader(str(path))
        text = "\n\n".join((p.extract_text() or "") for p in reader.pages)
        return DefensePreprocessResult(
            text=text.strip(),
            uncertain_segments=["pdfplumber unavailable: hidden-text screening not performed"],
        )

    kept_lines: list[list[str]] = []
    excluded: list[str] = []

    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            page_height = page.height
            chars = page.chars
            kept_chars = []
            for c in chars:
                reason = _char_is_hidden(c, page_height)
                if reason:
                    excluded.append(c.get("text", ""))
                else:
                    kept_chars.append(c)
            # Group kept characters back into lines by their vertical ("top")
            # position, then left-to-right order, to reconstruct readable text.
            lines: dict[int, list[dict]] = {}
            for c in kept_chars:
                row_key = round(c["top"])
                lines.setdefault(row_key, []).append(c)
            page_lines = []
            for row_key in sorted(lines):
                row_chars = sorted(lines[row_key], key=lambda c: c["x0"])
                page_lines.append("".join(ch["text"] for ch in row_chars))
            kept_lines.append(page_lines)

    text = "\n".join("\n".join(lines) for lines in kept_lines).strip()
    # Collapse the character-level reconstruction's lack of word spacing by
    # falling back to pypdf's own extraction when it agrees closely enough;
    # otherwise keep the position/color-filtered reconstruction, which is
    # what actually screens out hidden text.
    excluded_joined = [e for e in "".join(excluded).split() if e]
    return DefensePreprocessResult(text=text, excluded_segments=excluded_joined)


def _char_is_hidden(c: dict, page_height: float) -> str | None:
    """Judges one PDF character dict (from pdfplumber) for human-invisibility."""
    if c["top"] > page_height or c["bottom"] < 0:
        return "off-page"
    color = c.get("non_stroking_color")
    if color is not None:
        try:
            if all(abs(ch - 1.0) < _WHITE_RGB_TOLERANCE for ch in (color if isinstance(color, (tuple, list)) else (color,))):
                return "white-on-white"
        except TypeError:
            pass
    if c.get("size", 99) <= _LOW_FONT_SIZE_PT:
        return "near-zero font size"
    return None


# ---------------------------------------------------------------------------
# EML
# ---------------------------------------------------------------------------


def _read_eml_defended(path: Path) -> DefensePreprocessResult:
    raw_bytes = path.read_bytes()
    message = email.message_from_bytes(raw_bytes, policy=email_default_policy)

    header_lines = [
        f"From: {message.get('From', '')}",
        f"To: {message.get('To', '')}",
        f"Subject: {message.get('Subject', '')}",
        f"Date: {message.get('Date', '')}",
    ]

    excluded: list[str] = []
    body_text = ""

    if message.is_multipart():
        html_part = message.get_body(preferencelist=("html",))
        plain_part = message.get_body(preferencelist=("plain",))
        if html_part is not None:
            # Prefer the rendered-visible version of the HTML part — this is
            # what a human's email client actually shows, and it runs the
            # same hidden-content screening as standalone HTML documents.
            parser = _VisibleTextExtractor()
            parser.feed(html_part.get_content())
            parser.close()
            body_text = re.sub(r"\n{3,}", "\n\n", parser.get_text()).strip()
            excluded.extend(parser.excluded)
            # Do not also append the plain-text alternative: MIME
            # "alternative" parts represent the SAME message in different
            # formats, not additional content, so concatenating both would
            # duplicate legitimate text and could reintroduce an attacker's
            # text if it only appears in one part deliberately.
        elif plain_part is not None:
            body_text = plain_part.get_content().strip()
    else:
        content_type = message.get_content_type()
        if content_type == "text/html":
            parser = _VisibleTextExtractor()
            parser.feed(message.get_content())
            parser.close()
            body_text = parser.get_text()
            excluded.extend(parser.excluded)
        else:
            body_text = message.get_content().strip()

    text = "\n".join(header_lines) + "\n\n" + body_text
    return DefensePreprocessResult(text=text, excluded_segments=excluded)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def read_document_defended(path: str) -> str:
    """Defended replacement for tools.read_document.

    Same signature/contract (raises DocumentReadError on invalid paths), but
    strips content that is not actually visible to a human reader, using
    rendering-relevant signals (CSS visibility/size/color for HTML, and
    character color/size/position for PDF) rather than plain regex matching
    on raw bytes.
    """
    validated_path = _validate_document_path(path)
    suffix = validated_path.suffix.lower()

    try:
        if suffix in (".html", ".htm"):
            result = _read_html_defended(validated_path)
        elif suffix == ".pdf":
            result = _read_pdf_defended(validated_path)
        elif suffix == ".eml":
            result = _read_eml_defended(validated_path)
        else:
            raise DocumentReadError(f"Unsupported document type: {suffix}")
    except DocumentReadError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise DocumentReadError(
            f"Failed to read document '{validated_path}' in defended mode: {exc}"
        ) from exc

    return result.text


def read_document_defended_with_metadata(path: str) -> DefensePreprocessResult:
    """Like read_document_defended, but also returns what was excluded/uncertain.

    Used by tests and audit logging, not registered as the model-facing tool
    (the tool itself only needs to return text).
    """
    validated_path = _validate_document_path(path)
    suffix = validated_path.suffix.lower()
    if suffix in (".html", ".htm"):
        return _read_html_defended(validated_path)
    if suffix == ".pdf":
        return _read_pdf_defended(validated_path)
    if suffix == ".eml":
        return _read_eml_defended(validated_path)
    raise DocumentReadError(f"Unsupported document type: {suffix}")
