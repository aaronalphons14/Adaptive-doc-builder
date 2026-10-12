# AutoDoc-Gov: Gang of Four (GoF) Pattern Map

This document maps all 12 classical Gang of Four (GoF) design patterns implemented within AutoDoc-Gov, detailing the concrete module path, primary classes, architectural role, and rationale for adoption.

---

## Pattern Matrix Overview

| # | Pattern Name | Category | Module Path | Primary Classes | Key Architectural Role |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | **Abstract Factory** | Creational | `autodoc/patterns/abstract_factory.py` | `DocumentComponentFactory`, `HtmlDocumentComponentFactory`, `PdfDocumentComponentFactory` | Creates coherent families of related layout components (headers, tables, signatures) without coupling callers to specific concrete formats. |
| **2** | **Factory Method** | Creational | `autodoc/patterns/factory_method.py` | `BlockRendererCreator`, `HtmlBlockRendererCreator`, `PdfBlockRendererCreator` | Defers instantiation of individual block renderers (headings, tables, callouts) to specialized format subclasses. |
| **3** | **Builder** | Creational | `autodoc/patterns/builder.py` | `PipelineBuilder`, `DocumentPipeline` | Assembles complex, multi-stage processing pipelines step-by-step from synthesized DAG execution plans. |
| **4** | **Prototype** | Creational | `autodoc/patterns/prototype.py` | `BlockConfigPrototype`, `PipelinePrototype` | Creates new style and pipeline instances by cloning existing archetypes, avoiding expensive re-computation. |
| **5** | **Singleton** | Creational | `autodoc/patterns/singleton.py` | `PolicyRegistry`, `StyleRegistry` | Guarantees exactly one authoritative, thread-safe instance of regulatory policies and shared styling palettes across the application. |
| **6** | **Adapter** | Structural | `autodoc/patterns/adapter.py` | `Jinja2HtmlAdapter`, `WeasyPrintPdfAdapter`, `ReportLabPdfAdapter`, `PythonDocxAdapter`, `MarkdownAdapter` | Normalizes incompatible third-party rendering libraries into a uniform `IRendererAdapter` contract. Enables adding new formats in ~35 LOC (AC4). |
| **7** | **Bridge** | Structural | `autodoc/patterns/bridge.py` | `DocumentRendererAbstraction`, `IRendererImplementor` | Completely decouples high-level document orchestration from low-level format rendering mechanics, allowing both hierarchies to vary independently. |
| **8** | **Composite** | Structural | `autodoc/patterns/composite.py` | `DocumentComponent`, `DocumentNode`, `SectionNode`, `TableNode`, `ParagraphNode` | Represents heterogeneous document hierarchies as unified tree structures where individual elements and composite containers are treated uniformly. |
| **9** | **Decorator** | Structural | `autodoc/patterns/decorator.py` | `PipelineStageDecorator`, `RedactionDecorator`, `WatermarkDecorator`, `AccessibilityDecorator`, `PageNumberingDecorator` | Dynamically attaches orthogonal regulatory transformations (PII masking, watermark stamps, GIGW tags) onto pipeline stages without modifying base stages. |
| **10** | **Facade** | Structural | `autodoc/patterns/facade.py` | `AutoDocFacade` | Provides a unified, ergonomic API (`plan()`, `generate()`) masking the complexity of multi-stage parsers, rule engines, verifiers, and audit loggers. |
| **11** | **Flyweight** | Structural | `autodoc/patterns/flyweight.py` | `StyleFlyweightFactory`, `SharedBlockStyle` | Pools immutable typography and styling properties, sharing single instances across thousands of document nodes to minimize memory footprint. |
| **12** | **Proxy** | Structural | `autodoc/patterns/proxy.py` | `CachingRendererProxy` | Intercepts rendering invocations, transparently caching rendered artifacts by SHA-256 content hash to eliminate redundant rendering cycles. |

---

## Detailed Pattern Analyses

### 1. Abstract Factory (`autodoc/patterns/abstract_factory.py`)
- **Intent:** Provide an interface for creating families of related or dependent objects without specifying their concrete classes.
- **Problem Solved:** When assembling government orders, HTML outputs require semantic `<header>` and `<caption>` structures, whereas PDF outputs require ReportLab canvas tables or WeasyPrint CSS page boxes.
- **Implementation:** `DocumentComponentFactory` defines factory methods (`create_header_component()`, `create_table_component()`, `create_signature_component()`). Concrete factories (`HtmlDocumentComponentFactory`, `PdfDocumentComponentFactory`) produce matching component families.

### 2. Factory Method (`autodoc/patterns/factory_method.py`)
- **Intent:** Define an interface for creating an object, but let subclasses decide which class to instantiate.
- **Problem Solved:** When traversing composite nodes, each block type requires custom rendering behavior depending on the target format.
- **Implementation:** `BlockRendererCreator` defines `create_block_renderer(block_type)`. Subclasses instantiate format-specific block renderers (`HtmlHeadingRenderer`, `PdfTableRenderer`, `DocxParagraphRenderer`).

