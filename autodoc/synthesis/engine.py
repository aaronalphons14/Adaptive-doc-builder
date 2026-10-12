"""YAML Declarative Rule Engine (Mechanism N2).

Architectural Role:
    Parses and evaluates declarative rules from `rules/rules.yaml`.
    Maps Document Structure Signature (DSS) features and execution options
    to candidate pipeline stage components.

    Records detailed explainability metrics for every rule that evaluates
    to True, capturing matched condition expressions and added stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

import yaml

from autodoc.core.models import DocumentStructureFeatures
from autodoc.synthesis.dag import StageDescriptor


@dataclass
class FiredRule:
    """Record of a rule that matched during pipeline synthesis."""
    rule_id: str
    description: str
    condition: str
    priority: int
    components_added: List[str]


class RuleEngine:
    """Evaluates declarative YAML rules against DSS features and options."""

    def __init__(self, rules_path: Optional[Path] = None) -> None:
        if rules_path is None:
            rules_path = Path(__file__).parent.parent.parent / "rules" / "rules.yaml"
        self.rules_path = rules_path
        self.rules: List[Dict[str, Any]] = self._load_rules()

    def _load_rules(self) -> List[Dict[str, Any]]:
        if not self.rules_path.exists():
            return []
        content = self.rules_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content) or {}
        return cast(List[Dict[str, Any]], data.get("rules", []))


    def evaluate_rules(
        self,
        features: DocumentStructureFeatures,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[StageDescriptor], List[FiredRule]]:
        """Evaluate all loaded rules against feature vector and options."""
        options = options or {}
        candidate_stages: List[StageDescriptor] = []
        fired_rules: List[FiredRule] = []

        eval_context = {
            "features": features,
            "options": options,
            "len": len,
            "str": str,
            "int": int,
            "True": True,
            "False": False,
        }

        for rule in self.rules:
            rule_id = rule.get("id", "unnamed_rule")
            condition = str(rule.get("condition", "False"))
            priority = int(rule.get("priority", 50))
            description = rule.get("description", "")
            raw_components = rule.get("components", [])
            dependencies = [
                d.get("target") for d in rule.get("dependencies", []) if d.get("target")
            ]
            conflicts = rule.get("conflicts", [])

            try:
                # Safe evaluation in restricted globals namespace
                matches = bool(eval(condition, {"__builtins__": {}}, eval_context))
            except Exception:
                # If evaluation fails, log and skip or raise
                matches = False


            if matches:
                components_added: List[str] = []
                for comp in raw_components:
                    stage_id = comp.get("stage_id", "UnknownStage")
                    stage_type = comp.get("stage_type", "decorator")
                    params = comp.get("params", {}).copy()

                    # Merge runtime overrides
                    for k, v in options.items():
                        if k in params:
                            params[k] = v

                    descriptor = StageDescriptor(
                        stage_id=stage_id,
                        stage_type=stage_type,
                        priority=priority,
                        rule_id=rule_id,
                        params=params,
                        dependencies=dependencies,
                        conflicts=conflicts,
                    )
                    candidate_stages.append(descriptor)
                    components_added.append(stage_id)

                fired_rules.append(FiredRule(
                    rule_id=rule_id,
                    description=description,
                    condition=condition,
                    priority=priority,
                    components_added=components_added,
                ))

        return candidate_stages, fired_rules
