"""Singleton Pattern: Thread-Safe Policy and Style Registry.

Architectural Role:
    The Singleton pattern provides centralized, globally accessible, thread-safe registries
    for government compliance policies (`PolicyRegistry`) and government style/design tokens
    (`StyleRegistry`).

    Uses double-checked locking to guarantee exactly one registry instance exists per process,
    preventing duplicate disk reads of `policies.yaml` while ensuring consistent policy
    enforcement and immutable design standards across all concurrent document synthesis requests.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from autodoc.core.models import DocumentStructureFeatures


@dataclass
class PolicyDefinition:
    """Represents a regulatory compliance policy loaded from policies.yaml."""
    id: str
    name: str
    legal_basis: str
    description: str
    applicable_when: str
    mandatory_components: List[str]
    verifier_rules: Dict[str, Any]
    enforcement: str = "BLOCK"


class PolicyRegistry:
    """Thread-safe Singleton registry maintaining active compliance policies."""

    _instance: Optional[PolicyRegistry] = None
    _lock = threading.Lock()

    def __init__(self, policies_path: Optional[Path] = None) -> None:
        if policies_path is None:
            policies_path = Path(__file__).parent.parent.parent / "rules" / "policies.yaml"
        self.policies_path = policies_path
        self._policies: Dict[str, PolicyDefinition] = {}
        self._load_policies()

    @classmethod
    def get_instance(cls, policies_path: Optional[Path] = None) -> PolicyRegistry:
        """Double-checked locking thread-safe singleton accessor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(policies_path)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (useful for testing)."""
        with cls._lock:
            cls._instance = None

    def _load_policies(self) -> None:
        if not self.policies_path.exists():
            return
        content = self.policies_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content) or {}
        for p in data.get("policies", []):
            policy = PolicyDefinition(
                id=p.get("id", ""),
                name=p.get("name", ""),
                legal_basis=p.get("legal_basis", ""),
                description=p.get("description", ""),
                applicable_when=p.get("applicable_when", "False"),
                mandatory_components=p.get("mandatory_components", []),
                verifier_rules=p.get("verifier_rules", {}),
                enforcement=p.get("enforcement", "BLOCK"),
            )
            self._policies[policy.id] = policy

    def get_all_policies(self) -> List[PolicyDefinition]:
        return list(self._policies.values())

    def get_policy(self, policy_id: str) -> Optional[PolicyDefinition]:
        return self._policies.get(policy_id)

    def get_active_policies(self, features: DocumentStructureFeatures) -> List[PolicyDefinition]:
        """Determine which policies apply to a given document based on its DSS features."""
        active: List[PolicyDefinition] = []
        eval_context = {
            "features": features,
            "len": len,
            "True": True,
            "False": False,
        }

        for policy in self._policies.values():
            try:
                if bool(eval(policy.applicable_when, {"__builtins__": {}}, eval_context)):
                    active.append(policy)
            except Exception:
                pass
        return active


class StyleRegistry:
    """Thread-safe Singleton registry for government design tokens and typography standards."""

    _instance: Optional[StyleRegistry] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._tokens: Dict[str, Any] = {
            "primary_color": "#1e3a8a",
            "secondary_color": "#0f766e",
            "danger_color": "#dc2626",
            "default_font": "Noto Sans Devanagari, Arial, sans-serif",
            "heading_font": "Noto Sans Devanagari, Georgia, serif",
            "page_margin_mm": 25.4,
            "line_height": 1.6,
        }

    @classmethod
    def get_instance(cls) -> StyleRegistry:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_token(self, name: str, default: Any = None) -> Any:
        return self._tokens.get(name, default)

    def set_token(self, name: str, value: Any) -> None:
        with self._lock:
            self._tokens[name] = value
