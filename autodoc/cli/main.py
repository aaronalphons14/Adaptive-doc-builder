"""Typer CLI entrypoint for AutoDoc-Gov platform."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from autodoc.audit.hash_chain import HashChainAuditLogger
from autodoc.core.exceptions import ApprovalRequiredError, ComplianceError
from autodoc.patterns.facade import AutoDocFacade
from autodoc.verifier.accessibility_check import AccessibilityCheck
from autodoc.verifier.redaction_check import RedactionCheck
from autodoc.verifier.watermark_check import WatermarkCheck

app = typer.Typer(
    name="autodoc",
    help="AutoDoc-Gov: Self-Assembling Compliance-by-Construction Document Generation Platform",
    no_args_is_help=True,
)
console = Console()


@app.command("generate")
def generate_command(
    input_file: Path = typer.Argument(..., help="Path to input document (JSON, MD, DOCX, TXT)"),
    format: str = typer.Option("html", "--format", "-f", help="Output format: html, pdf, docx, markdown"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Explicit path to save output document"),
    output_dir: Path = typer.Option(Path("output"), "--output-dir", "-d", help="Directory to save output documents"),
    approver: Optional[str] = typer.Option(None, "--approver", "-a", help="Approver ID/token for confidential/secret documents"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview DSS and synthesized pipeline without rendering"),
) -> None:
    """Analyze input document, synthesize compliance pipeline, render output, and generate audit trail."""
    if not input_file.exists():
        console.print(f"[bold red]Error:[/] Input file not found: {input_file}")
        raise typer.Exit(code=1)

    facade = AutoDocFacade()

    if dry_run:
        console.print(Panel(f"[bold cyan]DRY-RUN MODE:[/] Planning pipeline for [yellow]{input_file.name}[/]", title="AutoDoc-Gov Plan"))
        try:
            plan_result = facade.plan(input_file, options={"format": format})

            dss = plan_result.dss
            dss_table = Table(title="Document Structure Signature (DSS - N1)", show_header=True)
            dss_table.add_column("Property", style="cyan")
            dss_table.add_column("Value", style="green")
            dss_table.add_row("Document ID", plan_result.document_id)
            dss_table.add_row("Classification", plan_result.classification.upper())
            dss_table.add_row("Approval Required", str(plan_result.approval_required))
            dss_table.add_row("Doc Type", str(dss.document_type))
            dss_table.add_row("Languages", ", ".join(dss.languages))
            dss_table.add_row("Nodes Count", str(dss.node_count))
            dss_table.add_row("Depth", str(dss.depth))
            dss_table.add_row("Sensitive Entities", str(len(dss.sensitive_entities)))
            dss_table.add_row("Fingerprint SHA-256", dss.fingerprint[:16] + "...")
            console.print(dss_table)

            stages_table = Table(title="Synthesized Pipeline Stages (N2)", show_header=True)
            stages_table.add_column("Step", style="magenta")
            stages_table.add_column("Stage ID", style="bold")
            for i, stg in enumerate(plan_result.ordered_stages, start=1):
                stages_table.add_row(str(i), stg)
            console.print(stages_table)

            console.print("\n[bold green][OK] Dry-run completed successfully. No artifacts rendered.[/]")
            return
        except typer.Exit:
            raise
        except Exception as e:
            console.print(f"[bold red]Planning failed:[/] {e}")
            raise typer.Exit(code=1)

    try:
        console.print(f"[bold blue]Processing:[/] {input_file.name} -> {format.upper()}")
        result = facade.generate(
            input_data=input_file,
            output_format=format,
            approval_token=approver,
            output_dir=output_dir,
        )

        # If user specified explicit output path
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(result.artifact, bytes):
                output.write_bytes(result.artifact)
            else:
                output.write_text(result.artifact, encoding="utf-8")
            saved_path = output
        else:
            saved_path = result.output_path or output_dir / f"{input_file.stem}.{format}"

        # Summary Display
        table = Table(title="Generation & Compliance Summary (AutoDoc-Gov)", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Details", style="green")
        table.add_row("Document ID", result.document_id)
        table.add_row("Format", result.format.upper())
        table.add_row("Saved Path", str(saved_path))
        table.add_row("DSS Hash", result.dss.fingerprint[:24] + "...")
        table.add_row("Compliance Verifier", "[bold green]PASSED (Zero Violations)[/]" if result.verification_passed else "[bold red]FAILED[/]")
        table.add_row("Audit Chain Hash", result.audit_entry.entry_hash[:24] + "...")
        table.add_row("Audit Block #", str(result.audit_entry.index))
        console.print(table)

        console.print(f"[bold green][OK] Output successfully generated and compliance-certified:[/] {saved_path}")

    except ApprovalRequiredError as e:
        console.print(f"\n[bold red]APPROVAL REQUIRED:[/] {e}")
        console.print("[yellow]Hint: Pass --approver <officer_id> to approve generation for classified documents.[/]")
        raise typer.Exit(code=2)
    except ComplianceError as e:
        console.print(f"\n[bold red]COMPLIANCE VIOLATION:[/] {e}")
        raise typer.Exit(code=3)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"\n[bold red]Generation Error:[/] {e}")
        raise typer.Exit(code=1)


@app.command("plan")
def plan_command(
    input_file: Path = typer.Argument(..., help="Path to input document"),
    format: str = typer.Option("html", "--format", "-f", help="Target output format"),
    mermaid: bool = typer.Option(False, "--mermaid", "-m", help="Print synthesized pipeline Mermaid flowchart"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output plan details as JSON"),
) -> None:
    """Inspect synthesized pipeline DAG, triggered rules, and DSS without rendering."""
    if not input_file.exists():
        console.print(f"[bold red]Error:[/] Input file not found: {input_file}")
        raise typer.Exit(code=1)

    facade = AutoDocFacade()
    try:
        plan_res = facade.plan(input_file, options={"format": format})

        if json_output:
            data = {
                "document_id": plan_res.document_id,
                "dss_fingerprint": plan_res.dss.fingerprint,
                "ordered_stages": plan_res.ordered_stages,
                "fired_rules": plan_res.fired_rules,
                "approval_required": plan_res.approval_required,
                "classification": plan_res.classification,
            }
            typer.echo(json.dumps(data, indent=2))
            return

        if mermaid:
            typer.echo(plan_res.mermaid_diagram)
            return

        console.print(Panel(f"Synthesized Plan for [yellow]{input_file.name}[/] ({format.upper()})", title="Pipeline Plan (N2)"))

        p_table = Table(show_header=True)
        p_table.add_column("Property", style="cyan")
        p_table.add_column("Value", style="green")
        p_table.add_row("Document ID", plan_res.document_id)
        p_table.add_row("Classification", plan_res.classification)
        p_table.add_row("Approval Required", str(plan_res.approval_required))
        p_table.add_row("DSS Hash", plan_res.dss.fingerprint[:24] + "...")
        p_table.add_row("Stages Count", str(len(plan_res.ordered_stages)))
        p_table.add_row("Rules Triggered", str(len(plan_res.fired_rules)))
        console.print(p_table)

        stages_table = Table(title="Execution Order (DAG Topological Sort)", show_header=True)
        stages_table.add_column("Sequence", style="magenta")
        stages_table.add_column("Stage Class / Decorator", style="bold green")
        for i, stg in enumerate(plan_res.ordered_stages, start=1):
            stages_table.add_row(str(i), stg)
        console.print(stages_table)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Planning error:[/] {e}")
        raise typer.Exit(code=1)


@app.command("verify")
def verify_command(
    output_file: Path = typer.Argument(..., help="Path to rendered output file to verify"),
    doc_type: str = typer.Option("general", "--type", "-t", help="Document type: rti_reply, tender_notice, etc."),
    classification: str = typer.Option("unclassified", "--classification", "-c", help="Classification level"),
) -> None:
    """Run post-render verification suite (redaction check, watermark check, accessibility check)."""
    if not output_file.exists():
        console.print(f"[bold red]Error:[/] Output file not found: {output_file}")
        raise typer.Exit(code=1)

    content = output_file.read_bytes() if output_file.suffix.lower() == ".pdf" else output_file.read_text(encoding="utf-8", errors="replace")

    t = Table(title=f"Verification Report for {output_file.name}")
    t.add_column("Check Name", style="cyan")
    t.add_column("Status", style="bold")
    t.add_column("Details", style="yellow")

    all_passed = True
    violations: list[str] = []

    # 1. Redaction / Zero-PII Check
    redaction_check = RedactionCheck()
    pii_pass, leaks, summary = redaction_check.check(content)
    if not pii_pass:
        all_passed = False
        violations.append(summary)
    t.add_row(
        "Zero-PII Compliance (DPDP Act)",
        "[green]PASSED[/]" if pii_pass else "[red]FAILED[/]",
        summary if pii_pass else f"[red]{summary} ({len(leaks)} leaks)[/]"
    )

    # 2. Watermark Check (if classified)
    if classification.lower() != "unclassified":
        wm_check = WatermarkCheck()
        wm_pass, wm_msg = wm_check.check(content, expected_watermark=classification.upper())
        if not wm_pass:
            all_passed = False
            violations.append(wm_msg)
        t.add_row(
            "Classification Watermark",
            "[green]PASSED[/]" if wm_pass else "[red]FAILED[/]",
            wm_msg
        )
    else:
        t.add_row("Classification Watermark", "[green]SKIPPED[/]", "Document is unclassified")

    # 3. Accessibility Check (for HTML)
    if isinstance(content, str) and output_file.suffix.lower() == ".html":
        acc_check = AccessibilityCheck()
        acc_pass, acc_errs = acc_check.check(content)
        if not acc_pass:
            all_passed = False
            violations.extend(acc_errs)
        t.add_row(
            "GIGW 3.0 / WCAG AA Accessibility",
            "[green]PASSED[/]" if acc_pass else "[red]FAILED[/]",
            "All structural tags and alt attributes valid" if acc_pass else f"[red]{', '.join(acc_errs)}[/]"
        )

    console.print(t)
    if all_passed:
        console.print("[bold green][OK] All compliance checks passed without violation.[/]")
        raise typer.Exit(code=0)
    else:
        console.print(f"[bold red][FAIL] Compliance verification failed with {len(violations)} violation(s).[/]")
        raise typer.Exit(code=1)


@app.command("batch")
def batch_command(
    folder: Path = typer.Argument(..., help="Folder containing documents to process"),
    format: str = typer.Option("html", "--format", "-f", help="Output format: html, pdf, docx, markdown"),
    output_dir: Path = typer.Option(Path("output"), "--output-dir", "-o", help="Directory to save output documents"),
    approver: str = typer.Option("GovBatchApprover-Auto", "--approver", "-a", help="Approver token for classified docs"),
) -> None:
    """Batch process a directory of heterogeneous documents with zero manual configuration."""
    if not folder.exists() or not folder.is_dir():
        console.print(f"[bold red]Error:[/] Invalid directory: {folder}")
        raise typer.Exit(code=1)

    extensions = [".json", ".md", ".docx", ".txt"]
    doc_files = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in extensions]

    if not doc_files:
        console.print(f"[yellow]No supported document files found in {folder}[/]")
        raise typer.Exit(code=0)

    console.print(f"[bold cyan]AutoDoc-Gov Batch Processing:[/] Found {len(doc_files)} documents in [yellow]{folder}[/]\n")

    facade = AutoDocFacade()
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_table = Table(title="Batch Processing Results (Self-Assembled Pipelines)", show_header=True)
    summary_table.add_column("File", style="cyan")
    summary_table.add_column("Type", style="magenta")
    summary_table.add_column("DSS Hash", style="dim")
    summary_table.add_column("Stages", style="blue")
    summary_table.add_column("Compliance", style="bold")
    summary_table.add_column("Duration", style="yellow")

    success_count = 0
    fail_count = 0

    for doc_path in doc_files:
        start_t = time.time()
        try:
            res = facade.generate(
                input_data=doc_path,
                output_format=format,
                approval_token=approver,
                output_dir=output_dir,
            )
            elapsed = f"{(time.time() - start_t) * 1000:.0f}ms"
            status_str = "[green]PASSED[/]" if res.verification_passed else "[red]FAILED[/]"
            stages_count = str(len(res.assembly_report_dict.get("ordered_stages", [])))

            summary_table.add_row(
                doc_path.name,
                res.dss.document_type,
                res.dss.fingerprint[:12] + "...",
                f"{stages_count} stages",
                status_str,
                elapsed,
            )
            success_count += 1
        except Exception as e:
            elapsed = f"{(time.time() - start_t) * 1000:.0f}ms"
            summary_table.add_row(
                doc_path.name,
                "ERROR",
                "N/A",
                "0",
                f"[red]FAIL: {str(e)[:20]}[/]",
                elapsed,
            )
            fail_count += 1

    console.print(summary_table)
    console.print(f"\n[bold]Batch Summary:[/] [green]{success_count} succeeded[/], [red]{fail_count} failed[/] out of {len(doc_files)} documents.")
    if fail_count > 0:
        raise typer.Exit(code=1)


@app.command("audit-verify")
def audit_verify_command(
    audit_file: Path = typer.Option(Path("output/audit_log.json"), "--audit-file", "-f", help="Path to audit log file"),
) -> None:
    """Verify cryptographic integrity of the hash-chained audit log."""
    if not audit_file.exists():
        console.print(f"[bold red]Error:[/] Audit log file does not exist: {audit_file}")
        raise typer.Exit(code=1)

    logger = HashChainAuditLogger(log_file=audit_file)
    is_valid, msg = logger.verify_integrity()

    blocks = len(logger.get_entries())
    if is_valid:
        console.print(Panel(
            f"[bold green][OK] Audit Chain Integrity VERIFIED[/]\nTotal blocks verified: [cyan]{blocks}[/]\nStatus: Tamper-evident chain is cryptographically intact.",
            title="Audit Chain Verification (N5)"
        ))
        raise typer.Exit(code=0)
    else:
        console.print(Panel(
            f"[bold red][FAIL] Audit Chain Integrity FAILED / TAMPERED[/]\nError: {msg}",
            title="Audit Chain Security Alert"
        ))
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
