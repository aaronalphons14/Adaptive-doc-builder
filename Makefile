.PHONY: all test lint benchmark demo clean serve

PYTHON = ./.venv/Scripts/python.exe
PYTEST = ./.venv/Scripts/pytest.exe
RUFF = ./.venv/Scripts/ruff.exe
MYPY = ./.venv/Scripts/mypy.exe

all: lint test

test:
	$(PYTEST) -v --cov=autodoc tests/

lint:
	$(RUFF) check autodoc tests benchmarks
	$(MYPY) autodoc

benchmark:
	$(PYTHON) benchmarks/run_benchmarks.py

demo:
	@echo "Executing End-to-End Demo Generation on All Bundled Samples..."
	$(PYTHON) -m autodoc.cli.main batch samples/ --format html --output-dir output --approver DemoSecretClearance
	$(PYTHON) -m autodoc.cli.main generate samples/01_government_order.json --format pdf --output-dir output --approver DemoSecretClearance
	$(PYTHON) -m autodoc.cli.main generate samples/02_tender_notice.md --format docx --output-dir output
	$(PYTHON) -m autodoc.cli.main generate samples/03_rti_reply.json --format html --output-dir output --approver RTI-Officer-Signoff
	$(PYTHON) -m autodoc.cli.main generate samples/04_public_circular_bilingual.json --format pdf --output-dir output
	$(PYTHON) -m autodoc.cli.main generate samples/05_certificate.txt --format markdown --output-dir output
	$(PYTHON) -m autodoc.cli.main audit-verify --audit-file output/audit_log.json
	@echo "[OK] All demo outputs successfully generated in output/"

serve:
	$(PYTHON) -m uvicorn autodoc.api.app:app --host 127.0.0.1 --port 8000 --reload

clean:
	rm -rf .pytest_cache .coverage output/*
