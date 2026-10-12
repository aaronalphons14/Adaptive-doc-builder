"""PDF Renderer Stage for AutoDoc-Gov."""

from __future__ import annotations

from typing import Any, Dict, Optional

from autodoc.core.types import OutputFormat
from autodoc.patterns.adapter import WeasyPrintPdfAdapter
from autodoc.renderers.base import BaseRendererStage


class PdfRendererStage(BaseRendererStage):
    """Pipeline stage for rendering PDF documents with Indic font support."""

    def __init__(
        self,
        stage_id: str = "PdfRendererStage",
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            stage_id=stage_id,
            adapter=WeasyPrintPdfAdapter(),
            target_format=OutputFormat.PDF,
            params=params,
        )
