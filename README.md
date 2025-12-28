# PAD2Skills

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

Extract occupations and skills data from World Bank Project Appraisal Documents (PADs).

## Overview

This project processes World Bank PAD PDFs to extract structured information about occupations and skills mentioned in development projects. The pipeline converts PDFs to markdown, uses LLM-based extraction to identify relevant data, and outputs structured formats (JSON/CSV) for analysis and visualization.

**Pipeline:**
```
PDF → Markdown → LLM Extraction → Structured Output → Visualization
```

## Project Status

### ✅ Completed
- **PDF to Markdown Conversion**: Converts PAD PDFs to markdown using [docling](https://github.com/DS4SD/docling) with TableFormer for accurate table extraction

### 🚧 In Progress
- LLM-based extraction of occupations and skills
- Structured output generation (JSON/CSV)
- Visualization and analysis tools

## Quick Start

### Prerequisites

This project uses [uv](https://github.com/astral-sh/uv) for Python package and environment management. uv is an extremely fast Python package installer and resolver written in Rust, serving as a drop-in replacement for pip and pip-tools. It's significantly faster than traditional tools and handles dependency resolution reliably.

**Install uv:**
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with Homebrew
brew install uv

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

For more installation options, see the [uv documentation](https://docs.astral.sh/uv/).

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/LaurenDahlin1/PAD2Skills.git
   cd PAD2Skills
   ```

2. **Set up Python environment:**
   ```bash
   # Pin Python version to 3.11
   uv python pin 3.11
   
   # Create virtual environment and install dependencies
   uv sync
   ```

## Usage

### PDF to Markdown Conversion

The `src/pdf_conversion` module converts PAD PDFs to markdown format with accurate table extraction.

**Place PDFs in the input directory:**
```bash
# Add your PDF files to:
data/bronze/pads_pdf/
```

**Convert all PDFs:**
```bash
uv run python -m src.pdf_conversion.cli
```

**Convert a specific PDF:**
```bash
uv run python -m src.pdf_conversion.cli --pdf yourfile.pdf
```

**Additional options:**
```bash
# Overwrite existing markdown files
uv run python -m src.pdf_conversion.cli --overwrite

# Disable accurate table mode (faster but less accurate)
uv run python -m src.pdf_conversion.cli --no-accurate-tables

# Use custom config file
uv run python -m src.pdf_conversion.cli --config custom_config.yaml
```

**Output location:**
```bash
# Converted markdown files are saved to:
data/silver/pads_md/
```

For detailed API usage and Python integration, see [docs/pdf_conversion.md](docs/pdf_conversion.md).

## Project Structure

```
PAD2Skills/
├── configs/              # Configuration files
│   └── base.yaml        # Base configuration (paths, settings)
├── data/
│   ├── bronze/          # Raw input data
│   │   ├── pads_pdf/   # PDF files
│   │   └── pdf_images/ # PDF page images
│   ├── silver/          # Processed data
│   │   └── pads_md/    # Converted markdown files
│   └── gold/            # Final structured outputs
├── docs/                # Documentation
│   ├── notes.md        # Development notes
│   └── pdf_conversion.md  # PDF conversion module docs
├── notebooks/           # Jupyter notebooks for exploration
│   ├── 01_test_pdf_conversion.ipynb
│   └── 02_pdf_to_images.ipynb
├── src/                 # Source code
│   ├── config.py       # Configuration management
│   ├── pdf_conversion/ # PDF to markdown conversion
│   ├── extraction/     # LLM-based extraction (planned)
│   ├── utils/          # Utility functions
│   └── visualization/  # Visualization tools (planned)
└── tests/               # Test suite
    └── test_pdf_conversion.py
```

## Development

### Running Tests
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_pdf_conversion.py -v

# Run with coverage
uv run pytest --cov=src
```

### Code Quality
```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check . --fix
```

### Jupyter Notebooks

Notebooks are used for exploration and prototyping. Once an approach is validated, implement the reusable version in `src/`.

```bash
# Notebooks are in:
notebooks/
```

## Configuration

Edit `configs/base.yaml` to customize paths and settings:

```yaml
paths:
  raw_pdfs: data/bronze/pads_pdf
  markdown: data/silver/pads_md
```

## Contributing

This is a research project. Contributions, suggestions, and feedback are welcome!

## License

This project is licensed under the [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-nc-sa/4.0/).

**You are free to:**
- **Share** — copy and redistribute the material in any medium or format
- **Adapt** — remix, transform, and build upon the material

**Under the following terms:**
- **Attribution** — You must give appropriate credit, provide a link to the license, and indicate if changes were made
- **NonCommercial** — You may not use the material for commercial purposes
- **ShareAlike** — If you remix, transform, or build upon the material, you must distribute your contributions under the same license

See the [LICENSE](LICENSE) file for full details.

## Acknowledgments

- [docling](https://github.com/DS4SD/docling) - PDF document conversion
- [uv](https://github.com/astral-sh/uv) - Fast Python package management

## Contact

[Lauren Dahlin](https://github.com/LaurenDahlin1)
