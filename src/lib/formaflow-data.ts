export type SampleDocument = {
  id: string;
  name: string;
  type: string;
  description: string;
  pages: number;
  size: string;
  updated: string;
  accent: "blue" | "teal" | "amber";
};

export type TreeNode = {
  id: string;
  label: string;
  type: string;
  detail?: string;
  children?: TreeNode[];
};

export type PipelineStep = {
  id: string;
  eyebrow: string;
  title: string;
  pattern: string;
  detail: string;
  tone: "blue" | "teal" | "violet" | "amber";
};

export const sampleDocuments: SampleDocument[] = [
  {
    id: "financial-report",
    name: "Q4 Financial Report",
    type: "Annual report",
    description: "Revenue analysis, regional tables, and executive summary.",
    pages: 28,
    size: "2.4 MB",
    updated: "Today, 09:42",
    accent: "blue",
  },
  {
    id: "vendor-contract",
    name: "Vendor Master Agreement",
    type: "Contract",
    description: "Clauses, definitions, signature blocks, and sensitive fields.",
    pages: 16,
    size: "1.1 MB",
    updated: "Yesterday, 16:18",
    accent: "teal",
  },
  {
    id: "technical-spec",
    name: "Edge Runtime Specification",
    type: "Technical spec",
    description: "Nested headings, code examples, API tables, and callouts.",
    pages: 42,
    size: "4.8 MB",
    updated: "Sep 18, 13:04",
    accent: "amber",
  },
];

export const structureTree: TreeNode[] = [
  {
    id: "cover",
    label: "Cover & executive summary",
    type: "section",
    children: [
      { id: "title", label: "Q4 performance overview", type: "heading" },
      { id: "summary", label: "Summary paragraph", type: "text" },
    ],
  },
  {
    id: "revenue",
    label: "1. Revenue performance",
    type: "section",
    children: [
      {
        id: "regional",
        label: "1.1 Regional breakdown",
        type: "subsection",
        children: [
          { id: "region-table", label: "Regional revenue table", type: "table", detail: "6 × 5" },
          { id: "cell-block", label: "Repeated metric cells", type: "repeated block", detail: "30 nodes" },
        ],
      },
      { id: "chart-note", label: "Year-over-year callout", type: "callout" },
    ],
  },
  {
    id: "operations",
    label: "2. Operating expenses",
    type: "section",
    children: [
      { id: "expense-table", label: "Expense detail table", type: "table", detail: "8 × 4" },
      { id: "notes", label: "Notes & assumptions", type: "footnotes" },
    ],
  },
  {
    id: "appendix",
    label: "Appendix",
    type: "section",
    children: [
      { id: "glossary", label: "Metric glossary", type: "list" },
      { id: "sources", label: "Source references", type: "references" },
    ],
  },
];

export const pipelineSteps: PipelineStep[] = [
  {
    id: "factory",
    eyebrow: "01 / SELECT",
    title: "Factory selection",
    pattern: "Abstract Factory",
    detail: "PDF family selected",
    tone: "blue",
  },
  {
    id: "builder",
    eyebrow: "02 / ASSEMBLE",
    title: "Builder assembly",
    pattern: "Builder",
    detail: "Cover · body · appendix",
    tone: "teal",
  },
  {
    id: "composite",
    eyebrow: "03 / COMPOSE",
    title: "Structure mapping",
    pattern: "Composite",
    detail: "Nested tables preserved",
    tone: "violet",
  },
  {
    id: "decorator",
    eyebrow: "04 / ENRICH",
    title: "Decorator stack",
    pattern: "Decorator",
    detail: "Redaction layer ready",
    tone: "amber",
  },
  {
    id: "adapter",
    eyebrow: "05 / TRANSLATE",
    title: "Format adapter",
    pattern: "Adapter",
    detail: "Semantic PDF output",
    tone: "blue",
  },
  {
    id: "proxy",
    eyebrow: "06 / CACHE",
    title: "Render proxy",
    pattern: "Proxy",
    detail: "Warm render cache",
    tone: "teal",
  },
  {
    id: "output",
    eyebrow: "07 / DELIVER",
    title: "Output ready",
    pattern: "Output",
    detail: "Download or refine",
    tone: "blue",
  },
];

export const historyRows = [
  { ...sampleDocuments[0], detected: "Financial report", format: "PDF", patterns: "6 patterns", status: "Ready", date: "Today, 09:42" },
  { ...sampleDocuments[1], detected: "Legal contract", format: "DOCX", patterns: "5 patterns", status: "Ready", date: "Yesterday, 16:18" },
  { ...sampleDocuments[2], detected: "Technical spec", format: "HTML", patterns: "7 patterns", status: "Ready", date: "Sep 18, 13:04" },
  { id: "board-pack", name: "Board Meeting Pack", type: "Board pack", description: "Slides, metrics, and decision log.", pages: 34, size: "6.2 MB", updated: "Sep 16, 10:12", accent: "blue" as const, detected: "Board pack", format: "PDF", patterns: "6 patterns", status: "Archived", date: "Sep 16, 10:12" },
];

export const getDocument = (id: string | undefined) => sampleDocuments.find((document) => document.id === id) ?? sampleDocuments[0];