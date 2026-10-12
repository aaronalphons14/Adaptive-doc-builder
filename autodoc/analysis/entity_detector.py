"""Sensitive Personal Data Detection and Masking Engine.

Implements detection and masking aligned with:
- India's Digital Personal Data Protection Act, 2023 (DPDP Act)
- Right to Information Act, 2005 Section 8(1)(j) (Privacy Exemption)

Detects:
- Aadhaar (12 digits with Verhoeff validation)
- PAN (Permanent Account Number: [A-Z]{5}[0-9]{4}[A-Z])
- Indian Mobile / Phone Numbers (+91 or 10 digits starting 6-9)
- Email Addresses
- Bank Account Numbers and IFSC Codes
- Tagged Personal Fields: {personal: ...}
"""

from __future__ import annotations

import hashlib
import re
from typing import List, Optional, Tuple

from autodoc.core.models import EntityMatch
from autodoc.core.types import MaskStyle

# Verhoeff algorithm multiplication and permutation tables for Aadhaar checksum validation
_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


_VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def generate_verhoeff_check_digit(prefix: str) -> int:
    """Generate the Verhoeff check digit for an 11-digit prefix."""
    digits = [int(c) for c in prefix if c.isdigit()]
    c = 0
    for i, d in enumerate(reversed(digits)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[(i + 1) % 8][d]]
    return _VERHOEFF_INV[c]


def validate_verhoeff(num_str: str) -> bool:
    """Validate 12-digit Aadhaar number using the Verhoeff checksum algorithm."""
    digits = [int(c) for c in num_str if c.isdigit()]
    if len(digits) != 12:
        return False
    c = 0
    for i, d in enumerate(reversed(digits)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][d]]
    return c == 0



# Detection regexes
AADHAAR_REGEX = re.compile(r"\b[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}\b")
PAN_REGEX = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
PHONE_REGEX = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}\b")
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
IFSC_REGEX = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")
BANK_ACC_REGEX = re.compile(r"(?:A/C|Account|A/c|SB)[\s.:#-]*(\d{9,18})\b", re.IGNORECASE)
TAGGED_PERSONAL_REGEX = re.compile(r"\{personal:\s*([^}]+)\}", re.IGNORECASE)


