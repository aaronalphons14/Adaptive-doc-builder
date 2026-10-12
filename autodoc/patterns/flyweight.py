"""Flyweight Pattern: Shared Immutable Style and Schema Token Pool.

Architectural Role:
    The Flyweight pattern minimizes memory usage when generating large government documents
    (or executing high-volume batch runs) by sharing fine-grained, immutable style definitions,
    typography tokens, and margin rules across thousands of Composite document nodes.

    Instead of every paragraph, table cell, or header instantiating its own redundant style
    configuration, nodes reference shared `StyleFlyweight` instances managed by a centralized,
    thread-safe `StyleFlyweightFactory`.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class StyleFlyweight:
    """Immutable intrinsic state representing a government styling specification."""
    font_family: str
    font_size_pt: float
    bold: bool
    italic: bool
    text_color: str
    background_color: Optional[str]
    alignment: str
    padding_pt: float
    margin_bottom_pt: float
    border: bool

    def to_css(self) -> str:
        """Convert flyweight attributes into inline CSS declarations."""
        weight = "bold" if self.bold else "normal"
        style = "italic" if self.italic else "normal"
        bg = f"background-color: {self.background_color};" if self.background_color else ""
        border_css = "border: 1px solid #cbd5e1;" if self.border else ""
        return (
            f"font-family: {self.font_family}; "
            f"font-size: {self.font_size_pt}pt; "
            f"font-weight: {weight}; "
            f"font-style: {style}; "
            f"color: {self.text_color}; "
            f"text-align: {self.alignment}; "
            f"padding: {self.padding_pt}pt; "
            f"margin-bottom: {self.margin_bottom_pt}pt; "
            f"{bg} {border_css}"
        ).strip()


class StyleFlyweightFactory:
    """Thread-safe factory creating and pooling shared StyleFlyweight instances."""

    _instance: Optional[StyleFlyweightFactory] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._pool: Dict[Tuple[Any, ...], StyleFlyweight] = {}
        self._hits = 0
        self._misses = 0

    @classmethod
    def get_instance(cls) -> StyleFlyweightFactory:
        """Singleton access to the flyweight factory pool."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def get_style(
        self,
        font_family: str = "Noto Sans Devanagari, Arial, sans-serif",
        font_size_pt: float = 11.0,
        bold: bool = False,
        italic: bool = False,
        text_color: str = "#111827",
        background_color: Optional[str] = None,
        alignment: str = "left",
        padding_pt: float = 4.0,
        margin_bottom_pt: float = 6.0,
        border: bool = False,
    ) -> StyleFlyweight:
        """Retrieve an existing shared flyweight from the pool or instantiate and cache a new one."""
        key = (
            font_family,
            font_size_pt,
            bold,
            italic,
            text_color,
            background_color,
            alignment,
            padding_pt,
            margin_bottom_pt,
            border,
        )

        with self._lock:
            if key in self._pool:
                self._hits += 1
                return self._pool[key]

            self._misses += 1
            flyweight = StyleFlyweight(
                font_family=font_family,
                font_size_pt=font_size_pt,
                bold=bold,
                italic=italic,
                text_color=text_color,
                background_color=background_color,
                alignment=alignment,
                padding_pt=padding_pt,
                margin_bottom_pt=margin_bottom_pt,
                border=border,
            )
            self._pool[key] = flyweight
            return flyweight

    def total_flyweights(self) -> int:
        """Return the number of unique flyweight objects currently pooled."""
        return len(self._pool)

    def stats(self) -> Dict[str, int]:
        """Return cache hit and miss statistics."""
        return {
            "pooled_objects": len(self._pool),
            "hits": self._hits,
            "misses": self._misses,
        }
