"""Document Structure Signature (DSS) Computation Engine (Mechanism N1).

Architectural Role:
    Parses a Composite document tree into a canonical, deterministic signature:
    a normalized feature vector coupled with a SHA-256 fingerprint.

    Features computed:
    - Block-type histogram (headings, paragraphs, tables, lists, signatures, callouts)
    - Tree nesting depth (maximum depth and average leaf depth)
    - Table density (cell count / total blocks) and list density (item count / total blocks)
    - Metadata attributes (document type, classification level, language set)
    - Sensitive data presence (Aadhaar, PAN, phone, email, bank accounts)
    - Citation and statutory reference presence
    - Signature / approval block count

    Invariance Guarantee:
    Identical document structures and semantics always produce the exact same
    DSS feature vector and canonical SHA-256 hash.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Dict, List, Optional, Set

from autodoc.analysis.entity_detector import EntityDetector
from autodoc.core.models import DocumentStructureFeatures, DSSSignature
from autodoc.patterns.composite import (
    CalloutNode,
    DocumentComponent,
    DocumentNode,
    HeadingNode,
    ListItemNode,
    ParagraphNode,
    SignatureNode,
    TableCellNode,
)


class DSSAnalyzer:
    """Computes deterministic Document Structure Signatures for DocumentNode trees."""

    def __init__(self, entity_detector: Optional[EntityDetector] = None) -> None:
        self.entity_detector = entity_detector or EntityDetector()

    def analyze(self, doc: DocumentNode) -> DSSSignature:
        """Analyze document tree and compute canonical DSS signature."""
        features = self.extract_features(doc)
        sig_hash = self.compute_canonical_hash(features)
        doc_id = doc.doc_metadata.document_number or doc.node_id
        return DSSSignature(
            signature_hash=sig_hash,
            feature_vector=features,
            document_id=doc_id,
        )

    compute_signature = analyze

    def extract_features(self, doc: DocumentNode) -> DocumentStructureFeatures:
        """Traverse Composite tree and compile the normalized feature vector."""
        block_counts: Dict[str, int] = {
            "heading": 0,
            "paragraph": 0,
            "table": 0,
            "table_cell": 0,
            "list": 0,
            "list_item": 0,
            "signature_block": 0,
            "callout": 0,
            "section": 0,
        }

        all_nodes: List[DocumentComponent] = list(doc.traverse())
        total_blocks = len(all_nodes)

        leaf_depths: List[int] = []
        max_depth = 1

        sensitive_matches_count = 0
        sensitive_types: Set[str] = set()
        citation_count = 0
        has_bilingual = False
        total_words = 0

        # Regular expressions for statutory and administrative citations
        citation_pattern = re.compile(
            r"\b(Section|Sec\.|Rule|Act|Order|G\.O\.|Article|Clause|Sub-clause)\s+[0-9A-Za-z\(\)\./-]+",
            re.IGNORECASE,
        )

        for node in all_nodes:
            b_type = node.block_type.value
            if b_type in block_counts:
                block_counts[b_type] += 1

            # Track tree depth
            d = self._node_depth_from_root(node)
            if d > max_depth:
                max_depth = d

            children = node.get_children()
            if not children and node is not doc:
                leaf_depths.append(d)

            # Analyze text content in atomic leaf elements
            text = ""
            if isinstance(node, ParagraphNode):
                text = node.text
                if node.is_bilingual or node.secondary_text:
                    has_bilingual = True
            elif isinstance(node, HeadingNode):
                text = node.text
            elif isinstance(node, TableCellNode):
                text = node.text
            elif isinstance(node, ListItemNode):
                text = node.text
            elif isinstance(node, CalloutNode):
                text = node.text
                if node.citation:
                    citation_count += 1
            elif isinstance(node, SignatureNode):
                text = f"{node.signatory_name} {node.designation} {node.department}"

            if text:
                total_words += len(text.split())

                # Scan for citations
                cits = citation_pattern.findall(text)
                citation_count += len(cits)

                # Scan for sensitive entities
                matches = self.entity_detector.scan_text(text)
                if matches:
                    sensitive_matches_count += len(matches)
                    for m in matches:
                        sensitive_types.add(m.entity_type)

        avg_depth = sum(leaf_depths) / len(leaf_depths) if leaf_depths else 1.0
        table_cells = block_counts["table_cell"]
        list_items = block_counts["list_item"]

        table_density = table_cells / max(1, total_blocks)
        list_density = list_items / max(1, total_blocks)

        meta = doc.doc_metadata
        if len(meta.languages) > 1:
            has_bilingual = True

        return DocumentStructureFeatures(
            doc_type=meta.doc_type.value,
            classification=meta.classification.value,
            languages=sorted(meta.languages),
            total_blocks=total_blocks,
            block_counts=block_counts,
            max_depth=max_depth,
            avg_depth=avg_depth,
            table_density=table_density,
            list_density=list_density,
            sensitive_data_count=sensitive_matches_count,
            sensitive_types_found=sorted(list(sensitive_types)),
            has_citations=(citation_count > 0),
            citation_count=citation_count,
            has_signature_blocks=(block_counts["signature_block"] > 0),
            signature_block_count=block_counts["signature_block"],
            has_bilingual_content=has_bilingual,
            word_count=total_words,
        )

    def _node_depth_from_root(self, node: DocumentComponent) -> int:
        """Calculate the 1-indexed tree depth from root to this node."""
        depth = 1
        curr = node
        while curr.parent is not None:
            depth += 1
            curr = curr.parent
        return depth

    def compute_canonical_hash(self, features: DocumentStructureFeatures) -> str:
        """Compute deterministic SHA-256 fingerprint over canonical feature vector."""
        canonical_dict = features.to_canonical_dict()
        canonical_json = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_structural_similarity(dss1: DSSSignature, dss2: DSSSignature) -> float:
        """Compute structural similarity between two DSS signatures (0.0 to 1.0).

        Used by Pipeline Memory to determine whether a cached pipeline prototype
        can be safely reused for an incoming document.
        """
        f1 = dss1.feature_vector
        f2 = dss2.feature_vector

        # Core non-negotiable invariants: must share doc_type, classification, and language set
        if f1.doc_type != f2.doc_type:
            return 0.0
        if f1.classification != f2.classification:
            return 0.0
        if f1.languages != f2.languages:
            return 0.0

        # Exact hash match
        if dss1.signature_hash == dss2.signature_hash:
            return 1.0

        # Structural feature vector similarity
        sim_scores: List[float] = []

        # 1. Depth similarity
        max_d = max(f1.max_depth, f2.max_depth, 1)
        sim_scores.append(1.0 - abs(f1.max_depth - f2.max_depth) / max_d)

        # 2. Table density similarity
        max_td = max(f1.table_density, f2.table_density, 0.01)
        sim_scores.append(1.0 - abs(f1.table_density - f2.table_density) / max_td)

        # 3. List density similarity
        max_ld = max(f1.list_density, f2.list_density, 0.01)
        sim_scores.append(1.0 - abs(f1.list_density - f2.list_density) / max_ld)

        # 4. Sensitive data profile
        both_sensitive = (f1.sensitive_data_count > 0) == (f2.sensitive_data_count > 0)
        sim_scores.append(1.0 if both_sensitive else 0.0)

        # 5. Citation profile
        both_citations = f1.has_citations == f2.has_citations
        sim_scores.append(1.0 if both_citations else 0.5)

        # 6. Signature profile
        both_signatures = f1.has_signature_blocks == f2.has_signature_blocks
        sim_scores.append(1.0 if both_signatures else 0.2)

        return round(sum(sim_scores) / len(sim_scores), 3)
