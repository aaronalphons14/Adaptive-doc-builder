"""Tests for Milestone 2: Document Structure Signature (DSS) and Determinism."""

from pathlib import Path

from autodoc.analysis.dss import DSSAnalyzer
from autodoc.analysis.entity_detector import EntityDetector, validate_verhoeff
from autodoc.analysis.parser import parse_document
from autodoc.core.types import MaskStyle
from autodoc.patterns.composite import DocumentNode


def test_verhoeff_algorithm_validation():
    """Verify Verhoeff checksum algorithm for Indian Aadhaar numbers."""
    from autodoc.analysis.entity_detector import generate_verhoeff_check_digit

    # Valid Aadhaar numbers with correct checksums
    assert validate_verhoeff("234567890124") is True
    assert generate_verhoeff_check_digit("23456789012") == 4
    # Deliberately invalid checksum
    assert validate_verhoeff("234567890129") is False
    # Non-12-digit strings
    assert validate_verhoeff("12345") is False



def test_entity_detector_patterns_and_mask_styles():
    """Verify detection of Aadhaar, PAN, phone, email, bank account, and tagged personal fields."""
    detector = EntityDetector()
    sample_text = (
        "Applicant Shri Rajesh Kumar (Aadhaar: 2345 6789 0126, PAN: ABCDE1234F). "
        "Contact: +91 9876543210, Email: rajesh.k@nic.in. "
        "Bank Details: State Bank of India A/C 987654321098, IFSC SBIN0001234. "
        "Confidential note: {personal: Nominee is Mrs. Sunita Kumar}."
    )

    matches = detector.scan_text(sample_text)
    types_detected = {m.entity_type for m in matches}
    assert "aadhaar" in types_detected
    assert "pan" in types_detected
    assert "phone" in types_detected
    assert "email" in types_detected
    assert "bank_account" in types_detected
    assert "personal" in types_detected

    # Test PARTIAL_TAIL mask style
    masked_tail, _ = detector.mask_text(sample_text, mask_style=MaskStyle.PARTIAL_TAIL)
    assert "XXXX-XXXX-0126" in masked_tail
    assert "ABXXXXX4F" in masked_tail
    assert "+91-XXXXX-3210" in masked_tail
    assert "ra***@nic.in" in masked_tail
    assert "2345 6789 0126" not in masked_tail

    # Test FULL mask style
    masked_full, _ = detector.mask_text(sample_text, mask_style=MaskStyle.FULL)
    assert "████████" in masked_full
    assert "ABCDE1234F" not in masked_full

    # Test STATUTORY_TAG mask style
    masked_stat, _ = detector.mask_text(sample_text, mask_style=MaskStyle.STATUTORY_TAG)
    assert "[EXEMPT UNDER RTI ACT SEC 8(1)(j): AADHAAR]" in masked_stat


def test_dss_feature_extraction_on_samples(
    parsed_gov_order: DocumentNode,
    parsed_tender: DocumentNode,
    parsed_rti: DocumentNode,
    parsed_circular: DocumentNode,
    parsed_certificate: DocumentNode,
):
    """Verify feature vector computation across the 5 canonical sample documents."""
    analyzer = DSSAnalyzer()

    # 1. Government Order
    dss_go = analyzer.analyze(parsed_gov_order)
    f_go = dss_go.feature_vector
    assert f_go.doc_type == "government_order"
    assert f_go.block_counts["table"] >= 1
    assert f_go.has_signature_blocks is True
    assert f_go.table_density > 0.0

    # 2. Tender Notice
    dss_tender = analyzer.analyze(parsed_tender)
    f_tender = dss_tender.feature_vector
    assert f_tender.doc_type == "tender_notice"
    assert f_tender.block_counts["table"] >= 1
    assert f_tender.block_counts["list"] >= 1

    # 3. RTI Reply
    dss_rti = analyzer.analyze(parsed_rti)
    f_rti = dss_rti.feature_vector
    assert f_rti.doc_type == "rti_reply"
    assert f_rti.sensitive_data_count > 0
    assert "aadhaar" in f_rti.sensitive_types_found
    assert "phone" in f_rti.sensitive_types_found
    assert f_rti.has_citations is True

    # 4. Bilingual Circular
    dss_circ = analyzer.analyze(parsed_circular)
    f_circ = dss_circ.feature_vector
    assert f_circ.doc_type == "public_circular"
    assert f_circ.has_bilingual_content is True
    assert "en" in f_circ.languages
    assert "hi" in f_circ.languages

    # 5. Certificate
    dss_cert = analyzer.analyze(parsed_certificate)
    f_cert = dss_cert.feature_vector
    assert f_cert.doc_type == "certificate"
    assert f_cert.has_signature_blocks is True


def test_dss_determinism_property(sample_gov_order_path: Path, sample_rti_path: Path):
    """Verify that identical document structures ALWAYS yield identical DSS hashes."""
    analyzer = DSSAnalyzer()

    # Repeatedly parse and analyze the exact same files
    doc1 = parse_document(sample_gov_order_path)
    dss1 = analyzer.analyze(doc1)

    doc2 = parse_document(sample_gov_order_path)
    dss2 = analyzer.analyze(doc2)

    # Hashes and canonical dicts must be 100% identical
    assert dss1.signature_hash == dss2.signature_hash
    assert dss1.feature_vector.to_canonical_dict() == dss2.feature_vector.to_canonical_dict()

    # Test on RTI document as well
    rti1 = parse_document(sample_rti_path)
    dss_rti1 = analyzer.analyze(rti1)

    rti2 = parse_document(sample_rti_path)
    dss_rti2 = analyzer.analyze(rti2)

    assert dss_rti1.signature_hash == dss_rti2.signature_hash
    assert dss_rti1.signature_hash != dss1.signature_hash


def test_dss_structural_similarity_scoring(
    parsed_gov_order: DocumentNode,
    parsed_rti: DocumentNode,
    sample_gov_order_path: Path,
):
    """Verify structural similarity computation between DSS signatures."""
    analyzer = DSSAnalyzer()

    dss_go1 = analyzer.analyze(parsed_gov_order)
    dss_rti = analyzer.analyze(parsed_rti)

    # Different doc types must score 0.0
    sim_diff = DSSAnalyzer.compute_structural_similarity(dss_go1, dss_rti)
    assert sim_diff == 0.0

    # Exactly identical documents must score 1.0
    dss_go2 = analyzer.analyze(parse_document(sample_gov_order_path))
    sim_same = DSSAnalyzer.compute_structural_similarity(dss_go1, dss_go2)
    assert sim_same == 1.0
