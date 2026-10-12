"""Adapter Pattern: Unifying Third-Party Rendering Engines.

Architectural Role:
    The Adapter pattern translates incompatible third-party interfaces (Jinja2 for HTML,
    WeasyPrint / ReportLab for PDF, and python-docx for DOCX) into a uniform, format-agnostic
    `IDocumentRendererAdapter` contract.

    This insulates the synthesis engine, pipeline stages, and verifiers from third-party
    library API details. Furthermore, the PDF adapter implements environment-resilient
    adaptation: if WeasyPrint encounters platform-specific native dynamic library issues
    (common on Windows), it seamlessly and transparently adapts via ReportLab to produce
    genuine PDFs with full Indic Unicode font support.
"""

from __future__ import annotations

import io
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from jinja2 import Environment, FileSystemLoader

from autodoc.patterns.composite import (
    CalloutNode,
    DocumentNode,
    HeadingNode,
    ListNode,
    ParagraphNode,
    SectionNode,
    SignatureNode,
    TableNode,
)


class IDocumentRendererAdapter(ABC):
    """Uniform adapter interface for rendering document trees into target formats."""

    @abstractmethod
    def render(
        self, doc: DocumentNode, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[Union[str, bytes], str]:
        """Render the document tree.

        Returns:
            Tuple of:
            - Rendered output artifact (str for HTML/Markdown, bytes for PDF/DOCX)
            - Flattened plaintext representation for post-render compliance re-scanning
        """
        pass


class Jinja2HtmlAdapter(IDocumentRendererAdapter):
    """Adapts Jinja2 templating engine to produce accessible semantic HTML5."""

    def __init__(self, templates_dir: Optional[Path] = None) -> None:
        if templates_dir is None:
            templates_dir = Path(__file__).parent.parent / "renderers" / "templates"
        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True,
        )

    def render(
        self, doc: DocumentNode, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        options = options or {}
        template_name = "base.html"

        doc_type_val = doc.doc_metadata.doc_type.value
        candidate_template = f"{doc_type_val}.html"
        if (self.templates_dir / candidate_template).exists():
            template_name = candidate_template

        template = self.env.get_template(template_name)
        watermark_text = options.get("watermark_text")
        if not watermark_text and doc.doc_metadata.classification.value != "unclassified":
            watermark_text = doc.doc_metadata.classification.value.upper()

        rendered_html = template.render(
            doc=doc,
            metadata=doc.doc_metadata,
            nodes=list(doc.get_children()),
            options=options,
            watermark_text=watermark_text,
            is_bilingual=len(doc.doc_metadata.languages) > 1,
        )

        plain_text = doc.get_text_content()
        return rendered_html, plain_text


class ReportLabPdfAdapter(IDocumentRendererAdapter):
    """Adapts ReportLab to generate genuine PDF documents with Indic font support."""

    def __init__(self) -> None:
        self.font_registered = False
        self._setup_fonts()

    def _setup_fonts(self) -> None:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        font_path = Path(__file__).parent.parent / "assets" / "fonts" / "NotoSansDevanagari-Regular.ttf"
        if font_path.exists():
            try:
                pdfmetrics.registerFont(TTFont("NotoSansDevanagari", str(font_path)))
                self.font_registered = True
            except Exception:
                self.font_registered = False

    def render(
        self, doc: DocumentNode, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[bytes, str]:
        from reportlab.lib.colors import HexColor
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import (
            HRFlowable,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
        )

        options = options or {}
        buf = io.BytesIO()
        pdf = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=40,
            rightMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        font_name = "NotoSansDevanagari" if self.font_registered else "Helvetica"
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "GovTitle",
            parent=styles["Heading1"],
            fontName=font_name,
            fontSize=15,
            leading=18,
            textColor=HexColor("#1e3a8a"),
            alignment=1, # Center
        )
        subtitle_style = ParagraphStyle(
            "GovSubtitle",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=10,
            leading=13,
            textColor=HexColor("#4b5563"),
            alignment=1,
        )
        body_style = ParagraphStyle(
            "GovBody",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=10,
            leading=14,
            textColor=HexColor("#111827"),
        )
        h2_style = ParagraphStyle(
            "GovH2",
            parent=styles["Heading2"],
            fontName=font_name,
            fontSize=12,
            leading=15,
            textColor=HexColor("#1e3a8a"),
            spaceBefore=8,
            spaceAfter=4,
        )

        story: List[Any] = []

        # Government Header / Emblem
        meta = doc.doc_metadata
        story.append(Paragraph(meta.title.upper(), title_style))
        story.append(Spacer(1, 4))
        if meta.document_number:
            story.append(Paragraph(f"<b>No:</b> {meta.document_number} | <b>Date:</b> {meta.date}", subtitle_style))
        story.append(Paragraph(f"{meta.department} — {meta.jurisdiction}", subtitle_style))
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#cbd5e1"), spaceAfter=10))

        # Watermark notice if classified
        watermark = options.get("watermark_text")
        if not watermark and meta.classification.value != "unclassified":
            watermark = meta.classification.value.upper()
        if watermark:
            wm_style = ParagraphStyle(
                "Watermark",
                parent=styles["Normal"],
                fontName=font_name,
                fontSize=14,
                leading=16,
                textColor=HexColor("#dc2626"),
                alignment=1,
            )
            story.append(Paragraph(f"*** {watermark} ***", wm_style))
            story.append(Spacer(1, 8))

        # Render composite children
        for node in doc.get_children():
            self._render_node_rl(node, story, font_name, body_style, h2_style)

        pdf.build(story)
        pdf_bytes = buf.getvalue()
        plain_text = doc.get_text_content()
        return pdf_bytes, plain_text

    def _render_node_rl(
        self,
        node: Any,
        story: List[Any],
        font_name: str,
        body_style: Any,
        h2_style: Any,
    ) -> None:
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import Paragraph, Spacer, TableStyle
        from reportlab.platypus import Table as RLTable

        if isinstance(node, HeadingNode):
            story.append(Paragraph(node.text, h2_style))
            story.append(Spacer(1, 4))

        elif isinstance(node, SectionNode):
            sec_title = f"{node.section_number} {node.title}".strip() if node.section_number else node.title
            if sec_title:
                story.append(Paragraph(sec_title, h2_style))
            for child in node.get_children():
                self._render_node_rl(child, story, font_name, body_style, h2_style)

        elif isinstance(node, ParagraphNode):
            txt = node.text
            if node.is_bilingual and node.secondary_text:
                txt = f"{node.text}<br/><font color='#4b5563'>{node.secondary_text}</font>"
            story.append(Paragraph(txt, body_style))
            story.append(Spacer(1, 6))

        elif isinstance(node, TableNode):
            data: List[List[Any]] = []
            for row in node.get_rows():
                r_cells = [Paragraph(c.text, body_style) for c in row.get_cells()]
                data.append(r_cells)
            if data:
                t = RLTable(data, colWidths=None)
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#f1f5f9")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), HexColor("#111827")),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, -1), font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
                ]))
                story.append(t)
                story.append(Spacer(1, 8))

        elif isinstance(node, ListNode):
            for item in node.get_items():
                story.append(Paragraph(f"• {item.text}", body_style))
                story.append(Spacer(1, 3))
            story.append(Spacer(1, 4))

        elif isinstance(node, CalloutNode):
            header = f"<b>{node.callout_type.upper()}: {node.citation or ''}</b><br/>"
            story.append(Paragraph(f"{header}{node.text}", body_style))
            story.append(Spacer(1, 6))

        elif isinstance(node, SignatureNode):
            sig_text = (
                f"<b>{node.signatory_name}</b><br/>"
                f"{node.designation}<br/>"
                f"{node.department}<br/>"
                f"Date: {node.date or ''}"
            )
            if node.digital_signed:
                sig_text += f"<br/><font color='#16a34a'>[Digitally Signed: {node.sign_token}]</font>"
            story.append(Spacer(1, 10))
            story.append(Paragraph(sig_text, body_style))
            story.append(Spacer(1, 6))


