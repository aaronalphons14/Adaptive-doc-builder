"""Tests for Milestone 7: Audit Hash Chain, QR Verification, Fallback Planning, and Approval Gate."""

from pathlib import Path

import pytest

from autodoc.audit.hash_chain import HashChainAuditLogger
from autodoc.audit.qr_service import QRVerificationService
from autodoc.audit.signer import MockPKIDigitalSigner
from autodoc.core.exceptions import ApprovalRequiredError
from autodoc.core.types import Classification, OutputFormat
from autodoc.patterns.builder import (
    DocumentPipeline,
    IPipelineStage,
    PipelineContext,
)
from autodoc.patterns.composite import DocumentNode
from autodoc.patterns.facade import AutoDocFacade
from autodoc.synthesis.self_healing import SelfHealingEngine


def test_hash_chain_tamper_detection(tmp_path: Path):
    """Acceptance Criterion 8: Tampering with one audit entry makes audit-verify fail."""
    log_file = tmp_path / "test_audit_log.json"
    logger = HashChainAuditLogger(log_file=log_file)
    logger.clear()

    # Record 3 sequential blocks
    logger.record("DOC-001", "hash_001", "html", ["rule_1"], ["StageA"], True)
    logger.record("DOC-002", "hash_002", "pdf", ["rule_2"], ["StageB"], True)
    logger.record("DOC-003", "hash_003", "docx", ["rule_3"], ["StageC"], True)

    assert len(logger.get_entries()) == 3
    # Step 1: Untampered chain verification must PASS
    valid, msg = logger.verify_integrity()
    assert valid is True
    assert "3 blocks intact" in (msg or "")

    # Step 2: Deliberately tamper with Block 1 in historical storage
    raw_content = log_file.read_text(encoding="utf-8")
    # Mutate a byte in block 1: replace 'DOC-002' with 'DOC-TAMPERED'
    tampered_content = raw_content.replace("DOC-002", "DOC-TAMPERED")
    log_file.write_text(tampered_content, encoding="utf-8")

    # Reload logger from tampered file
    tampered_logger = HashChainAuditLogger(log_file=log_file)

    # Step 3: Audit verification MUST FAIL and pinpoint the tampered block
    valid_tampered, tamper_msg = tampered_logger.verify_integrity()
    assert valid_tampered is False
    assert "Tampering detected at block 1" in (tamper_msg or "")


def test_qr_verification_service():
    """Verify QR code generator emits valid verification URLs and base64 PNG images."""
    qr_svc = QRVerificationService(base_portal_url="https://delhi.gov.in/verify")
    data = qr_svc.generate_verification_data(
        document_id="GO-2026-FIN-104",
        dss_hash="7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
    )

    assert "https://delhi.gov.in/verify" in data["verification_url"]
    assert "GO-2026-FIN-104" in data["verification_url"]
    assert data["qr_data_uri"].startswith("data:image/png;base64,iVBOR")
    assert "V-GOV-" in data["verification_token"]


def test_pluggable_digital_signer():
    """Verify digital signing hook produces valid PKI signatures and seals."""
    signer = MockPKIDigitalSigner()
    payload = b"Sanction of expenditure INR 45,50,00,000"

    sig_res = signer.sign(payload, key_alias="SECRETARY-FINANCE")
    assert "DS-SECRETARY-FINANCE" in sig_res["sign_token"]
    assert "National Informatics Centre" in sig_res["certificate_issuer"]

    # Verify signature
    assert signer.verify(payload, sig_res["sign_token"]) is True
    # Tampered payload must fail
    assert signer.verify(b"Tampered payload", sig_res["sign_token"]) is False


def test_self_healing_fallback_planning_recovers_from_broken_renderer(parsed_gov_order: DocumentNode):
    """Acceptance Criterion 9: Fallback planning recovers from a deliberately broken renderer."""
    healing_engine = SelfHealingEngine()

    class DeliberatelyBrokenPdfRenderer(IPipelineStage):
        def __init__(self) -> None:
            super().__init__("BrokenPdfRenderer")

        def execute(self, context: PipelineContext) -> PipelineContext:
            raise RuntimeError("CRITICAL RENDERER FAILURE: Native graphics driver crash!")

    # Pipeline containing the broken renderer
    pipeline = DocumentPipeline(stages=[DeliberatelyBrokenPdfRenderer()])
    context = PipelineContext(document=parsed_gov_order, format=OutputFormat.PDF)

    # Healing engine must catch exception, switch to fallback, and complete execution
    healed_context = healing_engine.execute_with_self_healing(pipeline, context)

    assert healed_context.rendered_artifact is not None
    assert isinstance(healed_context.rendered_artifact, bytes)
    assert healed_context.rendered_artifact.startswith(b"%PDF")

    # Assembly report must record the fallback occurrence and reason
    fallbacks = healed_context.assembly_report.get("fallbacks_used", [])
    assert len(fallbacks) == 1
    assert fallbacks[0]["failed_stage"] == "BrokenPdfRenderer"
    assert "SelfHealing_FallbackPdfRenderer" in fallbacks[0]["fallback_stage"]


def test_dry_run_mode_and_approval_gate(parsed_gov_order: DocumentNode, tmp_path: Path):
    """Verify dry-run plan() mode and approval gate enforcement on classified documents."""
    facade = AutoDocFacade(audit_logger=HashChainAuditLogger(log_file=tmp_path / "facade_audit.json"))

    # 1. Test Dry-Run Plan Mode
    plan = facade.plan(parsed_gov_order, {"format": "pdf"})
    assert plan.document_id is not None
    assert len(plan.ordered_stages) >= 2
    assert "flowchart LR" in plan.mermaid_diagram
    assert plan.approval_required is False

    # 2. Test Approval Gate on Classified Document
    parsed_gov_order.doc_metadata.classification = Classification.CONFIDENTIAL

    # Attempting generate() without approval token must be BLOCKED
    with pytest.raises(ApprovalRequiredError, match="Approval Gate Blocked"):
        facade.generate(parsed_gov_order, output_format=OutputFormat.HTML)

    # Supplying authorized officer approval token opens the gate
    gen_result = facade.generate(
        parsed_gov_order,
        output_format=OutputFormat.HTML,
        approval_token="OFFICER-DIGITAL-TOKEN-2026-AUTH",
        output_dir=tmp_path / "out",
    )

    assert gen_result.verification_passed is True
    assert gen_result.artifact is not None
    clean_name = gen_result.document_id.replace("/", "_").replace(" ", "_")
    assert (tmp_path / "out" / f"{clean_name}_report.md").exists()

