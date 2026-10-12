"""FastAPI REST API server for AutoDoc-Gov platform."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from autodoc.analysis.parser import parse_document
from autodoc.audit.hash_chain import HashChainAuditLogger
from autodoc.core.exceptions import ApprovalRequiredError, ComplianceError
from autodoc.patterns.facade import AutoDocFacade

app = FastAPI(
    title="AutoDoc-Gov API",
    description="Self-Assembling, Compliance-by-Construction Document Generation Platform for Government Departments",
    version="1.0.0",
)

# CORS middleware for development and UI integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent.parent.parent
SAMPLES_DIR = BASE_DIR / "samples"
OUTPUT_DIR = BASE_DIR / "output"
STATIC_DIR = Path(__file__).parent / "static"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Mount static folder
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class PlanRequestBody(BaseModel):
    content: str
    format: str = "html"
    file_type: str = "json"


class GenerateRequestBody(BaseModel):
    content: str
    format: str = "html"
    file_type: str = "json"
    approver: Optional[str] = None


@app.get("/health")
def health_check() -> Dict[str, Any]:
    """Health check returning platform status and capabilities."""
    facade = AutoDocFacade()
    return {
        "status": "healthy",
        "service": "AutoDoc-Gov",
        "version": "1.0.0",
        "supported_formats": ["html", "pdf", "docx", "markdown"],
        "rules_registered": len(facade.synthesizer.rule_engine.rules),
        "output_directory": str(OUTPUT_DIR),
    }


@app.get("/samples")
def list_samples() -> List[Dict[str, Any]]:
    """List bundled government sample documents for interactive demo testing."""
    samples = []
    if SAMPLES_DIR.exists():
        for path in sorted(SAMPLES_DIR.iterdir()):
            if path.is_file() and path.suffix in [".json", ".md", ".docx", ".txt"]:
                try:
                    text_content = path.read_text(encoding="utf-8")
                except Exception:
                    text_content = "[Binary or unreadable format]"
                samples.append({
                    "filename": path.name,
                    "stem": path.stem,
                    "suffix": path.suffix.lstrip("."),
                    "content": text_content,
                })
    return samples


@app.post("/plan")
def plan_pipeline(req: PlanRequestBody) -> Dict[str, Any]:
    """Dry-run synthesize pipeline from content without rendering."""
    facade = AutoDocFacade()
    try:
        doc = parse_document(req.content, format_hint=req.file_type)
        plan_res = facade.plan(doc, options={"format": req.format})
        return {
            "document_id": plan_res.document_id,
            "classification": plan_res.classification,
            "approval_required": plan_res.approval_required,
            "dss": {
                "fingerprint": plan_res.dss.fingerprint,
                "document_type": plan_res.dss.document_type,
                "languages": plan_res.dss.languages,
                "node_count": plan_res.dss.node_count,
                "depth": plan_res.dss.depth,
                "sensitive_data_count": plan_res.dss.sensitive_data_count,
                "sensitive_types": plan_res.dss.sensitive_entities,
                "feature_vector": plan_res.dss.feature_vector.to_canonical_dict(),
            },
            "ordered_stages": plan_res.ordered_stages,
            "fired_rules": plan_res.fired_rules,
            "conflict_log": plan_res.conflict_log,
            "mermaid_diagram": plan_res.mermaid_diagram,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Planning failed: {str(e)}")


@app.post("/generate")
def generate_document_endpoint(req: GenerateRequestBody) -> Dict[str, Any]:
    """End-to-end synthesis, rendering, compliance verification, and hash-chain audit."""
    facade = AutoDocFacade()
    try:
        doc = parse_document(req.content, format_hint=req.file_type)
        res = facade.generate(
            input_data=doc,
            output_format=req.format,
            approval_token=req.approver,
            output_dir=OUTPUT_DIR,
        )

        # Artifact representation
        is_binary = isinstance(res.artifact, bytes)
        content_preview = ""
        b64_data = ""
        if isinstance(res.artifact, bytes):
            b64_data = base64.b64encode(res.artifact).decode("utf-8")
        else:
            content_preview = str(res.artifact)

        filename = res.output_path.name if res.output_path else f"{res.document_id}.{req.format}"

        return {
            "success": True,
            "document_id": res.document_id,
            "format": res.format,
            "filename": filename,
            "download_url": f"/output/{filename}",
            "verification_passed": res.verification_passed,
            "dss_fingerprint": res.dss.fingerprint,
            "audit_entry": {
                "index": res.audit_entry.index,
                "entry_hash": res.audit_entry.entry_hash,
                "prev_hash": res.audit_entry.prev_hash,
                "timestamp": res.audit_entry.timestamp,
            },
            "assembly_report_markdown": res.assembly_report_markdown,
            "assembly_report": res.assembly_report_dict,
            "content_preview": content_preview,
            "binary_base64": b64_data if is_binary else None,
        }
    except ApprovalRequiredError as e:
        raise HTTPException(status_code=403, detail=f"Approval Required: {str(e)}")
    except ComplianceError as e:
        raise HTTPException(status_code=422, detail=f"Compliance Breach: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.post("/upload/generate")
async def upload_and_generate(
    file: UploadFile = File(...),
    format: str = Query("html"),
    approver: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Handle multipart file uploads and generate compliant output."""
    raw_bytes = await file.read()
    suffix = Path(file.filename or "doc.json").suffix.lstrip(".")
    try:
        text_content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text_content = ""

    facade = AutoDocFacade()
    try:
        if suffix == "docx":
            tmp_docx = OUTPUT_DIR / f"_upload_{file.filename or 'doc.docx'}"
            tmp_docx.write_bytes(raw_bytes)
            doc = parse_document(tmp_docx, format_hint=suffix)
        else:
            doc = parse_document(text_content, format_hint=suffix)
        res = facade.generate(
            input_data=doc,
            output_format=format,
            approval_token=approver,
            output_dir=OUTPUT_DIR,
        )

        filename = res.output_path.name if res.output_path else f"{res.document_id}.{format}"
        is_binary = isinstance(res.artifact, bytes)

        return {
            "success": True,
            "document_id": res.document_id,
            "format": res.format,
            "filename": filename,
            "download_url": f"/output/{filename}",
            "verification_passed": res.verification_passed,
            "dss_fingerprint": res.dss.fingerprint,
            "audit_entry": {
                "index": res.audit_entry.index,
                "entry_hash": res.audit_entry.entry_hash,
                "prev_hash": res.audit_entry.prev_hash,
                "timestamp": res.audit_entry.timestamp,
            },
            "assembly_report_markdown": res.assembly_report_markdown,
            "content_preview": str(res.artifact) if not is_binary else "",
        }
    except ApprovalRequiredError as e:
        raise HTTPException(status_code=403, detail=f"Approval Required: {str(e)}")
    except ComplianceError as e:
        raise HTTPException(status_code=422, detail=f"Compliance Breach: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.get("/output/{filename}")
def download_output_file(filename: str):
    """Serve rendered artifact file from output directory."""
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    media_types = {
        ".html": "text/html",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".json": "application/json",
    }
    media_type = media_types.get(path.suffix.lower(), "application/octet-stream")
    return FileResponse(path=path, media_type=media_type, filename=path.name)


@app.get("/audit/verify")
def verify_audit_chain() -> Dict[str, Any]:
    """Verify cryptographic integrity of the hash chain audit log."""
    logger = HashChainAuditLogger(log_file=OUTPUT_DIR / "audit_log.json")
    valid, message = logger.verify_integrity()
    return {
        "valid": valid,
        "total_blocks": len(logger.get_entries()),
        "message": message or "Hash chain is cryptographically intact",
    }


@app.get("/audit/entries")
def get_audit_entries() -> List[Dict[str, Any]]:
    """Retrieve full immutable audit entries log."""
    logger = HashChainAuditLogger(log_file=OUTPUT_DIR / "audit_log.json")
    return [
        {
            "index": e.index,
            "timestamp": e.timestamp,
            "document_id": e.document_id,
            "dss_hash": e.dss_hash,
            "output_format": e.output_format,
            "rules_fired": e.rules_fired,
            "stages_executed": e.stages_executed,
            "verification_passed": e.verification_passed,
            "prev_hash": e.prev_hash,
            "entry_hash": e.entry_hash,
            "extra_metadata": e.extra_metadata,
        }
        for e in logger.get_entries()
    ]


@app.get("/", response_class=HTMLResponse)
def index_page():
    """Serve standalone web demo user interface."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>AutoDoc-Gov API Active</h1><p>Static UI not yet written.</p>")
