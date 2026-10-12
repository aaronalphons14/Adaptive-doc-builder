"""Self-Healing & Fallback Planning Engine (Mechanism N4).

Architectural Role:
    Implements autonomic recovery when a rendering engine or decorator stage encounters
    a failure.

    Capabilities:
    1. Incident Detection: Intercepts stage execution failures (e.g. crashed renderer,
       broken external dependency, or environment error).
    2. Fallback Re-Planning: Synthesizes an alternative, resilient component chain:
       - Primary PDF renderer failure -> falls back to ReportLab/headless fallback adapter.
       - Primary HTML renderer failure -> falls back to basic template adapter.
    3. Explainability Auditing: Records the exact failure reason, the replacement stage,
       and the recovery rationale into the document's Assembly Report.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from autodoc.core.exceptions import SelfHealingError
from autodoc.core.types import OutputFormat
from autodoc.patterns.adapter import ReportLabPdfAdapter
from autodoc.patterns.builder import DocumentPipeline, IPipelineStage, PipelineContext
from autodoc.renderers.base import BaseRendererStage


class FallbackRendererStage(BaseRendererStage):
    """Resilient fallback renderer stage substituted during self-healing."""

    def __init__(
        self,
        stage_id: str = "FallbackPdfRendererStage",
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            stage_id=stage_id,
            adapter=ReportLabPdfAdapter(),
            target_format=OutputFormat.PDF,
            params=params,
        )


class SelfHealingEngine:
    """Manages fallback planning and recovery for pipeline execution."""

    def __init__(self) -> None:
        self.recovery_log: List[Dict[str, Any]] = []

    def execute_with_self_healing(
        self, pipeline: DocumentPipeline, context: PipelineContext
    ) -> PipelineContext:
        """Execute pipeline stages with automatic failure recovery and fallback planning."""
        fallbacks_used: List[Dict[str, Any]] = []

        for i, stage in enumerate(pipeline.stages):
            try:
                context = stage.execute(context)
            except Exception as exc:
                # Primary stage failed -> attempt self-healing fallback planning
                fallback_stage = self._plan_fallback(stage, exc)
                if fallback_stage is None:
                    raise SelfHealingError(
                        f"Self-healing failed: No viable fallback found for stage '{stage.stage_id}': {exc}"
                    ) from exc

                recovery_record = {
                    "failed_stage": stage.stage_id,
                    "error": str(exc),
                    "fallback_stage": fallback_stage.stage_id,
                    "reason": f"Recovered from {type(exc).__name__} in {stage.stage_id} via {fallback_stage.stage_id}",
                }
                fallbacks_used.append(recovery_record)
                self.recovery_log.append(recovery_record)

                # Execute fallback stage
                context = fallback_stage.execute(context)

        if "fallbacks_used" not in context.assembly_report:
            context.assembly_report["fallbacks_used"] = []
        context.assembly_report["fallbacks_used"].extend(fallbacks_used)

        return context

    def _plan_fallback(self, failed_stage: IPipelineStage, error: Exception) -> Optional[IPipelineStage]:
        """Determine an appropriate fallback stage for a failing component."""
        s_id = failed_stage.stage_id.lower()

        if "pdf" in s_id or "renderer" in s_id:
            # Fallback for failing PDF or primary renderer
            return FallbackRendererStage(
                stage_id="SelfHealing_FallbackPdfRenderer",
                params={"recovery_from": failed_stage.stage_id, "error": str(error)},
            )

        return None
