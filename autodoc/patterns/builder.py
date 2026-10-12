"""Builder Pattern: Dynamic Processing Pipeline Assembly.

Architectural Role:
    The Builder pattern separates the construction of a complex, multi-stage document
    transformation pipeline from its runtime execution representation.

    Rather than relying on static, hardcoded stage sequences or procedural scripts,
    the `PipelineBuilder` receives the topologically sorted components derived by the
    synthesis ontology (N2) and constructs a cohesive `DocumentPipeline` step-by-step.

    It enables independent variation of pipeline parts:
    - Preprocessing stages (normalizers, structural sanitizers)
    - Decorator chains (redaction, watermarking, citation formatting, accessibility)
    - Format renderers (HTML, PDF, DOCX, Markdown)
    - Post-render verifiers (PII re-scanners, watermark validators)
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

from autodoc.core.models import DSSSignature
from autodoc.core.types import OutputFormat
from autodoc.patterns.composite import DocumentNode


@dataclass
class PipelineContext:
    """Carries document state, parameters, telemetry, and artifacts across pipeline stages."""
    document: DocumentNode
    dss: Optional[DSSSignature] = None
    options: Dict[str, Any] = field(default_factory=dict)
    format: OutputFormat = OutputFormat.HTML
    rendered_artifact: Optional[Union[str, bytes]] = None
    rendered_text: Optional[str] = None
    stage_results: Dict[str, Any] = field(default_factory=dict)
    assembly_report: Dict[str, Any] = field(default_factory=dict)
    verification_passed: bool = True
    verification_errors: List[str] = field(default_factory=list)
    is_approved: bool = False
    approval_token: Optional[str] = None
    execution_time_ms: float = 0.0


class IPipelineStage(ABC):
    """Abstract interface for all pipeline transformation stages."""

    def __init__(self, stage_id: str, params: Optional[Dict[str, Any]] = None) -> None:
        self.stage_id = stage_id
        self.params: Dict[str, Any] = params or {}

    @abstractmethod
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute stage logic and mutate context accordingly."""
        pass


class GenericPipelineStage(IPipelineStage):
    """Generic or placeholder pipeline stage execution."""

    def __init__(
        self,
        stage_id: str,
        params: Optional[Dict[str, Any]] = None,
        executor: Optional[Callable[[PipelineContext], PipelineContext]] = None,
    ) -> None:
        super().__init__(stage_id, params)
        self.executor = executor


    def execute(self, context: PipelineContext) -> PipelineContext:
        if self.executor:
            return self.executor(context)
        context.stage_results[self.stage_id] = {
            "status": "completed",
            "params": self.params,
        }
        return context



class DocumentPipeline:
    """The constructed product: an executable sequence of pipeline stages."""

    def __init__(self, stages: Optional[List[IPipelineStage]] = None) -> None:
        self.stages: List[IPipelineStage] = stages or []
        self.dss: Optional[DSSSignature] = None

    def add_stage(self, stage: IPipelineStage) -> None:
        """Append an additional stage to the execution sequence."""
        self.stages.append(stage)

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Run each stage sequentially with error handling and timing telemetry."""
        start_time = time.perf_counter()

        for stage in self.stages:
            stage_start = time.perf_counter()
            context = stage.execute(context)
            stage_duration = (time.perf_counter() - stage_start) * 1000.0

            existing_res = context.stage_results.get(stage.stage_id, {})
            if not isinstance(existing_res, dict):
                existing_res = {"output": existing_res}
            existing_res.setdefault("status", "success")
            existing_res["duration_ms"] = round(stage_duration, 2)
            existing_res["params"] = stage.params
            context.stage_results[stage.stage_id] = existing_res


        context.execution_time_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        return context

    def get_stage_names(self) -> List[str]:
        """Return list of stage identifiers."""
        return [s.stage_id for s in self.stages]

    def to_mermaid(self) -> str:
        """Generate a Mermaid flowchart diagram representing this pipeline."""
        lines = ["flowchart LR", "  Input[Document Node Tree] --> Start([Start])"]
        prev = "Start"
        for i, s in enumerate(self.stages):
            node_id = f"S{i}_{s.stage_id}"
            lines.append(f"  {prev} --> {node_id}[\"{s.stage_id}\"]")
            prev = node_id
        lines.append(f"  {prev} --> Output([Rendered Output Artifact])")
        return "\n".join(lines)


class PipelineBuilder:
    """Builder for assembling a DocumentPipeline from synthesized stages."""

    def __init__(self) -> None:
        self.preprocessors: List[IPipelineStage] = []
        self.decorators: List[IPipelineStage] = []
        self.renderer: Optional[IPipelineStage] = None
        self.verifiers: List[IPipelineStage] = []
        self.dss: Optional[DSSSignature] = None

    def set_dss(self, dss: DSSSignature) -> PipelineBuilder:
        self.dss = dss
        return self

    def add_preprocessor(self, stage: IPipelineStage) -> PipelineBuilder:
        self.preprocessors.append(stage)
        return self

    def add_decorator(self, stage: IPipelineStage) -> PipelineBuilder:
        self.decorators.append(stage)
        return self

    def set_renderer(self, stage: IPipelineStage) -> PipelineBuilder:
        self.renderer = stage
        return self

    def add_verifier(self, stage: IPipelineStage) -> PipelineBuilder:
        self.verifiers.append(stage)
        return self

    def add_stage(self, stage: IPipelineStage, stage_type: str) -> PipelineBuilder:
        """Add stage according to its classification."""
        if stage_type == "preprocessor":
            self.add_preprocessor(stage)
        elif stage_type == "decorator":
            self.add_decorator(stage)
        elif stage_type == "renderer":
            self.set_renderer(stage)
        elif stage_type == "verifier":
            self.add_verifier(stage)
        else:
            self.add_decorator(stage)
        return self

    def build(self) -> DocumentPipeline:
        """Assemble all stages in proper topological order into a DocumentPipeline."""
        all_stages: List[IPipelineStage] = []
        all_stages.extend(self.preprocessors)
        all_stages.extend(self.decorators)
        if self.renderer:
            all_stages.append(self.renderer)
        all_stages.extend(self.verifiers)

        pipeline = DocumentPipeline(stages=all_stages)
        pipeline.dss = self.dss
        return pipeline
