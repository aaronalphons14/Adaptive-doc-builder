"""Baseline Static Document Pipeline (Traditional Approach).

Architectural Contrast:
    Demonstrates the limitations of legacy government document builders:
    1. Rigid single fixed pipeline: Expects uniform JSON schema. Throws parse errors
       on Markdown or Plain Text inputs without manual configuration.
    2. Zero runtime synthesis: Hardcoded stage execution.
    3. Zero compliance-by-construction: Does not redact Aadhaar/PAN/phone/email
       (violating DPDP Act 2023 & RTI Act Sec 8(1)(j)).
    4. Zero classification awareness: Fails to enforce mandatory watermarks
       on 'confidential' or 'secret' documents.
    5. Zero self-healing: Unhandled errors result in unrecoverable pipeline aborts.
    6. Zero audit chain: Output has no cryptographic tamper-evident lineage.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict


class BaselineStaticPipeline:
    """Traditional hardcoded document generation pipeline."""

    def __init__(self) -> None:
        self.name = "BaselineStaticPipeline"

    def process(self, file_path: Path) -> Dict[str, Any]:
        """Process document through rigid fixed pipeline without runtime adaptation."""
        start_time = time.time()
        result: Dict[str, Any] = {
            "file": file_path.name,
            "success": False,
            "error": None,
            "pii_leaks": 0,
            "watermark_present": False,
            "classification": "unknown",
            "execution_time_ms": 0.0,
            "zero_config_handled": False,
        }

        try:
            # Step 1: Fixed Parser (Only handles JSON; fails on MD and TXT without custom code)
            if file_path.suffix.lower() != ".json":
                raise ValueError(
                    f"Baseline pipeline only supports JSON schema. "
                    f"Cannot parse {file_path.suffix} without custom adapter."
                )

            data = json.loads(file_path.read_text(encoding="utf-8"))
            classification = data.get("classification", "unclassified")
            result["classification"] = classification
            result["zero_config_handled"] = True

            # Step 2: Fixed HTML Assembly (Hardcoded template string)
            html_parts = [
                "<!DOCTYPE html>",
                "<html><head><title>Static Gov Doc</title></head><body>",
                f"<h1>{data.get('title', 'Document')}</h1>",
                f"<p>Document Number: {data.get('document_number', 'N/A')}</p>",
            ]

            # Step 3: Raw body serialization (NO PII REDACTION DECORATOR!)
            raw_text = ""
            for item in data.get("content", []):
                text = item.get("text", "")
                raw_text += " " + text
                html_parts.append(f"<p>{text}</p>")

            html_parts.append("</body></html>")
            rendered_html = "\n".join(html_parts)

            # Check for PII leaks in output (simulating post-audit scan)
            import re
            aadhaar_leaks = len(re.findall(r"\b\d{4}\s\d{4}\s\d{4}\b", rendered_html))
            pan_leaks = len(re.findall(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", rendered_html))
            result["pii_leaks"] = aadhaar_leaks + pan_leaks

            # Check if watermark was applied for classified doc (baseline has no watermark decorator)
            result["watermark_present"] = False

            result["success"] = True

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            result["zero_config_handled"] = False

        result["execution_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return result
