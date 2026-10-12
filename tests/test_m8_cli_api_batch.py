"""Tests for Milestone 8: Typer CLI, FastAPI REST API, Batch Processing, and Web UI."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from autodoc.api.app import app as fastapi_app
from autodoc.cli.main import app as cli_app


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def api_client():
    return TestClient(fastapi_app)


def test_cli_help(cli_runner):
    """Test CLI base command prints help with all 5 commands."""
    res = cli_runner.invoke(cli_app, ["--help"])
    assert res.exit_code == 0
    assert "generate" in res.output
    assert "plan" in res.output
    assert "verify" in res.output
    assert "batch" in res.output
    assert "audit-verify" in res.output


def test_cli_plan_command_and_mermaid(cli_runner):
    """Test CLI 'plan' dry-run inspects DSS, DAG stages, and mermaid."""
    sample_path = "samples/01_government_order.json"

    # 1. Plain plan table
    res = cli_runner.invoke(cli_app, ["plan", sample_path])
    assert res.exit_code == 0
    assert "Pipeline Plan (N2)" in res.output
    assert "Execution Order" in res.output

    # 2. Mermaid diagram
    res_m = cli_runner.invoke(cli_app, ["plan", sample_path, "--mermaid"])
    assert res_m.exit_code == 0
    assert "flowchart LR" in res_m.output
    assert "HtmlRendererStage" in res_m.output

    # 3. JSON format
    res_j = cli_runner.invoke(cli_app, ["plan", sample_path, "--json"])
    assert res_j.exit_code == 0
    raw_json = res_j.output[res_j.output.find("{") : res_j.output.rfind("}") + 1]
    plan_data = json.loads(raw_json)
    assert "ordered_stages" in plan_data
    assert "dss_fingerprint" in plan_data


def test_cli_generate_dry_run(cli_runner):
    """Test CLI 'generate --dry-run' exits with zero without rendering."""
    sample_path = "samples/02_tender_notice.md"
    res = cli_runner.invoke(cli_app, ["generate", sample_path, "--dry-run"])
    assert res.exit_code == 0
    assert "DRY-RUN MODE" in res.output
    assert "Document Structure Signature" in res.output
    assert "[OK] Dry-run completed successfully" in res.output


def test_cli_generate_full_html_and_audit(cli_runner, tmp_path):
    """Test CLI end-to-end generate creates artifact and updates audit log."""
    sample_path = "samples/01_government_order.json"
    out_file = tmp_path / "cli_test_order.html"

    res = cli_runner.invoke(cli_app, [
        "generate",
        sample_path,
        "--format", "html",
        "--output", str(out_file),
    ])
    assert res.exit_code == 0
    assert out_file.exists()
    assert "PASSED (Zero Violations)" in res.output
    assert "[OK] Output successfully generated" in res.output

    content = out_file.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content


def test_cli_verify_command(cli_runner, tmp_path):
    """Test CLI 'verify' command on compliant and non-compliant artifacts."""
    # Compliant HTML
    clean_html = tmp_path / "clean.html"
    clean_html.write_text("""<!DOCTYPE html>
<html lang="en">
<head><title>Title</title></head>
<body>
  <main>
    <h1>Primary Heading</h1>
    <p>Clean text without sensitive identifiers.</p>
  </main>
</body>
</html>""", encoding="utf-8")

    res_clean = cli_runner.invoke(cli_app, ["verify", str(clean_html)])
    assert res_clean.exit_code == 0
    assert "All compliance checks passed without violation" in res_clean.output

    # Non-compliant HTML with unmasked Aadhaar
    dirty_html = tmp_path / "dirty.html"
    dirty_html.write_text("""<!DOCTYPE html>
<html lang="en">
<head><title>Title</title></head>
<body>
  <h1>Primary Heading</h1>
  <p>Beneficiary Aadhaar: 3675 9834 6012</p>
</body>
</html>""", encoding="utf-8")

    res_dirty = cli_runner.invoke(cli_app, ["verify", str(dirty_html)])
    assert res_dirty.exit_code == 1
    assert "Compliance verification failed" in res_dirty.output


def test_cli_batch_processing(cli_runner, tmp_path):
    """Test CLI 'batch' command runs across directory of heterogeneous documents."""
    batch_out = tmp_path / "batch_out"
    res = cli_runner.invoke(cli_app, [
        "batch",
        "samples/",
        "--format", "html",
        "--output-dir", str(batch_out),
        "--approver", "BatchOfficer-Clearance",
    ])
    assert res.exit_code == 0
    assert "Batch Summary: 5 succeeded, 0 failed" in res.output


def test_cli_audit_verify(cli_runner):
    """Test CLI 'audit-verify' validates cryptographic integrity of the audit chain."""
    res = cli_runner.invoke(cli_app, ["audit-verify"])
    assert res.exit_code == 0
    assert "Audit Chain Integrity VERIFIED" in res.output


def test_api_health_endpoint(api_client):
    """Test FastAPI /health endpoint."""
    res = api_client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "html" in data["supported_formats"]


def test_api_samples_list(api_client):
    """Test FastAPI /samples endpoint returns bundled government files."""
    res = api_client.get("/samples")
    assert res.status_code == 200
    samples = res.json()
    assert len(samples) >= 5
    filenames = [s["filename"] for s in samples]
    assert any("government_order" in fn for fn in filenames)
    assert any("tender_notice" in fn for fn in filenames)


def test_api_plan_endpoint(api_client):
    """Test FastAPI /plan endpoint produces DSS and synthesized DAG."""
    payload = {
        "content": Path("samples/01_government_order.json").read_text(encoding="utf-8"),
        "format": "html",
        "file_type": "json",
    }
    res = api_client.post("/plan", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "dss" in data
    assert "ordered_stages" in data
    assert "mermaid_diagram" in data
    assert len(data["ordered_stages"]) > 0


def test_api_generate_endpoint_and_report(api_client):
    """Test FastAPI /generate endpoint returns artifact and full assembly report."""
    payload = {
        "content": Path("samples/03_rti_reply.json").read_text(encoding="utf-8"),
        "format": "html",
        "file_type": "json",
        "approver": "RTI-Appellate-Authority",
    }
    res = api_client.post("/generate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["verification_passed"] is True
    assert "audit_entry" in data
    assert "assembly_report_markdown" in data
    assert "content_preview" in data
    # Confirm RTI personal identifiers were redacted in output
    assert "3675 9834 6012" not in data["content_preview"]
    assert "ABCDE1234F" not in data["content_preview"]


def test_api_audit_verify_endpoint(api_client):
    """Test FastAPI /audit/verify endpoint."""
    res = api_client.get("/audit/verify")
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["total_blocks"] > 0


def test_api_web_demo_ui_serving(api_client):
    """Test root endpoint / serves HTML Web Demo UI."""
    res = api_client.get("/")
    assert res.status_code == 200
    assert "AutoDoc-Gov" in res.text
    assert "mermaid" in res.text