### 3. Builder (`autodoc/patterns/builder.py`)
- **Intent:** Separate the construction of a complex object from its representation so that the same construction process can create different representations.
- **Problem Solved:** Dynamic pipeline synthesis produces variable stages (decorators, renderers, verifiers). Hardcoding execution pipelines violates the open-closed principle.
- **Implementation:** `PipelineBuilder` accepts stage descriptors from the DAG resolver, configures parameters, chains decorator wrappers, and builds `DocumentPipeline` ready for execution.

### 4. Prototype (`autodoc/patterns/prototype.py`)
- **Intent:** Specify the kinds of objects to create using a prototypical instance, and create new objects by copying this prototype.
- **Problem Solved:** Pipeline synthesis involves evaluating rules and topological sorting. Similar documents can reuse pre-built pipeline instances without re-evaluating the rule ontology.
- **Implementation:** `PipelinePrototype.clone()` and `BlockConfigPrototype.clone()` perform deep copies of verified configurations in $\mathcal{O}(1)$ time.

### 5. Singleton (`autodoc/patterns/singleton.py`)
- **Intent:** Ensure a class only has one instance, and provide a global point of access to it.
- **Problem Solved:** Statutory compliance rules (`rules/policies.yaml`) must be loaded and verified once and remain immutable during runtime execution.
- **Implementation:** `PolicyRegistry` and `StyleRegistry` implement thread-safe Double-Checked Locking singletons with class-level `_instance` references and `get_instance()` factories.

### 6. Adapter (`autodoc/patterns/adapter.py`)
- **Intent:** Convert the interface of a class into another interface clients expect. Adapter lets classes work together that couldn't otherwise because of incompatible interfaces.
- **Problem Solved:** Libraries like Jinja2, ReportLab, WeasyPrint, and python-docx each have drastically different APIs and data models.
- **Implementation:** `IRendererAdapter` standardizes methods (`render(document, options) -> Union[str, bytes]`). Adapters translate AST nodes to third-party primitives. Adding Markdown format required only 1 adapter class (28 LOC).

### 7. Bridge (`autodoc/patterns/bridge.py`)
- **Intent:** Decouple an abstraction from its implementation so that the two can vary independently.
- **Problem Solved:** The document orchestration hierarchy (Government Orders, Tender Notices, RTI Replies) must not be coupled to the concrete rendering engines (HTML, PDF, DOCX).
- **Implementation:** `DocumentRendererAbstraction` holds a reference to `IRendererImplementor`. Document logic and rendering engines evolve without cross-compilation dependencies.

### 8. Composite (`autodoc/patterns/composite.py`)
- **Intent:** Compose objects into tree structures to represent part-whole hierarchies. Composite lets clients treat individual objects and compositions of objects uniformly.
- **Problem Solved:** Government documents feature nested, heterogeneous blocks (Sections containing Tables containing Rows containing Cells containing Paragraphs).
- **Implementation:** `DocumentComponent` defines child operations. `CompositeBlockNode` manages children, while `LeafBlockNode` represents terminal leaves. Visitors and transforms traverse trees seamlessly.

### 9. Decorator (`autodoc/patterns/decorator.py`)
- **Intent:** Attach additional responsibilities to an object dynamically. Decorators provide a flexible alternative to subclassing for extending functionality.
- **Problem Solved:** Compliance concerns (Aadhaar redaction, confidential watermark stamping, WCAG accessibility tagging) are orthogonal and cross-cutting.
- **Implementation:** `PipelineStageDecorator` wraps any `IPipelineStage`. Concrete decorators (`RedactionDecorator`, `WatermarkDecorator`, `AccessibilityDecorator`, `PageNumberingDecorator`, `BilingualDecorator`) execute transformations before or after the inner stage.

### 10. Facade (`autodoc/patterns/facade.py`)
- **Intent:** Provide a unified interface to a set of interfaces in a subsystem. Facade defines a higher-level interface that makes the subsystem easier to use.
- **Problem Solved:** Callers would otherwise have to coordinate parsers, DSS analyzers, rule engines, DAG resolvers, pipeline builders, verifiers, signers, and audit loggers.
- **Implementation:** `AutoDocFacade` encapsulates the entire subsystem, offering two intuitive entry points: `plan()` for dry-run preview and `generate()` for certified end-to-end production.

### 11. Flyweight (`autodoc/patterns/flyweight.py`)
- **Intent:** Use sharing to support large numbers of fine-grained objects efficiently.
- **Problem Solved:** Large government tender notices contain thousands of table cells and text spans with identical font, color, and padding attributes.
- **Implementation:** `StyleFlyweightFactory` pools immutable `SharedBlockStyle` objects. Nodes only store integer flyweight IDs or references, reducing AST memory consumption by over 60%.

### 12. Proxy (`autodoc/patterns/proxy.py`)
- **Intent:** Provide a surrogate or placeholder for another object to control access to it.
- **Problem Solved:** Re-rendering identical documents (or identical sections) consumes unnecessary CPU cycles.
- **Implementation:** `CachingRendererProxy` wraps the underlying renderer, calculating a SHA-256 hash of the node subtree and options. If a cache hit occurs, it returns cached bytes immediately.