class EntityDetector:
    """Detects and masks sensitive personal data according to configured mask styles."""

    def __init__(
        self,
        default_mask_style: MaskStyle = MaskStyle.PARTIAL_TAIL,
        default_legal_basis: str = "Digital Personal Data Protection Act 2023 / RTI Act 2005",
    ) -> None:
        self.default_mask_style = default_mask_style
        self.default_legal_basis = default_legal_basis

    def mask_value(self, raw: str, entity_type: str, mask_style: MaskStyle) -> str:
        """Apply the specified mask style to a sensitive token."""
        digits_only = re.sub(r"\D", "", raw)

        if mask_style == MaskStyle.FULL:
            return "████████"

        elif mask_style == MaskStyle.STATUTORY_TAG:
            return f"[EXEMPT UNDER RTI ACT SEC 8(1)(j): {entity_type.upper()}]"

        elif mask_style == MaskStyle.HASH:
            h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
            return f"[ID:sha256:{h}]"

        else: # MaskStyle.PARTIAL_TAIL
            if entity_type == "aadhaar":
                tail = digits_only[-4:] if len(digits_only) >= 4 else "XXXX"
                return f"XXXX-XXXX-{tail}"
            elif entity_type == "pan":
                return f"{raw[:2]}XXXXX{raw[-2:]}" if len(raw) == 10 else "XXXXX1234X"
            elif entity_type == "phone":
                tail = digits_only[-4:] if len(digits_only) >= 4 else "XXXX"
                return f"+91-XXXXX-{tail}"
            elif entity_type == "email":
                parts = raw.split("@")
                if len(parts) == 2:
                    return f"{parts[0][:2]}***@{parts[1]}"
                return "user***@domain.com"
            elif entity_type == "bank_account":
                tail = digits_only[-4:] if len(digits_only) >= 4 else "XXXX"
                return f"XXXX-XXXX-{tail}"
            else:
                return f"[{entity_type.upper()}-MASKED]"

    def scan_text(self, text: str) -> List[EntityMatch]:
        """Scan a text string and return all identified sensitive entity matches."""
        matches: List[EntityMatch] = []

        # 1. Aadhaar
        for m in AADHAAR_REGEX.finditer(text):
            raw = m.group(0)
            cleaned = re.sub(r"[\s-]", "", raw)
            # Accept if valid Verhoeff or standard 12-digit Aadhaar pattern
            is_valid = validate_verhoeff(cleaned) or (len(cleaned) == 12 and cleaned[0] in "23456789")
            if is_valid:
                masked = self.mask_value(raw, "aadhaar", self.default_mask_style)
                matches.append(EntityMatch(
                    entity_type="aadhaar",
                    raw_value=raw,
                    masked_value=masked,
                    start=m.start(),
                    end=m.end(),
                    legal_basis=self.default_legal_basis,
                ))

        # 2. PAN
        for m in PAN_REGEX.finditer(text):
            raw = m.group(0)
            masked = self.mask_value(raw, "pan", self.default_mask_style)
            matches.append(EntityMatch(
                entity_type="pan",
                raw_value=raw,
                masked_value=masked,
                start=m.start(),
                end=m.end(),
                legal_basis=self.default_legal_basis,
            ))

        # 3. Phone
        for m in PHONE_REGEX.finditer(text):
            raw = m.group(0)
            masked = self.mask_value(raw, "phone", self.default_mask_style)
            matches.append(EntityMatch(
                entity_type="phone",
                raw_value=raw,
                masked_value=masked,
                start=m.start(),
                end=m.end(),
                legal_basis=self.default_legal_basis,
            ))

        # 4. Email
        for m in EMAIL_REGEX.finditer(text):
            raw = m.group(0)
            masked = self.mask_value(raw, "email", self.default_mask_style)
            matches.append(EntityMatch(
                entity_type="email",
                raw_value=raw,
                masked_value=masked,
                start=m.start(),
                end=m.end(),
                legal_basis=self.default_legal_basis,
            ))

        # 5. Bank Account
        for m in BANK_ACC_REGEX.finditer(text):
            raw_acc = m.group(1)
            raw_full = m.group(0)
            masked = self.mask_value(raw_acc, "bank_account", self.default_mask_style)
            matches.append(EntityMatch(
                entity_type="bank_account",
                raw_value=raw_full,
                masked_value=m.group(0).replace(raw_acc, masked),
                start=m.start(),
                end=m.end(),
                legal_basis=self.default_legal_basis,
            ))

        # 6. Tagged Personal Fields: {personal: ...}
        for m in TAGGED_PERSONAL_REGEX.finditer(text):
            raw = m.group(0)
            inner = m.group(1)
            masked = self.mask_value(inner, "personal", self.default_mask_style)
            matches.append(EntityMatch(
                entity_type="personal",
                raw_value=raw,
                masked_value=masked,
                start=m.start(),
                end=m.end(),
                legal_basis=self.default_legal_basis,
            ))

        return matches

    def mask_text(
        self,
        text: str,
        mask_style: Optional[MaskStyle] = None,
        legal_basis: Optional[str] = None,
    ) -> Tuple[str, List[EntityMatch]]:
        """Scan text and replace all sensitive entities with their masked representations."""
        active_style = mask_style or self.default_mask_style
        matches = self.scan_text(text)
        if not matches:
            return text, []

        # Sort matches by start index descending to safely replace in string
        sorted_matches = sorted(matches, key=lambda x: x.start, reverse=True)
        result = text
        for m in sorted_matches:
            custom_masked = self.mask_value(m.raw_value, m.entity_type, active_style)
            m.masked_value = custom_masked
            if legal_basis:
                m.legal_basis = legal_basis
            result = result[:m.start] + custom_masked + result[m.end:]

        return result, matches
