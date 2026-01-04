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
- **Document Section Extraction**: Identifies and extracts major document sections from PADs using OpenAI API
- **Abbreviation Extraction**: Extracts abbreviations and acronyms tables from PAD documents
- **Document Chunking**: Splits PAD documents into section-based chunks for easier processing
- **PAD Summary Generation**: Generates concise summaries of PAD documents using abbreviations and first sections
- **Occupations and Skills Extraction**: Extracts occupations and skills from PAD chunks using OpenAI API
- **ESCO Occupation Matching**: Matches PAD occupations to ESCO taxonomy using semantic similarity

### 🚧 In Progress
- Structured output generation and aggregation (CSV)
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

### Step 1: PDF to Markdown Conversion

The first step in the pipeline converts PAD PDFs to markdown format with accurate table extraction using [docling](https://github.com/DS4SD/docling) and TableFormer.

#### 1. Place PDFs in the input directory
```bash
# Add your PDF files to:
data/bronze/pads_pdf/
```

#### 2. Run the conversion

**Convert all PDFs:**
```bash
uv run python -m src.pdf_conversion.cli
```

**Convert a specific PDF:**
```bash
uv run python -m src.pdf_conversion.cli --pdf yourfile.pdf
```

#### 3. Check the output
```bash
# Converted markdown files are saved to:
data/silver/pads_md/
```

#### Additional Options

```bash
# Overwrite existing markdown files
uv run python -m src.pdf_conversion.cli --overwrite

# Disable accurate table mode (faster but less accurate)
uv run python -m src.pdf_conversion.cli --no-accurate-tables

# Use custom config file
uv run python -m src.pdf_conversion.cli --config custom_config.yaml
```

#### Features
- **Batch processing**: Convert all PDFs at once or specify individual files
- **Smart skipping**: Automatically skips already-converted files (use `--overwrite` to force re-conversion)
- **Accurate table extraction**: Uses TableFormer ACCURATE mode by default for better table handling
- **Error resilience**: Continues processing if individual PDFs fail

For detailed API usage and Python integration, see [docs/pdf_conversion.md](docs/pdf_conversion.md).

### Step 2: Extract Document Sections

The second step identifies and extracts the major sections (I., II., III., Annexes, etc.) from the PAD markdown files using OpenAI API.

#### 1. Set up OpenAI API key
```bash
# Copy .env.example to .env and add your OpenAI API key
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=your-key-here
```

#### 2. Run section extraction

**Extract sections from all markdown files:**
```bash
uv run python -m src.extraction.cli_sections
```

**Extract from a specific file:**
```bash
uv run python -m src.extraction.cli_sections --markdown P075941.md
```

#### 3. Check the output
```bash
# Section JSON files are saved to:
data/silver/document_sections/
```

#### Additional Options

```bash
# Overwrite existing section files
uv run python -m src.extraction.cli_sections --overwrite

# Use custom config file
uv run python -m src.extraction.cli_sections --config custom_config.yaml
```

#### Features
- **Batch processing**: Process all markdown files or specify individual files
- **Smart skipping**: Automatically skips already-processed files (use `--overwrite` to force re-extraction)
- **Error resilience**: Continues processing if individual files fail
- **Structured output**: Saves sections as JSON with section IDs, titles, and header text

### Step 3: Extract Abbreviations

The third step extracts abbreviations and acronyms from the PAD markdown files using OpenAI API.

#### 1. Run abbreviation extraction

**Extract abbreviations from all markdown files:**
```bash
uv run python -m src.extraction.cli_abbreviations
```

**Extract from a specific file:**
```bash
uv run python -m src.extraction.cli_abbreviations --markdown P075941.md
```

#### 2. Check the output
```bash
# Abbreviation markdown tables are saved to:
data/silver/abbreviations_md/
```

#### Additional Options

```bash
# Overwrite existing abbreviation files
uv run python -m src.extraction.cli_abbreviations --overwrite

# Use custom config file
uv run python -m src.extraction.cli_abbreviations --config custom_config.yaml
```

#### Features
- **Batch processing**: Process all markdown files or specify individual files
- **Smart skipping**: Automatically skips already-processed files (use `--overwrite` to force re-extraction)
- **Error resilience**: Continues processing if individual files fail
- **Markdown output**: Saves abbreviations as clean markdown tables

### Step 4: Create Chunked Markdown Files

The fourth step splits the full PAD markdown files into separate chunks based on the extracted document sections, making it easier to process individual sections.

#### 1. Run chunk creation

**Create chunks from all markdown files:**
```bash
uv run python -m src.extraction.cli_chunks
```

**Create chunks from a specific file:**
```bash
uv run python -m src.extraction.cli_chunks --markdown P075941_1.md
```

#### 2. Check the output
```bash
# Chunked markdown files are saved to:
data/silver/pads_md_chunks/
# Example: P075941_0_strategic_context.md, P075941_1_project_development_objectives.md
```

#### Additional Options

```bash
# Overwrite existing chunk files
uv run python -m src.extraction.cli_chunks --overwrite

# Use custom config file
uv run python -m src.extraction.cli_chunks --config custom_config.yaml
```

#### Features
- **Batch processing**: Process all markdown files or specify individual files
- **Smart skipping**: Automatically skips already-processed files (use `--overwrite` to force re-creation)
- **Error resilience**: Continues processing if individual files fail
- **Clean filenames**: Removes `_1` suffix from project IDs and uses snake_case section titles
- **Section-based splitting**: Uses extracted section information to accurately split documents

**Note:** This step requires that section extraction (Step 2) has already been completed for the target files.

### Step 5: Generate PAD Summaries

The fifth step generates concise summaries of PAD documents by combining abbreviations and the first four document sections, using OpenAI API.

#### 1. Run summary generation

**Generate summaries for all projects:**
```bash
uv run python -m src.extraction.cli_summary
```

**Generate summary for a specific project:**
```bash
uv run python -m src.extraction.cli_summary --project P075941
```

#### 2. Check the output
```bash
# Summary text files are saved to:
data/silver/pad_summaries/
# Example: P075941_summary.txt
```

#### Additional Options

```bash
# Overwrite existing summary files
uv run python -m src.extraction.cli_summary --overwrite

# Use a different number of chunks (default: 4)
uv run python -m src.extraction.cli_summary --num-chunks 6

# Use custom config file
uv run python -m src.extraction.cli_summary --config custom_config.yaml
```

#### Features
- **Batch processing**: Process all projects or specify individual project IDs
- **Smart skipping**: Automatically skips already-processed files (use `--overwrite` to force re-generation)
- **Error resilience**: Continues processing if individual projects fail
- **Abbreviation integration**: Automatically incorporates abbreviations for better context
- **Configurable chunks**: Control how many document chunks to include (default: 4)

**Note:** This step requires that chunks (Step 4) have already been created for the target projects. Abbreviations (Step 3) are optional but recommended for better summaries.

### Step 5: Extract Occupations and Skills

The fifth step extracts occupations and skills from PAD document chunks using OpenAI API. This step analyzes each chunk to identify in-country occupations needed for project implementation.

#### 1. Run occupation extraction

**Extract occupations from all chunks:**
```bash
uv run python -m src.extraction.cli_occupations
```

**Extract from a specific project:**
```bash
uv run python -m src.extraction.cli_occupations --project P075941
```

#### 2. Check the output
```bash
# Occupation JSON files are saved to:
data/silver/occupations_skills_json/
# Example: P075941_0_occupations.json, P075941_1_occupations.json
```

#### Additional Options

```bash
# Overwrite existing occupation files
uv run python -m src.extraction.cli_occupations --overwrite

# Use custom config file
uv run python -m src.extraction.cli_occupations --config custom_config.yaml
```

#### Features
- **Batch processing**: Process all chunks or specify individual project IDs
- **Smart skipping**: Automatically skips already-processed files (use `--overwrite` to force re-extraction)
- **Error resilience**: Continues processing if individual chunks fail
- **Abbreviation integration**: Automatically incorporates abbreviations for better context
- **Structured output**: Saves extracted occupations and skills as JSON with occupation titles, activities, and evidence quotes

**Note:** This step requires that chunks (Step 4) have already been created for the target projects. Abbreviations (Step 3) are optional but recommended for better extraction results.

### Step 6: Match PAD Occupations to ESCO

The seventh step matches occupations extracted from PAD documents to the European Skills, Competences, Qualifications and Occupations (ESCO) taxonomy using semantic similarity. This step has two utilities: one for preparing ESCO data with embeddings, and another for matching PAD occupations to ESCO.

#### 1. Prepare ESCO data (run once)

**Prepare ESCO occupations with embeddings:**
```bash
uv run python -m src.matching.cli_prepare_esco
```

This utility:
- Reads ESCO occupations and skills from CSV files
- Filters for essential skills and competences
- Merges and flattens the data
- Creates combined text fields for semantic matching
- Generates embeddings using sentence-transformers

#### 2. Match PAD occupations to ESCO

**Match occupations for a specific project:**
```bash
uv run python -m src.matching.cli_match_pads P075941
```

**Match with custom parameters:**
```bash
# Get top 10 matches instead of default 20
uv run python -m src.matching.cli_match_pads P075941 --top-k 10

# Use larger chunk sizes (default: 75)
uv run python -m src.matching.cli_match_pads P075941 --chunk-size 100

# Skip diagnostic output
uv run python -m src.matching.cli_match_pads P075941 --no-diagnostics
```

#### 3. Check the outputs

```bash
# Full matching results (CSV with top 20 matches):
data/silver/esco_matching_csv/{project_id}_esco_matches.csv

# Simplified diagnostic view (CSV):
data/silver/esco_matching_csv/diagnostics/{project_id}_esco_matches_diagnostics.csv

# Chunked JSON files (top 10 matches per chunk):
data/silver/esco_matching_json/{project_id}_000-074_esco_matches.json
```

#### ESCO Preparation Options

```bash
# Regenerate embeddings (if model changed or data updated)
uv run python -m src.matching.cli_prepare_esco --overwrite-embeddings

# Use a different sentence-transformer model
uv run python -m src.matching.cli_prepare_esco --model intfloat/multilingual-e5-large
```

#### Features
- **Semantic matching**: Uses sentence-transformers for accurate occupation matching
- **Cached embeddings**: ESCO embeddings are saved and reused for efficiency
- **Top-K retrieval**: Returns the most similar ESCO occupations for each PAD occupation
- **Multiple output formats**: CSV for analysis, JSON for application integration
- **Chunked outputs**: Large result sets split into manageable JSON files
- **Diagnostic mode**: Simplified CSV view for quick inspection

**Note:** This step requires that occupation extraction has been completed for the target projects. The ESCO preparation utility should be run once before matching any projects.

## Project Structure

```
PAD2Skills/
├── configs/              # Configuration files
│   └── base.yaml        # Base configuration (paths, settings)
├── data/
│   ├── bronze/          # Raw input data
│   │   ├── pads_pdf/   # PDF files
│   │   ├── pdf_images/ # PDF page images
│   │   ├── esco/       # ESCO taxonomy CSV files
│   │   └── nace/       # NACE industry codes
│   ├── silver/          # Processed data
│   │   ├── pads_md/    # Converted markdown files
│   │   ├── document_sections/  # Extracted document sections (JSON)
│   │   ├── abbreviations_md/   # Extracted abbreviations (markdown tables)
│   │   ├── pads_md_chunks/     # Section-based markdown chunks
│   │   ├── pad_summaries/      # Generated PAD summaries (text)
│   │   ├── esco_occupations_prepared.csv  # Prepared ESCO data
│   │   ├── embeddings/         # Cached ESCO embeddings
│   │   ├── esco_matching_csv/  # PAD-to-ESCO matching results (CSV)
│   │   ├── esco_matching_json/ # PAD-to-ESCO matching results (JSON chunks)
│   │   └── occupations_skills_json/  # Extracted occupations/skills (JSON)
│   └── gold/            # Final structured outputs
├── docs/                # Documentation
│   ├── notes.md        # Development notes
│   └── pdf_conversion.md  # PDF conversion module docs
├── notebooks/           # Jupyter notebooks for exploration
│   ├── 01_test_pdf_conversion.ipynb
│   ├── 02_document_sections.ipynb
│   └── 99_pipeline.ipynb
├── src/                 # Source code
│   ├── config.py       # Configuration management
│   ├── pdf_conversion/ # PDF to markdown conversion
│   ├── extraction/     # Document section and abbreviation extraction
│   ├── matching/       # ESCO occupation matching
│   ├── utils/          # Utility functions
│   └── visualization/  # Visualization tools (planned)
└── tests/               # Test suite
    ├── test_pdf_conversion.py
    └── test_extraction.py
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
