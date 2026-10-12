"""Pydantic data models for AutoDoc-Gov."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from autodoc.core.types import Classification, DocumentType


class EntityMatch(BaseModel):
    """Detected sensitive entity (e.g., Aadhaar, PAN, phone)."""
    entity_type: str
    raw_value: str
    masked_value: str
    start: int = 0
    end: int = 0
    confidence: float = 1.0
    legal_basis: Optional[str] = None


class DocumentMetadata(BaseModel):
    """Document header, authority, classification, and language metadata."""
    title: str = "Government Document"
    doc_type: DocumentType = DocumentType.GOVERNMENT_ORDER
    document_number: Optional[str] = None
    department: str = "General Administration Department"
    jurisdiction: str = "Government of National Capital Territory"
    date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    classification: Classification = Classification.UNCLASSIFIED
    languages: List[str] = Field(default_factory=lambda: ["en"])
    security_signoff: bool = False
    approval_token: Optional[str] = None
    retention_years: int = 10
    sensitivity_tags: List[str] = Field(default_factory=list)
    legal_basis: str = "Digital Personal Data Protection Act 2023 / RTI Act 2005"
    signatory_name: Optional[str] = None
    signatory_designation: Optional[str] = None
    qr_verification_url: Optional[str] = None


class DocumentStructureFeatures(BaseModel):
    """Normalized feature vector extracted from the Composite tree."""
    doc_type: str
    classification: str
    languages: List[str]
    total_blocks: int = 0
    block_counts: Dict[str, int] = Field(default_factory=dict)
    max_depth: int = 1
    avg_depth: float = 1.0
    table_density: float = 0.0
    list_density: float = 0.0
    sensitive_data_count: int = 0
    sensitive_types_found: List[str] = Field(default_factory=list)
    has_citations: bool = False
    citation_count: int = 0
    has_signature_blocks: bool = False
    signature_block_count: int = 0
    has_bilingual_content: bool = False
    word_count: int = 0

    def to_canonical_dict(self) -> Dict[str, Any]:
        """Convert features to canonical sorted dictionary for deterministic hashing."""
        return {
            "doc_type": self.doc_type,
            "classification": self.classification,
            "languages": sorted(self.languages),
            "total_blocks": self.total_blocks,
            "block_counts": {k: self.block_counts[k] for k in sorted(self.block_counts.keys())},
            "max_depth": self.max_depth,
            "avg_depth": round(self.avg_depth, 3),
            "table_density": round(self.table_density, 3),
            "list_density": round(self.list_density, 3),
            "sensitive_data_count": self.sensitive_data_count,
            "sensitive_types_found": sorted(self.sensitive_types_found),
            "has_citations": self.has_citations,
            "citation_count": self.citation_count,
            "has_signature_blocks": self.has_signature_blocks,
            "signature_block_count": self.signature_block_count,
            "has_bilingual_content": self.has_bilingual_content,
            "word_count": self.word_count,
        }


class DSSSignature(BaseModel):
    """Canonical Document Structure Signature (DSS)."""
    signature_hash: str
    feature_vector: DocumentStructureFeatures
    document_id: Optional[str] = None
    computed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def fingerprint(self) -> str:
        return self.signature_hash

    @property
    def document_type(self) -> str:
        return self.feature_vector.doc_type

    @property
    def languages(self) -> List[str]:
        return self.feature_vector.languages

    @property
    def node_count(self) -> int:
        return self.feature_vector.total_blocks

    @property
    def depth(self) -> int:
        return self.feature_vector.max_depth

    @property
    def sensitive_entities(self) -> List[str]:
        return self.feature_vector.sensitive_types_found

    @property
    def sensitive_data_count(self) -> int:
        return self.feature_vector.sensitive_data_count


class BlockConfig(BaseModel):
    """Configuration prototype for styling, fonts, and layout parameters."""
    style_name: str = "default"
    font_family: str = "Noto Sans, Arial, sans-serif"
    font_size_pt: float = 11.0
    bold: bool = False
    italic: bool = False
    alignment: str = "left" # left, center, right, justify
    padding_pt: float = 4.0
    margin_bottom_pt: float = 6.0
    border: bool = False
    background_color: Optional[str] = None
    text_color: str = "#111827"
    extra_attributes: Dict[str, Any] = Field(default_factory=dict)
