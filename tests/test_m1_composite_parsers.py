"""Tests for Milestone 1: Models, Composite Tree, and Multi-format Parsers."""

from pathlib import Path

from autodoc.analysis.parser import (
    parse_document,
)
from autodoc.core.models import (
    BlockConfig,
    DocumentMetadata,
    DocumentStructureFeatures,
    EntityMatch,
)
from autodoc.core.types import (
    BlockType,
    Classification,
    DocumentType,
)
from autodoc.patterns.composite import (
    CalloutNode,
    DocumentNode,
    HeadingNode,
    ListItemNode,
    ListNode,
    ParagraphNode,
    SectionNode,
    SignatureNode,
    TableCellNode,
    TableNode,
    TableRowNode,
)


def test_core_models_instantiation():
    """Verify Pydantic models validate and serialize properly."""
    meta = DocumentMetadata(
        title="Test Order",
        doc_type=DocumentType.GOVERNMENT_ORDER,
        classification=Classification.UNCLASSIFIED,
        languages=["en"],
    )
    assert meta.title == "Test Order"
    assert meta.doc_type == DocumentType.GOVERNMENT_ORDER
    assert meta.classification == Classification.UNCLASSIFIED

    match = EntityMatch(
        entity_type="aadhaar",
        raw_value="123456789012",
        masked_value="XXXX-XXXX-9012",
    )
    assert match.entity_type == "aadhaar"
    assert match.masked_value == "XXXX-XXXX-9012"

    config = BlockConfig(style_name="gov_header", bold=True, font_size_pt=14.0)
    assert config.bold is True
    assert config.font_size_pt == 14.0

    features = DocumentStructureFeatures(
        doc_type="government_order",
        classification="unclassified",
        languages=["en"],
        total_blocks=10,
        sensitive_data_count=2,
    )
    canonical = features.to_canonical_dict()
    assert canonical["total_blocks"] == 10
    assert canonical["sensitive_data_count"] == 2


def test_composite_pattern_tree_construction():
    """Verify Composite pattern tree operations, traversal, and depth calculations."""
    doc = DocumentNode(doc_metadata=DocumentMetadata(title="Cabinet Resolution"))
    sec1 = SectionNode(title="Policy Directives", section_number="1.0")
    h1 = HeadingNode(text="Preamble", level=2)
    p1 = ParagraphNode(text="This resolution adopts new civil guidelines.")

    table = TableNode(caption="Allocation Metrics", headers=["Metric", "Target"])
    h_row = TableRowNode(is_header_row=True)
    h_row.add(TableCellNode(text="Metric", is_header=True))
    h_row.add(TableCellNode(text="Target", is_header=True))
    table.add(h_row)

    d_row = TableRowNode()
    d_row.add(TableCellNode(text="Digital Penetration"))
    d_row.add(TableCellNode(text="98%"))
    table.add(d_row)

    lst = ListNode(ordered=True)
    lst.add(ListItemNode(text="Phase 1 rollout"))
    lst.add(ListItemNode(text="Phase 2 rollout"))

    sig = SignatureNode(
        signatory_name="Secretary",
        designation="Chief Secretary",
        department="Cabinet Secretariat",
    )

    sec1.add(h1)
    sec1.add(p1)
    sec1.add(table)
    sec1.add(lst)
    doc.add(sec1)
    doc.add(sig)

    # Test tree operations
    assert doc.depth() >= 4
    assert doc.count_nodes() >= 8
    assert table.cell_count() == 4
    assert len(lst.get_items()) == 2

    # Traversal
    all_nodes = list(doc.traverse())
    node_types = [n.block_type for n in all_nodes]
    assert BlockType.DOCUMENT in node_types
    assert BlockType.SECTION in node_types
    assert BlockType.HEADING in node_types
    assert BlockType.PARAGRAPH in node_types
    assert BlockType.TABLE in node_types
    assert BlockType.LIST in node_types
    assert BlockType.SIGNATURE_BLOCK in node_types

    # Text content flattening
    full_text = doc.get_text_content()
    assert "Cabinet Resolution" in full_text
    assert "Digital Penetration" in full_text
    assert "Chief Secretary" in full_text


def test_parse_json_government_order(parsed_gov_order: DocumentNode):
    """Verify parsing of 01_government_order.json into Composite tree."""
    doc = parsed_gov_order
    assert doc.doc_metadata.doc_type == DocumentType.GOVERNMENT_ORDER
    assert doc.doc_metadata.document_number == "G.O. Ms. No. 104/2026/FIN-EXP"
    assert "FINANCE" in doc.doc_metadata.department.upper()

    nodes = list(doc.traverse())
    assert any(isinstance(n, TableNode) for n in nodes)
    assert any(isinstance(n, SignatureNode) for n in nodes)
    assert any(isinstance(n, CalloutNode) for n in nodes)

    # Table content inspection
    tables = [n for n in nodes if isinstance(n, TableNode)]
    assert len(tables) >= 1
    assert len(tables[0].get_rows()) >= 3


