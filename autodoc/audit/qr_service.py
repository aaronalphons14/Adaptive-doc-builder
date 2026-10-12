"""QR Code Generation & Verification URL Service (Mechanism N5).

Architectural Role:
    Generates cryptographic verification tokens and scannable QR codes embedded in
    government documents. The QR code encodes a public verification URL resolving
    to the document's tamper-evident audit record and DSS fingerprint.
"""

from __future__ import annotations

import base64
import io
from typing import Dict, Optional

import qrcode  # type: ignore


class QRVerificationService:
    """Service generating verification URLs, tokens, and embedded QR code images."""

    def __init__(self, base_portal_url: str = "https://gov.in/autodoc/verify") -> None:
        self.base_portal_url = base_portal_url

    def generate_verification_data(
        self,
        document_id: str,
        dss_hash: str,
        audit_entry_hash: Optional[str] = None,
    ) -> Dict[str, str]:
        """Construct the verification URL, human-readable token, and base64 QR code image."""
        audit_id = audit_entry_hash[:16] if audit_entry_hash else dss_hash[:16]
        verification_url = (
            f"{self.base_portal_url}?doc_id={document_id}&dss={dss_hash[:16]}&audit={audit_id}"
        )
        token = f"V-GOV-{document_id[-6:] if len(document_id) >= 6 else document_id}-{dss_hash[:8]}".upper()

        # Generate QR Code image in PNG format
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=2,
        )
        qr.add_data(verification_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#1e3a8a", back_color="#ffffff")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()
        base64_img = base64.b64encode(png_bytes).decode("ascii")
        data_uri = f"data:image/png;base64,{base64_img}"

        return {
            "verification_url": verification_url,
            "verification_token": token,
            "qr_data_uri": data_uri,
        }
