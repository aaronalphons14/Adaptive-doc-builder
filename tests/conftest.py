"""Shared pytest fixtures for AutoDoc-Gov test suite."""

from pathlib import Path

import pytest

from autodoc.analysis.parser import parse_document
from autodoc.patterns.composite import DocumentNode


@pytest.fixture
def samples_dir() -> Path:
    return Path(__file__).parent.parent / "samples"


@pytest.fixture
def sample_gov_order_path(samples_dir: Path) -> Path:
    return samples_dir / "01_government_order.json"


@pytest.fixture
def sample_tender_path(samples_dir: Path) -> Path:
    return samples_dir / "02_tender_notice.md"


@pytest.fixture
def sample_rti_path(samples_dir: Path) -> Path:
    return samples_dir / "03_rti_reply.json"


@pytest.fixture
def sample_circular_path(samples_dir: Path) -> Path:
    return samples_dir / "04_public_circular_bilingual.json"


@pytest.fixture
def sample_certificate_path(samples_dir: Path) -> Path:
    return samples_dir / "05_certificate.txt"


@pytest.fixture
def parsed_gov_order(sample_gov_order_path: Path) -> DocumentNode:
    return parse_document(sample_gov_order_path)


@pytest.fixture
def parsed_tender(sample_tender_path: Path) -> DocumentNode:
    return parse_document(sample_tender_path)


@pytest.fixture
def parsed_rti(sample_rti_path: Path) -> DocumentNode:
    return parse_document(sample_rti_path)


@pytest.fixture
def parsed_circular(sample_circular_path: Path) -> DocumentNode:
    return parse_document(sample_circular_path)


@pytest.fixture
def parsed_certificate(sample_certificate_path: Path) -> DocumentNode:
    return parse_document(sample_certificate_path)
