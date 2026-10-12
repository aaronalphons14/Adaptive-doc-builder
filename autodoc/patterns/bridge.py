"""Bridge Pattern: Decoupling Document Content Abstraction from Rendering Implementation.

Architectural Role:
    The Bridge pattern decouples the document domain model hierarchy (e.g. Government Orders,
    Tender Notices, RTI Replies, Public Circulars, and Certificates) from the rendering
    format implementation hierarchy (HTML, PDF, DOCX, Markdown).

    By placing a Bridge between the domain-specific business abstractions and the low-level
    renderer primitives, both dimensions can evolve independently:
    - New government document types can be introduced without changing rendering drivers.
    - New output formats can be supported without rewriting domain-specific document logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple, Union

from autodoc.patterns.adapter import (
    Jinja2HtmlAdapter,
    MarkdownAdapter,
    PythonDocxAdapter,
    WeasyPrintPdfAdapter,
)
from autodoc.patterns.composite import DocumentNode


class IRendererImplementor(ABC):
    """The Implementor interface defining low-level rendering driver operations."""

    @abstractmethod
    def render_tree(
        self, doc: DocumentNode, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[Union[str, bytes], str]:
        """Execute rendering of the document tree."""
        pass


class HtmlImplementor(IRendererImplementor):
    """Concrete implementor for HTML5 rendering."""
    def __init__(self) -> None:
        self.adapter = Jinja2HtmlAdapter()

    def render_tree(
        self, doc: DocumentNode, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        return self.adapter.render(doc, options)


class PdfImplementor(IRendererImplementor):
    """Concrete implementor for PDF rendering."""
    def __init__(self) -> None:
        self.adapter = WeasyPrintPdfAdapter()

    def render_tree(
        self, doc: DocumentNode, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[bytes, str]:
        return self.adapter.render(doc, options)


class DocxImplementor(IRendererImplementor):
    """Concrete implementor for DOCX rendering."""
    def __init__(self) -> None:
        self.adapter = PythonDocxAdapter()

    def render_tree(
        self, doc: DocumentNode, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[bytes, str]:
        return self.adapter.render(doc, options)


class MarkdownImplementor(IRendererImplementor):
    """Concrete implementor for Markdown rendering."""
    def __init__(self) -> None:
        self.adapter = MarkdownAdapter()

    def render_tree(
        self, doc: DocumentNode, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        return self.adapter.render(doc, options)


class DocumentBridge:
    """The Abstraction: maintains a reference to an IRendererImplementor and coordinates output."""

    def __init__(self, doc: DocumentNode, implementor: IRendererImplementor) -> None:
        self.doc = doc
        self.implementor = implementor

    def produce(self, options: Optional[Dict[str, Any]] = None) -> Tuple[Union[str, bytes], str]:
        """Bridge method: delegates rendering to the concrete implementor."""
        return self.implementor.render_tree(self.doc, options)


class GovernmentOrderDocumentBridge(DocumentBridge):
    """Refined Abstraction for Government Orders."""
    pass


class TenderNoticeDocumentBridge(DocumentBridge):
    """Refined Abstraction for Tender Notices."""
    pass


class RtiReplyDocumentBridge(DocumentBridge):
    """Refined Abstraction for RTI Replies."""
    pass


class PublicCircularDocumentBridge(DocumentBridge):
    """Refined Abstraction for Public Circulars."""
    pass


class CertificateDocumentBridge(DocumentBridge):
    """Refined Abstraction for Official Certificates."""
    pass
