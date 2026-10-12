"""DAG Conflict and Dependency Resolution Engine (Mechanism N2).

Architectural Role:
    Resolves dependencies, mutual exclusions, and ordering constraints among
    dynamically selected pipeline stages into a valid, deterministic execution sequence.

    Key capabilities:
    1. Conflict Resolution: Evaluates declared mutual exclusions (e.g. HtmlRenderer vs
       PdfRenderer) and uses rule priorities to disambiguate or prune redundant stages.
    2. Dependency Modeling: Models partial order constraints (e.g. RedactionDecorator
       must precede CitationDecorator; all decorators must precede Renderers; Renderers
       must precede Verifier).
    3. Topological Sorting: Applies Kahn's algorithm with priority tie-breaking to
       guarantee a cycle-free, strictly ordered processing pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set, Tuple

from autodoc.core.exceptions import CyclicDependencyError


@dataclass
class StageDescriptor:
    """Descriptor for a pipeline component stage identified during synthesis."""
    stage_id: str
    stage_type: str # decorator, renderer, verifier, preprocessor
    priority: int = 50
    rule_id: str = "default"
    params: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list) # stage_ids that must run after this stage
    prerequisites: List[str] = field(default_factory=list) # stage_ids that must run before this stage
    conflicts: List[str] = field(default_factory=list) # stage_ids mutually exclusive with this stage

    def __hash__(self) -> int:
        return hash(self.stage_id)


class DAGResolver:
    """Resolves conflicts and generates a deterministic topological execution sequence."""

    def resolve(
        self,
        stages: List[StageDescriptor],
    ) -> Tuple[List[StageDescriptor], List[str]]:
        """Resolve conflicts and return the topologically ordered stage list and conflict log."""
        # Step 1: Conflict resolution based on priority
        active_stages, conflict_log = self._resolve_conflicts(stages)

        # Step 2: Build adjacency graph
        stage_map: Dict[str, StageDescriptor] = {s.stage_id: s for s in active_stages}
        adj: Dict[str, Set[str]] = {s.stage_id: set() for s in active_stages}
        in_degree: Dict[str, int] = {s.stage_id: 0 for s in active_stages}

        # Apply standard structural constraints:
        # Preprocessors -> Decorators -> Renderers -> Verifiers
        type_precedence = {"preprocessor": 1, "decorator": 2, "renderer": 3, "verifier": 4}

        for s1 in active_stages:
            for s2 in active_stages:
                if s1.stage_id == s2.stage_id:
                    continue
                t1 = type_precedence.get(s1.stage_type, 2)
                t2 = type_precedence.get(s2.stage_type, 2)
                if t1 < t2:
                    if s2.stage_id not in adj[s1.stage_id]:
                        adj[s1.stage_id].add(s2.stage_id)

        # Apply explicitly declared dependencies
        for s in active_stages:
            for dep in s.dependencies:
                # If dep is an active stage, s must run before dep
                if dep in stage_map and dep not in adj[s.stage_id]:
                    adj[s.stage_id].add(dep)
            for prereq in s.prerequisites:
                # If prereq is active, prereq must run before s
                if prereq in stage_map and s.stage_id not in adj[prereq]:
                    adj[prereq].add(s.stage_id)

        # Compute in-degrees
        for u in adj:
            for v in adj[u]:
                in_degree[v] += 1

        # Step 3: Kahn's algorithm with priority tie-breaker
        # Queue contains nodes with in_degree == 0, sorted by priority desc, stage_id asc
        ready = [s_id for s_id, deg in in_degree.items() if deg == 0]
        ready.sort(key=lambda x: (-stage_map[x].priority, x))

        ordered_stages: List[StageDescriptor] = []

        while ready:
            curr_id = ready.pop(0)
            ordered_stages.append(stage_map[curr_id])

            for neighbor in sorted(adj[curr_id]):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    ready.append(neighbor)
                    ready.sort(key=lambda x: (-stage_map[x].priority, x))

        # Check for cycles
        if len(ordered_stages) < len(active_stages):
            unresolved = set(active_stages) - set(ordered_stages)
            cycle_ids = [s.stage_id for s in unresolved]
            raise CyclicDependencyError(
                f"Circular dependency detected among pipeline stages: {cycle_ids}"
            )

        return ordered_stages, conflict_log

    def _resolve_conflicts(
        self, stages: List[StageDescriptor]
    ) -> Tuple[List[StageDescriptor], List[str]]:
        """Remove conflicting lower-priority stages."""
        conflict_log: List[str] = []
        stage_by_id = {s.stage_id: s for s in stages}
        pruned_ids: Set[str] = set()

        for s in stages:
            if s.stage_id in pruned_ids:
                continue
            for conflicting_id in s.conflicts:
                if conflicting_id in stage_by_id and conflicting_id not in pruned_ids:
                    other = stage_by_id[conflicting_id]
                    if s.priority >= other.priority:
                        pruned_ids.add(conflicting_id)
                        conflict_log.append(
                            f"Conflict resolved: {s.stage_id} (priority {s.priority}) "
                            f"retained over {conflicting_id} (priority {other.priority})"
                        )
                    else:
                        pruned_ids.add(s.stage_id)
                        conflict_log.append(
                            f"Conflict resolved: {conflicting_id} (priority {other.priority}) "
                            f"retained over {s.stage_id} (priority {s.priority})"
                        )
                        break

        active = [s for s in stages if s.stage_id not in pruned_ids]
        return active, conflict_log
