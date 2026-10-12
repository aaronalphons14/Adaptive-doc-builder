"""Prototype Pattern: Deep Cloning for Block Configurations and Whole Cached Pipelines.

Architectural Role:
    The Prototype pattern provides cloning mechanisms for two critical components:
    1. Fine-grained block configurations (`BlockConfigPrototype`): Allows duplicate sections,
       table headers, or callout cards to clone established styling prototypes without
       re-parsing or rebuilding config objects.
    2. Whole-pipeline prototypes (`PipelinePrototype`): Serves as the operational backbone
       for Pipeline Memory (N4). When a structurally similar document is detected, the engine
       retrieves the cached pipeline prototype and deep-clones it, bypassing redundant rule
       evaluations and DAG topological sorting.
"""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from typing import Any, Generic, List, Optional, TypeVar

from autodoc.core.models import BlockConfig
from autodoc.patterns.builder import DocumentPipeline, GenericPipelineStage, IPipelineStage

T = TypeVar("T")


class IPrototype(ABC, Generic[T]):
    """Generic Prototype contract specifying cloning behavior."""

    @abstractmethod
    def clone(self) -> T:
        """Create and return a deep or independent clone of this prototype."""
        pass


class BlockConfigPrototype(IPrototype[BlockConfig]):
    """Prototype wrapper for cloning and modifying BlockConfig instances."""

    def __init__(self, config: Optional[BlockConfig] = None) -> None:
        self.config = config or BlockConfig()

    def clone(self, **overrides: Any) -> BlockConfig:
        """Return an independent deep copy of the block configuration with optional attribute overrides."""
        cloned_dict = self.config.model_dump()
        cloned_dict.update(overrides)
        return BlockConfig(**cloned_dict)


class PipelinePrototype(IPrototype[DocumentPipeline]):
    """Prototype wrapper for cloning whole compiled processing pipelines."""

    def __init__(self, pipeline: DocumentPipeline) -> None:
        self.pipeline = pipeline

    def clone(self) -> DocumentPipeline:
        """Deep-clone the entire pipeline, creating fresh stage instances with duplicated parameters."""
        cloned_stages: List[IPipelineStage] = []

        for stage in self.pipeline.stages:
            stage_cls = type(stage)
            cloned_params = copy.deepcopy(stage.params)
            try:
                cloned_stage = stage_cls(stage_id=stage.stage_id, params=cloned_params)
            except Exception:
                # Fallback to GenericPipelineStage if constructor signature varies
                cloned_stage = GenericPipelineStage(stage_id=stage.stage_id, params=cloned_params)
            cloned_stages.append(cloned_stage)

        new_pipeline = DocumentPipeline(stages=cloned_stages)
        if self.pipeline.dss:
            new_pipeline.dss = copy.deepcopy(self.pipeline.dss)
        return new_pipeline
