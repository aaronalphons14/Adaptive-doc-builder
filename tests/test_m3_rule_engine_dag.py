"""Tests for Milestone 3: Rule Engine, DAG Conflict/Dependency Resolution, and Pipeline Builder."""

import pytest

from autodoc.core.exceptions import SynthesisError
from autodoc.patterns.builder import (
    IPipelineStage,
    PipelineBuilder,
    PipelineContext,
)
from autodoc.patterns.composite import DocumentNode
from autodoc.synthesis.dag import DAGResolver, StageDescriptor
from autodoc.synthesis.engine import RuleEngine
from autodoc.synthesis.synthesizer import PipelineSynthesizer


def test_rule_engine_loading_and_evaluation(parsed_rti: DocumentNode):
    """Verify rule engine correctly matches DSS feature expressions."""
    from autodoc.analysis.dss import DSSAnalyzer

    analyzer = DSSAnalyzer()
    dss = analyzer.analyze(parsed_rti)

    engine = RuleEngine()
    stages, fired = engine.evaluate_rules(dss.feature_vector, {"format": "pdf"})

    fired_rule_ids = {r.rule_id for r in fired}
    # RTI reply has sensitive data, citations, accessibility, verifier, and format=pdf
    assert "rule_pii_redaction" in fired_rule_ids
    assert "rule_citation_preservation" in fired_rule_ids
    assert "rule_accessibility_tagging" in fired_rule_ids
    assert "rule_format_pdf" in fired_rule_ids
    assert "rule_output_verifier" in fired_rule_ids
    assert "rule_format_html" not in fired_rule_ids


def test_dag_dependency_ordering_and_precedence():
    """Verify DAG resolver strictly orders Redaction before Citation before Renderer before Verifier."""
    resolver = DAGResolver()

    # Stages presented in arbitrary/reverse order
    input_stages = [
        StageDescriptor(stage_id="VerifierStage", stage_type="verifier", priority=10),
        StageDescriptor(
            stage_id="CitationDecorator",
            stage_type="decorator",
            priority=80,
            dependencies=["RendererStage"],
        ),
        StageDescriptor(
            stage_id="RendererStage",
            stage_type="renderer",
            priority=50,
            dependencies=["VerifierStage"],
        ),
        StageDescriptor(
            stage_id="RedactionDecorator",
            stage_type="decorator",
            priority=100,
            dependencies=["CitationDecorator", "RendererStage"],
        ),
        StageDescriptor(stage_id="AccessibilityDecorator", stage_type="decorator", priority=70),
    ]

    ordered, conflicts = resolver.resolve(input_stages)
    ordered_ids = [s.stage_id for s in ordered]

    # Verify strict partial ordering requirements
    redact_idx = ordered_ids.index("RedactionDecorator")
    cite_idx = ordered_ids.index("CitationDecorator")
    render_idx = ordered_ids.index("RendererStage")
    verify_idx = ordered_ids.index("VerifierStage")

    assert redact_idx < cite_idx, "Redaction must run before Citation"
    assert cite_idx < render_idx, "Citation must run before Renderer"
    assert render_idx < verify_idx, "Renderer must run before Verifier"


def test_dag_conflict_resolution():
    """Verify mutual exclusion conflict resolution using priority."""
    resolver = DAGResolver()

    # Both HTML and PDF renderers requested
    input_stages = [
        StageDescriptor(
            stage_id="HtmlRendererStage",
            stage_type="renderer",
            priority=60, # Higher priority
            conflicts=["PdfRendererStage"],
        ),
        StageDescriptor(
            stage_id="PdfRendererStage",
            stage_type="renderer",
            priority=40, # Lower priority
            conflicts=["HtmlRendererStage"],
        ),
    ]

    ordered, conflict_log = resolver.resolve(input_stages)
    ordered_ids = [s.stage_id for s in ordered]

    assert "HtmlRendererStage" in ordered_ids
    assert "PdfRendererStage" not in ordered_ids
    assert len(conflict_log) >= 1
    assert "retained over PdfRendererStage" in conflict_log[0]


def test_dag_circular_dependency_detection():
    """Verify cycle detection raises SynthesisError."""
    resolver = DAGResolver()

    # Create explicit cycle: A -> B -> A
    cycle_stages = [
        StageDescriptor(stage_id="StageA", stage_type="decorator", dependencies=["StageB"]),
        StageDescriptor(stage_id="StageB", stage_type="decorator", dependencies=["StageA"]),
    ]

    with pytest.raises(SynthesisError, match="Circular dependency"):
        resolver.resolve(cycle_stages)


def test_builder_pattern_assembly_and_execution():
    """Verify PipelineBuilder constructs executable DocumentPipeline and Mermaid diagram."""
    builder = PipelineBuilder()

    class CustomTestStage(IPipelineStage):
        def execute(self, context: PipelineContext) -> PipelineContext:
            context.stage_results[self.stage_id] = {"executed": True}
            return context

    builder.add_decorator(CustomTestStage("TestDecorator"))
    builder.set_renderer(CustomTestStage("TestRenderer"))
    builder.add_verifier(CustomTestStage("TestVerifier"))

    pipeline = builder.build()
    assert len(pipeline.stages) == 3
    assert pipeline.get_stage_names() == ["TestDecorator", "TestRenderer", "TestVerifier"]

    # Mermaid diagram inspection
    mermaid = pipeline.to_mermaid()
    assert "flowchart LR" in mermaid
    assert "TestDecorator" in mermaid
    assert "TestRenderer" in mermaid
    assert "TestVerifier" in mermaid

    # Execution verification
    context = PipelineContext(document=DocumentNode())
    result_ctx = pipeline.execute(context)
    assert result_ctx.stage_results["TestDecorator"]["executed"] is True
    assert result_ctx.stage_results["TestRenderer"]["executed"] is True
    assert result_ctx.execution_time_ms >= 0.0


def test_pipeline_synthesizer_on_different_documents(
    parsed_gov_order: DocumentNode,
    parsed_rti: DocumentNode,
    parsed_circular: DocumentNode,
):
    """Verify synthesizer produces distinct, tailored pipelines and reports per document."""
    synthesizer = PipelineSynthesizer()

    # 1. Synthesize for RTI reply (HTML)
    res_rti = synthesizer.synthesize(parsed_rti, {"format": "html"})
    stages_rti = [s.stage_id for s in res_rti.stages]
    assert "RedactionDecorator" in stages_rti
    assert "HtmlRendererStage" in stages_rti
    assert "VerifierStage" in stages_rti

    # 2. Synthesize for Government Order (PDF)
    res_go = synthesizer.synthesize(parsed_gov_order, {"format": "pdf"})
    stages_go = [s.stage_id for s in res_go.stages]
    assert "PdfRendererStage" in stages_go
    assert "PageNumberingDecorator" in stages_go
    assert "RedactionDecorator" not in stages_go # No sensitive PII in GO sample

    # 3. Synthesize for Bilingual Circular (DOCX)
    res_circ = synthesizer.synthesize(parsed_circular, {"format": "docx"})
    stages_circ = [s.stage_id for s in res_circ.stages]
    assert "BilingualDecorator" in stages_circ
    assert "DocxRendererStage" in stages_circ

    # Verify assembly reports differ and explain decisions
    assert res_rti.assembly_report["signature_hash"] != res_go.assembly_report["signature_hash"]
    assert any(r["rule_id"] == "rule_pii_redaction" for r in res_rti.assembly_report["fired_rules"])
    assert not any(r["rule_id"] == "rule_pii_redaction" for r in res_go.assembly_report["fired_rules"])
