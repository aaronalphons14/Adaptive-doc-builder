"""Base Renderer Stage Interface for AutoDoc-Gov."""

from __future__ import annotations

from typing import Any, Dict, Optional

from autodoc.core.types import OutputFormat
from autodoc.patterns.adapter import IDocumentRendererAdapter
from autodoc.patterns.builder import IPipelineStage, PipelineContext


class BaseRendererStage(IPipelineStage):
    """Pipeline stage executing format-specific document rendering via an Adapter."""

    def __init__(
        self,
        stage_id: str,
        adapter: IDocumentRendererAdapter,
        target_format: OutputFormat,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(stage_id, params)
        self.adapter = adapter
        self.target_format = target_format

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Render document and attach the output artifact and text to context."""
        artifact, plain_text = self.adapter.render(context.document, context.options)
        context.rendered_artifact = artifact
        context.rendered_text = plain_text
        context.format = self.target_format

        context.stage_results[self.stage_id] = {
            "status": "rendered",
            "format": self.target_format.value,
            "artifact_size_bytes": len(artifact) if isinstance(artifact, (bytes, str)) else 0,
        }
        return context
