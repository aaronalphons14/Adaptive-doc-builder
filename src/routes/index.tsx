import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useRef, useState } from "react";
import { ArrowUpRight, Check, FileText, FolderUp, ScanSearch, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { sampleDocuments } from "@/lib/formaflow-data";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Upload — FormaFlow" },
      { name: "description", content: "Upload a document and let FormaFlow assemble the right transformation pipeline." },
      { property: "og:title", content: "Upload — FormaFlow" },
      { property: "og:description", content: "Upload once. Detect structure. Build the right pipeline automatically." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: UploadPage,
});

function UploadPage() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [fileName, setFileName] = useState("");
  const [processing, setProcessing] = useState(false);

  const openAnalysis = (id = "financial-report") => {
    setProcessing(true);
    window.setTimeout(() => navigate({ to: "/analysis", search: { doc: id } }), 850);
  };

  const chooseFile = (file?: File) => {
    if (!file) return;
    setFileName(file.name);
    openAnalysis();
  };

  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex items-start justify-between gap-6">
        <div>
          <div className="mb-5 flex items-center gap-2 text-primary"><span className="size-1.5 rounded-full bg-primary" /><span className="ff-mono text-[11px] uppercase tracking-[0.1em]">Adaptive document transformation</span></div>
          <h1 className="max-w-3xl text-4xl font-semibold tracking-[-0.04em] text-foreground md:text-6xl">Upload once. We detect the structure and build the right pipeline automatically.</h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-muted-foreground">FormaFlow reads the shape of your document, then composes the design patterns needed to render it cleanly across formats.</p>
        </div>
        <div className="hidden items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 md:flex"><span className="size-2 rounded-full bg-primary shadow-[0_0_12px] shadow-primary" /><span className="ff-mono text-[10px] text-muted-foreground">ENGINE ONLINE</span></div>
      </div>

      <section className="mt-12 grid gap-5 lg:grid-cols-[1fr_300px]">
        <div
          className={`ff-panel relative flex min-h-[360px] flex-col items-center justify-center overflow-hidden rounded-lg border-dashed p-8 text-center transition-colors ${dragging ? "border-primary bg-primary/5" : "border-border"}`}
          onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => { event.preventDefault(); setDragging(false); chooseFile(event.dataTransfer.files[0]); }}
        >
          <div className="absolute left-0 top-0 h-px w-1/3 bg-primary/70" />
          <div className="mb-5 flex size-14 items-center justify-center rounded-lg border border-primary/25 bg-primary/10 text-primary"><FolderUp className="size-6" /></div>
          <h2 className="text-xl font-semibold">{processing ? "Preparing analysis…" : fileName || "Drop a document here"}</h2>
          <p className="mt-2 max-w-md text-sm text-muted-foreground">or choose a file to start the structure scan. We support DOCX, PDF, and Markdown.</p>
          <input ref={inputRef} type="file" accept=".docx,.pdf,.md" className="hidden" onChange={(event) => chooseFile(event.target.files?.[0])} />
          <Button className="mt-7" disabled={processing} onClick={() => inputRef.current?.click()}>{processing ? <ScanSearch className="animate-pulse" /> : <FolderUp />} {processing ? "Analyzing structure" : "Choose document"}</Button>
          <div className="mt-7 flex flex-wrap justify-center gap-2">{[".docx", ".pdf", ".md"].map((type) => <Badge key={type} variant="outline" className="ff-mono text-[10px] text-muted-foreground">{type}</Badge>)}</div>
        </div>

        <aside className="ff-panel rounded-lg p-5">
          <div className="flex items-center gap-2"><Sparkles className="size-4 text-primary" /><p className="ff-mono text-[11px] uppercase text-muted-foreground">How it works</p></div>
          <div className="mt-6 space-y-5">{[["01", "Detect", "Headings, tables, repeated blocks"], ["02", "Compose", "Patterns selected by structure"], ["03", "Render", "One source, any output"]].map(([number, title, body]) => <div key={number} className="flex gap-3"><span className="ff-mono text-xs text-primary">{number}</span><div><p className="text-sm font-medium">{title}</p><p className="mt-1 text-xs leading-5 text-muted-foreground">{body}</p></div></div>)}</div>
          <div className="mt-8 border-t border-border pt-4"><p className="text-xs text-muted-foreground">No per-document setup. The engine adapts to what it finds.</p></div>
        </aside>
      </section>

      <section className="mt-14">
        <div className="mb-5 flex items-end justify-between"><div><p className="ff-mono text-[11px] uppercase tracking-[0.1em] text-muted-foreground">Start with a sample</p><h2 className="mt-2 text-xl font-semibold">Explore a live pipeline</h2></div><p className="hidden text-xs text-muted-foreground sm:block">Pre-loaded examples · no upload required</p></div>
        <div className="grid gap-3 md:grid-cols-3">
          {sampleDocuments.map((document) => <button key={document.id} type="button" onClick={() => openAnalysis(document.id)} className="ff-panel group rounded-lg p-5 text-left transition-colors hover:border-primary/60 hover:bg-accent/60"><div className="flex items-start justify-between"><span className="flex size-9 items-center justify-center rounded-md border border-border bg-background text-muted-foreground"><FileText className="size-4" /></span><ArrowUpRight className="size-4 text-muted-foreground transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary" /></div><p className="mt-5 text-sm font-semibold">{document.name}</p><p className="mt-1 text-xs leading-5 text-muted-foreground">{document.description}</p><div className="mt-5 flex items-center gap-2 text-[10px] text-muted-foreground"><span className="ff-mono">{document.type}</span><span className="size-1 rounded-full bg-border" /><span>{document.pages} pages</span><span className="size-1 rounded-full bg-border" /><Check className="size-3 text-primary" /> ready</div></button>)}
        </div>
      </section>
    </div>
  );
}