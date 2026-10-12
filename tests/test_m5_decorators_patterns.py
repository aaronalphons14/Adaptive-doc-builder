"""Tests for Milestone 5: Decorator Stack, Flyweight, Prototype, Proxy, and Pipeline Memory."""

from pathlib import Path

from autodoc.analysis.parser import parse_document
from autodoc.core.models import BlockConfig
from autodoc.core.types import Classification
from autodoc.patterns.adapter import Jinja2HtmlAdapter
from autodoc.patterns.builder import PipelineContext
from autodoc.patterns.composite import DocumentNode
from autodoc.patterns.decorator import (
    AccessibilityDecorator,
    CitationDecorator,
    PageNumberingDecorator,
    RedactionDecorator,
    WatermarkDecorator,
)
from autodoc.patterns.flyweight import StyleFlyweightFactory
from autodoc.patterns.prototype import BlockConfigPrototype, PipelinePrototype
from autodoc.patterns.proxy import CachedRendererProxy
from autodoc.synthesis.memory import PipelineMemory
from autodoc.synthesis.synthesizer import PipelineSynthesizer


def test_decorator_pattern_stack_execution(parsed_rti: DocumentNode):
    """Verify Decorator hierarchy modifies context and document tree orthogonally."""
    # 1. RedactionDecorator
    redaction_dec = RedactionDecorator()
    context = PipelineContext(document=parsed_rti)
    context = redaction_dec.execute(context)

    res_redact = context.stage_results["RedactionDecorator"]
    assert res_redact["status"] == "completed"
    assert res_redact["redactions_applied"] >= 3

    # Document tree must reflect masked values
    tree_text = parsed_rti.get_text_content()
    assert "XXXX-XXXX-" in tree_text
    assert "5489 2104 7832" not in tree_text

    # 2. WatermarkDecorator
    parsed_rti.doc_metadata.classification = Classification.CONFIDENTIAL
    wm_dec = WatermarkDecorator()
    context = wm_dec.execute(context)
    assert context.options["watermark_text"] == "CONFIDENTIAL"

    # 3. CitationDecorator
    cite_dec = CitationDecorator()
    context = cite_dec.execute(context)
    assert context.stage_results["CitationDecorator"]["citations_processed"] >= 1

    # 4. PageNumberingDecorator
    page_dec = PageNumberingDecorator()
    context = page_dec.execute(context)
    assert context.options["page_number_format"] == "Page {page} of {total}"

    # 5. AccessibilityDecorator
    acc_dec = AccessibilityDecorator()
    context = acc_dec.execute(context)
    assert context.options["enable_semantic_tags"] is True
    assert context.options["wcag_level"] == "AA"


def test_flyweight_pattern_style_pooling():
    """Verify StyleFlyweightFactory shares identical immutable style objects."""
    factory = StyleFlyweightFactory()

    # Request identical style multiple times
    style1 = factory.get_style(font_size_pt=12.0, bold=True, text_color="#1e3a8a")
    style2 = factory.get_style(font_size_pt=12.0, bold=True, text_color="#1e3a8a")

    # Must return the exact same instance in memory
    assert style1 is style2
    assert style1.to_css() == style2.to_css()

    # Requesting a different style creates a second entry
    style3 = factory.get_style(font_size_pt=14.0, bold=False, text_color="#dc2626")
    assert style3 is not style1

    # Simulate 500 nodes reusing style1
    for _ in range(500):
        s = factory.get_style(font_size_pt=12.0, bold=True, text_color="#1e3a8a")
        assert s is style1

    stats = factory.stats()
    assert stats["pooled_objects"] == 2
    assert stats["hits"] >= 500


def test_prototype_pattern_block_config_and_pipeline():
    """Verify Prototype cloning for both block configs and whole pipelines."""
    # 1. BlockConfigPrototype
    orig_config = BlockConfig(style_name="gov_card", font_size_pt=11.0, bold=True)
    proto_config = BlockConfigPrototype(orig_config)
    cloned_config = proto_config.clone(font_size_pt=13.0)

    assert cloned_config.style_name == "gov_card"
    assert cloned_config.bold is True
    assert cloned_config.font_size_pt == 13.0
    assert orig_config.font_size_pt == 11.0 # Original unchanged

    # 2. PipelinePrototype
    synthesizer = PipelineSynthesizer()
    res = synthesizer.synthesize(DocumentNode())
    proto_pipeline = PipelinePrototype(res.pipeline)
    cloned_pipeline = proto_pipeline.clone()

    assert len(cloned_pipeline.stages) == len(res.pipeline.stages)
    assert cloned_pipeline is not res.pipeline
    # Stages must be distinct cloned instances
    assert cloned_pipeline.stages[0] is not res.pipeline.stages[0]


def test_proxy_pattern_content_hash_caching(parsed_gov_order: DocumentNode):
    """Verify CachedRendererProxy caches artifacts based on content hash and options."""
    real_adapter = Jinja2HtmlAdapter()
    proxy = CachedRendererProxy(real_adapter)

    # First call: cache miss
    art1, text1 = proxy.render(parsed_gov_order, {"format": "html"})
    assert proxy.misses == 1
    assert proxy.hits == 0

    # Second call with identical content: cache hit
    art2, text2 = proxy.render(parsed_gov_order, {"format": "html"})
    assert proxy.misses == 1
    assert proxy.hits == 1
    assert art1 == art2

    # Third call with altered options: cache miss
    art3, text3 = proxy.render(parsed_gov_order, {"format": "html", "watermark_text": "DRAFT"})
    assert proxy.misses == 2
    assert proxy.hits == 1

    stats = proxy.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 2


def test_pipeline_memory_prototype_cache_and_similarity(
    parsed_gov_order: DocumentNode,
    sample_gov_order_path: Path,
):
    """Acceptance Criterion 7: Pipeline memory gives cache hit for structurally similar second document."""
    memory = PipelineMemory()
    memory.clear()
    synthesizer = PipelineSynthesizer()

    # 1. Synthesize pipeline for first document and record in memory
    res1 = synthesizer.synthesize(parsed_gov_order, {"format": "pdf"})
    memory.remember(res1.dss, res1.pipeline)
    assert memory.stats()["cached_pipelines"] == 1

    # 2. Query with the exact same DSS -> exact hit
    hit_exact = memory.recall(res1.dss)
    assert hit_exact is not None
    cloned_pipe1, hit_type = hit_exact
    assert hit_type == "exact"
    assert len(cloned_pipe1.stages) == len(res1.pipeline.stages)

    # 3. Create a structurally similar second document (same doc_type, table, signatures, but modified text)
    doc2 = parse_document(sample_gov_order_path)
    doc2.doc_metadata.document_number = "G.O. Ms. No. 105/2026/FIN-NEW"
    from autodoc.analysis.dss import DSSAnalyzer
    dss2 = DSSAnalyzer().analyze(doc2)

    # Must score high similarity and return a similar-cache hit
    hit_sim = memory.recall(dss2, allow_similar=True)
    assert hit_sim is not None
    cloned_pipe2, hit_type2 = hit_sim
    assert "exact" in hit_type2 or "similar" in hit_type2
    assert len(cloned_pipe2.stages) == len(res1.pipeline.stages)

    stats = memory.stats()
    assert stats["total_hits"] >= 2
