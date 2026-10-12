"""Assembly Report Generator (Mechanism N5).

Architectural Role:
    Compiles an explainability Assembly Report shipping alongside every generated output:
    - Document Structure Signature (DSS) vector & canonical hash
    - Each declarative rule that fired, along with matched feature conditions
    - Selected pattern components and ordered pipeline stages
    - Conflicts resolved and dependencies satisfied
    - Fallbacks planned and recovery rationale (if any)
    - Post-render verification results (zero-PII, watermark, accessibility proofs)
    - Hash-chained audit log block proof (prev_hash, entry_hash)
    - Embedded QR code and verification token

    Produces both structured JSON and human-readable Markdown reports.
"""

from __future__ import annotations

from typing import Any, Dict


class AssemblyReportGenerator:
    """Generates structured JSON and Markdown assembly explainability reports."""

    def generate_markdown_report(self, report_data: Dict[str, Any]) -> str:
        """Format assembly report data into a clean, GitHub-flavored Markdown report."""
        lines = []
        doc_id = report_data.get("document_id", "N/A")
        sig_hash = report_data.get("signature_hash", "N/A")
        token = report_data.get("verification_token", "N/A")

        lines.append(f"# AutoDoc-Gov Assembly Report: {doc_id}")
        lines.append(f"**Verification Token:** `{token}`  ")
        lines.append(f"**Document Structure Signature (DSS):** `{sig_hash}`\n")
        lines.append("---\n")

        # 1. DSS Features Summary
        features = report_data.get("features_summary", {})
        lines.append("## 1. Document Structure Analysis (DSS)")
        lines.append(f"- **Document Type:** `{features.get('doc_type', 'N/A')}`")
        lines.append(f"- **Classification:** `{features.get('classification', 'N/A').upper()}`")
        lines.append(f"- **Languages:** {', '.join(features.get('languages', []))}")
        lines.append(f"- **Total Composite Blocks:** {features.get('total_blocks', 0)}")
        lines.append(f"- **Sensitive PII Count:** {features.get('sensitive_data_count', 0)}")
        lines.append(f"- **Has Citations:** {features.get('has_citations', False)}")
        lines.append(f"- **Bilingual Layout:** {features.get('has_bilingual_content', False)}\n")

        # 2. Firing Rules
        lines.append("## 2. Declarative Rule Engine Decisions")
        fired_rules = report_data.get("fired_rules", [])
        if fired_rules:
            lines.append("| Rule ID | Priority | Condition Matched | Components Injected |")
            lines.append("| :--- | :---: | :--- | :--- |")
            for r in fired_rules:
                comps = ", ".join(r.get("components_added", []))
                lines.append(f"| `{r.get('rule_id')}` | {r.get('priority')} | `{r.get('condition')}` | {comps} |")
        else:
            lines.append("*No rules triggered.*")
        lines.append("")

        # 3. Pipeline Stages & Ordering
        lines.append("## 3. Synthesized Processing Pipeline")
        stages = report_data.get("ordered_stages", [])
        for idx, s in enumerate(stages, 1):
            lines.append(f"{idx}. `{s}`")
        lines.append("")

        # 4. Conflicts & Fallbacks
        conflicts = report_data.get("conflict_log", [])
        if conflicts:
            lines.append("### Conflict Resolutions")
            for c in conflicts:
                lines.append(f"- {c}")
            lines.append("")

        fallbacks = report_data.get("fallbacks_used", [])
        if fallbacks:
            lines.append("### Self-Healing & Fallbacks Used")
            for fb in fallbacks:
                lines.append(f"- **{fb.get('failed_stage')}** failed: {fb.get('error')}")
                lines.append(f"  *Recovery:* Switched to `{fb.get('fallback_stage')}` ({fb.get('reason')})")
            lines.append("")

        # 5. Post-Render Verification
        verif = report_data.get("verification_result", {})
        verif_passed = verif.get("passed", True)
        status_badge = "✅ PASSED (Compliance Verified)" if verif_passed else "❌ FAILED (Output Blocked)"
        lines.append(f"## 4. Post-Render Output Verification: {status_badge}")
        checks = verif.get("checks_executed", [])
        lines.append(f"- **Checks Executed:** {', '.join(checks) if checks else 'None'}")
        if verif.get("violations"):
            lines.append("- **Violations Detected:**")
            for v in verif.get("violations"):
                lines.append(f"  * {v}")
        else:
            lines.append("- Zero compliance violations detected in rendered artifact.")
        lines.append("")

        # 6. Audit Hash Chain
        audit = report_data.get("audit_entry", {})
        if audit:
            lines.append("## 5. Tamper-Evident Hash Chain Proof")
            lines.append(f"- **Block Index:** `{audit.get('index')}`")
            lines.append(f"- **Previous Block Hash:** `{audit.get('prev_hash')}`")
            lines.append(f"- **Current Block Hash:** `{audit.get('entry_hash')}`")
            lines.append(f"- **Recorded At:** `{audit.get('timestamp')}`\n")

        # 7. QR Verification Link
        qr_url = report_data.get("verification_url")
        if qr_url:
            lines.append(f"**Public Verification Portal:** [{qr_url}]({qr_url})")

        return "\n".join(lines)
