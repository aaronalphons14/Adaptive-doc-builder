"""Pipeline Memory: Whole-Pipeline Prototype Caching Engine (Mechanism N4).

Architectural Role:
    Pipeline Memory caches synthesized processing pipelines keyed by Document Structure
    Signatures (DSS). When structurally similar documents are processed, it bypasses
    redundant rule evaluations and topological sorting by cloning a proven pipeline
    prototype (Prototype pattern).

    Supports:
    - Exact DSS signature hash lookups (100% match)
    - Structural similarity threshold lookups (e.g. >= 0.95 similarity score)
    - Memory telemetry (hits, misses, prototypes cached)
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional, Tuple

from autodoc.analysis.dss import DSSAnalyzer
from autodoc.core.models import DSSSignature
from autodoc.patterns.builder import DocumentPipeline
from autodoc.patterns.prototype import PipelinePrototype


class PipelineMemory:
    """Thread-safe cache of proven synthesized pipelines keyed by DSS."""

    _instance: Optional[PipelineMemory] = None
    _lock = threading.Lock()

    def __init__(self, similarity_threshold: float = 0.95) -> None:
        self.similarity_threshold = similarity_threshold
        self._prototypes: Dict[str, Tuple[DSSSignature, PipelinePrototype]] = {}
        self.hits = 0
        self.misses = 0
        self.similarity_hits = 0

    @classmethod
    def get_instance(cls) -> PipelineMemory:
        """Singleton accessor for global Pipeline Memory."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def remember(self, dss: DSSSignature, pipeline: DocumentPipeline) -> None:
        """Store a synthesized pipeline prototype keyed by DSS signature hash."""
        with self._lock:
            prototype = PipelinePrototype(pipeline)
            self._prototypes[dss.signature_hash] = (dss, prototype)

    def recall(
        self, dss: DSSSignature, allow_similar: bool = True
    ) -> Optional[Tuple[DocumentPipeline, str]]:
        """Retrieve a cached pipeline clone for the given DSS.

        Returns:
            Tuple of (cloned_pipeline, hit_type) where hit_type is 'exact' or 'similar',
            or None on cache miss.
        """
        with self._lock:
            # 1. Exact hash match
            if dss.signature_hash in self._prototypes:
                self.hits += 1
                _, prototype = self._prototypes[dss.signature_hash]
                cloned = prototype.clone()
                cloned.dss = dss
                return cloned, "exact"

            # 2. Structural similarity match
            if allow_similar and self._prototypes:
                best_match: Optional[Tuple[str, float, PipelinePrototype]] = None
                for sig_hash, (cached_dss, prototype) in self._prototypes.items():
                    sim = DSSAnalyzer.compute_structural_similarity(dss, cached_dss)
                    if sim >= self.similarity_threshold:
                        if best_match is None or sim > best_match[1]:
                            best_match = (sig_hash, sim, prototype)

                if best_match is not None:
                    self.similarity_hits += 1
                    _, _, proto = best_match
                    cloned = proto.clone()
                    cloned.dss = dss
                    return cloned, f"similar_{best_match[1]:.2f}"

            self.misses += 1
            return None

    def clear(self) -> None:
        """Clear memory cache and reset counters."""
        with self._lock:
            self._prototypes.clear()
            self.hits = 0
            self.misses = 0
            self.similarity_hits = 0

    def stats(self) -> Dict[str, Any]:
        """Return memory cache operational telemetry."""
        with self._lock:
            total_requests = self.hits + self.similarity_hits + self.misses
            return {
                "cached_pipelines": len(self._prototypes),
                "exact_hits": self.hits,
                "similarity_hits": self.similarity_hits,
                "total_hits": self.hits + self.similarity_hits,
                "misses": self.misses,
                "hit_ratio": round((self.hits + self.similarity_hits) / max(1, total_requests), 3),
            }
