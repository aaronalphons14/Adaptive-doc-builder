# AutoDoc-Gov: PowerShell Demonstration Script for Windows Environments
# Executes full end-to-end synthesis, rendering across formats, and audit verification.

$ErrorActionPreference = "Stop"

Write-Host "`n=======================================================" -ForegroundColor Cyan
Write-Host " AutoDoc-Gov: Self-Assembling Document Platform Demo" -ForegroundColor Cyan
Write-Host "=======================================================`n" -ForegroundColor Cyan

$PythonExe = ".\.venv\Scripts\python.exe"

# Step 1: Batch Process All Samples to HTML
Write-Host "[1/6] Batch processing all samples to HTML..." -ForegroundColor Yellow
& $PythonExe -m autodoc.cli.main batch samples/ --format html --output-dir output --approver DemoClearanceToken

# Step 2: Generate Government Order in Indic-capable PDF
Write-Host "`n[2/6] Synthesizing Government Order to PDF (Indic font embedded)..." -ForegroundColor Yellow
& $PythonExe -m autodoc.cli.main generate samples/01_government_order.json --format pdf --output-dir output --approver DemoClearanceToken

# Step 3: Generate PWD Tender Notice in DOCX format
Write-Host "`n[3/6] Synthesizing Tender Notice to DOCX (python-docx adapter)..." -ForegroundColor Yellow
& $PythonExe -m autodoc.cli.main generate samples/02_tender_notice.md --format docx --output-dir output

# Step 4: Generate RTI Reply with PII Masking Certification
Write-Host "`n[4/6] Synthesizing RTI Reply with Automated PII Masking (DPDP Act 2023)..." -ForegroundColor Yellow
& $PythonExe -m autodoc.cli.main generate samples/03_rti_reply.json --format html --output-dir output --approver RTI-Appellate-Signoff

# Step 5: Generate Public Circular in Bilingual PDF
Write-Host "`n[5/6] Synthesizing Bilingual English/Hindi Circular..." -ForegroundColor Yellow
& $PythonExe -m autodoc.cli.main generate samples/04_public_circular_bilingual.json --format pdf --output-dir output

# Step 6: Verify Cryptographic Audit Chain Integrity
Write-Host "`n[6/6] Verifying Cryptographic Audit Chain Lineage (N5)..." -ForegroundColor Yellow
& $PythonExe -m autodoc.cli.main audit-verify --audit-file output/audit_log.json

Write-Host "`n=======================================================" -ForegroundColor Green
Write-Host " [OK] Demo Complete! Outputs generated in output/" -ForegroundColor Green
Write-Host "=======================================================`n" -ForegroundColor Green
