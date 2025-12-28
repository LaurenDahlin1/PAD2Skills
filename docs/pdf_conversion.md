# PDF Conversion Module

## Overview
The `src/pdf_conversion` module converts World Bank PAD PDFs to Markdown using docling with TableFormer for accurate table extraction.

## Features
- **Batch conversion**: Convert all PDFs or a specific one
- **Skip existing**: Avoids re-converting unless `--overwrite` flag is used
- **Accurate tables**: Uses TableFormer ACCURATE mode for better table extraction
- **Error handling**: Catches and reports conversion failures without stopping

## Usage

### CLI Interface

Convert all PDFs:
```bash
uv run python -m src.pdf_conversion.cli
```

Convert a specific PDF:
```bash
uv run python -m src.pdf_conversion.cli --pdf test.pdf
```

Overwrite existing markdown files:
```bash
uv run python -m src.pdf_conversion.cli --overwrite
```

Disable accurate table mode (faster but less accurate):
```bash
uv run python -m src.pdf_conversion.cli --no-accurate-tables
```

Use custom config:
```bash
uv run python -m src.pdf_conversion.cli --config custom_config.yaml
```

### Python API

```python
from pathlib import Path
from src.pdf_conversion.converter import PDFConverter, convert_pdfs

# Single PDF conversion
converter = PDFConverter(accurate_tables=True)
markdown = converter.convert_pdf(Path("input.pdf"))

# Batch conversion
results = convert_pdfs(
    pdf_dir=Path("data/bronze/pads_pdf"),
    output_dir=Path("data/silver/pads_md"),
    specific_pdf=None,      # None = convert all
    overwrite=False,        # Skip existing files
    accurate_tables=True    # Use TableFormer ACCURATE mode
)

print(f"Converted: {len(results['converted'])}")
print(f"Skipped: {len(results['skipped'])}")
print(f"Failed: {len(results['failed'])}")
```

## Module Structure

```
src/pdf_conversion/
├── __init__.py          # Package initialization
├── __main__.py          # Enables python -m execution
├── converter.py         # Core conversion logic
└── cli.py              # Command-line interface
```

## Testing

Run tests:
```bash
uv run pytest tests/test_pdf_conversion.py -v
```

The test suite includes:
- Converter initialization
- Single PDF conversion
- Batch conversion (all PDFs)
- Specific PDF conversion
- Skip existing files
- Overwrite mode
- Error handling

## Development Workflow

1. **Prototype in notebook**: Test ideas in `notebooks/01_test_pdf_conversion.ipynb`
2. **Implement in src**: Reusable code goes in `src/pdf_conversion/`
3. **Add tests**: Write tests in `tests/test_pdf_conversion.py`
4. **Use CLI**: Run production conversions with the CLI

## Configuration

The module reads paths from `configs/base.yaml`:
```yaml
paths:
  raw_pdfs: data/bronze/pads_pdf
  markdown: data/silver/pads_md
```

## Dependencies

- `docling`: PDF parsing and conversion
- `pydantic`: Configuration validation
- `pyyaml`: Config file parsing

See `pyproject.toml` for full dependency list.
