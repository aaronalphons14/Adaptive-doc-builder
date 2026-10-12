"""Cryptographic SHA-256 Hash-Chained Audit Log (Mechanism N5).

Architectural Role:
    Every document generation and verification event writes a tamper-evident audit entry.
    Each entry includes the previous entry's SHA-256 cryptographic digest, forming an
    immutable hash chain:
        H_i = SHA-256( H_{i-1} || index || doc_id || dss_hash || rules || stages || timestamp )

    Tamper Detection:
    Any retroactive modification of an existing audit entry breaks subsequent hashes in the chain,
    causing `verify_integrity()` to detect and isolate the tampered record.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class AuditEntry:
    """An individual immutable record in the audit hash chain."""
    index: int
    timestamp: str
    document_id: str
    dss_hash: str
    output_format: str
    rules_fired: List[str]
    stages_executed: List[str]
    verification_passed: bool
    prev_hash: str
    entry_hash: str
    extra_metadata: Dict[str, Any]


class HashChainAuditLogger:
    """Thread-safe manager for recording and validating the tamper-evident audit log."""

    _instance: Optional[HashChainAuditLogger] = None
    _lock = threading.Lock()

    def __init__(self, log_file: Optional[Path] = None) -> None:
        if log_file is None:
            log_file = Path(__file__).parent.parent.parent / "output" / "audit_log.json"
        self.log_file = log_file
        self._entries: List[AuditEntry] = []
        self._load_or_init()

    @classmethod
    def get_instance(cls, log_file: Optional[Path] = None) -> HashChainAuditLogger:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(log_file)
            return cls._instance

    def _load_or_init(self) -> None:
        if self.log_file.exists():
            try:
                data = json.loads(self.log_file.read_text(encoding="utf-8"))
                self._entries = [AuditEntry(**e) for e in data]
                return
            except Exception:
                self._entries = []
        self._entries = []

    def _persist(self) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        serialized = [asdict(e) for e in self._entries]
        self.log_file.write_text(json.dumps(serialized, indent=2), encoding="utf-8")

    def _compute_hash(
        self,
        prev_hash: str,
        index: int,
        timestamp: str,
        document_id: str,
        dss_hash: str,
        output_format: str,
        rules_fired: List[str],
        stages_executed: List[str],
        verification_passed: bool,
    ) -> str:
        payload = (
            f"{prev_hash}|{index}|{timestamp}|{document_id}|{dss_hash}|"
            f"{output_format}|{','.join(rules_fired)}|{','.join(stages_executed)}|"
            f"{verification_passed}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def record(
        self,
        document_id: str,
        dss_hash: str,
        output_format: str,
        rules_fired: List[str],
        stages_executed: List[str],
        verification_passed: bool,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """Append a new cryptographic audit entry to the hash chain."""
        with self._lock:
            index = len(self._entries)
            timestamp = datetime.utcnow().isoformat()
            prev_hash = self._entries[-1].entry_hash if self._entries else "0" * 64

            entry_hash = self._compute_hash(
                prev_hash=prev_hash,
                index=index,
                timestamp=timestamp,
                document_id=document_id,
                dss_hash=dss_hash,
                output_format=output_format,
                rules_fired=sorted(rules_fired),
                stages_executed=stages_executed,
                verification_passed=verification_passed,
            )

            entry = AuditEntry(
                index=index,
                timestamp=timestamp,
                document_id=document_id,
                dss_hash=dss_hash,
                output_format=output_format,
                rules_fired=sorted(rules_fired),
                stages_executed=stages_executed,
                verification_passed=verification_passed,
                prev_hash=prev_hash,
                entry_hash=entry_hash,
                extra_metadata=extra_metadata or {},
            )
            self._entries.append(entry)
            self._persist()
            return entry

    def verify_integrity(self) -> Tuple[bool, Optional[str]]:
        """Verify cryptographic integrity across the entire hash chain.

        Returns:
            Tuple of (True, None) if completely untampered,
            or (False, error_message) indicating the exact tampered index.
        """
        with self._lock:
            if not self._entries:
                return True, None

            expected_prev = "0" * 64

            for i, entry in enumerate(self._entries):
                # Check previous hash link
                if entry.prev_hash != expected_prev:
                    return (
                        False,
                        f"Tampering detected at block {i}: prev_hash '{entry.prev_hash[:12]}...' "
                        f"does not match expected hash '{expected_prev[:12]}...'",
                    )

                # Recompute current entry hash
                recomputed = self._compute_hash(
                    prev_hash=entry.prev_hash,
                    index=entry.index,
                    timestamp=entry.timestamp,
                    document_id=entry.document_id,
                    dss_hash=entry.dss_hash,
                    output_format=entry.output_format,
                    rules_fired=entry.rules_fired,
                    stages_executed=entry.stages_executed,
                    verification_passed=entry.verification_passed,
                )

                if entry.entry_hash != recomputed:
                    return (
                        False,
                        f"Tampering detected at block {i}: stored hash '{entry.entry_hash[:12]}...' "
                        f"does not match recomputed hash '{recomputed[:12]}...'",
                    )

                expected_prev = entry.entry_hash

            return True, f"Audit chain verified: {len(self._entries)} blocks intact."

    def get_entries(self) -> List[AuditEntry]:
        with self._lock:
            return list(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            if self.log_file.exists():
                self.log_file.unlink()
