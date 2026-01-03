"""Tests for extraction module."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.extraction.extractor import (
    DocumentExtractor,
    extract_all_abbreviations,
    extract_all_sections,
)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    with patch("src.extraction.extractor.OpenAI") as mock_client:
        yield mock_client


@pytest.fixture
def sample_markdown(tmp_path):
    """Create a sample markdown file for testing."""
    md_file = tmp_path / "P075941.md"
    md_file.write_text("# Sample PAD Document\n\nI. STRATEGIC CONTEXT\n\nSome content here.")
    return md_file


def test_extractor_initialization(mock_openai_client):
    """Test DocumentExtractor initialization."""
    extractor = DocumentExtractor()
    assert extractor.client is not None
    mock_openai_client.assert_called_once()


def test_extract_sections_success(mock_openai_client, sample_markdown, tmp_path):
    """Test successful section extraction."""
    # Mock response
    mock_response = Mock()
    mock_item = Mock()
    mock_item.content = [Mock(text='{"sections": [{"section_id": 0, "section_title": "STRATEGIC CONTEXT"}]}')]
    mock_item.role = "assistant"
    mock_response.output = [mock_item]

    mock_client_instance = mock_openai_client.return_value
    mock_client_instance.responses.create.return_value = mock_response

    # Test extraction
    extractor = DocumentExtractor()
    result = extractor.extract_sections(sample_markdown, "P075941")

    assert "sections" in result
    assert len(result["sections"]) == 1
    assert result["sections"][0]["section_id"] == 0


def test_extract_sections_file_not_found(mock_openai_client):
    """Test section extraction with missing file."""
    extractor = DocumentExtractor()

    with pytest.raises(FileNotFoundError):
        extractor.extract_sections(Path("nonexistent.md"), "P999999")


def test_extract_abbreviations_success(mock_openai_client, sample_markdown, tmp_path):
    """Test successful abbreviation extraction."""
    # Mock response
    mock_response = Mock()
    mock_item = Mock()
    mock_item.content = [Mock(text="| Abbreviation | Definition |\n|---|---|\n| PAD | Project Appraisal Document |")]
    mock_item.role = "assistant"
    mock_response.output = [mock_item]

    mock_client_instance = mock_openai_client.return_value
    mock_client_instance.responses.create.return_value = mock_response

    # Test extraction
    extractor = DocumentExtractor()
    result = extractor.extract_abbreviations(sample_markdown, "P075941")

    assert "PAD" in result
    assert "Project Appraisal Document" in result


def test_extract_all_sections(mock_openai_client, tmp_path):
    """Test batch section extraction."""
    # Create sample markdown files
    (tmp_path / "P075941.md").write_text("Content 1")
    (tmp_path / "P119893.md").write_text("Content 2")

    output_dir = tmp_path / "output"

    # Mock response
    mock_response = Mock()
    mock_item = Mock()
    mock_item.content = [Mock(text='{"sections": []}')]
    mock_item.role = "assistant"
    mock_response.output = [mock_item]

    mock_client_instance = mock_openai_client.return_value
    mock_client_instance.responses.create.return_value = mock_response

    # Test batch extraction
    results = extract_all_sections(
        markdown_dir=tmp_path,
        output_dir=output_dir,
        specific_file=None,
        overwrite=False,
    )

    assert len(results["extracted"]) == 2
    assert len(results["skipped"]) == 0
    assert len(results["failed"]) == 0


def test_extract_all_sections_skip_existing(mock_openai_client, tmp_path):
    """Test that existing files are skipped."""
    # Create sample markdown and existing output
    (tmp_path / "P075941.md").write_text("Content")
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "P075941_sections.json").write_text('{"sections": []}')

    # Test extraction without overwrite
    results = extract_all_sections(
        markdown_dir=tmp_path,
        output_dir=output_dir,
        specific_file=None,
        overwrite=False,
    )

    assert len(results["extracted"]) == 0
    assert len(results["skipped"]) == 1


def test_extract_all_abbreviations(mock_openai_client, tmp_path):
    """Test batch abbreviation extraction."""
    # Create sample markdown files
    (tmp_path / "P075941.md").write_text("Content 1")
    (tmp_path / "P119893.md").write_text("Content 2")

    output_dir = tmp_path / "output"

    # Mock response
    mock_response = Mock()
    mock_item = Mock()
    mock_item.content = [Mock(text="| Abbreviation | Definition |\n|---|---|")]
    mock_item.role = "assistant"
    mock_response.output = [mock_item]

    mock_client_instance = mock_openai_client.return_value
    mock_client_instance.responses.create.return_value = mock_response

    # Test batch extraction
    results = extract_all_abbreviations(
        markdown_dir=tmp_path,
        output_dir=output_dir,
        specific_file=None,
        overwrite=False,
    )

    assert len(results["extracted"]) == 2
    assert len(results["skipped"]) == 0
    assert len(results["failed"]) == 0


def test_extract_specific_file(mock_openai_client, tmp_path):
    """Test extracting a specific file."""
    # Create sample markdown files
    (tmp_path / "P075941.md").write_text("Content 1")
    (tmp_path / "P119893.md").write_text("Content 2")

    output_dir = tmp_path / "output"

    # Mock response
    mock_response = Mock()
    mock_item = Mock()
    mock_item.content = [Mock(text='{"sections": []}')]
    mock_item.role = "assistant"
    mock_response.output = [mock_item]

    mock_client_instance = mock_openai_client.return_value
    mock_client_instance.responses.create.return_value = mock_response

    # Test specific file extraction
    results = extract_all_sections(
        markdown_dir=tmp_path,
        output_dir=output_dir,
        specific_file="P075941.md",
        overwrite=False,
    )

    assert len(results["extracted"]) == 1
    assert "P075941.md" in results["extracted"]
