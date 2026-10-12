"""Facade Pattern: Unified High-Level Document Generation Entry Point.

Architectural Role:
    The Facade pattern wraps the entire AutoDoc-Gov subsystem (multi-format parsers,
    DSS analyzers, rule engine, DAG topological sorters, Builder pipelines, renderers,
    decorators, post-render verifiers, self-healing engines, hash-chained audit loggers,
    and QR verification services) behind a single, cohesive, client-friendly interface:
    `AutoDocFacade`.

    Key API operations:
    - `generate()`: End-to-end parse, synthesize, heal, render, verify, audit, and emit.
    - `plan()`: Dry-run mode for officers to inspect planned stages without rendering.
    - `verify()`: Independent post-render compliance verification.
    - `audit_verify()`: Cryptographic hash chain tamper validation.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from autodoc.analysis.parser import parse_document
from autodoc.audit.hash_chain import AuditEntry, HashChainAuditLogger
from autodoc.audit.qr_service import QRVerificationService
from autodoc.audit.report_generator import AssemblyReportGenerator
from autodoc.audit.signer import MockPKIDigitalSigner
from autodoc.core.exceptions import ApprovalRequiredError
from autodoc.core.models import DSSSignature
from autodoc.core.types import Classification, OutputFormat
from autodoc.patterns.builder import PipelineContext
from autodoc.patterns.composite import DocumentNode
from autodoc.synthesis.self_healing import SelfHealingEngine
from autodoc.synthesis.synthesizer import PipelineSynthesizer


@dataclass
class GenerationResult:
    """Consolidated outcome of the generate() facade operation."""
    document_id: str
    format: str
    artifact: Union[str, bytes]
    dss: DSSSignature
    assembly_report_dict: Dict[str, Any]
    assembly_report_markdown: str
    audit_entry: AuditEntry
    verification_passed: bool
    output_path: Optional[Path] = None


@dataclass
class PlanResult:
    """Outcome of the plan() dry-run facade operation."""
    document_id: str
    dss: DSSSignature
    ordered_stages: List[str]
    fired_rules: List[Dict[str, Any]]
    conflict_log: List[str]
    mermaid_diagram: str
    approval_required: bool
    classification: str


class AutoDocFacade:
    """Unified Facade for all AutoDoc-Gov platform services."""

    def __init__(
        self,
        synthesizer: Optional[PipelineSynthesizer] = None,
        audit_logger: Optional[HashChainAuditLogger] = None,
        qr_service: Optional[QRVerificationService] = None,
        signer: Optional[MockPKIDigitalSigner] = None,
    ) -> None:
        self.synthesizer = synthesizer or PipelineSynthesizer()
        self.audit_logger = audit_logger or HashChainAuditLogger.get_instance()
        self.qr_service = qr_service or QRVerificationService()
        self.signer = signer or MockPKIDigitalSigner()
        self.report_generator = AssemblyReportGenerator()
        self.self_healing_engine = SelfHealingEngine()

    def plan(
        self,
        input_data: Union[str, Path, DocumentNode],
        options: Optional[Dict[str, Any]] = None,
    ) -> PlanResult:
        """Dry-run mode: synthesizes pipeline and returns plan WITHOUT executing or rendering."""
        options = options or {}
        doc = input_data if isinstance(input_data, DocumentNode) else parse_document(input_data)
        doc_id = doc.doc_metadata.document_number or doc.doc_metadata.title

        synth_result = self.synthesizer.synthesize(doc, options)

        classification = doc.doc_metadata.classification.value
        approval_required = classification in ["confidential", "secret"]

        return PlanResult(
            document_id=doc_id,
            dss=synth_result.dss,
            ordered_stages=synth_result.pipeline.get_stage_names(),
            fired_rules=[asdict(r) for r in synth_result.fired_rules],
            conflict_log=synth_result.conflict_log,
            mermaid_diagram=synth_result.pipeline.to_mermaid(),
            approval_required=approval_required,
            classification=classification,
        )


    def generate(
        self,
        input_data: Union[str, Path, DocumentNode],
        output_format: Union[str, OutputFormat] = OutputFormat.HTML,
        options: Optional[Dict[str, Any]] = None,
        approval_token: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> GenerationResult:
        """End-to-end execution: parse, check approval gate, synthesize, heal, render, verify, and audit."""
        options = options or {}
        fmt_str = output_format.value if isinstance(output_format, OutputFormat) else str(output_format).lower()
        options["format"] = fmt_str

        # 1. Parse document into Composite tree
        doc = input_data if isinstance(input_data, DocumentNode) else parse_document(input_data)
        doc_id = doc.doc_metadata.document_number or doc.node_id

        # 2. Government Feature: Approval Gate for High-Risk / Classified Documents
        classification = doc.doc_metadata.classification
        if classification in [Classification.CONFIDENTIAL, Classification.SECRET]:
            valid_approval = approval_token or doc.doc_metadata.approval_token
            if not valid_approval:
                raise ApprovalRequiredError(
                    f"Approval Gate Blocked: Document '{doc_id}' is classified as "
                    f"'{classification.value.upper()}' and requires an officer approval token before release.",
                    classification=classification.value,
                    doc_id=doc_id,
                )

        # 3. Synthesize processing pipeline (N2)
        synth_result = self.synthesizer.synthesize(doc, options)

        # 4. Execute pipeline with self-healing fallback planning (N4)
        context = PipelineContext(
            document=doc,
            dss=synth_result.dss,
            options=options,
            format=OutputFormat(fmt_str),
            approval_token=approval_token,
            is_approved=bool(approval_token),
        )

        context = self.self_healing_engine.execute_with_self_healing(
            synth_result.pipeline, context
        )

        artifact = context.rendered_artifact
        if artifact is None:
            raise RuntimeError("Pipeline completed without generating a rendered artifact.")

        # 5. Pluggable Digital Signature Hook (Feature 7)
        raw_bytes = artifact.encode("utf-8") if isinstance(artifact, str) else artifact
        sig_result = self.signer.sign(raw_bytes, key_alias=doc.doc_metadata.signatory_name)

        # 6. QR Verification Token (Mechanism N5)
        qr_info = self.qr_service.generate_verification_data(
            document_id=doc_id,
            dss_hash=synth_result.dss.signature_hash,
            audit_entry_hash=None, # Will be linked with audit
        )

        # 7. Record Hash-Chained Audit Entry (Mechanism N5)
        audit_entry = self.audit_logger.record(
            document_id=doc_id,
            dss_hash=synth_result.dss.signature_hash,
            output_format=fmt_str,
            rules_fired=[r.rule_id for r in synth_result.fired_rules],
            stages_executed=synth_result.pipeline.get_stage_names(),
            verification_passed=context.verification_passed,
            extra_metadata={
                "sign_token": sig_result["sign_token"],
                "verification_token": qr_info["verification_token"],
                "execution_time_ms": context.execution_time_ms,
            },
        )

        # 8. Compile Assembly Report (Mechanism N5)
        report_data = dict(synth_result.assembly_report)
        report_data.update({
            "verification_token": qr_info["verification_token"],
            "verification_url": qr_info["verification_url"],
            "digital_signature": sig_result,
            "audit_entry": asdict(audit_entry),
            "verification_result": {
                "passed": context.verification_passed,
                "violations": context.verification_errors,
                "checks_executed": context.stage_results.get("VerifierStage", {}).get("checks_executed", []),
            },
            "fallbacks_used": context.assembly_report.get("fallbacks_used", []),
        })

        report_md = self.report_generator.generate_markdown_report(report_data)

        # 9. Optionally persist artifact and reports to disk
        output_file_path: Optional[Path] = None
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            clean_name = doc_id.replace("/", "_").replace(" ", "_")
            ext = f".{fmt_str}"
            output_file_path = output_dir / f"{clean_name}{ext}"

            if isinstance(artifact, str):
                output_file_path.write_text(artifact, encoding="utf-8")
            else:
                output_file_path.write_bytes(artifact)

            # Also persist assembly report
            (output_dir / f"{clean_name}_report.md").write_text(report_md, encoding="utf-8")
            (output_dir / f"{clean_name}_report.json").write_text(
                json.dumps(report_data, indent=2), encoding="utf-8"
            )

        return GenerationResult(
            document_id=doc_id,
            format=fmt_str,
            artifact=artifact,
            dss=synth_result.dss,
            assembly_report_dict=report_data,
            assembly_report_markdown=report_md,
            audit_entry=audit_entry,
            verification_passed=context.verification_passed,
            output_path=output_file_path,
        )

    def audit_verify(self) -> Tuple[bool, Optional[str]]:
        """Verify the cryptographic integrity of the audit log hash chain."""
        return self.audit_logger.verify_integrity()
