"""Markdown Renderer Stage for AutoDoc-Gov (Proof of Open/Closed Extension)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from autodoc.core.types import OutputFormat
from autodoc.patterns.adapter import MarkdownAdapter
from autodoc.renderers.base import BaseRendererStage


class MarkdownRendererStage(BaseRendererStage):
    """Pipeline stage for rendering Markdown documentation."""

    def __init__(
        self,
        stage_id: str = "MarkdownRendererStage",
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            stage_id=stage_id,
            adapter=MarkdownAdapter(),
            target_format=OutputFormat.MARKDOWN,
            params=params,
        )
