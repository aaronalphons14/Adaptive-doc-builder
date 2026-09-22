# FormaFlow implementation plan

## Scope
Build the requested demo frontend as a cohesive multi-page document transformation workspace with mock data and simulated processing states.

## Experience
- Persistent left sidebar for Upload, Analysis, Preview, and History.
- Dark-first technical SaaS visual language: charcoal surfaces, electric blue/teal accents, monospace pipeline labels, clean sans-serif body type, and a light-mode toggle.
- Responsive layout that keeps the workspace usable on smaller screens without changing the main information hierarchy.

## Screens and behavior
- **Upload:** product intro, drag-and-drop document zone accepting `.docx`, `.pdf`, and `.md`, sample document shortcuts, and a simulated upload/analyze action.
- **Analysis:** selected document summary, collapsible detected-structure tree with node type tags, and a pipeline diagram that reveals Factory, Builder, Composite/Decorator, Adapter, Proxy, and Output stages sequentially.
- **Preview:** PDF/DOCX/HTML tabs, live Decorator switches for Watermark, Redaction, Citations, and Accessibility, a rendered document mock that changes with toggles, and a readable active-pipeline list.
- **History:** realistic processed-document table with status and pattern metadata; selecting a row reopens the corresponding pipeline/preview context.

## Technical approach
- Keep the app frontend-only with centralized typed mock data in the route layer for easy API replacement later.
- Use TanStack Router routes for `/`, `/analysis`, `/preview`, and `/history`; navigation uses router Links.
- Use React state and timers for the 1–2 second simulated analysis/build experience; use semantic design tokens in `src/styles.css` rather than hardcoded component colors.
- Add route-specific metadata and preserve the TanStack Start root layout.

## Validation
- Verify the live preview across desktop and mobile-sized viewports.
- Check that upload/sample actions navigate into analysis, pipeline stages reveal in sequence, preview toggles visibly alter the render, history rows reopen the workspace, and the theme toggle works.
