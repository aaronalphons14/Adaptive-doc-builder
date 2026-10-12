"""Abstract Factory Pattern: Renderer Family per Output Format.

Architectural Role:
    The Abstract Factory pattern declares an interface for creating complete families
    of format-specific rendering products (DocumentRendererAdapter, LayoutManager,
    and TypographyEngine) without coupling clients to concrete classes.

    Each supported output format corresponds to a concrete factory:
    - HtmlRendererFactory: produces HTML5 adapter, CSS grid layout manager, and web typography engine.
    - PdfRendererFactory: produces PDF adapter (with Indic font fallbacks), page box layout manager, and print typography engine.
    - DocxRendererFactory: produces Word adapter, document body layout manager, and XML run typography engine.
    - MarkdownRendererFactory: produces Markdown adapter, plain layout manager, and ASCII typography engine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from autodoc.core.types import OutputFormat
from autodoc.patterns.adapter import (
    IDocumentRendererAdapter,
    Jinja2HtmlAdapter,
    MarkdownAdapter,
    PythonDocxAdapter,
    WeasyPrintPdfAdapter,
)


class ILayoutManager(ABC):
    """Abstract Product: Manages page dimensions, margins, and geometric flow."""

    @abstractmethod
    def configure_margins(self, top: float, right: float, bottom: float, left: float) -> Dict[str, Any]:
        pass


class ITypographyEngine(ABC):
    """Abstract Product: Manages font embedding, fallbacks, and text styling."""

    @abstractmethod
    def resolve_font(self, font_name: str, fallback: str) -> str:
        pass


class HtmlLayoutManager(ILayoutManager):
    def configure_margins(self, top: float, right: float, bottom: float, left: float) -> Dict[str, Any]:
        return {"css_margin": f"{top}mm {right}mm {bottom}mm {left}mm"}


class HtmlTypographyEngine(ITypographyEngine):
    def resolve_font(self, font_name: str, fallback: str) -> str:
        return f"'{font_name}', '{fallback}', sans-serif"


class PdfLayoutManager(ILayoutManager):
    def configure_margins(self, top: float, right: float, bottom: float, left: float) -> Dict[str, Any]:
        return {"page_size": "A4", "margin_top": top, "margin_bottom": bottom}


class PdfTypographyEngine(ITypographyEngine):
    def resolve_font(self, font_name: str, fallback: str) -> str:
        return "NotoSansDevanagari" if "devanagari" in font_name.lower() or "hindi" in font_name.lower() else font_name


class DocxLayoutManager(ILayoutManager):
    def configure_margins(self, top: float, right: float, bottom: float, left: float) -> Dict[str, Any]:
        return {"inches_top": top / 25.4, "inches_bottom": bottom / 25.4}


class DocxTypographyEngine(ITypographyEngine):
    def resolve_font(self, font_name: str, fallback: str) -> str:
        return font_name or fallback


class MarkdownLayoutManager(ILayoutManager):
    def configure_margins(self, top: float, right: float, bottom: float, left: float) -> Dict[str, Any]:
        return {"max_line_width": 80}


class MarkdownTypographyEngine(ITypographyEngine):
    def resolve_font(self, font_name: str, fallback: str) -> str:
        return "monospace"


class DocumentRendererFactory(ABC):
    """Abstract Factory interface declaring factory methods for format products."""

    @abstractmethod
    def create_adapter(self) -> IDocumentRendererAdapter:
        pass

    @abstractmethod
    def create_layout_manager(self) -> ILayoutManager:
        pass

    @abstractmethod
    def create_typography_engine(self) -> ITypographyEngine:
        pass


class HtmlRendererFactory(DocumentRendererFactory):
    def create_adapter(self) -> IDocumentRendererAdapter:
        return Jinja2HtmlAdapter()

    def create_layout_manager(self) -> ILayoutManager:
        return HtmlLayoutManager()

    def create_typography_engine(self) -> ITypographyEngine:
        return HtmlTypographyEngine()


class PdfRendererFactory(DocumentRendererFactory):
    def create_adapter(self) -> IDocumentRendererAdapter:
        return WeasyPrintPdfAdapter()

    def create_layout_manager(self) -> ILayoutManager:
        return PdfLayoutManager()

    def create_typography_engine(self) -> ITypographyEngine:
        return PdfTypographyEngine()


class DocxRendererFactory(DocumentRendererFactory):
    def create_adapter(self) -> IDocumentRendererAdapter:
        return PythonDocxAdapter()

    def create_layout_manager(self) -> ILayoutManager:
        return DocxLayoutManager()

    def create_typography_engine(self) -> ITypographyEngine:
        return DocxTypographyEngine()


class MarkdownRendererFactory(DocumentRendererFactory):
    def create_adapter(self) -> IDocumentRendererAdapter:
        return MarkdownAdapter()

    def create_layout_manager(self) -> ILayoutManager:
        return MarkdownLayoutManager()

    def create_typography_engine(self) -> ITypographyEngine:
        return MarkdownTypographyEngine()


def get_renderer_factory(output_format: OutputFormat) -> DocumentRendererFactory:
    """Helper to retrieve the appropriate Abstract Factory for an output format."""
    if output_format == OutputFormat.HTML:
        return HtmlRendererFactory()
    elif output_format == OutputFormat.PDF:
        return PdfRendererFactory()
    elif output_format == OutputFormat.DOCX:
        return DocxRendererFactory()
    elif output_format == OutputFormat.MARKDOWN:
        return MarkdownRendererFactory()
    else:
        return HtmlRendererFactory()
