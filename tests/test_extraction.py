"""Tests for extraction module."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.extraction.extractor import (
    DocumentExtractor,
    create_chunks,
    extract_all_abbreviations,
    extract_all_sections,
    find_header_in_markdown,
    to_snake_case,
)
from src.extraction.summarizer import PADSummarizer, generate_all_summaries


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    with patch("src.extraction.extractor.OpenAI") as mock_client:
        yield mock_client


@pytest.fixture
def sample_markdown(tmp_path):
    """Create a sample markdown file for testing."""
    md_file = tmp_path / "P075941.md"
    md_file.write_text(
        "# Sample PAD Document\n\nI. STRATEGIC CONTEXT\n\nSome content here."
    )
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
    mock_item.content = [
        Mock(
            text='{"sections": [{"section_id": 0, "section_title": "STRATEGIC CONTEXT"}]}'
        )
    ]
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
    mock_item.content = [
        Mock(
            text="| Abbreviation | Definition |\n|---|---|\n| PAD | Project Appraisal Document |"
        )
    ]
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


def test_to_snake_case():
    """Test snake case conversion."""
    assert to_snake_case("Strategic Context") == "strategic_context"
    assert (
        to_snake_case("Project Development Objectives")
        == "project_development_objectives"
    )
    assert (
        to_snake_case("IMPLEMENTATION (with special chars!)")
        == "implementation_with_special_chars"
    )
    assert to_snake_case("Key   Multiple   Spaces") == "key_multiple_spaces"


def test_find_header_in_markdown():
    """Test finding headers with whitespace variations."""
    markdown = "# Header 1\n\n## Header  with   spaces\n\nContent"

    # Exact match
    assert find_header_in_markdown(markdown, "# Header 1") == 0

    # Normalized whitespace match
    assert find_header_in_markdown(markdown, "## Header with spaces") > 0

    # Not found
    assert find_header_in_markdown(markdown, "## Nonexistent") == -1


def test_create_chunks(tmp_path):
    """Test creating chunked markdown files."""
    # Create markdown directory with _1 suffix file
    md_dir = tmp_path / "markdown"
    md_dir.mkdir()
    md_file = md_dir / "P075941_1.md"
    md_content = """# I. STRATEGIC CONTEXT

Some content about strategic context.

# II. PROJECT DEVELOPMENT OBJECTIVES

PDO content here.

# III. IMPLEMENTATION

Implementation details.
"""
    md_file.write_text(md_content)

    # Create sections directory with sections JSON
    sections_dir = tmp_path / "sections"
    sections_dir.mkdir()
    sections_file = sections_dir / "P075941_1_sections.json"
    sections_data = {
        "sections": [
            {
                "section_id": 0,
                "section_title": "STRATEGIC CONTEXT",
                "header_text": "# I. STRATEGIC CONTEXT",
            },
            {
                "section_id": 1,
                "section_title": "PROJECT DEVELOPMENT OBJECTIVES",
                "header_text": "# II. PROJECT DEVELOPMENT OBJECTIVES",
            },
            {
                "section_id": 2,
                "section_title": "IMPLEMENTATION",
                "header_text": "# III. IMPLEMENTATION",
            },
        ]
    }
    import json

    sections_file.write_text(json.dumps(sections_data))

    # Create output directory
    output_dir = tmp_path / "chunks"

    # Run chunking
    results = create_chunks(
        markdown_dir=md_dir,
        sections_dir=sections_dir,
        output_dir=output_dir,
        specific_file=None,
        overwrite=False,
    )

    # Verify results
    assert len(results["chunked"]) == 1
    assert "P075941" in results["chunked"]
    assert len(results["failed"]) == 0

    # Verify chunks were created (without _1 suffix)
    chunk_files = list(output_dir.glob("P075941_*.md"))
    assert len(chunk_files) == 3

    # Check filenames
    expected_files = [
        "P075941_0_strategic_context.md",
        "P075941_1_project_development_objectives.md",
        "P075941_2_implementation.md",
    ]
    for expected in expected_files:
        assert (output_dir / expected).exists()

    # Verify content
    chunk_content = (output_dir / "P075941_0_strategic_context.md").read_text()
    assert "STRATEGIC CONTEXT" in chunk_content
    assert "Some content about strategic context" in chunk_content


def test_create_chunks_skip_existing(tmp_path):
    """Test that existing chunks are skipped without overwrite."""
    # Create markdown and sections
    md_dir = tmp_path / "markdown"
    md_dir.mkdir()
    (md_dir / "P075941_1.md").write_text("# I. TEST\n\nContent")

    sections_dir = tmp_path / "sections"
    sections_dir.mkdir()
    import json

    sections_data = {
        "sections": [
            {"section_id": 0, "section_title": "TEST", "header_text": "# I. TEST"}
        ]
    }
    (sections_dir / "P075941_1_sections.json").write_text(json.dumps(sections_data))

    output_dir = tmp_path / "chunks"
    output_dir.mkdir()
    # Create existing chunk
    (output_dir / "P075941_0_test.md").write_text("existing content")

    # Run chunking without overwrite
    results = create_chunks(
        markdown_dir=md_dir,
        sections_dir=sections_dir,
        output_dir=output_dir,
        specific_file=None,
        overwrite=False,
    )

    # Should be skipped (chunks already exist)
    assert len(results["chunked"]) == 0
    assert len(results["skipped"]) == 1

    # Verify existing content wasn't overwritten
    assert (output_dir / "P075941_0_test.md").read_text() == "existing content"


def test_create_chunks_no_sections_file(tmp_path):
    """Test chunking when sections file doesn't exist."""
    # Create markdown without sections
    md_dir = tmp_path / "markdown"
    md_dir.mkdir()
    (md_dir / "P075941_1.md").write_text("# Content")

    sections_dir = tmp_path / "sections"
    sections_dir.mkdir()
    # No sections file created

    output_dir = tmp_path / "chunks"

    # Run chunking
    results = create_chunks(
        markdown_dir=md_dir,
        sections_dir=sections_dir,
        output_dir=output_dir,
        specific_file=None,
        overwrite=False,
    )

    # Should be skipped due to missing sections file
    assert len(results["skipped"]) == 1
    assert len(results["chunked"]) == 0
    assert len(results["failed"]) == 0


