"""Factory Method Pattern: Block-Level Rendering Instantiation.

Architectural Role:
    The Factory Method pattern defines an interface for creating individual block-level
    renderers, deferring the concrete instantiation decision to specialized factory methods
    based on the Composite tree node's `BlockType`.

    This encapsulates element-specific rendering rules (e.g. how headings, tables, callouts,
    and digital signatures are formatted) and enables adding new document block types
    (e.g. Charts, Barcodes, Financial Ledgers) by creating new block renderers without
    modifying client rendering pipelines.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from autodoc.core.types import BlockType
from autodoc.patterns.composite import (
    CalloutNode,
    DocumentComponent,
    HeadingNode,
    ListNode,
    ParagraphNode,
    SignatureNode,
    TableNode,
)


class IBlockRenderer(ABC):
    """Abstract Product interface for rendering individual document blocks."""

    @abstractmethod
    def render(self, component: DocumentComponent, context: Optional[Dict[str, Any]] = None) -> str:
        """Render the component into its textual or markup representation."""
        pass


class HeadingBlockRenderer(IBlockRenderer):
    def render(self, component: DocumentComponent, context: Optional[Dict[str, Any]] = None) -> str:
        if isinstance(component, HeadingNode):
            return f"<h{component.level}>{component.text}</h{component.level}>"
        return f"<h1>{component.get_text_content()}</h1>"


class ParagraphBlockRenderer(IBlockRenderer):
    def render(self, component: DocumentComponent, context: Optional[Dict[str, Any]] = None) -> str:
        if isinstance(component, ParagraphNode):
            if component.is_bilingual and component.secondary_text:
                return (
                    f"<p class=\"bilingual-primary\">{component.text}</p>"
                    f"<p class=\"bilingual-secondary\">{component.secondary_text}</p>"
                )
            return f"<p>{component.text}</p>"
        return f"<p>{component.get_text_content()}</p>"


class TableBlockRenderer(IBlockRenderer):
    def render(self, component: DocumentComponent, context: Optional[Dict[str, Any]] = None) -> str:
        if isinstance(component, TableNode):
            lines = ["<table class=\"gov-table\">"]
            if component.caption:
                lines.append(f"  <caption>{component.caption}</caption>")
            for row in component.get_rows():
                lines.append("  <tr>")
                for cell in row.get_cells():
                    tag = "th" if cell.is_header else "td"
                    lines.append(f"    <{tag}>{cell.text}</{tag}>")
                lines.append("  </tr>")
            lines.append("</table>")
            return "\n".join(lines)
        return ""


class ListBlockRenderer(IBlockRenderer):
    def render(self, component: DocumentComponent, context: Optional[Dict[str, Any]] = None) -> str:
        if isinstance(component, ListNode):
            tag = "ol" if component.ordered else "ul"
            lines = [f"<{tag}>"]
            for item in component.get_items():
                lines.append(f"  <li>{item.text}</li>")
            lines.append(f"</{tag}>")
            return "\n".join(lines)
        return ""


class SignatureBlockRenderer(IBlockRenderer):
    def render(self, component: DocumentComponent, context: Optional[Dict[str, Any]] = None) -> str:
        if isinstance(component, SignatureNode):
            status = (
                f"<span class=\"digital-seal\">Digitally Signed: {component.sign_token}</span>"
                if component.digital_signed
                else "<span class=\"signed-seal\">Signed</span>"
            )
            return (
                f"<div class=\"signature-block\">\n"
                f"  {status}\n"
                f"  <p class=\"sig-name\"><strong>{component.signatory_name}</strong></p>\n"
                f"  <p class=\"sig-desig\">{component.designation}</p>\n"
                f"  <p class=\"sig-dept\">{component.department}</p>\n"
                f"  <p class=\"sig-date\">Date: {component.date or ''}</p>\n"
                f"</div>"
            )
        return ""


class CalloutBlockRenderer(IBlockRenderer):
    def render(self, component: DocumentComponent, context: Optional[Dict[str, Any]] = None) -> str:
        if isinstance(component, CalloutNode):
            cit = f"<span class=\"statutory-ref\">[{component.citation}]</span> " if component.citation else ""
            return (
                f"<div class=\"gov-callout callout-{component.callout_type}\">\n"
                f"  <p>{cit}{component.text}</p>\n"
                f"</div>"
            )
        return ""


class BlockRendererFactory:
    """Creator class defining the Factory Method for block renderers."""

    @classmethod
    def create_block_renderer(cls, block_type: BlockType) -> IBlockRenderer:
        """The Factory Method: returns appropriate block renderer for given BlockType."""
        if block_type == BlockType.HEADING:
            return HeadingBlockRenderer()
        elif block_type == BlockType.PARAGRAPH:
            return ParagraphBlockRenderer()
        elif block_type == BlockType.TABLE:
            return TableBlockRenderer()
        elif block_type == BlockType.LIST:
            return ListBlockRenderer()
        elif block_type == BlockType.SIGNATURE_BLOCK:
            return SignatureBlockRenderer()
        elif block_type == BlockType.CALLOUT:
            return CalloutBlockRenderer()
        else:
            return ParagraphBlockRenderer()