class WeasyPrintPdfAdapter(IDocumentRendererAdapter):
    """Adapts WeasyPrint for CSS-paged PDF output, with transparent ReportLab fallback."""

    def __init__(self) -> None:
        self.html_adapter = Jinja2HtmlAdapter()
        self.fallback_adapter = ReportLabPdfAdapter()

    def render(
        self, doc: DocumentNode, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[bytes, str]:
        options = options or {}
        html_str, plain_text = self.html_adapter.render(doc, options)

        # Attempt WeasyPrint native render
        try:
            import weasyprint  # type: ignore
            html_obj = weasyprint.HTML(string=html_str)
            pdf_bytes = html_obj.write_pdf()
            return pdf_bytes, plain_text
        except (ImportError, OSError, Exception):
            # Native GTK/Cairo libraries absent on Windows -> Transparent Fallback via ReportLab
            return self.fallback_adapter.render(doc, options)


class PythonDocxAdapter(IDocumentRendererAdapter):
    """Adapts python-docx library to generate Microsoft Word (.docx) documents."""

    def render(
        self, doc: DocumentNode, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[bytes, str]:
        import docx  # type: ignore
        from docx.shared import Pt, RGBColor  # type: ignore

        docx_doc = docx.Document()
        meta = doc.doc_metadata

        # Title
        title_p = docx_doc.add_heading(level=1)
        r = title_p.add_run(meta.title)
        r.font.size = Pt(16)
        r.font.bold = True
        r.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

        # Metadata Header
        meta_p = docx_doc.add_paragraph()
        if meta.document_number:
            meta_p.add_run(f"No: {meta.document_number} | Date: {meta.date}\n").bold = True
        meta_p.add_run(f"{meta.department} — {meta.jurisdiction}")

        # Classification notice
        watermark = (options or {}).get("watermark_text")
        if not watermark and meta.classification.value != "unclassified":
            watermark = meta.classification.value.upper()
        if watermark:
            wm_p = docx_doc.add_paragraph()
            wm_run = wm_p.add_run(f"*** CLASSIFICATION: {watermark} ***")
            wm_run.font.bold = True
            wm_run.font.color.rgb = RGBColor(0xDC, 0x26, 0x26)

        # Children
        for node in doc.get_children():
            self._render_node_docx(node, docx_doc)

        buf = io.BytesIO()
        docx_doc.save(buf)
        plain_text = doc.get_text_content()
        return buf.getvalue(), plain_text

    def _render_node_docx(self, node: Any, docx_doc: Any) -> None:
        if isinstance(node, HeadingNode):
            docx_doc.add_heading(node.text, level=min(3, node.level))

        elif isinstance(node, SectionNode):
            sec_title = f"{node.section_number} {node.title}".strip() if node.section_number else node.title
            if sec_title:
                docx_doc.add_heading(sec_title, level=2)
            for child in node.get_children():
                self._render_node_docx(child, docx_doc)

        elif isinstance(node, ParagraphNode):
            p = docx_doc.add_paragraph()
            p.add_run(node.text)
            if node.is_bilingual and node.secondary_text:
                p.add_run(f"\n{node.secondary_text}").italic = True

        elif isinstance(node, TableNode):
            rows = node.get_rows()
            if rows:
                col_count = len(rows[0].get_cells())
                table = docx_doc.add_table(rows=len(rows), cols=col_count)
                table.style = "Table Grid"
                for r_idx, row in enumerate(rows):
                    for c_idx, cell in enumerate(row.get_cells()):
                        if c_idx < col_count:
                            table.cell(r_idx, c_idx).text = cell.text

        elif isinstance(node, ListNode):
            for item in node.get_items():
                docx_doc.add_paragraph(item.text, style="List Bullet")

        elif isinstance(node, CalloutNode):
            p = docx_doc.add_paragraph()
            p.add_run(f"[{node.callout_type.upper()}: {node.citation or ''}] ").bold = True
            p.add_run(node.text)

        elif isinstance(node, SignatureNode):
            p = docx_doc.add_paragraph()
            p.add_run(f"\n{node.signatory_name}\n").bold = True
            p.add_run(f"{node.designation}\n{node.department}\nDate: {node.date or ''}")
            if node.digital_signed:
                p.add_run(f"\n[Digitally Signed: {node.sign_token}]").italic = True


class MarkdownAdapter(IDocumentRendererAdapter):
    """Adapts canonical Markdown output format (demonstrates Open/Closed extension)."""

    def render(
        self, doc: DocumentNode, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        lines: List[str] = []
        meta = doc.doc_metadata

        lines.append(f"# {meta.title}\n")
        if meta.document_number:
            lines.append(f"**Document Number:** {meta.document_number}  ")
        lines.append(f"**Department:** {meta.department}  ")
        lines.append(f"**Date:** {meta.date}  ")
        lines.append(f"**Classification:** {meta.classification.value.upper()}\n")
        lines.append("---\n")

        for node in doc.get_children():
            self._render_node_md(node, lines)

        md_content = "\n".join(lines)
        plain_text = doc.get_text_content()
        return md_content, plain_text

    def _render_node_md(self, node: Any, lines: List[str]) -> None:
        if isinstance(node, HeadingNode):
            hashes = "#" * min(6, node.level + 1)
            lines.append(f"\n{hashes} {node.text}\n")

        elif isinstance(node, SectionNode):
            sec_title = f"{node.section_number} {node.title}".strip() if node.section_number else node.title
            lines.append(f"\n## {sec_title}\n")
            for child in node.get_children():
                self._render_node_md(child, lines)

        elif isinstance(node, ParagraphNode):
            lines.append(node.text)
            if node.is_bilingual and node.secondary_text:
                lines.append(f"*{node.secondary_text}*")
            lines.append("")

        elif isinstance(node, TableNode):
            rows = node.get_rows()
            if rows:
                headers = [c.text for c in rows[0].get_cells()]
                lines.append("| " + " | ".join(headers) + " |")
                lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
                for r in rows[1:]:
                    cells = [c.text for c in r.get_cells()]
                    lines.append("| " + " | ".join(cells) + " |")
                lines.append("")

        elif isinstance(node, ListNode):
            for item in node.get_items():
                lines.append(f"- {item.text}")
            lines.append("")

        elif isinstance(node, CalloutNode):
            cit = f" [{node.citation}]" if node.citation else ""
            lines.append(f"> **{node.callout_type.upper()}{cit}**: {node.text}\n")

        elif isinstance(node, SignatureNode):
            lines.append(f"\n[Sd/-]\n**{node.signatory_name}**  \n{node.designation}  \n{node.department}  ")
            if node.digital_signed:
                lines.append(f"*Digitally Signed: {node.sign_token}*  ")
            lines.append("")
