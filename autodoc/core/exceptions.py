"""Domain exception classes for AutoDoc-Gov."""

from typing import Any, Dict, List, Optional


class AutoDocError(Exception):
    """Base exception for all AutoDoc errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ComplianceError(AutoDocError):
    """Raised when an active regulatory policy is violated or verification fails."""
    def __init__(
        self,
        message: str,
        policy_id: Optional[str] = None,
        violations: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        super().__init__(message, {"policy_id": policy_id, "violations": violations or []})
        self.policy_id = policy_id
        self.violations = violations or []


class ApprovalRequiredError(AutoDocError):
    """Raised when document classification requires human approval before release."""
    def __init__(self, message: str, classification: str, doc_id: Optional[str] = None) -> None:
        super().__init__(message, {"classification": classification, "doc_id": doc_id})
        self.classification = classification
        self.doc_id = doc_id


class SynthesisError(AutoDocError):
    """Raised when pipeline synthesis encounters conflicting or unsatisfiable rules."""
    pass


class CyclicDependencyError(SynthesisError):
    """Raised when a circular dependency cycle is detected in the pipeline stage DAG."""
    pass


class VerificationError(AutoDocError):
    """Raised when post-render output verification fails."""
    def __init__(self, message: str, failures: Optional[List[str]] = None) -> None:
        super().__init__(message, {"failures": failures or []})
        self.failures = failures or []


class SelfHealingError(AutoDocError):
    """Raised when self-healing fallback planning fails to find an alternate chain."""
    pass
