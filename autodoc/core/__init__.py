"""Core domain models, types, and exceptions for AutoDoc-Gov."""

from autodoc.core.exceptions import (
    ApprovalRequiredError,
    AutoDocError,
    ComplianceError,
    SelfHealingError,
    SynthesisError,
    VerificationError,
)
from autodoc.core.models import (
    BlockConfig,
    DocumentMetadata,
    DocumentStructureFeatures,
    DSSSignature,
    EntityMatch,
)
from autodoc.core.types import BlockType, Classification, DocumentType, MaskStyle, OutputFormat

__all__ = [
    "BlockType",
    "Classification",
    "DocumentType",
    "MaskStyle",
    "OutputFormat",
    "BlockConfig",
    "DocumentMetadata",
    "DocumentStructureFeatures",
    "DSSSignature",
    "EntityMatch",
    "AutoDocError",
    "ComplianceError",
    "ApprovalRequiredError",
    "SynthesisError",
    "VerificationError",
    "SelfHealingError",
]
