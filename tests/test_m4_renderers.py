"""Tests for Milestone 4: Renderer Families (HTML, PDF, DOCX, Markdown), Patterns, and Indic Script."""


from autodoc.core.types import BlockType, OutputFormat
from autodoc.patterns.abstract_factory import (
    DocxRendererFactory,
    HtmlRendererFactory,
    MarkdownRendererFactory,
    PdfRendererFactory,
    get_renderer_factory,
)
from autodoc.patterns.adapter import (
    Jinja2HtmlAdapter,
    MarkdownAdapter,
    PythonDocxAdapter,
    WeasyPrintPdfAdapter,
)
from autodoc.patterns.bridge import (
    DocumentBridge,
    HtmlImplementor,
    MarkdownImplementor,
    PdfImplementor,
)
from autodoc.patterns.builder import PipelineContext
from autodoc.patterns.composite import DocumentNode
from autodoc.patterns.factory_method import BlockRendererFactory
from autodoc.synthesis.synthesizer import PipelineSynthesizer


def test_abstract_factory_pattern():
    """Verify Abstract Factory creates cohesive families of rendering products."""
    html_f = get_renderer_factory(OutputFormat.HTML)
    assert isinstance(html_f, HtmlRendererFactory)
    assert isinstance(html_f.create_adapter(), Jinja2HtmlAdapter)

    pdf_f = get_renderer_factory(OutputFormat.PDF)
    assert isinstance(pdf_f, PdfRendererFactory)
    assert isinstance(pdf_f.create_adapter(), WeasyPrintPdfAdapter)

    docx_f = get_renderer_factory(OutputFormat.DOCX)
    assert isinstance(docx_f, DocxRendererFactory)
    assert isinstance(docx_f.create_adapter(), PythonDocxAdapter)

    md_f = get_renderer_factory(OutputFormat.MARKDOWN)
    assert isinstance(md_f, MarkdownRendererFactory)
    assert isinstance(md_f.create_adapter(), MarkdownAdapter)


def test_factory_method_block_renderers(parsed_gov_order: DocumentNode):
    """Verify Factory Method instantiates appropriate block renderers."""
    h_ren = BlockRendererFactory.create_block_renderer(BlockType.HEADING)
    p_ren = BlockRendererFactory.create_block_renderer(BlockType.PARAGRAPH)
    t_ren = BlockRendererFactory.create_block_renderer(BlockType.TABLE)
    l_ren = BlockRendererFactory.create_block_renderer(BlockType.LIST)
    s_ren = BlockRendererFactory.create_block_renderer(BlockType.SIGNATURE_BLOCK)
    c_ren = BlockRendererFactory.create_block_renderer(BlockType.CALLOUT)

    assert "HeadingBlockRenderer" in type(h_ren).__name__
    assert "ParagraphBlockRenderer" in type(p_ren).__name__
    assert "TableBlockRenderer" in type(t_ren).__name__
    assert "ListBlockRenderer" in type(l_ren).__name__
    assert "SignatureBlockRenderer" in type(s_ren).__name__
    assert "CalloutBlockRenderer" in type(c_ren).__name__


def test_bridge_pattern_decoupling(parsed_tender: DocumentNode):
    """Verify Bridge pattern allows decoupled invocation across implementors."""
    bridge_html = DocumentBridge(parsed_tender, HtmlImplementor())
    art_html, _ = bridge_html.produce()
    assert "<!DOCTYPE html>" in art_html
    assert "NOTICE INVITING TENDER" in art_html

    bridge_pdf = DocumentBridge(parsed_tender, PdfImplementor())
    art_pdf, _ = bridge_pdf.produce()
    assert isinstance(art_pdf, bytes)
    assert art_pdf.startswith(b"%PDF")

    bridge_md = DocumentBridge(parsed_tender, MarkdownImplementor())
    art_md, _ = bridge_md.produce()
    assert "# NOTICE INVITING E-TENDER" in art_md


def test_all_five_sample_docs_render_to_all_formats(
    parsed_gov_order: DocumentNode,
    parsed_tender: DocumentNode,
    parsed_rti: DocumentNode,
    parsed_circular: DocumentNode,
    parsed_certificate: DocumentNode,
):
    """Acceptance Criterion 1: All 5 sample document types render to HTML, PDF, DOCX with zero code changes."""
    samples = [
        ("gov_order", parsed_gov_order),
        ("tender", parsed_tender),
        ("rti_reply", parsed_rti),
        ("circular", parsed_circular),
        ("certificate", parsed_certificate),
    ]

    html_adapter = Jinja2HtmlAdapter()
    pdf_adapter = WeasyPrintPdfAdapter()
    docx_adapter = PythonDocxAdapter()

    for name, doc in samples:
        # 1. HTML Rendering
        html_out, text_html = html_adapter.render(doc)
        assert isinstance(html_out, str)
        assert len(html_out) > 200
        assert "<!DOCTYPE html>" in html_out
        assert doc.doc_metadata.title in html_out or doc.doc_metadata.department in html_out

        # 2. PDF Rendering
        pdf_out, text_pdf = pdf_adapter.render(doc)
        assert isinstance(pdf_out, bytes)
        assert len(pdf_out) > 500
        assert pdf_out.startswith(b"%PDF"), f"Sample {name} failed PDF magic byte check"

        # 3. DOCX Rendering
        docx_out, text_docx = docx_adapter.render(doc)
        assert isinstance(docx_out, bytes)
        assert len(docx_out) > 1000
        assert docx_out.startswith(b"PK\x03\x04"), f"Sample {name} failed DOCX ZIP magic check"


def test_bilingual_indic_script_rendering(parsed_circular: DocumentNode):
    """Verify bilingual Hindi (Devanagari) rendering across HTML, PDF, and DOCX."""
    hindi_phrase = "नागरिक सुविधा केंद्रों"
    html_out, _ = Jinja2HtmlAdapter().render(parsed_circular)
    assert hindi_phrase in html_out

    # PDF rendering must succeed without UnicodeEncodeError
    pdf_out, _ = WeasyPrintPdfAdapter().render(parsed_circular)
    assert isinstance(pdf_out, bytes)
    assert len(pdf_out) > 1000

    # DOCX rendering must succeed without UnicodeEncodeError
    docx_out, _ = PythonDocxAdapter().render(parsed_circular)
    assert isinstance(docx_out, bytes)
    assert len(docx_out) > 1000


def test_pipeline_synthesizer_execution_with_renderers(parsed_gov_order: DocumentNode):
    """Verify end-to-end execution of a synthesized pipeline containing a renderer stage."""
    synthesizer = PipelineSynthesizer()
    res = synthesizer.synthesize(parsed_gov_order, {"format": "html"})

    context = PipelineContext(document=parsed_gov_order, dss=res.dss, options={"format": "html"})
    out_ctx = res.pipeline.execute(context)

    assert out_ctx.rendered_artifact is not None
    assert "<!DOCTYPE html>" in out_ctx.rendered_artifact
    assert "HtmlRendererStage" in out_ctx.stage_results
    assert out_ctx.stage_results["HtmlRendererStage"]["status"] == "rendered"
