# AutoDoc-Gov: System Architecture Specification

## 1. Executive Summary

**AutoDoc-Gov** is an architectural paradigm shift in automated government document generation. Traditional systems rely on rigid, hardcoded pipelines and static templates that scale poorly ($\mathcal{O}(M \times N)$ permutations of document types and output formats), fail on heterogeneous inputs, leak sensitive personally identifiable information (PII), and lack explainable regulatory auditability.

AutoDoc-Gov replaces static pipelines with **Self-Assembling, Compliance-by-Construction Pipelines**. It treats document generation not as template interpolation, but as a **dynamic constraint satisfaction and code synthesis problem**:
1. At runtime, it analyzes each document's semantic and syntactic structure into an Abstract Syntax Tree (Composite pattern).
2. It computes a deterministic **Document Structure Signature (DSS)**.
3. An ontology-driven **Rule Engine** evaluates the signature against statutory mandates (DPDP Act 2023, RTI Act 2005, GIGW 3.0, WCAG AA).
4. A **DAG Resolver** (Kahn's algorithm) synthesizes the minimal, compliant processing pipeline.
5. Decorators and Renderers assemble the artifact via Bridge and Adapter patterns.
6. A **Post-Render Verifier** independently re-scans the rendered artifact before release, strictly blocking any non-compliant output.
7. An immutable **SHA-256 Hash-Chained Audit Log** and self-explaining Assembly Report certify the artifact with legal evidentiary value.

---

## 2. End-to-End Processing Lifecycle (Mermaid Flowchart)

```mermaid
flowchart TD
    subgraph Ingestion ["1. Multi-Format Ingestion & Composite Parsing"]
        RawInput["Raw Input Document\n(JSON / Markdown / DOCX / TXT)"]
        ParserFactory["Multi-Format Parser Registry"]
        CompositeTree["Composite AST Document Node Tree\n(Headings, Paragraphs, Tables, Callouts, Signatures)"]
        RawInput --> ParserFactory --> CompositeTree
    end

    subgraph DSS_Engine ["2. Mechanism N1: Document Structure Signature (DSS)"]
        EntityDetector["Entity Detector\n(Aadhaar Verhoeff, PAN, Phone, Email, Bank IFSC)"]
        FeatureExtractor["DSS Feature Extractor\n(Block Counts, Max Depth, Table/List Density, Word Counts)"]
        FeatureVector["Canonical Feature Vector (JSON-Sorted)"]
        SHA256Signature["Deterministic SHA-256 Fingerprint"]
        
        CompositeTree --> EntityDetector
        CompositeTree --> FeatureExtractor
        EntityDetector --> FeatureVector
        FeatureExtractor --> FeatureVector
        FeatureVector --> SHA256Signature
    end

    subgraph Synthesis ["3. Mechanism N2: Declarative Rule Engine & DAG Synthesis"]
        RuleYAML["Regulatory Ontology Rules\n(rules/rules.yaml)"]
        RuleEngine["Rule Engine Evaluation\n(Evaluates conditions against DSS feature vector)"]
        ConflictResolver["Conflict Resolver & Precedence Matrix"]
        KahnDAG["Kahn's Topological Sort\n(Dependency Resolution & Priority Tie-Breaking)"]
        PipelinePlan["Synthesized Pipeline DAG Plan"]

        SHA256Signature --> RuleEngine
        RuleYAML --> RuleEngine
        RuleEngine --> ConflictResolver
        ConflictResolver --> KahnDAG
        KahnDAG --> PipelinePlan
    end

    subgraph Assembly ["4. Execution & Pipeline Assembly (GoF Patterns)"]
        Builder["PipelineBuilder (GoF Builder)"]
        Decorators["Decorator Stack (GoF Decorator)\n(Redaction, Watermark, Citations, Accessibility, Bilingual)"]
        Bridge["Renderer Bridge (GoF Bridge)"]
        Adapters["Format Adapters (GoF Adapter)\n(HTML / WeasyPrint / ReportLab / python-docx / Markdown)"]
        SelfHealing["Mechanism N4: Self-Healing Engine\n(Fallback Planning on Failure)"]
        RawArtifact["Rendered Output Artifact\n(HTML5 / Indic PDF / DOCX / Markdown)"]

        PipelinePlan --> Builder
        Builder --> Decorators
        Decorators --> Bridge
        Bridge --> Adapters
        Adapters -. Error Caught .-> SelfHealing
        SelfHealing -. Reconfigured Pipeline .-> Adapters
        Adapters --> RawArtifact
    end

    subgraph Verification ["5. Mechanism N3: Post-Render Output Verifier"]
        VerifierStage["OutputVerifier Stage\n(Re-scans Rendered Artifact, not input)"]
        RedactionCheck["Redaction Check: Zero-PII Invariant (DPDP Act)"]
        WatermarkCheck["Watermark Check: Classification Enforcement"]
        AccessibilityCheck["Accessibility Check: GIGW 3.0 / WCAG AA"]
        Gate{"Compliance Passed?"}
        BlockRelease["Release BLOCKED\n(ComplianceError Raised)"]

        RawArtifact --> VerifierStage
        VerifierStage --> RedactionCheck
        VerifierStage --> WatermarkCheck
        VerifierStage --> AccessibilityCheck
        RedactionCheck --> Gate
        WatermarkCheck --> Gate
        AccessibilityCheck --> Gate
        Gate -- No --> BlockRelease
    end

    subgraph AuditLog ["6. Mechanism N5: Cryptographic Audit Trail & Proof"]
        Gate -- Yes --> CertifiedArtifact["Compliance-Certified Document Artifact"]
        ReportGen["Assembly Report Generator\n(Human-Readable Explanations of All Rule Decisions)"]
        HashChain["SHA-256 Hash Chain Logger\n(Immutable Block Linked to Previous Block)"]
        QRService["QR Verification Code Service\n(Tamper-Evident Physical Verification Link)"]

        CertifiedArtifact --> ReportGen
        CertifiedArtifact --> HashChain
        CertifiedArtifact --> QRService
        ReportGen --> FinalPackage["Final Delivered Package\n(Artifact + Report + QR + Audit Hash)"]
        HashChain --> FinalPackage
        QRService --> FinalPackage
```

---

## 3. The 5 Novel Architectural Mechanisms

### N1. Document Structure Signature (DSS)
- **Input Invariance:** Transforms unstructured or semi-structured government documents into a normalized Composite tree (`DocumentNode`).
- **Feature Vector:** Computes a normalized vector:
  $$\mathbf{f} = \langle \text{doc\_type}, \text{classification}, \text{languages}, N_{\text{blocks}}, D_{\text{max}}, D_{\text{avg}}, \rho_{\text{table}}, \rho_{\text{list}}, N_{\text{sensitive}}, C_{\text{statutory}}, W_{\text{count}} \rangle$$
- **Determinism Property:** Identical document structures deterministically produce identical SHA-256 fingerprints:
  $$\text{Fingerprint} = \text{SHA-256}(\text{CanonicalSortedJSON}(\mathbf{f}))$$
- **Structural Similarity:** Cosine similarity metric $\text{Sim}(\mathbf{f}_1, \mathbf{f}_2) \in [0.0, 1.0]$ enables pipeline reuse and anomaly detection.

### N2. Rule-Driven Pipeline Synthesis via DAG
- **Declarative Ontology:** Rules are defined in external YAML (`rules/rules.yaml`), divorcing government policies from application code.
- **Topological Sorting:** Kahn’s algorithm computes a conflict-free execution sequence.
- **Priority Tie-Breaking:** If two stages share the same in-degree, the stage with higher statutory priority executes first.
- **Cycle Detection:** Directed cycles raise `CyclicDependencyError` at synthesis time before any document rendering begins.

### N3. Compliance-by-Construction + Post-Render Verification
- **Dual-Layer Defense:**
  1. *Construction Layer:* Redaction and Watermark decorators automatically mask sensitive entities and watermark classified content.
  2. *Verification Layer:* The `OutputVerifier` re-scans the actual rendered artifact (HTML, PDF, DOCX text).
- **Zero-PII Invariant:** Aadhaar numbers (with Verhoeff checksum validation), PAN cards, phone numbers, email addresses, and bank accounts must be strictly zero in public/RTI outputs.
- **Release Blocking:** If any invariant is violated, the system raises `ComplianceError` and halts delivery.

### N4. Self-Healing Fallback Planning & Pipeline Memory
- **Self-Healing:** If an active renderer fails (e.g. WeasyPrint missing OS native GTK libraries on Windows), the `SelfHealingEngine` inspects fallback alternatives, automatically re-routes to `ReportLabPdfAdapter`, and completes rendering without human intervention.
- **Pipeline Memory:** Caches synthesized pipelines indexed by DSS fingerprint. If a document with an identical or near-identical signature arrives, the pipeline is retrieved via the Prototype pattern in $\mathcal{O}(1)$ time.

### N5. Explainable Assembly Report & Cryptographic Hash Chain
- **Explainability:** Generates an Assembly Report detailing every rule evaluated, why it fired or did not fire, conflict resolutions, and execution timings.
- **Tamper-Evident Hash Chain:** Every execution produces an immutable block:
  $$H_i = \text{SHA-256}(H_{i-1} \parallel i \parallel \text{timestamp} \parallel \text{doc\_id} \parallel \text{dss\_hash} \parallel \text{format} \parallel \text{rules} \parallel \text{stages} \parallel \text{verified})$$
  Any post-facto modification of output documents or logs immediately invalidates the cryptographic chain.
- **QR Code Verification:** Embeds a verification payload into the document footer for physical and digital verification.

---

## 4. Key Architectural Trade-offs & Decisions

| Decision | Alternative Considered | Why We Chose Our Approach |
| :--- | :--- | :--- |
| **Kahn's DAG Algorithm** | Depth-First Search (DFS) | Kahn's algorithm yields natural topological layers and allows deterministic priority tie-breaking among ready nodes. |
| **Verhoeff Checksum** | Luhn Algorithm / Regex only | Aadhaar check-digits use the dihedral group $D_5$ (Verhoeff algorithm). Regex alone produces false positives; Verhoeff eliminates invalid random digit sequences. |
| **Post-Render Verification** | Input-only validation | Input validation cannot detect bugs in templates or third-party renderers that might inadvertently re-expose confidential data. Post-render inspection is zero-trust. |
| **SHA-256 Hash Chain** | Central SQL database log | A hash chain creates a tamper-evident cryptographic data structure that can be independently audited by citizens, courts, or external watchdogs without database access. |
| **ReportLab Fallback Adapter** | Hard failure when WeasyPrint missing | In air-gapped or restricted government server environments, native C libraries (GTK/Cairo) are frequently blocked. Bundled ReportLab ensures 100% rendering reliability. |
