"""Tests for PDF conversion functionality."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.pdf_conversion.converter import PDFConverter, convert_pdfs


class TestPDFConverter:
    """Test PDFConverter class."""

    def test_converter_initialization(self):
        """Test converter initializes with correct settings."""
        converter = PDFConverter(accurate_tables=True)
        assert converter.converter is not None

    def test_converter_initialization_no_accurate_tables(self):
        """Test converter initializes without accurate table mode."""
        converter = PDFConverter(accurate_tables=False)
        assert converter.converter is not None

    @patch("src.pdf_conversion.converter.DocumentConverter")
    def test_convert_pdf_file_not_found(self, mock_converter):
        """Test convert_pdf raises FileNotFoundError for missing PDF."""
        converter = PDFConverter()
        fake_path = Path("/nonexistent/file.pdf")

        with pytest.raises(FileNotFoundError, match="PDF not found"):
            converter.convert_pdf(fake_path)

    @patch("src.pdf_conversion.converter.DocumentConverter")
    def test_convert_pdf_success(self, mock_converter, tmp_path):
        """Test successful PDF conversion."""
        # Create a dummy PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")

        # Mock the converter
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "# Test Markdown"
        mock_converter.return_value.convert.return_value = mock_result

        converter = PDFConverter()
        converter.converter = mock_converter.return_value

        markdown = converter.convert_pdf(pdf_file)

        assert markdown == "# Test Markdown"
        mock_converter.return_value.convert.assert_called_once_with(str(pdf_file))


class TestConvertPDFs:
    """Test convert_pdfs batch conversion function."""

    @patch("src.pdf_conversion.converter.PDFConverter")
    def test_convert_all_pdfs(self, mock_converter_class, tmp_path):
        """Test converting all PDFs in directory."""
        # Setup
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        output_dir = tmp_path / "markdown"

        # Create test PDFs
        (pdf_dir / "test1.pdf").write_text("pdf1")
        (pdf_dir / "test2.pdf").write_text("pdf2")

        # Mock converter
        mock_converter = MagicMock()
        mock_converter.convert_pdf.return_value = "# Markdown"
        mock_converter_class.return_value = mock_converter

        # Convert
        results = convert_pdfs(pdf_dir, output_dir)

        # Verify
        assert len(results["converted"]) == 2
        assert len(results["skipped"]) == 0
        assert len(results["failed"]) == 0
        assert "test1.pdf" in results["converted"]
        assert "test2.pdf" in results["converted"]
        assert (output_dir / "test1.md").exists()
        assert (output_dir / "test2.md").exists()

    @patch("src.pdf_conversion.converter.PDFConverter")
    def test_convert_specific_pdf(self, mock_converter_class, tmp_path):
        """Test converting a specific PDF."""
        # Setup
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        output_dir = tmp_path / "markdown"

        # Create test PDFs
        (pdf_dir / "test1.pdf").write_text("pdf1")
        (pdf_dir / "test2.pdf").write_text("pdf2")

        # Mock converter
        mock_converter = MagicMock()
        mock_converter.convert_pdf.return_value = "# Markdown"
        mock_converter_class.return_value = mock_converter

        # Convert only test1.pdf
        results = convert_pdfs(pdf_dir, output_dir, specific_pdf="test1.pdf")

        # Verify
        assert len(results["converted"]) == 1
        assert "test1.pdf" in results["converted"]
        assert (output_dir / "test1.md").exists()
        assert not (output_dir / "test2.md").exists()

    @patch("src.pdf_conversion.converter.PDFConverter")
    def test_skip_existing_markdown(self, mock_converter_class, tmp_path):
        """Test that existing markdown files are skipped."""
        # Setup
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        output_dir = tmp_path / "markdown"
        output_dir.mkdir()

        # Create test PDF and existing markdown
        (pdf_dir / "test.pdf").write_text("pdf")
        (output_dir / "test.md").write_text("existing markdown")

        # Mock converter
        mock_converter = MagicMock()
        mock_converter_class.return_value = mock_converter

        # Convert (should skip)
        results = convert_pdfs(pdf_dir, output_dir, overwrite=False)

        # Verify
        assert len(results["converted"]) == 0
        assert len(results["skipped"]) == 1
        assert "test.pdf" in results["skipped"]
        # Original content should remain
        assert (output_dir / "test.md").read_text() == "existing markdown"

    @patch("src.pdf_conversion.converter.PDFConverter")
    def test_overwrite_existing_markdown(self, mock_converter_class, tmp_path):
        """Test that existing markdown files are overwritten when flag is set."""
        # Setup
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        output_dir = tmp_path / "markdown"
        output_dir.mkdir()

        # Create test PDF and existing markdown
        (pdf_dir / "test.pdf").write_text("pdf")
        (output_dir / "test.md").write_text("old markdown")

        # Mock converter
        mock_converter = MagicMock()
        mock_converter.convert_pdf.return_value = "# New Markdown"
        mock_converter_class.return_value = mock_converter

        # Convert with overwrite
        results = convert_pdfs(pdf_dir, output_dir, overwrite=True)

        # Verify
        assert len(results["converted"]) == 1
        assert len(results["skipped"]) == 0
        assert "test.pdf" in results["converted"]
        assert (output_dir / "test.md").read_text() == "# New Markdown"

    @patch("src.pdf_conversion.converter.PDFConverter")
    def test_handle_conversion_error(self, mock_converter_class, tmp_path):
        """Test that conversion errors are caught and reported."""
        # Setup
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        output_dir = tmp_path / "markdown"

        # Create test PDF
        (pdf_dir / "test.pdf").write_text("pdf")

        # Mock converter to raise error
        mock_converter = MagicMock()
        mock_converter.convert_pdf.side_effect = Exception("Conversion failed")
        mock_converter_class.return_value = mock_converter

        # Convert
        results = convert_pdfs(pdf_dir, output_dir)

        # Verify
        assert len(results["converted"]) == 0
        assert len(results["failed"]) == 1
        assert results["failed"][0][0] == "test.pdf"
        assert "Conversion failed" in results["failed"][0][1]
