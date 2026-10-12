"""Microsoft Word (DOCX) Renderer Stage for AutoDoc-Gov."""

from __future__ import annotations

from typing import Any, Dict, Optional

from autodoc.core.types import OutputFormat
from autodoc.patterns.adapter import PythonDocxAdapter
from autodoc.renderers.base import BaseRendererStage


class DocxRendererStage(BaseRendererStage):
    """Pipeline stage for rendering Microsoft Word (.docx) documents."""

    def __init__(
        self,
        stage_id: str = "DocxRendererStage",
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            stage_id=stage_id,
            adapter=PythonDocxAdapter(),
            target_format=OutputFormat.DOCX,
            params=params,
        )
