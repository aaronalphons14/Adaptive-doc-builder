"""Composite Pattern: Hierarchical Document Tree Representation.

Architectural Role:
    The Composite pattern structures raw government document content into a canonical,
    type-safe, in-memory tree hierarchy. Individual content primitives (paragraphs, table
    cells, headings) and branch containers (sections, tables, lists, the root document)
    share a unified `DocumentComponent` interface.

    This abstraction allows the Document Structure Signature (DSS) analyzer, format
    renderers, and post-render verifiers to traverse, evaluate, and transform complex
    nested document trees recursively without needing to know whether a given node is
    a single leaf element or an aggregate collection.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, List, Optional

from autodoc.core.models import BlockConfig, DocumentMetadata, EntityMatch
from autodoc.core.types import BlockType


class DocumentComponent(ABC):
    """Unified interface for all leaf and composite nodes in the document tree."""

    def __init__(
        self,
        block_type: BlockType,
        node_id: Optional[str] = None,
        config: Optional[BlockConfig] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.block_type = block_type
        self.node_id = node_id or str(uuid.uuid4())
        self.config = config or BlockConfig()
        self.metadata: Dict[str, Any] = metadata or {}
        self.parent: Optional[DocumentComponent] = None

    @abstractmethod
    def get_text_content(self) -> str:
        """Return the flattened plaintext representation of this node and its subtree."""
        pass

    @abstractmethod
    def get_children(self) -> List[DocumentComponent]:
        """Return direct child components."""
        pass

    def add(self, component: DocumentComponent) -> None:
        """Add child component (default no-op for leaf nodes)."""
        raise NotImplementedError(f"Cannot add child to leaf node of type {self.block_type}")

    def remove(self, component: DocumentComponent) -> None:
        """Remove child component."""
        raise NotImplementedError(f"Cannot remove child from leaf node of type {self.block_type}")

    def traverse(self) -> Iterator[DocumentComponent]:
        """Traverse the entire subtree rooted at this node in preorder."""
        yield self
        for child in self.get_children():
            yield from child.traverse()

    def depth(self) -> int:
        """Compute the maximum tree depth from this node down to leaves."""
        children = self.get_children()
        if not children:
            return 1
        return 1 + max(c.depth() for c in children)

    def count_nodes(self) -> int:
        """Count total nodes in this subtree."""
        return 1 + sum(c.count_nodes() for c in self.get_children())


class CompositeNode(DocumentComponent):
    """Base container component capable of holding children."""

    def __init__(
        self,
        block_type: BlockType,
        node_id: Optional[str] = None,
        config: Optional[BlockConfig] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(block_type, node_id, config, metadata)
        self.children: List[DocumentComponent] = []

    def add(self, component: DocumentComponent) -> None:
        component.parent = self
        self.children.append(component)

    def remove(self, component: DocumentComponent) -> None:
        if component in self.children:
            self.children.remove(component)
            component.parent = None

    def get_children(self) -> List[DocumentComponent]:
        return list(self.children)

    def get_text_content(self) -> str:
        return "\n".join(c.get_text_content() for c in self.children if c.get_text_content())


class DocumentNode(CompositeNode):
    """Root node representing an entire government document."""

    def __init__(
        self,
        doc_metadata: Optional[DocumentMetadata] = None,
        node_id: Optional[str] = None,
        config: Optional[BlockConfig] = None,
    ) -> None:
        super().__init__(BlockType.DOCUMENT, node_id, config)
        self.doc_metadata: DocumentMetadata = doc_metadata or DocumentMetadata()

    def get_text_content(self) -> str:
        parts = [f"Title: {self.doc_metadata.title}"]
        if self.doc_metadata.document_number:
            parts.append(f"Number: {self.doc_metadata.document_number}")
        body = super().get_text_content()
        if body:
            parts.append(body)
        return "\n".join(parts)


class SectionNode(CompositeNode):
    """Logical section or chapter within a document."""

    def __init__(
        self,
        title: str = "",
        section_number: Optional[str] = None,
        node_id: Optional[str] = None,
        config: Optional[BlockConfig] = None,
    ) -> None:
        super().__init__(BlockType.SECTION, node_id, config)
        self.title = title
        self.section_number = section_number

    def get_text_content(self) -> str:
        header = f"{self.section_number} {self.title}".strip() if self.section_number else self.title
        body = super().get_text_content()
        return f"{header}\n{body}".strip() if header else body


class SubsectionNode(CompositeNode):
    """Nested subsection within a main section."""

    def __init__(
        self,
        title: str = "",
        subsection_number: Optional[str] = None,
        node_id: Optional[str] = None,
        config: Optional[BlockConfig] = None,
    ) -> None:
        super().__init__(BlockType.SUBSECTION, node_id, config)
        self.title = title
        self.subsection_number = subsection_number

    def get_text_content(self) -> str:
        header = f"{self.subsection_number} {self.title}".strip() if self.subsection_number else self.title
        body = super().get_text_content()
        return f"{header}\n{body}".strip() if header else body


class HeadingNode(DocumentComponent):
    """Section or document header element."""

    def __init__(
        self,
        text: str,
        level: int = 1,
        node_id: Optional[str] = None,
        config: Optional[BlockConfig] = None,
    ) -> None:
        super().__init__(BlockType.HEADING, node_id, config)
        self.text = text
        self.level = max(1, min(6, level))

    def get_text_content(self) -> str:
        return self.text

    def get_children(self) -> List[DocumentComponent]:
        return []


class ParagraphNode(DocumentComponent):
    """Atomic text paragraph with potential sensitive entity detections."""

    def __init__(
        self,
        text: str,
        node_id: Optional[str] = None,
        config: Optional[BlockConfig] = None,
        entities: Optional[List[EntityMatch]] = None,
        is_bilingual: bool = False,
        secondary_text: Optional[str] = None,
    ) -> None:
        super().__init__(BlockType.PARAGRAPH, node_id, config)
        self.text = text
        self.entities: List[EntityMatch] = entities or []
        self.is_bilingual = is_bilingual
        self.secondary_text = secondary_text

    def get_text_content(self) -> str:
        if self.secondary_text:
            return f"{self.text} / {self.secondary_text}"
        return self.text

    def get_children(self) -> List[DocumentComponent]:
        return []


class TableCellNode(DocumentComponent):
    """Individual cell inside a table row."""

    def __init__(
        self,
        text: str,
        is_header: bool = False,
        col_span: int = 1,
        row_span: int = 1,
        node_id: Optional[str] = None,
        config: Optional[BlockConfig] = None,
    ) -> None:
        super().__init__(BlockType.TABLE_CELL, node_id, config)
        self.text = text
        self.is_header = is_header
        self.col_span = col_span
        self.row_span = row_span

    def get_text_content(self) -> str:
        return self.text

    def get_children(self) -> List[DocumentComponent]:
        return []


class TableRowNode(CompositeNode):
    """Row container holding table cells."""

    def __init__(
        self,
        is_header_row: bool = False,
        node_id: Optional[str] = None,
        config: Optional[BlockConfig] = None,
    ) -> None:
        super().__init__(BlockType.TABLE_ROW, node_id, config)
        self.is_header_row = is_header_row

    def get_cells(self) -> List[TableCellNode]:
        return [c for c in self.children if isinstance(c, TableCellNode)]

    def get_text_content(self) -> str:
        return "\t".join(c.get_text_content() for c in self.get_cells())


class TableNode(CompositeNode):
    """Tabular data element containing rows and columns."""

    def __init__(
        self,
        caption: Optional[str] = None,
        headers: Optional[List[str]] = None,
        node_id: Optional[str] = None,
        config: Optional[BlockConfig] = None,
    ) -> None:
        super().__init__(BlockType.TABLE, node_id, config)
        self.caption = caption
        self.headers = headers or []

    def get_rows(self) -> List[TableRowNode]:
        return [c for c in self.children if isinstance(c, TableRowNode)]

    def cell_count(self) -> int:
        return sum(len(r.get_cells()) for r in self.get_rows())

    def get_text_content(self) -> str:
        rows_text = "\n".join(r.get_text_content() for r in self.get_rows())
        return f"{self.caption}\n{rows_text}".strip() if self.caption else rows_text


class ListItemNode(DocumentComponent):
    """Single item in an ordered or unordered list."""

    def __init__(
        self,
        text: str,
        bullet: Optional[str] = None,
        node_id: Optional[str] = None,
        config: Optional[BlockConfig] = None,
    ) -> None:
        super().__init__(BlockType.LIST_ITEM, node_id, config)
        self.text = text
        self.bullet = bullet

    def get_text_content(self) -> str:
        prefix = f"{self.bullet} " if self.bullet else "- "
        return f"{prefix}{self.text}"

    def get_children(self) -> List[DocumentComponent]:
        return []


class ListNode(CompositeNode):
    """Container for list items."""

    def __init__(
        self,
        ordered: bool = False,
        node_id: Optional[str] = None,
        config: Optional[BlockConfig] = None,
    ) -> None:
        super().__init__(BlockType.LIST, node_id, config)
        self.ordered = ordered

    def get_items(self) -> List[ListItemNode]:
        return [c for c in self.children if isinstance(c, ListItemNode)]

    def get_text_content(self) -> str:
        return "\n".join(item.get_text_content() for item in self.get_items())


class SignatureNode(DocumentComponent):
    """Official government signatory block with designation, department, and seal."""

    def __init__(
        self,
        signatory_name: str,
        designation: str,
        department: str,
        date: Optional[str] = None,
        digital_signed: bool = False,
        sign_token: Optional[str] = None,
        node_id: Optional[str] = None,
        config: Optional[BlockConfig] = None,
    ) -> None:
        super().__init__(BlockType.SIGNATURE_BLOCK, node_id, config)
        self.signatory_name = signatory_name
        self.designation = designation
        self.department = department
        self.date = date
        self.digital_signed = digital_signed
        self.sign_token = sign_token

    def get_text_content(self) -> str:
        status = f"[Digitally Signed: {self.sign_token}]" if self.digital_signed else "[Signed]"
        return (
            f"{status}\n"
            f"{self.signatory_name}\n"
            f"{self.designation}\n"
            f"{self.department}\n"
            f"Date: {self.date or ''}".strip()
        )

    def get_children(self) -> List[DocumentComponent]:
        return []


class CalloutNode(DocumentComponent):
    """Highlighted statutory exemption, caution, or compliance advisory block."""

    def __init__(
        self,
        text: str,
        callout_type: str = "advisory", # advisory, warning, statutory
        citation: Optional[str] = None,
        node_id: Optional[str] = None,
        config: Optional[BlockConfig] = None,
    ) -> None:
        super().__init__(BlockType.CALLOUT, node_id, config)
        self.text = text
        self.callout_type = callout_type
        self.citation = citation

    def get_text_content(self) -> str:
        header = f"[{self.callout_type.upper()}: {self.citation}]" if self.citation else f"[{self.callout_type.upper()}]"
        return f"{header}\n{self.text}"

    def get_children(self) -> List[DocumentComponent]:
        return []