def test_parse_markdown_tender_notice(parsed_tender: DocumentNode):
    """Verify parsing of 02_tender_notice.md with frontmatter and markdown tables."""
    doc = parsed_tender
    assert doc.doc_metadata.doc_type == DocumentType.TENDER_NOTICE
    assert doc.doc_metadata.document_number == "NIT-PWD/CIVIL/2026/089"
    assert "MAHARASHTRA" in doc.doc_metadata.jurisdiction.upper()

    nodes = list(doc.traverse())
    assert any(isinstance(n, TableNode) for n in nodes)
    assert any(isinstance(n, ListNode) for n in nodes)
    assert any(isinstance(n, SignatureNode) for n in nodes)

    full_text = doc.get_text_content()
    assert "NIT-PWD/CIVIL/2026/089" in full_text or "Er. Sunil V. Patil" in full_text
    assert "Construction of State Archives" in full_text


def test_parse_json_rti_reply(parsed_rti: DocumentNode):
    """Verify parsing of 03_rti_reply.json with statutory citations and PII."""
    doc = parsed_rti
    assert doc.doc_metadata.doc_type == DocumentType.RTI_REPLY
    assert doc.doc_metadata.document_number is not None
    assert "RTI" in doc.doc_metadata.document_number

    nodes = list(doc.traverse())
    callouts = [n for n in nodes if isinstance(n, CalloutNode)]
    assert len(callouts) >= 1
    assert callouts[0].citation is not None
    assert "Section 8(1)(j)" in callouts[0].citation

    full_text = doc.get_text_content()
    assert "Rameshwar Dayal" in full_text
    assert "5489 2104 7832" in full_text


def test_parse_bilingual_circular(parsed_circular: DocumentNode):
    """Verify parsing of 04_public_circular_bilingual.json with Devanagari Hindi text."""
    doc = parsed_circular
    assert doc.doc_metadata.doc_type == DocumentType.PUBLIC_CIRCULAR
    assert "en" in doc.doc_metadata.languages
    assert "hi" in doc.doc_metadata.languages

    nodes = list(doc.traverse())
    paragraphs = [n for n in nodes if isinstance(n, ParagraphNode)]
    bilingual_p = [p for p in paragraphs if p.is_bilingual]
    assert len(bilingual_p) >= 1
    assert bilingual_p[0].secondary_text is not None
    assert "नागरिक सेवा केंद्र" in bilingual_p[0].secondary_text

    full_text = doc.get_text_content()
    assert "सार्वजनिक परिपत्र" in full_text or "नागरिक सुविधा केंद्रों" in full_text


def test_parse_plaintext_certificate(parsed_certificate: DocumentNode):
    """Verify parsing of 05_certificate.txt using heuristic parser."""
    doc = parsed_certificate
    assert doc.doc_metadata.doc_type == DocumentType.CERTIFICATE
    assert doc.doc_metadata.document_number is not None
    assert "CRT/DOM/2026/BLR-EAST/98214" in doc.doc_metadata.document_number

    full_text = doc.get_text_content()
    assert "Kum. Ananya S. Rao" in full_text
    assert "Karnataka Civil Services" in full_text
    assert "Tahsildar" in full_text



def test_parse_document_format_detection(samples_dir: Path):
    """Verify parse_document correctly handles file paths, raw strings, and hints."""
    # Test passing Path object
    doc1 = parse_document(samples_dir / "01_government_order.json")
    assert isinstance(doc1, DocumentNode)

    # Test passing raw JSON string
    json_str = (samples_dir / "01_government_order.json").read_text(encoding="utf-8")
    doc2 = parse_document(json_str, format_hint="json")
    assert isinstance(doc2, DocumentNode)

    # Test passing raw Markdown string
    md_str = (samples_dir / "02_tender_notice.md").read_text(encoding="utf-8")
    doc3 = parse_document(md_str, format_hint="markdown")
    assert isinstance(doc3, DocumentNode)

    # Test passing plain text
    txt_str = "GOVERNMENT CIRCULAR\nNo: 123/2026\n\nThis is an urgent public advisory.\n\nSd/-\nDirector"
    doc4 = parse_document(txt_str, format_hint="text")
    assert isinstance(doc4, DocumentNode)
    assert doc4.doc_metadata.doc_type == DocumentType.PUBLIC_CIRCULAR
