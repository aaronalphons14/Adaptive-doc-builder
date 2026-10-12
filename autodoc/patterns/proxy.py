"""Proxy Pattern: Content-Hash Caching and Lazy Rendering.

Architectural Role:
    The Proxy pattern acts as a surrogate or intermediary for real rendering adapters.
    The `CachedRendererProxy` intercepts render calls, computing a deterministic cryptographic
    digest over the document's content tree and rendering options.

    If an identical request has been processed before, the proxy immediately returns the
    cached binary/markup artifact, eliminating redundant rendering computations.
    It tracks hit/miss telemetry and supports lazy evaluation and cache invalidation.
"""

from __future__ import annotations

import hashlib
import json
import threading
from typing import Any, Dict, Optional, Tuple, Union

from autodoc.patterns.adapter import IDocumentRendererAdapter
from autodoc.patterns.composite import DocumentNode


class CachedRendererProxy(IDocumentRendererAdapter):
    """Proxy controlling access to real renderer adapters with content-hash caching."""

    def __init__(self, real_adapter: IDocumentRendererAdapter) -> None:
        self.real_adapter = real_adapter
        self._cache: Dict[str, Tuple[Union[str, bytes], str]] = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def _compute_key(self, doc: DocumentNode, options: Optional[Dict[str, Any]] = None) -> str:
        """Compute SHA-256 fingerprint from document text and options."""
        options = options or {}
        doc_content = doc.get_text_content()
        meta_id = doc.doc_metadata.document_number or doc.doc_metadata.title
        options_json = json.dumps(options, sort_keys=True, default=str)

        combined = f"{meta_id}|{doc_content}|{options_json}".encode("utf-8")
        return hashlib.sha256(combined).hexdigest()

    def render(
        self, doc: DocumentNode, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[Union[str, bytes], str]:
        """Intercept render call and return cached artifact if available."""
        cache_key = self._compute_key(doc, options)

        with self._lock:
            if cache_key in self._cache:
                self.hits += 1
                return self._cache[cache_key]

            self.misses += 1

        # Execute real rendering
        artifact, plain_text = self.real_adapter.render(doc, options)

        with self._lock:
            self._cache[cache_key] = (artifact, plain_text)

        return artifact, plain_text

    def clear(self) -> None:
        """Clear all cached entries and reset telemetry."""
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0

    def stats(self) -> Dict[str, Any]:
        """Return proxy hit, miss, and size statistics."""
        with self._lock:
            return {
                "size": len(self._cache),
                "hits": self.hits,
                "misses": self.misses,
                "hit_ratio": round(self.hits / max(1, self.hits + self.misses), 3),
            }
