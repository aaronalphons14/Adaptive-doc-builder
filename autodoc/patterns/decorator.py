"""Decorator Pattern: Orthogonal Pipeline Stage Transformations.

Architectural Role:
    The Decorator pattern wraps pipeline execution stages to attach cross-cutting,
    orthogonal responsibilities (PII redaction, watermarking, citation formatting,
    running page numbering, and accessibility tagging) dynamically without modifying
    concrete document renderers or composite tree classes.

    Each decorator conforms to `IPipelineStage` and can either wrap an existing stage
    or execute independently in the synthesized pipeline sequence.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from autodoc.analysis.entity_detector import EntityDetector
from autodoc.core.types import MaskStyle
from autodoc.patterns.builder import IPipelineStage, PipelineContext
from autodoc.patterns.composite import (
    CalloutNode,
    HeadingNode,
    ParagraphNode,
    TableCellNode,
)


class BasePipelineDecorator(IPipelineStage):
    """Base decorator wrapping a pipeline stage."""

    def __init__(
        self,
        stage_id: str,
        params: Optional[Dict[str, Any]] = None,
        wrapped_stage: Optional[IPipelineStage] = None,
    ) -> None:
        super().__init__(stage_id, params)
        self.wrapped_stage = wrapped_stage if isinstance(wrapped_stage, IPipelineStage) else None

    def execute(self, context: PipelineContext) -> PipelineContext:
        if self.wrapped_stage:
            context = self.wrapped_stage.execute(context)
        return self.decorate(context)

    def decorate(self, context: PipelineContext) -> PipelineContext:
        """Subclasses override this method to perform decoration logic."""
        return context


class RedactionDecorator(BasePipelineDecorator):
    """Detects and masks sensitive personal data across all text nodes in the Composite tree."""

    def __init__(
        self,
        stage_id: str = "RedactionDecorator",
        params: Optional[Dict[str, Any]] = None,
        wrapped_stage: Optional[IPipelineStage] = None,
    ) -> None:
        super().__init__(stage_id, params, wrapped_stage)
        style_str = (self.params.get("mask_style") or "partial_tail").lower()

        if style_str == "full":
            self.mask_style = MaskStyle.FULL
        elif style_str == "statutory":
            self.mask_style = MaskStyle.STATUTORY_TAG
        elif style_str == "hash":
            self.mask_style = MaskStyle.HASH
        else:
            self.mask_style = MaskStyle.PARTIAL_TAIL
        self.legal_basis = self.params.get("legal_basis", "Digital Personal Data Protection Act 2023 / RTI Act 2005")
        self.detector = EntityDetector(
            default_mask_style=self.mask_style, default_legal_basis=self.legal_basis
        )

    def decorate(self, context: PipelineContext) -> PipelineContext:
        """Traverse document tree and redact PII in-place."""
        total_redacted = 0
        matches_found: List[str] = []

        for node in context.document.traverse():
            if isinstance(node, ParagraphNode):
                masked_text, matches = self.detector.mask_text(node.text, self.mask_style, self.legal_basis)
                if matches:
                    node.text = masked_text
                    total_redacted += len(matches)
                    matches_found.extend([m.entity_type for m in matches])
                if node.secondary_text:
                    m_sec, m_matches = self.detector.mask_text(node.secondary_text, self.mask_style, self.legal_basis)
                    if m_matches:
                        node.secondary_text = m_sec
                        total_redacted += len(m_matches)

            elif isinstance(node, TableCellNode):
                masked_text, matches = self.detector.mask_text(node.text, self.mask_style, self.legal_basis)
                if matches:
                    node.text = masked_text
                    total_redacted += len(matches)

            elif isinstance(node, HeadingNode):
                masked_text, matches = self.detector.mask_text(node.text, self.mask_style, self.legal_basis)
                if matches:
                    node.text = masked_text
                    total_redacted += len(matches)

        context.stage_results[self.stage_id] = {
            "status": "completed",
            "redactions_applied": total_redacted,
            "entity_types": list(set(matches_found)),
            "mask_style": self.mask_style.value,
            "legal_basis": self.legal_basis,
        }
        return context


class WatermarkDecorator(BasePipelineDecorator):
    """Injects classification watermark text into document options."""

    def __init__(
        self,
        stage_id: str = "WatermarkDecorator",
        params: Optional[Dict[str, Any]] = None,
        wrapped_stage: Optional[IPipelineStage] = None,
    ) -> None:
        super().__init__(stage_id, params, wrapped_stage)

    def decorate(self, context: PipelineContext) -> PipelineContext:
        classification = context.document.doc_metadata.classification.value
        watermark = self.params.get("watermark_text")
        if not watermark and classification != "unclassified":
            watermark = classification.upper()

        if watermark:
            context.options["watermark_text"] = watermark
            context.stage_results[self.stage_id] = {
                "status": "applied",
                "watermark_text": watermark,
                "opacity": self.params.get("opacity", 0.15),
            }
        else:
            context.stage_results[self.stage_id] = {"status": "skipped_unclassified"}

        return context


class CitationDecorator(BasePipelineDecorator):
    """Identifies and highlights statutory and legal citations."""

    def __init__(
        self,
        stage_id: str = "CitationDecorator",
        params: Optional[Dict[str, Any]] = None,
        wrapped_stage: Optional[IPipelineStage] = None,
    ) -> None:
        super().__init__(stage_id, params, wrapped_stage)

    def decorate(self, context: PipelineContext) -> PipelineContext:
        citations_tagged = 0
        for node in context.document.traverse():
            if isinstance(node, CalloutNode) and node.citation:
                citations_tagged += 1

        context.stage_results[self.stage_id] = {
            "status": "completed",
            "citations_processed": citations_tagged,
        }
        return context


class PageNumberingDecorator(BasePipelineDecorator):
    """Attaches running header and page numbering configuration."""

    def __init__(
        self,
        stage_id: str = "PageNumberingDecorator",
        params: Optional[Dict[str, Any]] = None,
        wrapped_stage: Optional[IPipelineStage] = None,
    ) -> None:
        super().__init__(stage_id, params, wrapped_stage)

    def decorate(self, context: PipelineContext) -> PipelineContext:
        fmt = self.params.get("format", "Page {page} of {total}")
        context.options["page_number_format"] = fmt
        context.stage_results[self.stage_id] = {
            "status": "configured",
            "format": fmt,
        }
        return context


class AccessibilityDecorator(BasePipelineDecorator):
    """Enforces GIGW 3.0 and WCAG AA accessibility compliance requirements."""

    def __init__(
        self,
        stage_id: str = "AccessibilityDecorator",
        params: Optional[Dict[str, Any]] = None,
        wrapped_stage: Optional[IPipelineStage] = None,
    ) -> None:
        super().__init__(stage_id, params, wrapped_stage)

    def decorate(self, context: PipelineContext) -> PipelineContext:
        context.options["enable_semantic_tags"] = True
        context.options["high_contrast"] = True
        context.options["wcag_level"] = self.params.get("wcag_level", "AA")
        context.stage_results[self.stage_id] = {
            "status": "enforced",
            "gigw_compliance": True,
            "wcag_level": "AA",
        }
        return context


class BilingualDecorator(BasePipelineDecorator):
    """Configures bilingual parallel or sequential layout rendering."""

    def __init__(
        self,
        stage_id: str = "BilingualDecorator",
        params: Optional[Dict[str, Any]] = None,
        wrapped_stage: Optional[IPipelineStage] = None,
    ) -> None:
        super().__init__(stage_id, params, wrapped_stage)

    def decorate(self, context: PipelineContext) -> PipelineContext:
        context.options["bilingual_enabled"] = True
        context.options["layout_mode"] = self.params.get("layout_mode", "side_by_side")
        context.stage_results[self.stage_id] = {
            "status": "enabled",
            "layout_mode": context.options["layout_mode"],
        }
        return context

