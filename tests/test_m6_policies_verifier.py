"""Tests for Milestone 6: Policies, Post-Render Verifier, and Output Blocking."""

import pytest

from autodoc.core.exceptions import ComplianceError
from autodoc.core.types import Classification
from autodoc.patterns.builder import PipelineContext
from autodoc.patterns.composite import DocumentNode, ParagraphNode
from autodoc.patterns.singleton import PolicyRegistry
from autodoc.synthesis.synthesizer import PipelineSynthesizer
from autodoc.verifier.verifier import VerifierStage


def test_policy_registry_loading_and_activation(parsed_rti: DocumentNode, parsed_gov_order: DocumentNode):
    """Verify PolicyRegistry loads policies.yaml and evaluates applicable policies."""
    registry = PolicyRegistry.get_instance()
    all_policies = registry.get_all_policies()
    assert len(all_policies) >= 3

    from autodoc.analysis.dss import DSSAnalyzer
    analyzer = DSSAnalyzer()

    # RTI reply has sensitive data -> policy_dpdp_privacy must be active
    dss_rti = analyzer.analyze(parsed_rti)
    active_rti = [p.id for p in registry.get_active_policies(dss_rti.feature_vector)]
    assert "policy_dpdp_privacy" in active_rti

    # Government order is unclassified with no PII
    dss_go = analyzer.analyze(parsed_gov_order)
    active_go = [p.id for p in registry.get_active_policies(dss_go.feature_vector)]
    assert "policy_dpdp_privacy" not in active_go


def test_compliance_by_construction_refusal():
    """Verify synthesizer strictly REFUSES to emit a pipeline violating an active policy."""
    synthesizer = PipelineSynthesizer()

    # Document containing sensitive personal data
    doc = DocumentNode()
    doc.add(ParagraphNode(text="Citizen Aadhaar 2345 6789 0124 and Phone +91 9876543210."))

    # Caller attempts to suppress mandatory redaction
    with pytest.raises(ComplianceError, match="Active policy.*mandates 'RedactionDecorator'"):
        synthesizer.synthesize(doc, options={"skip_redaction": True})


def test_rti_sample_output_zero_unmasked_pii(parsed_rti: DocumentNode):
    """Acceptance Criterion 6: RTI sample output has zero unmasked IDs/phones/emails (asserted)."""
    synthesizer = PipelineSynthesizer()

    # Synthesize complete compliant pipeline for RTI document
    res = synthesizer.synthesize(parsed_rti, {"format": "html"})
    context = PipelineContext(document=parsed_rti, dss=res.dss, options={"format": "html"})

    # Execute pipeline through rendering and post-render verification
    out_ctx = res.pipeline.execute(context)

    # 1. Pipeline verification passed
    assert out_ctx.verification_passed is True
    assert len(out_ctx.verification_errors) == 0

    # 2. Strict independent inspection of final rendered HTML
    rendered_html = out_ctx.rendered_artifact
    assert isinstance(rendered_html, str)

    # Assert raw PII strings from 03_rti_reply.json are ABSENT from the output
    assert "5489 2104 7832" not in rendered_html, "Raw Aadhaar leaked in rendered output!"
    assert "ABCDE1234F" not in rendered_html, "Raw PAN leaked in rendered output!"
    assert "9876543210" not in rendered_html, "Raw mobile phone leaked in rendered output!"
    assert "rameshwar.dayal84@example.com" not in rendered_html, "Raw email leaked in rendered output!"

    # Assert masked replacements ARE present
    assert "XXXX-XXXX-" in rendered_html or "[EXEMPT" in rendered_html


def test_verifier_blocks_intentionally_non_compliant_case(parsed_gov_order: DocumentNode):
    """Acceptance Criterion 5: Verifier blocks an intentionally non-compliant case (test injects a leak)."""
    verifier_stage = VerifierStage(block_on_violation=True)

    # Construct context with an injected unmasked PII leak in the rendered artifact
    leaked_html = (
        "<!DOCTYPE html><html lang='en'><head><title>Order</title></head><body>"
        "<main><h1>Sanction Order</h1>"
        "<p>Beneficiary Aadhaar Number: 2345 6789 0124 (LEAKED UNMASKED!)</p>"
        "<p>Contact Phone: +91 9876543210</p>"
        "</main></body></html>"
    )

    from autodoc.analysis.dss import DSSAnalyzer
    dss = DSSAnalyzer().analyze(parsed_gov_order)
    # Simulate active privacy policy
    dss.feature_vector.sensitive_data_count = 1

    bad_context = PipelineContext(
        document=parsed_gov_order,
        dss=dss,
        rendered_artifact=leaked_html,
        rendered_text="Beneficiary Aadhaar: 2345 6789 0124, Phone: +91 9876543210",
    )

    # Verifier MUST raise ComplianceError and block output release
    with pytest.raises(ComplianceError) as exc_info:
        verifier_stage.execute(bad_context)

    err_msg = str(exc_info.value)
    assert "Output release BLOCKED" in err_msg
    assert "PII Leakage Detected" in err_msg


def test_watermark_verifier_blocks_missing_classification(parsed_gov_order: DocumentNode):
    """Verify that a classified document missing a required watermark is blocked."""
    parsed_gov_order.doc_metadata.classification = Classification.SECRET

    verifier_stage = VerifierStage(block_on_violation=True)

    # Rendered artifact missing the SECRET watermark
    unmarked_html = (
        "<!DOCTYPE html><html lang='en'><head><title>Gov Order</title></head><body>"
        "<main><h1>Routine Announcement Without Watermark</h1></main></body></html>"
    )

    from autodoc.analysis.dss import DSSAnalyzer
    dss = DSSAnalyzer().analyze(parsed_gov_order)

    context = PipelineContext(
        document=parsed_gov_order,
        dss=dss,
        rendered_artifact=unmarked_html,
        rendered_text="Routine Announcement Without Watermark",
    )

    with pytest.raises(ComplianceError, match="Mandatory watermark 'SECRET' missing"):
        verifier_stage.execute(context)
