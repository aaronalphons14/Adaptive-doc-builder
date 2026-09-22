# Adaptive Doc Builder

Build a web app called "FormaFlow" — a demo frontend for an adaptive document-transformation 

engine that automatically assembles a rendering pipeline based on a document's content structure.

CORE CONCEPT TO VISUALIZE:

The app takes an uploaded document, analyzes its structure (sections, tables, headings, 

repeated blocks), and shows the engine dynamically composing a chain of design-pattern-based 

transformation steps to render it into different output formats — without any manual 

per-document configuration.

PAGES / SCREENS:

1. Landing / Upload screen

   - Clean hero section explaining "Upload once. We detect the structure and build the 

     right pipeline automatically."

   - Drag-and-drop upload zone (accept .docx, .pdf, .md — mock the actual parsing, just 

     use placeholder sample documents if no backend)

   - A few pre-loaded sample documents to click and try instantly (e.g. "Financial Report", 

     "Contract", "Technical Spec")

2. Structure Analysis screen

   - Left panel: a collapsible tree view of the detected document structure (sections → 

     subsections → tables → cells → repeated blocks), each node tagged with its detected 

     type

   - Right panel: a live-building visual pipeline diagram — animated nodes appearing in 

     sequence representing: Factory selection → Builder assembly → Decorator stack → 

     Adapter → Output — like a flowchart building itself node by node with a subtle 

     animation as "analysis" completes

   - Small badges/tags per node showing which pattern is active (e.g. "Abstract Factory: 

     PDF family", "Decorator: Redaction layer", "Composite: nested table")

3. Output Preview screen

   - Tabs to switch between output formats (PDF / DOCX / HTML preview mock)

   - A toggle panel of "Decorator" options the user can turn on/off live (Watermark, 

     Redact sensitive fields, Add citations, Accessibility tags) — toggling should visibly 

     re-render the preview panel styling instantly

   - Sidebar showing the current active pipeline as a readable list, e.g.:

     "AbstractFactory(PDF) → Builder(cover, body, appendix) → Composite(nested tables) → 

     Decorator(Watermark, Redaction) → Proxy(cached render) → Output"

4. Dashboard/History screen

   - Table of past processed documents with columns: Name, Detected Type, Output Format, 

     Patterns Used, Status, Date

   - Clicking a row reopens that document's pipeline view

DESIGN STYLE:

- Modern, technical-but-approachable SaaS aesthetic — think Linear or Vercel dashboard style

- Dark mode default with a light mode toggle

- Monospace accents for pipeline/pattern labels, clean sans-serif for body text

- Subtle animated transitions when the pipeline "builds" (nodes fade/slide in sequentially, 

  not all at once)

- Use a restrained accent color (e.g. electric blue or teal) against neutral dark background

DATA:

- No real backend needed yet — use realistic mock data and simulated async delays (1-2s) 

  to fake the "analyzing structure" and "building pipeline" steps so it feels alive

- Structure all mock data in a way that's easy to later swap for real API calls

Keep the whole thing as a single cohesive multi-page app with a persistent left sidebar 

for navigation between Upload / Analysis / Preview / History.

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/152b21bc-98ca-45d2-b994-33aa81dd80e9).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
