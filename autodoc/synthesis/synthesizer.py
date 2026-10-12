"""Master Pipeline Synthesizer Engine (Mechanism N2).

Architectural Role:
    Orchestrates runtime analysis, rule evaluation, DAG conflict resolution,
    and Builder assembly to synthesize compliant document transformation pipelines.

    Open/Closed Guarantee:
    New document types or output formats require only new stage classes or YAML rules,
    with zero modifications to the core synthesis logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

from autodoc.analysis.dss import DSSAnalyzer
from autodoc.core.models import DSSSignature
from autodoc.patterns.builder import (
    DocumentPipeline,
    GenericPipelineStage,
    IPipelineStage,
    PipelineBuilder,
)
from autodoc.patterns.composite import DocumentNode
from autodoc.synthesis.dag import DAGResolver, StageDescriptor
from autodoc.synthesis.engine import FiredRule, RuleEngine


@dataclass
class SynthesisResult:
    """Output of the pipeline synthesis phase."""
    pipeline: DocumentPipeline
    dss: DSSSignature
    stages: List[StageDescriptor]
    fired_rules: List[FiredRule]
    conflict_log: List[str]
    assembly_report: Dict[str, Any]


class PipelineSynthesizer:
    """Synthesizes custom, compliant transformation pipelines at runtime based on DSS."""

    def __init__(
        self,
        rule_engine: Optional[RuleEngine] = None,
        dss_analyzer: Optional[DSSAnalyzer] = None,
        dag_resolver: Optional[DAGResolver] = None,
    ) -> None:
        self.rule_engine = rule_engine or RuleEngine()
        self.dss_analyzer = dss_analyzer or DSSAnalyzer()
        self.dag_resolver = dag_resolver or DAGResolver()
        self._stage_factory_registry: Dict[str, Type[IPipelineStage]] = {}
        self._register_default_stages()

    def _register_default_stages(self) -> None:
        """Register core rendering and decorator stages."""
        from autodoc.patterns.decorator import (
            AccessibilityDecorator,
            BilingualDecorator,
            CitationDecorator,
            PageNumberingDecorator,
            RedactionDecorator,
            WatermarkDecorator,
        )
        from autodoc.renderers.docx_renderer import DocxRendererStage
        from autodoc.renderers.html_renderer import HtmlRendererStage
        from autodoc.renderers.markdown_renderer import MarkdownRendererStage
        from autodoc.renderers.pdf_renderer import PdfRendererStage

        # Renderers
        self.register_stage("HtmlRendererStage", HtmlRendererStage)
        self.register_stage("PdfRendererStage", PdfRendererStage)
        self.register_stage("DocxRendererStage", DocxRendererStage)
        self.register_stage("MarkdownRendererStage", MarkdownRendererStage)

        # Decorators
        self.register_stage("RedactionDecorator", RedactionDecorator)
        self.register_stage("WatermarkDecorator", WatermarkDecorator)
        self.register_stage("CitationDecorator", CitationDecorator)
        self.register_stage("PageNumberingDecorator", PageNumberingDecorator)
        self.register_stage("AccessibilityDecorator", AccessibilityDecorator)
        self.register_stage("BilingualDecorator", BilingualDecorator)

        # Verifier
        from autodoc.verifier.verifier import VerifierStage
        self.register_stage("VerifierStage", VerifierStage)





    def register_stage(self, stage_id: str, stage_cls: Type[IPipelineStage]) -> None:
        """Register a concrete stage class (supports Open/Closed expansion)."""
        self._stage_factory_registry[stage_id] = stage_cls

    def instantiate_stage(self, descriptor: StageDescriptor) -> IPipelineStage:
        """Instantiate a concrete stage instance using registry or generic fallback."""
        if descriptor.stage_id in self._stage_factory_registry:
            cls = self._stage_factory_registry[descriptor.stage_id]
            return cls(descriptor.stage_id, descriptor.params)
        return GenericPipelineStage(descriptor.stage_id, descriptor.params)

    def synthesize(
        self,
        doc: DocumentNode,
        options: Optional[Dict[str, Any]] = None,
    ) -> SynthesisResult:
        """Synthesize an optimal, compliant processing pipeline for the given document."""
        options = options or {}
        if "format" not in options:
            options["format"] = "html"

        # 1. Analyze document structure signature (N1)
        dss = self.dss_analyzer.analyze(doc)

        # 2. Evaluate declarative rules (N2)
        candidate_stages, fired_rules = self.rule_engine.evaluate_rules(
            dss.feature_vector, options
        )

        # 2b. Compliance-by-Construction: Policy Injection & Invariant Checking (N3)
        from autodoc.core.exceptions import ComplianceError
        from autodoc.patterns.singleton import PolicyRegistry

        policy_reg = PolicyRegistry.get_instance()
        active_policies = policy_reg.get_active_policies(dss.feature_vector)

        for policy in active_policies:
            for mandatory_comp in policy.mandatory_components:
                # If caller explicitly attempted to suppress a mandatory component
                if options.get(f"disable_{mandatory_comp.lower()}") or options.get("skip_redaction"):
                    raise ComplianceError(
                        f"Compliance-by-Construction Violation: Active policy '{policy.name}' "
                        f"mandates '{mandatory_comp}'. Synthesizer refuses to construct pipeline.",
                        policy_id=policy.id,
                    )
                # Ensure mandatory component is present in candidate stages
                if not any(s.stage_id == mandatory_comp for s in candidate_stages):
                    candidate_stages.append(StageDescriptor(
                        stage_id=mandatory_comp,
                        stage_type="decorator",
                        priority=100,
                        rule_id=f"injected_by_{policy.id}",
                        dependencies=["RendererStage"],
                    ))

        # 3. Resolve conflicts and order topologically via DAG

        ordered_stages, conflict_log = self.dag_resolver.resolve(candidate_stages)

        # 4. Assemble pipeline via Builder pattern
        builder = PipelineBuilder().set_dss(dss)
        for descriptor in ordered_stages:
            stage_instance = self.instantiate_stage(descriptor)
            builder.add_stage(stage_instance, descriptor.stage_type)

        pipeline = builder.build()

        # 5. Compile explainability assembly report (N5)
        assembly_report = {
            "document_id": dss.document_id,
            "signature_hash": dss.signature_hash,
            "fired_rules": [
                {
                    "rule_id": r.rule_id,
                    "description": r.description,
                    "condition": r.condition,
                    "priority": r.priority,
                    "components_added": r.components_added,
                }
                for r in fired_rules
            ],
            "ordered_stages": [s.stage_id for s in ordered_stages],
            "conflict_log": conflict_log,
            "features_summary": {
                "doc_type": dss.feature_vector.doc_type,
                "classification": dss.feature_vector.classification,
                "languages": dss.feature_vector.languages,
                "sensitive_data_count": dss.feature_vector.sensitive_data_count,
                "has_citations": dss.feature_vector.has_citations,
                "has_bilingual_content": dss.feature_vector.has_bilingual_content,
                "total_blocks": dss.feature_vector.total_blocks,
            },
        }

        return SynthesisResult(
            pipeline=pipeline,
            dss=dss,
            stages=ordered_stages,
            fired_rules=fired_rules,
            conflict_log=conflict_log,
            assembly_report=assembly_report,
        )
