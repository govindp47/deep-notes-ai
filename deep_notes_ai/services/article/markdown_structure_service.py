"""
deep_notes_ai/services/article/markdown_structure_service.py

MarkdownStructureService

Responsible for converting extracted markdown into a sequence of logical
DocumentSection objects.

Responsibilities:
    • Parse markdown using markdown-it-py.
    • Preserve heading hierarchy.
    • Associate body text with the correct heading.
    • Create an Introduction section when content exists before the first
      heading.
    • Ignore empty sections.
    • Preserve original document order.
    • Preserve markdown structure (lists, tables, code, blockquotes,
      inline formatting, links, images, horizontal rules, raw HTML) as
      faithfully as possible when reconstructing section content.

This service intentionally performs NO tokenization beyond what is needed
to reconstruct section content.

This service intentionally performs NO chapter generation.

This service intentionally performs NO markdown rendering to HTML.

Input:
    Markdown

Output:
    list[DocumentSection]
"""

from __future__ import annotations

import logging

from markdown_it import MarkdownIt
from markdown_it.token import Token

from deep_notes_ai.domain.models import (
    ArticleStructureError,
    DocumentSection,
)

logger = logging.getLogger(__name__)


class MarkdownStructureService:
    """
    Parse markdown into logical document sections.

    Every top-level heading begins a new DocumentSection.

    Any content that appears before the first heading becomes a
    synthetic "Introduction" section with heading level 0, indicating
    that it was not derived from an actual markdown heading.

    The returned sections preserve the original ordering of the document,
    allowing downstream services to generate ChapterTranscript objects
    without losing structure.

    Section content is reconstructed directly from markdown-it-py tokens
    (rather than from isolated inline text) so that nested lists, ordered
    list numbering, fenced/indented code blocks, tables, blockquotes,
    inline formatting, links, images, horizontal rules, and raw HTML are
    preserved as faithfully as possible.
    """

    def __init__(self) -> None:
        # The "table" and "strikethrough" rules are enabled explicitly
        # because they are disabled by default under the "commonmark"
        # preset, but are required to preserve GFM-style tables and
        # ~~strikethrough~~ spans without pulling in additional presets
        # (such as "gfm-like") that would also enable linkify/typographer
        # behavior and alter raw inline content.
        self._markdown = MarkdownIt("commonmark").enable(
            ["table", "strikethrough"]
        )

    def parse(
        self,
        markdown: str,
    ) -> list[DocumentSection]:
        """
        Parse markdown into document sections.

        Args:
            markdown:
                Clean markdown extracted from the article.

        Returns:
            Ordered list of DocumentSection objects.

        Raises:
            ArticleStructureError
        """
        if not markdown.strip():
            raise ArticleStructureError(
                "Cannot parse an empty markdown document."
            )

        logger.info(
            "Parsing markdown document (%d characters).",
            len(markdown),
        )

        try:
            tokens = self._markdown.parse(markdown)
        except Exception as exc:
            raise ArticleStructureError(
                f"Markdown parsing failed: {exc}"
            ) from exc

        try:
            sections = self._build_sections(tokens)
        except ArticleStructureError:
            raise
        except Exception as exc:
            raise ArticleStructureError(
                f"Markdown structure extraction failed: {exc}"
            ) from exc

        if not sections:
            raise ArticleStructureError(
                "No document sections could be extracted."
            )

        logger.info(
            "Parsed %d document section%s.",
            len(sections),
            "" if len(sections) == 1 else "s",
        )

        return sections

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _build_sections(
        self,
        tokens: list[Token],
    ) -> list[DocumentSection]:
        """
        Convert markdown tokens into ordered DocumentSection objects.

        A single forward pass builds a map from each "_open" token index
        to its matching "_close" token index. That map lets every nested
        construct (lists, blockquotes, tables, ...) be rendered without
        rescanning the token stream, keeping the parser O(n) with respect
        to the number of tokens.

        A second pass walks the top-level (depth 0) tokens looking for
        heading boundaries. Everything between two top-level headings is
        rendered, as a single markdown-preserving pass, into the content
        of the preceding section.

        A heading ancestry stack is maintained while walking top-level
        headings so hierarchy information is never lost while parsing,
        even though DocumentSection only stores a flat heading/level.
        """
        close_map = self._build_close_map(tokens)

        sections: list[DocumentSection] = []

        heading_stack: list[tuple[str, int]] = []

        current_heading = "Introduction"
        current_level = 1

        segment_start = 0
        index = 0
        total = len(tokens)

        while index < total:
            token = tokens[index]

            if token.level == 0 and token.type == "heading_open":
                content = self._render_block_range(
                    tokens,
                    close_map,
                    segment_start,
                    index,
                )

                self._append_section(
                    sections=sections,
                    heading=current_heading,
                    level=current_level,
                    content=content,
                )

                close = close_map[index]
                level = int(token.tag[1])

                inline = tokens[index + 1]
                text = self._render_inline(inline).strip()

                heading_text = (
                    text if text else f"Untitled Section {len(sections) + 1}"
                )

                while heading_stack and heading_stack[-1][1] >= level:
                    heading_stack.pop()

                heading_stack.append((heading_text, level))

                logger.debug(
                    "Heading ancestry: %s",
                    " > ".join(f"{h} (h{lvl})" for h, lvl in heading_stack),
                )

                current_heading = heading_text
                current_level = level

                segment_start = close + 1
                index = close + 1
                continue

            index += 1

        content = self._render_block_range(
            tokens,
            close_map,
            segment_start,
            total,
        )

        self._append_section(
            sections=sections,
            heading=current_heading,
            level=current_level,
            content=content,
        )

        return sections

    def _build_close_map(
        self,
        tokens: list[Token],
    ) -> dict[int, int]:
        """
        Build a mapping from every "_open" token index to its matching
        "_close" token index.

        Raises:
            ArticleStructureError:
                If the markdown token stream contains unbalanced or
                improperly nested open/close tokens.
        """
        close_map: dict[int, int] = {}
        stack: list[tuple[int, str]] = []

        for index, token in enumerate(tokens):
            if token.type.endswith("_open"):
                expected_close = token.type[:-5] + "_close"
                stack.append((index, expected_close))

            elif token.type.endswith("_close"):
                if not stack:
                    raise ArticleStructureError(
                        f"Unexpected closing token '{token.type}' "
                        f"at index {index}."
                    )

                open_index, expected_close = stack.pop()

                if token.type != expected_close:
                    raise ArticleStructureError(
                        "Malformed markdown token stream: "
                        f"expected '{expected_close}' but found "
                        f"'{token.type}'."
                    )

                close_map[open_index] = index

        if stack:
            _, expected_close = stack[-1]

            raise ArticleStructureError(
                "Malformed markdown token stream: "
                f"missing closing token '{expected_close}'."
            )

        return close_map

    def _append_section(
        self,
        sections: list[DocumentSection],
        heading: str,
        level: int,
        content: str,
    ) -> None:
        """
        Append a section if it contains meaningful content.
        """
        content = content.strip()

        if not content:
            return
        
        if not heading:
            logger.warning("no heading for section content: %s", content[:min(25, len(content))])
            heading = "NO HEADING DETECTED"
        
        if level < 1:
            logger.warning("Level for section: %s is < 1", heading)
            level = 1

        sections.append(
            DocumentSection(
                heading=heading,
                level=level,
                content=content,
            )
        )

    def _render_block_range(
        self,
        tokens: list[Token],
        close_map: dict[int, int],
        start: int,
        end: int,
    ) -> str:
        """
        Render a sequence of sibling block-level tokens, tokens[start:end),
        into markdown text, recursing into nested constructs as needed.

        Blocks are separated by a blank line, mirroring standard markdown
        block separation.
        """
        blocks: list[str] = []

        index = start

        while index < end:
            token = tokens[index]

            if token.type == "heading_open":
                close = close_map[index]
                inline = tokens[index + 1]
                text = self._render_inline(inline).strip()
                marker = "#" * int(token.tag[1])

                blocks.append(f"{marker} {text}".rstrip())

                index = close + 1

            elif token.type == "paragraph_open":
                close = close_map[index]
                inline = tokens[index + 1]

                blocks.append(self._render_inline(inline).strip())

                index = close + 1

            elif token.type == "fence":
                blocks.append(self._render_fence(token))
                index += 1

            elif token.type == "code_block":
                blocks.append(self._render_code_block(token))
                index += 1

            elif token.type == "html_block":
                blocks.append(token.content.rstrip("\n"))
                index += 1

            elif token.type == "hr":
                marker = token.markup[0] * 3 if token.markup else "---"

                blocks.append(marker)
                index += 1

            elif token.type == "blockquote_open":
                close = close_map[index]

                inner = self._render_block_range(
                    tokens,
                    close_map,
                    index + 1,
                    close,
                )

                blocks.append(self._prefix_lines(inner, "> "))

                index = close + 1

            elif token.type in ("bullet_list_open", "ordered_list_open"):
                close = close_map[index]

                blocks.append(
                    self._render_list(tokens, close_map, index, close)
                )

                index = close + 1

            elif token.type == "table_open":
                close = close_map[index]

                blocks.append(
                    self._render_table(tokens, close_map, index, close)
                )

                index = close + 1

            else:
                logger.warning("Skipping unsupported markdown block token '%s'.", token.type)
                index += 1

        return "\n\n".join(block for block in blocks if block != "")

    def _render_fence(
        self,
        token: Token,
    ) -> str:
        """
        Render a fenced code block, preserving its fence marker and
        language info string exactly.
        """
        marker = token.markup or "```"
        language = token.info.strip()

        lines = [f"{marker}{language}"]

        body = token.content.rstrip("\n")

        if body:
            lines.append(body)

        lines.append(marker)

        return "\n".join(lines)

    def _render_code_block(
        self,
        token: Token,
    ) -> str:
        """
        Render an indented code block, preserving the four-space
        indentation convention.
        """
        content = token.content.rstrip("\n")

        lines = [f"    {line}" if line else "" for line in content.split("\n")]

        return "\n".join(lines)

    def _render_list(
        self,
        tokens: list[Token],
        close_map: dict[int, int],
        open_index: int,
        close_index: int,
    ) -> str:
        """
        Render a bullet or ordered list, preserving nesting, mixed list
        types, and original ordered-list numbering.
        """
        ordered = tokens[open_index].type == "ordered_list_open"

        items: list[str] = []

        start_number = 1

        if ordered:
            attrs = tokens[open_index].attrs or {}
            start_number = int(attrs.get("start", 1))

        current_number = start_number

        index = open_index + 1

        while index < close_index:
            token = tokens[index]

            if token.type == "list_item_open":
                item_close = close_map[index]

                if ordered:
                    marker = f"{current_number}{token.markup or '.'}"
                    current_number += 1
                else:
                    marker = token.markup or "-"

                prefix = f"{marker} "

                inner = self._render_block_range(
                    tokens,
                    close_map,
                    index + 1,
                    item_close,
                )

                items.append(self._indent_continuation(inner, prefix))

                index = item_close + 1

            else:
                index += 1

        return "\n".join(items)

    def _render_table(
        self,
        tokens: list[Token],
        close_map: dict[int, int],
        open_index: int,
        close_index: int,
    ) -> str:
        """
        Reconstruct a markdown table, including column alignment, from
        its token stream rather than discarding it.
        """
        header_cells: list[str] = []
        alignments: list[str] = []
        body_rows: list[list[str]] = []

        index = open_index + 1

        while index < close_index:
            token = tokens[index]

            if token.type == "thead_open":
                thead_close = close_map[index]
                header_cells, alignments = self._render_table_header_row(
                    tokens,
                    close_map,
                    index,
                    thead_close,
                )
                index = thead_close + 1

            elif token.type == "tbody_open":
                tbody_close = close_map[index]
                body_rows = self._render_table_body_rows(
                    tokens,
                    close_map,
                    index,
                    tbody_close,
                )
                index = tbody_close + 1

            else:
                index += 1

        # Markdown requires a header row. If the parser produced a table without
        # one, treat the token stream as malformed instead of generating invalid
        # markdown.
        if not header_cells:
            raise ArticleStructureError(
                "Malformed markdown table: missing header row."
            )

        separator_cells = [
            self._alignment_to_separator(alignment)
            for alignment in alignments
        ]

        expected_columns = len(header_cells)

        for row_index, row in enumerate(body_rows, start=1):
            if len(row) != expected_columns:
                raise ArticleStructureError(
                    "Malformed markdown table: "
                    f"row {row_index} contains {len(row)} cell(s), "
                    f"expected {expected_columns}."
                )

        lines = [
            self._render_table_row(header_cells),
            self._render_table_row(separator_cells),
        ]

        lines.extend(
            self._render_table_row(row)
            for row in body_rows
        )

        return "\n".join(lines)

    def _render_table_header_row(
        self,
        tokens: list[Token],
        close_map: dict[int, int],
        thead_open: int,
        thead_close: int,
    ) -> tuple[list[str], list[str]]:
        """
        Extract header cell text and column alignment from a thead block.
        """
        cells: list[str] = []
        alignments: list[str] = []

        index = thead_open + 1

        while index < thead_close:
            token = tokens[index]

            if token.type == "th_open":
                th_close = close_map[index]
                inline = tokens[index + 1]

                cells.append(self._render_inline(inline).strip())
                alignments.append(self._extract_alignment(token))

                index = th_close + 1

            else:
                index += 1

        return cells, alignments

    def _render_table_body_rows(
        self,
        tokens: list[Token],
        close_map: dict[int, int],
        tbody_open: int,
        tbody_close: int,
    ) -> list[list[str]]:
        """
        Extract each row's cell text from a tbody block.
        """
        rows: list[list[str]] = []

        index = tbody_open + 1

        while index < tbody_close:
            token = tokens[index]

            if token.type == "tr_open":
                tr_close = close_map[index]

                rows.append(
                    self._render_table_row_cells(
                        tokens,
                        close_map,
                        index,
                        tr_close,
                    )
                )

                index = tr_close + 1

            else:
                index += 1

        return rows

    def _render_table_row_cells(
        self,
        tokens: list[Token],
        close_map: dict[int, int],
        tr_open: int,
        tr_close: int,
    ) -> list[str]:
        """
        Extract cell text from a single table row.
        """
        cells: list[str] = []

        index = tr_open + 1

        while index < tr_close:
            token = tokens[index]

            if token.type == "td_open":
                td_close = close_map[index]
                inline = tokens[index + 1]

                cells.append(self._render_inline(inline).strip())

                index = td_close + 1

            else:
                index += 1

        return cells
    
    def _escape_table_cell(
        self,
        text: str,
    ) -> str:
        """
        Escape characters that would otherwise break markdown table syntax.
        """
        return (
            text
            .replace("\\", "\\\\")
            .replace("|", "\\|")
        )

    def _extract_alignment(
        self,
        token: Token,
    ) -> str:
        """
        Extract column alignment ("left", "center", "right", or "") from
        a th/td token's inline style attribute.
        """
        style = token.attrs.get("style", "") if token.attrs else ""

        if "center" in style:
            return "center"

        if "right" in style:
            return "right"

        if "left" in style:
            return "left"

        return ""

    def _alignment_to_separator(
        self,
        alignment: str,
    ) -> str:
        """
        Convert a column alignment into its markdown separator cell.
        """
        if alignment == "center":
            return ":---:"

        if alignment == "right":
            return "---:"

        if alignment == "left":
            return ":---"

        return "---"

    def _render_table_row(
        self,
        cells: list[str],
    ) -> str:
        """
        Render a single markdown table row from cell text.
        """
        escaped_cells = [
            self._escape_table_cell(cell)
            for cell in cells
        ]

        return "| " + " | ".join(escaped_cells) + " |"

    def _prefix_lines(
        self,
        text: str,
        prefix: str,
    ) -> str:
        """
        Prefix every line of text with the given prefix, preserving blank
        lines without trailing whitespace.
        """
        lines = text.split("\n")

        return "\n".join(
            f"{prefix}{line}" if line else prefix.rstrip()
            for line in lines
        )
    
    def _render_inline(
        self,
        inline: Token,
    ) -> str:
        """
        Reconstruct inline markdown from an inline token, preserving
        emphasis, strong text, inline code, links, images, line breaks,
        HTML, and other inline formatting.
        """
        children = inline.children or []

        result: list[str] = []

        stack: list[tuple[str, str]] = []

        for token in children:
            t = token.type

            if t == "text":
                result.append(token.content)

            elif t == "softbreak":
                result.append("\n")

            elif t == "hardbreak":
                result.append("  \n")

            elif t == "code_inline":
                result.append(f"`{token.content}`")

            elif t == "em_open":
                result.append("*")
                stack.append(("em", "*"))

            elif t == "em_close":
                if not stack:
                    raise ArticleStructureError("Malformed inline markdown: unexpected emphasis closing token.")

                token_type, marker = stack.pop()
                if token_type != "em":
                    raise ArticleStructureError("Malformed inline markdown: mismatched emphasis closing token.")
                result.append(marker)

            elif t == "strong_open":
                result.append("**")
                stack.append(("strong", "**"))

            elif t == "strong_close":
                if not stack:
                    raise ArticleStructureError("Malformed inline markdown: unexpected strong closing token.")

                token_type, marker = stack.pop()
                if token_type != "strong":
                    raise ArticleStructureError("Malformed inline markdown: mismatched strong closing token.")
                result.append(marker)

            elif t == "s_open":
                result.append("~~")
                stack.append(("strike", "~~"))

            elif t == "s_close":
                if not stack:
                    raise ArticleStructureError("Malformed inline markdown: unexpected strikethrough closing token.")

                token_type, marker = stack.pop()
                if token_type != "strike":
                    raise ArticleStructureError("Malformed inline markdown: mismatched strikethrough closing token.")
                result.append(marker)

            elif t == "link_open":
                result.append("[")
                href = token.attrs.get("href", "") if token.attrs else ""
                stack.append(("link", href))

            elif t == "link_close":
                if not stack:
                    raise ArticleStructureError("Malformed inline markdown: unexpected link closing token.")

                token_type, href = stack.pop()
                if token_type != "link":
                    raise ArticleStructureError("Malformed inline markdown: mismatched link closing token.")
                result.append(f"]({href})")

            elif t == "image":
                alt = token.content
                src = token.attrs.get("src", "") if token.attrs else ""
                result.append(f"![{alt}]({src})")

            elif t == "html_inline":
                result.append(token.content)

            else:
                logger.warning("Skipping unsupported markdown inline token '%s'.", t)

        if stack:
            raise ArticleStructureError("Malformed inline markdown: unclosed inline formatting.")

        return "".join(result)

    def _indent_continuation(
        self,
        text: str,
        prefix: str,
    ) -> str:
        """
        Render a list item: the first line is prefixed with the list
        marker, and continuation lines (including nested blocks) are
        indented to align beneath the marker's content.
        """
        if not text:
            return prefix.rstrip()

        lines = text.split("\n")
        padding = " " * len(prefix)

        rendered = [f"{prefix}{lines[0]}" if lines[0] else prefix.rstrip()]

        for line in lines[1:]:
            rendered.append(f"{padding}{line}" if line else "")

        return "\n".join(rendered)