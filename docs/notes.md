# Notes 
Many of these notes will be added to Readme.md

## Set up

### How I set up the environment 
1. Install uv. If you have homebrew you can do the following in your terminal. 
`brew install uv`
2. `cd` into `PAD2Skills` in terminal or open a new terminal in VS Code  
3. This project is built with python 3.11. In termainal:
`uv python pin 3.11`
4. Initialize uv
`uv init --bare`
5. Add version to .toml fie
`requires-python = "==3.11.*"`
6. Create a fresh venv and sync
`uv venv --python 3.11`
`uv sync`
7. Add packages
`uv add --dev ipykernel pytest ruff`
`uv add pydantic pyyaml`
`uv add pandas dash plotly "docling" "torch<2.3" "numpy<2.0.0"`
`uv sync`

8. For image testing
`brew install poppler`
`uv add pdf2image pillow matplotlib`
`uv sync`

## ESCO Matching Utilities

### ESCO Data Preparation

The ESCO preparation utility is in `src/matching/esco_prepare.py`. It:
- Reads ESCO occupations and skills files
- Filters for essential skills/competences
- Merges and flattens skills by occupation
- Creates combined text representations
- Generates embeddings using sentence transformers

**Usage from Python:**
```python
from pathlib import Path
from src.matching.esco_prepare import prepare_esco_data

esco_dir = Path("data/bronze/esco")
output_csv = Path("data/silver/esco_occupations_prepared.csv")
embeddings_file = Path("data/silver/embeddings/esco_embeddings.npy")

df, embeddings = prepare_esco_data(
    esco_dir=esco_dir,
    output_csv=output_csv,
    embeddings_file=embeddings_file,
    overwrite_embeddings=False,
    model_name="intfloat/e5-small-v2"
)
```

**Usage from CLI:**
```bash
# Prepare ESCO data (uses cached embeddings if available)
uv run python -m src.matching.cli_prepare_esco

# Force regenerate embeddings
uv run python -m src.matching.cli_prepare_esco --overwrite-embeddings

# Use different model
uv run python -m src.matching.cli_prepare_esco --model "sentence-transformers/all-MiniLM-L6-v2"
```

**Outputs:**
- `data/silver/esco_occupations_prepared.csv` - Prepared ESCO occupations with combined text
- `data/silver/embeddings/esco_embeddings.npy` - Normalized embeddings for similarity search

### PAD to ESCO Matching

The PAD matching utility is in `src/matching/pad_matcher.py`. It:
- Loads PAD occupation extractions from JSON files
- Encodes them using sentence transformers
- Computes cosine similarity against ESCO embeddings
- Creates results with top K matches (default 20)
- Saves results as CSV and chunked JSON files

**Usage from Python:**
```python
from pathlib import Path
from src.matching.pad_matcher import match_pad_to_esco

pad_occupations_dir = Path("data/silver/occupations_skills_json")
esco_csv = Path("data/silver/esco_occupations_prepared.csv")
esco_embeddings = Path("data/silver/embeddings/esco_embeddings.npy")
output_dir = Path("data/silver")

results_df = match_pad_to_esco(
    pad_occupations_dir=pad_occupations_dir,
    project_id="P075941",
    esco_csv=esco_csv,
    esco_embeddings=esco_embeddings,
    output_dir=output_dir,
    model_name="intfloat/e5-small-v2",
    top_k=20,
    chunk_size=75,
    save_diagnostics=True
)
```

**Usage from CLI:**
```bash
# Match PAD occupations to ESCO (default: top 20 matches, chunk size 75)
uv run python -m src.matching.cli_match_pads P075941

# Customize number of matches
uv run python -m src.matching.cli_match_pads P075941 --top-k 10

# Customize chunk size for JSON output
uv run python -m src.matching.cli_match_pads P075941 --chunk-size 100

# Skip diagnostic file
uv run python -m src.matching.cli_match_pads P075941 --no-diagnostics
```

**Outputs:**
- `data/silver/esco_matching_csv/{project_id}_esco_matches.csv` - Full results with top K matches
- `data/silver/esco_matching_csv/diagnostics/{project_id}_esco_matches_diagnostics.csv` - Simplified diagnostic view
- `data/silver/esco_matching_json/{project_id}_000-074_esco_matches.json` - Chunked JSON files with top 10 matches per record