# ===== PAD Summarizer Tests =====


def test_summarizer_initialization():
    """Test PADSummarizer initialization."""
    with patch("src.extraction.summarizer.OpenAI") as mock_client:
        summarizer = PADSummarizer()
        assert summarizer.client is not None
        mock_client.assert_called_once()


def test_generate_summary_success(tmp_path):
    """Test successful summary generation."""
    # Create test chunks
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    
    project_id = "P075941"
    for i in range(4):
        chunk_file = chunks_dir / f"{project_id}_{i}_section.md"
        chunk_file.write_text(f"# Section {i}\n\nContent for section {i}.")
    
    # Create abbreviations
    abbr_dir = tmp_path / "abbr"
    abbr_dir.mkdir()
    abbr_file = abbr_dir / f"{project_id}_abbr.md"
    abbr_file.write_text("| PAD | Project Appraisal Document |")
    
    # Mock OpenAI response
    with patch("src.extraction.summarizer.OpenAI") as mock_client:
        mock_response = Mock()
        mock_response.output_text = "This is a test summary of the PAD document."
        mock_client_instance = mock_client.return_value
        mock_client_instance.responses.create.return_value = mock_response
        
        # Test summary generation
        summarizer = PADSummarizer()
        result = summarizer.generate_summary(
            project_id=project_id,
            chunks_dir=chunks_dir,
            abbr_dir=abbr_dir,
            num_chunks=4,
        )
        
        assert result == "This is a test summary of the PAD document."
        mock_client_instance.responses.create.assert_called_once()


def test_generate_summary_no_abbreviations(tmp_path):
    """Test summary generation without abbreviations."""
    # Create test chunks
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    
    project_id = "P075941"
    for i in range(2):
        chunk_file = chunks_dir / f"{project_id}_{i}_section.md"
        chunk_file.write_text(f"# Section {i}\n\nContent for section {i}.")
    
    # Mock OpenAI response
    with patch("src.extraction.summarizer.OpenAI") as mock_client:
        mock_response = Mock()
        mock_response.output_text = "This is a test summary."
        mock_client_instance = mock_client.return_value
        mock_client_instance.responses.create.return_value = mock_response
        
        # Test summary generation without abbreviations
        summarizer = PADSummarizer()
        result = summarizer.generate_summary(
            project_id=project_id,
            chunks_dir=chunks_dir,
            abbr_dir=None,
            num_chunks=2,
        )
        
        assert result == "This is a test summary."


def test_generate_summary_missing_chunks(tmp_path):
    """Test summary generation with missing chunks."""
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    
    with patch("src.extraction.summarizer.OpenAI"):
        summarizer = PADSummarizer()
        
        with pytest.raises(FileNotFoundError, match="No chunks found"):
            summarizer.generate_summary(
                project_id="P999999",
                chunks_dir=chunks_dir,
                num_chunks=4,
            )


def test_generate_all_summaries(tmp_path):
    """Test batch summary generation."""
    # Create test chunks for multiple projects
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    
    projects = ["P075941", "P119893"]
    for project_id in projects:
        for i in range(2):
            chunk_file = chunks_dir / f"{project_id}_{i}_section.md"
            chunk_file.write_text(f"# Section {i}\n\nContent.")
    
    # Create output directory
    output_dir = tmp_path / "summaries"
    
    # Mock OpenAI responses
    with patch("src.extraction.summarizer.OpenAI") as mock_client:
        mock_response = Mock()
        mock_response.output_text = "Test summary."
        mock_client_instance = mock_client.return_value
        mock_client_instance.responses.create.return_value = mock_response
        
        # Test batch generation
        results = generate_all_summaries(
            chunks_dir=chunks_dir,
            output_dir=output_dir,
            num_chunks=2,
            overwrite=False,
        )
        
        assert len(results["generated"]) == 2
        assert len(results["skipped"]) == 0
        assert len(results["failed"]) == 0
        
        # Verify output files were created
        for project_id in projects:
            output_file = output_dir / f"{project_id}_summary.txt"
            assert output_file.exists()
            assert output_file.read_text() == "Test summary."


def test_generate_all_summaries_skip_existing(tmp_path):
    """Test batch summary generation with existing files."""
    # Create test chunks
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    
    project_id = "P075941"
    for i in range(2):
        chunk_file = chunks_dir / f"{project_id}_{i}_section.md"
        chunk_file.write_text(f"# Section {i}\n\nContent.")
    
    # Create output directory with existing summary
    output_dir = tmp_path / "summaries"
    output_dir.mkdir()
    existing_file = output_dir / f"{project_id}_summary.txt"
    existing_file.write_text("Existing summary.")
    
    with patch("src.extraction.summarizer.OpenAI"):
        results = generate_all_summaries(
            chunks_dir=chunks_dir,
            output_dir=output_dir,
            num_chunks=2,
            overwrite=False,
        )
        
        assert len(results["generated"]) == 0
        assert len(results["skipped"]) == 1
        assert project_id in results["skipped"]
