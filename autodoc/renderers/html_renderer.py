"""HTML Renderer Stage for AutoDoc-Gov."""

from __future__ import annotations

from typing import Any, Dict, Optional

from autodoc.core.types import OutputFormat
from autodoc.patterns.adapter import Jinja2HtmlAdapter
from autodoc.renderers.base import BaseRendererStage


class HtmlRendererStage(BaseRendererStage):
    """Pipeline stage for rendering accessible semantic HTML5."""

    def __init__(
        self,
        stage_id: str = "HtmlRendererStage",
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            stage_id=stage_id,
            adapter=Jinja2HtmlAdapter(),
            target_format=OutputFormat.HTML,
            params=params,
        )
