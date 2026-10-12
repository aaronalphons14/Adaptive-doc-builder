"""Post-Render Classification Watermark Verifier (Mechanism N3).

Architectural Role:
    Verifies that required classification watermarks (e.g. RESTRICTED, CONFIDENTIAL, SECRET)
    are present in the final rendered output artifact before release.
"""

from __future__ import annotations

from typing import Optional, Tuple, Union


class WatermarkCheck:
    """Verifies that mandatory classification watermarks are present in the output."""

    def check(
        self,
        rendered_artifact: Union[str, bytes],
        expected_watermark: str,
        rendered_text: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Verify presence of expected watermark string in rendered output."""
        expected_upper = expected_watermark.upper()

        if isinstance(rendered_artifact, str):
            if expected_upper in rendered_artifact.upper():
                return True, f"Verified: Watermark '{expected_upper}' present in rendered markup."
            return False, f"Violation: Mandatory watermark '{expected_upper}' missing from output markup."

        elif isinstance(rendered_artifact, bytes):
            # Check within plain text or raw byte stream
            if rendered_text and expected_upper in rendered_text.upper():
                return True, f"Verified: Watermark '{expected_upper}' present in rendered document."
            # Check ASCII/UTF-8 representation in binary stream
            if expected_upper.encode("utf-8") in rendered_artifact.upper():
                return True, f"Verified: Watermark '{expected_upper}' present in binary document stream."
            return False, f"Violation: Mandatory watermark '{expected_upper}' missing from binary output."

        return False, "Violation: Unable to inspect rendered output for watermark."
