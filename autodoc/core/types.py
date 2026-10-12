"""Enums and fundamental types for AutoDoc-Gov."""

from enum import Enum


class DocumentType(str, Enum):
    """Supported government document categories."""
    GOVERNMENT_ORDER = "government_order"
    TENDER_NOTICE = "tender_notice"
    RTI_REPLY = "rti_reply"
    PUBLIC_CIRCULAR = "public_circular"
    CERTIFICATE = "certificate"
    CUSTOM = "custom"


class OutputFormat(str, Enum):
    """Supported output rendering formats."""
    HTML = "html"
    PDF = "pdf"
    DOCX = "docx"
    MARKDOWN = "markdown"


class Classification(str, Enum):
    """Security and sensitivity classification levels."""
    UNCLASSIFIED = "unclassified"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"


class MaskStyle(str, Enum):
    """Masking styles for sensitive personal data protection."""
    FULL = "full"                 # e.g., ████████
    PARTIAL_TAIL = "partial_tail" # e.g., XXXX-XXXX-1234
    HASH = "hash"                 # e.g., [ID: sha256:7f83b165]
    STATUTORY_TAG = "statutory"   # e.g., [EXEMPT UNDER RTI ACT SEC 8(1)(j)]


class BlockType(str, Enum):
    """Canonical block node types within the Composite tree."""
    DOCUMENT = "document"
    SECTION = "section"
    SUBSECTION = "subsection"
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    TABLE = "table"
    TABLE_ROW = "table_row"
    TABLE_CELL = "table_cell"
    LIST = "list"
    LIST_ITEM = "list_item"
    SIGNATURE_BLOCK = "signature_block"
    CALLOUT = "callout"
    HEADER = "header"
    FOOTER = "footer"
    METADATA_PANEL = "metadata_panel"
