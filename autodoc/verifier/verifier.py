"""Master Post-Render Output Verifier and Pipeline Stage (Mechanism N3).

Architectural Role:
    Executes the post-render verification phase. Re-scans the rendered artifact
    (not the input) to verify compliance invariants:
    - Zero unmasked sensitive PII (Aadhaar, PAN, phone, email, bank accounts)
    - Required classification watermark presence
    - GIGW 3.0 / WCAG AA accessibility compliance

    Blocking Guarantee:
    If any active policy is violated in the final output artifact, the Verifier
    strictly blocks release by raising `ComplianceError` and recording violations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from autodoc.core.exceptions import ComplianceError, VerificationError
from autodoc.patterns.builder import IPipelineStage, PipelineContext
from autodoc.patterns.singleton import PolicyRegistry
from autodoc.verifier.accessibility_check import AccessibilityCheck
from autodoc.verifier.redaction_check import RedactionCheck
from autodoc.verifier.watermark_check import WatermarkCheck


@dataclass
class VerificationResult:
    """Consolidated outcome of the post-render verification inspection."""
    passed: bool
    violations: List[str] = field(default_factory=list)
    checks_executed: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class OutputVerifier:
    """Orchestrates all post-render compliance checks on the generated output artifact."""

    def __init__(self, policy_registry: Optional[PolicyRegistry] = None) -> None:
        self.policy_registry = policy_registry or PolicyRegistry.get_instance()
        self.redaction_check = RedactionCheck()
        self.watermark_check = WatermarkCheck()
        self.accessibility_check = AccessibilityCheck()

    def verify(
        self,
        rendered_artifact: Union[str, bytes],
        context: PipelineContext,
    ) -> VerificationResult:
        """Inspect rendered artifact against all active regulatory policies."""
        violations: List[str] = []
        checks_run: List[str] = []
        details: Dict[str, Any] = {}

        dss = context.dss
        active_policies = (
            self.policy_registry.get_active_policies(dss.feature_vector)
            if dss
            else self.policy_registry.get_all_policies()
        )

        for policy in active_policies:
            rules = policy.verifier_rules

            # 1. Zero-PII Check
            if rules.get("check_zero_pii"):
                checks_run.append("ZeroPIICheck")
                pii_pass, leaks, summary = self.redaction_check.check(
                    rendered_artifact=rendered_artifact,
                    rendered_text=context.rendered_text,
                )
                details["zero_pii_check"] = {
                    "passed": pii_pass,
                    "summary": summary,
                    "leak_count": len(leaks),
                }
                if not pii_pass:
                    violations.append(
                        f"[{policy.name}] Compliance Breach: {summary}"
                    )

            # 2. Watermark Check
            if rules.get("check_watermark"):
                checks_run.append("WatermarkCheck")
                classification = context.document.doc_metadata.classification.value
                if classification != "unclassified":
                    expected_wm = context.options.get("watermark_text") or classification.upper()
                    wm_pass, wm_msg = self.watermark_check.check(
                        rendered_artifact=rendered_artifact,
                        expected_watermark=expected_wm,
                        rendered_text=context.rendered_text,
                    )
                    details["watermark_check"] = {"passed": wm_pass, "message": wm_msg}
                    if not wm_pass:
                        violations.append(f"[{policy.name}] {wm_msg}")

            # 3. Accessibility Check (GIGW 3.0 / WCAG AA applies to HTML web outputs)
            if rules.get("check_accessibility") and isinstance(rendered_artifact, str) and context.options.get("format", "html") == "html":
                checks_run.append("AccessibilityCheck")
                acc_pass, acc_errors = self.accessibility_check.check(rendered_artifact)
                details["accessibility_check"] = {
                    "passed": acc_pass,
                    "errors": acc_errors,
                }
                if not acc_pass:
                    violations.extend([f"[{policy.name}] {e}" for e in acc_errors])

        passed = len(violations) == 0
        return VerificationResult(
            passed=passed,
            violations=violations,
            checks_executed=checks_run,
            details=details,
        )


class VerifierStage(IPipelineStage):
    """Pipeline stage executing the post-render OutputVerifier and enforcing blocking."""

    def __init__(
        self,
        stage_id: str = "VerifierStage",
        params: Optional[Dict[str, Any]] = None,
        block_on_violation: bool = True,
    ) -> None:
        super().__init__(stage_id, params)
        self.block_on_violation = block_on_violation
        self.verifier = OutputVerifier()

    def execute(self, context: PipelineContext) -> PipelineContext:
        if context.rendered_artifact is None:
            raise VerificationError("Cannot run VerifierStage: No rendered artifact found in pipeline context.")

        result = self.verifier.verify(context.rendered_artifact, context)
        context.verification_passed = result.passed
        context.verification_errors = result.violations

        context.stage_results[self.stage_id] = {
            "status": "passed" if result.passed else "failed",
            "passed": result.passed,
            "violations_count": len(result.violations),
            "checks_executed": result.checks_executed,
            "details": result.details,
        }

        if not result.passed and self.block_on_violation:
            # Block output release by raising ComplianceError
            violation_summary = "; ".join(result.violations)
            raise ComplianceError(
                message=f"Output release BLOCKED due to compliance verification failure: {violation_summary}",
                violations=[{"violation": v} for v in result.violations],
            )

        return context
