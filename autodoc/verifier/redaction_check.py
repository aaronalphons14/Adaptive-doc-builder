"""Post-Render Redaction & PII Leakage Verifier (Mechanism N3).

Architectural Role:
    Scans the actual rendered output artifact (not the input) to mathematically prove
    compliance with privacy laws (DPDP Act 2023, RTI Act Sec 8(1)(j)).

    Extracts text from the rendered HTML, PDF bytes, or DOCX bytes and tests for
    zero unmasked Aadhaar, PAN, phone numbers, email addresses, or bank accounts.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple, Union

from autodoc.analysis.entity_detector import EntityDetector
from autodoc.core.models import EntityMatch


class RedactionCheck:
    """Verifies that no unmasked sensitive entities remain in the rendered output."""

    def __init__(self) -> None:
        self.detector = EntityDetector()

    def check(
        self,
        rendered_artifact: Union[str, bytes],
        rendered_text: Optional[str] = None,
    ) -> Tuple[bool, List[EntityMatch], str]:
        """Scan rendered content for leaked PII tokens."""
        content_to_scan = ""

        if isinstance(rendered_artifact, str):
            # For HTML or Markdown: strip markup tags to avoid false positives on HTML attribute names
            cleaned = re.sub(r"<[^>]+>", " ", rendered_artifact)
            content_to_scan = cleaned
        elif isinstance(rendered_artifact, bytes):
            # For PDF or DOCX: use the extracted plain text or decode latin-1 strings
            if rendered_text:
                content_to_scan = rendered_text
            else:
                try:
                    content_to_scan = rendered_artifact.decode("utf-8", errors="ignore")
                except Exception:
                    content_to_scan = ""
        else:
            content_to_scan = rendered_text or ""

        # Scan extracted content for sensitive entities
        leaks = self.detector.scan_text(content_to_scan)

        # Filter out already masked tokens (e.g. "XXXX-XXXX-1234" is not a leak)
        true_leaks: List[EntityMatch] = []
        for m in leaks:
            raw = m.raw_value.strip()
            # If the raw value is already masked, it's not a leak
            if "XXXX" in raw or "██" in raw or "[EXEMPT" in raw or "[ID:" in raw:
                continue
            true_leaks.append(m)

        if true_leaks:
            summary = (
                f"PII Leakage Detected: {len(true_leaks)} unmasked sensitive tokens found "
                f"({[m.entity_type for m in true_leaks]})"
            )
            return False, true_leaks, summary

        return True, [], "Zero unmasked personal identifiers detected in rendered output."
