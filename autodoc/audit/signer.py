"""Pluggable Digital Signature Hook Interface (Government Feature 7).

Architectural Role:
    Provides an extensible interface (`IDigitalSigner`) to attach cryptographic digital
    signatures to output documents, compliant with India's Information Technology Act, 2000
    (Sections 3 & 3A) and e-Mudhra / NIC PKI standards.

    Ships with `MockPKIDigitalSigner` for testing and demonstration.
"""

from __future__ import annotations

import hashlib
import hmac
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional


class IDigitalSigner(ABC):
    """Abstract contract for attaching digital signatures."""

    @abstractmethod
    def sign(
        self, data: bytes, key_alias: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sign document bytes and return signature metadata and token."""
        pass

    @abstractmethod
    def verify(self, data: bytes, signature_token: str) -> bool:
        """Verify the digital signature of given data bytes."""
        pass


class MockPKIDigitalSigner(IDigitalSigner):
    """Mock PKI / X.509 Digital Signer implementing HMAC-SHA256 government digital seals."""

    def __init__(self, secret_key: bytes = b"GOV_NIC_PKI_MASTER_SECRET_2026") -> None:
        self.secret_key = secret_key

    def sign(
        self, data: bytes, key_alias: Optional[str] = None
    ) -> Dict[str, Any]:
        alias = key_alias or "NIC-CERT-OFFICER-01"
        timestamp = datetime.utcnow().isoformat()
        digest = hashlib.sha256(data).hexdigest()

        # Compute HMAC signature
        sig_mac = hmac.new(self.secret_key, digest.encode("utf-8"), hashlib.sha256).hexdigest()
        sign_token = f"DS-{alias}-{sig_mac[:12].upper()}"

        return {
            "sign_token": sign_token,
            "signature_hex": sig_mac,
            "key_alias": alias,
            "certificate_issuer": "National Informatics Centre Certifying Authority (NIC-CA)",
            "certificate_serial": f"CERT-SN-2026-{digest[:8].upper()}",
            "signed_at": timestamp,
            "algorithm": "SHA256withRSA/HMAC",
        }

    def verify(self, data: bytes, signature_token: str) -> bool:
        digest = hashlib.sha256(data).hexdigest()
        expected_mac = hmac.new(self.secret_key, digest.encode("utf-8"), hashlib.sha256).hexdigest()
        expected_prefix = expected_mac[:12].upper()
        return expected_prefix in signature_token
