"""PDF to Markdown conversion using docling with TableFormer."""

from pathlib import Path
from typing import Optional

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption


class PDFConverter:
    """Convert PDF documents to Markdown using docling with TableFormer."""

    def __init__(self, accurate_tables: bool = True):
        """
        Initialize the PDF converter.

        Args:
            accurate_tables: Use TableFormer ACCURATE mode for better table extraction.
        """
        # Configure pipeline options
        opts = PdfPipelineOptions(do_table_structure=True)
        if accurate_tables:
            opts.table_structure_options.mode = TableFormerMode.ACCURATE
            opts.table_structure_options.do_cell_matching = False

        # Initialize converter
        self.converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
        )

    def convert_pdf(self, pdf_path: Path) -> str:
        """
        Convert a single PDF to Markdown.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Markdown content as string

        Raises:
            FileNotFoundError: If PDF doesn't exist
            Exception: If conversion fails
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        result = self.converter.convert(str(pdf_path))
        return result.document.export_to_markdown()


def convert_pdfs(
    pdf_dir: Path,
    output_dir: Path,
    specific_pdf: Optional[str] = None,
    overwrite: bool = False,
    accurate_tables: bool = True,
) -> dict[str, list]:
    """
    Convert PDF(s) to Markdown files.

    Args:
        pdf_dir: Directory containing PDF files
        output_dir: Directory to save markdown files
        specific_pdf: Specific PDF filename to convert (None = convert all)
        overwrite: Whether to overwrite existing markdown files
        accurate_tables: Use TableFormer ACCURATE mode

    Returns:
        Dictionary with conversion results:
            - converted: List of successfully converted filenames
            - skipped: List of skipped filenames (already exists)
            - failed: List of tuples (filename, error_message)
    """
    # Initialize converter
    converter = PDFConverter(accurate_tables=accurate_tables)

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get list of PDFs to convert
    if specific_pdf:
        target_pdf = pdf_dir / specific_pdf
        pdfs_to_convert = [target_pdf] if target_pdf.exists() else []
    else:
        pdfs_to_convert = list(pdf_dir.glob("*.pdf"))

    # Track results
    results = {"converted": [], "skipped": [], "failed": []}

    # Process each PDF
    for pdf_file in pdfs_to_convert:
        output_file = output_dir / f"{pdf_file.stem}.md"

        # Check if markdown already exists
        if output_file.exists() and not overwrite:
            results["skipped"].append(pdf_file.name)
            continue

        try:
            # Convert PDF
            markdown_content = converter.convert_pdf(pdf_file)

            # Save markdown
            output_file.write_text(markdown_content, encoding="utf-8")
            results["converted"].append(pdf_file.name)

        except Exception as e:
            results["failed"].append((pdf_file.name, str(e)))

    return results
