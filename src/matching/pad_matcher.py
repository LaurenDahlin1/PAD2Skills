"""Match PAD occupations to ESCO taxonomy using embeddings."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


def match_pad_to_esco(
    pad_occupations_dir: Path,
    project_id: str,
    esco_csv: Path,
    esco_embeddings: Path,
    output_dir: Path,
    model_name: str = "intfloat/e5-small-v2",
    top_k: int = 20,
    chunk_size: int = 75,
    save_diagnostics: bool = True,
    overwrite: bool = False,
) -> pd.DataFrame:
    """
    Match PAD occupations to ESCO taxonomy using semantic similarity.

    Loads PAD occupation extractions, encodes them using a sentence transformer,
    computes cosine similarity against ESCO embeddings, and saves top matches
    in CSV and JSON formats (chunked).

    Args:
        pad_occupations_dir: Directory containing PAD occupation JSON files
        project_id: Project ID (e.g., "P075941")
        esco_csv: Path to prepared ESCO CSV file
        esco_embeddings: Path to ESCO embeddings numpy file
        output_dir: Directory to save matching results (will create esco_matching_csv and esco_matching_json subdirs)
        model_name: Name of sentence transformer model to use (default: intfloat/e5-small-v2)
        top_k: Number of top matches to retrieve (default: 20)
        chunk_size: Number of records per JSON file (default: 75)
        save_diagnostics: Whether to save diagnostic CSV file (default: True)
        overwrite: Whether to overwrite existing output files (default: False)

    Returns:
        DataFrame with PAD occupations and top ESCO matches

    Raises:
        FileNotFoundError: If required files don't exist
    """
    # Check for existing files and handle overwrite
    csv_output_dir = output_dir / "esco_matching_csv"
    json_output_dir = output_dir / "esco_matching_json"
    csv_file = csv_output_dir / f"{project_id}_esco_matches.csv"
    
    if csv_file.exists() and not overwrite:
        print(f"Output already exists: {csv_file}")
        print("Use overwrite=True to force re-matching")
        return pd.read_csv(csv_file)
    
    if overwrite and csv_file.exists():
        csv_file.unlink()
        print(f"Deleted existing CSV: {csv_file.name}")
        
        # Delete existing JSON chunk files
        if json_output_dir.exists():
            json_files = list(json_output_dir.glob(f"{project_id}_*_esco_matches.json"))
            if json_files:
                for json_file in json_files:
                    json_file.unlink()
                print(f"Deleted {len(json_files)} existing JSON chunk files")
    
    # Load ESCO data
    print(f"Loading ESCO data from {esco_csv}...")
    if not esco_csv.exists():
        raise FileNotFoundError(
            f"ESCO CSV not found: {esco_csv}\n"
            "Run 'python -m src.matching.cli_prepare_esco' first to prepare ESCO data"
        )
    esco_df = pd.read_csv(esco_csv)
    print(f"✓ Loaded {len(esco_df):,} ESCO occupations")

    # Load ESCO embeddings
    print(f"Loading ESCO embeddings from {esco_embeddings}...")
    if not esco_embeddings.exists():
        raise FileNotFoundError(
            f"ESCO embeddings not found: {esco_embeddings}\n"
            "Run 'python -m src.matching.cli_prepare_esco' first to generate embeddings"
        )
    E = np.load(esco_embeddings)
    print(f"✓ Loaded embeddings: shape={E.shape}, size={E.nbytes / 1024 / 1024:.2f} MB")

    # Load PAD occupations
    print(f"Loading PAD occupations for project {project_id}...")
    pad_df = _load_pad_occupations(pad_occupations_dir, project_id)
    print(f"✓ Loaded {len(pad_df):,} PAD occupation extractions")

    # Load model and encode PAD occupations
    print(f"Loading model: {model_name}...")
    model = SentenceTransformer(model_name)
    print(f"  Max sequence length: {model.max_seq_length}")
    print(f"  Embedding dimension: {model.get_sentence_embedding_dimension()}")

    # Prepare PAD texts with "query: " prefix for e5 model
    queries = ["query: " + text for text in pad_df["combined_text"].tolist()]
    print(f"Encoding {len(queries):,} PAD occupation queries...")

    # Encode PAD queries (normalized for cosine similarity via dot product)
    Q = model.encode(queries, normalize_embeddings=True, batch_size=64, show_progress_bar=True)
    print(f"✓ Encoded PAD occupations: shape={Q.shape}, size={Q.nbytes / 1024 / 1024:.2f} MB")

    # Compute similarities and get top matches
    print("Computing similarity scores...")
    scores = Q @ E.T
    print(f"✓ Computed similarity matrix: shape={scores.shape}")
    print(f"  Score range: [{scores.min():.4f}, {scores.max():.4f}], mean={scores.mean():.4f}")

    print(f"Finding top {top_k} matches for each PAD occupation...")
    topk_indices = np.argsort(-scores, axis=1)[:, :top_k]
    topk_scores = np.take_along_axis(scores, topk_indices, axis=1)
    print(f"✓ Found top {top_k} matches for all {len(pad_df):,} PAD occupations")

    # Create results DataFrame
    results_df = _create_results_dataframe(pad_df, esco_df, topk_indices, topk_scores, top_k)
    print(f"✓ Created results DataFrame: shape={results_df.shape}")

    # Save results to CSV
    csv_output_dir = output_dir / "esco_matching_csv"
    csv_output_dir.mkdir(parents=True, exist_ok=True)
    csv_file = csv_output_dir / f"{project_id}_esco_matches.csv"
    results_df.to_csv(csv_file, index=False)
    print(f"✓ Saved CSV results to: {csv_file}")
    print(f"  File size: {csv_file.stat().st_size / 1024:.2f} KB")

    # Save diagnostics if requested
    if save_diagnostics:
        diag_dir = csv_output_dir / "diagnostics"
        diag_dir.mkdir(parents=True, exist_ok=True)
        diag_file = diag_dir / f"{project_id}_esco_matches_diagnostics.csv"

        diag_cols = ["identified_occupation", "source_material_quote"] + [
            f"match_{i}_occupation" for i in range(1, top_k + 1)
        ]
        diagnostics_df = results_df[diag_cols].copy()
        diagnostics_df.to_csv(diag_file, index=False)
        print(f"✓ Saved diagnostics to: {diag_file}")
        print(f"  File size: {diag_file.stat().st_size / 1024:.2f} KB")

    # Save to JSON in chunks
    _save_json_chunks(results_df, project_id, output_dir, chunk_size)

    return results_df


def _load_pad_occupations(pad_occupations_dir: Path, project_id: str) -> pd.DataFrame:
    """
    Load PAD occupation extractions from JSON files.

    Args:
        pad_occupations_dir: Directory containing occupation JSON files
        project_id: Project ID to filter files

    Returns:
        DataFrame with PAD occupations, pad_id, and combined_text columns

    Raises:
        FileNotFoundError: If no matching JSON files found
    """
    # Find all matching JSON files
    json_files = sorted(pad_occupations_dir.glob(f"{project_id}_*_occupations.json"))

    if not json_files:
        raise FileNotFoundError(
            f"No occupation JSON files found for project {project_id} in {pad_occupations_dir}"
        )

    # Read all JSON files and collect extractions
    all_extractions = []
    for json_file in json_files:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check if extractions exist and are not null
        if data.get("extractions") is not None:
            for extraction in data["extractions"]:
                extraction["project_id"] = data["project_id"]
                extraction["section_id"] = data["section_id"]
                all_extractions.append(extraction)

    # Convert to DataFrame
    df = pd.DataFrame(all_extractions)

    # Create three-digit ID with leading zeros
    df["pad_id"] = [f"{i:03d}" for i in range(len(df))]

    # Create combined text column
    df["combined_text"] = df.apply(_combine_pad_fields, axis=1)

    return df


def _combine_pad_fields(row: pd.Series) -> str:
    """
    Combine PAD occupation fields into single text column.

    Combines identified_occupation, activity_description_in_pad, and
    skills_needed_for_activity into a space-separated string.

    Args:
        row: DataFrame row with PAD occupation fields

    Returns:
        Combined text string
    """
    parts = []

    # Add identified_occupation
    if pd.notna(row["identified_occupation"]):
        parts.append(str(row["identified_occupation"]))

    # Add activity_description_in_pad
    if pd.notna(row["activity_description_in_pad"]):
        parts.append(str(row["activity_description_in_pad"]))

    # Add skills_needed_for_activity (clean list format)
    skills = row["skills_needed_for_activity"]
    if skills is not None and skills is not pd.NA:
        # If it's a list, join with commas
        if isinstance(skills, list):
            skills_str = ", ".join(str(s) for s in skills)
        else:
            # If it's a string representation of a list, clean it up
            skills_str = str(skills).strip("[]").replace("'", "").replace('"', "")
        parts.append(skills_str)

    return " ".join(parts)


def _create_results_dataframe(
    pad_df: pd.DataFrame,
    esco_df: pd.DataFrame,
    topk_indices: np.ndarray,
    topk_scores: np.ndarray,
    top_k: int,
) -> pd.DataFrame:
    """
    Create results DataFrame with top ESCO matches.

    Args:
        pad_df: PAD occupations DataFrame
        esco_df: ESCO occupations DataFrame
        topk_indices: Indices of top matches (shape: [n_pad, top_k])
        topk_scores: Similarity scores of top matches (shape: [n_pad, top_k])
        top_k: Number of top matches

    Returns:
        DataFrame with PAD occupations and top ESCO matches
        (adds 5*top_k columns: esco_id, uri, occupation, description, score for each rank)
    """
    results_df = pad_df.copy()

    # Build all match columns at once to avoid DataFrame fragmentation
    match_columns = {}
    for rank in range(top_k):
        # Get ESCO data for this rank
        indices = topk_indices[:, rank]
        
        match_columns[f"match_{rank+1}_esco_id"] = [
            esco_df.iloc[idx]["esco_id"] for idx in indices
        ]
        match_columns[f"match_{rank+1}_uri"] = [
            esco_df.iloc[idx]["conceptUri"] for idx in indices
        ]
        match_columns[f"match_{rank+1}_occupation"] = [
            esco_df.iloc[idx]["preferredLabel"] for idx in indices
        ]
        match_columns[f"match_{rank+1}_description"] = [
            esco_df.iloc[idx]["description"] for idx in indices
        ]
        match_columns[f"match_{rank+1}_score"] = topk_scores[:, rank]

    # Add all match columns at once using concat
    match_df = pd.DataFrame(match_columns, index=results_df.index)
    results_df = pd.concat([results_df, match_df], axis=1)

    return results_df


def _save_json_chunks(
    results_df: pd.DataFrame, project_id: str, output_dir: Path, chunk_size: int
) -> None:
    """
    Save results to JSON files in chunks.

    Each JSON record contains top 10 ESCO candidates (even if top_k > 10 in CSV).

    Args:
        results_df: Results DataFrame with matches
        project_id: Project ID for filenames
        output_dir: Base output directory
        chunk_size: Number of records per JSON file
    """
    json_output_dir = output_dir / "esco_matching_json"
    json_output_dir.mkdir(parents=True, exist_ok=True)

    # Delete existing JSON chunk files for this project
    existing_files = list(json_output_dir.glob(f"{project_id}_*_esco_matches.json"))
    if existing_files:
        print(f"Deleting {len(existing_files)} existing JSON chunk file(s)...")
        for file in existing_files:
            file.unlink()

    # Transform each row into JSON format (top 10 matches only for JSON)
    records = []
    for _, row in results_df.iterrows():
        # Build esco_candidates array with top 10 matches
        esco_candidates = []
        for rank in range(1, 11):  # Top 10 matches for JSON
            candidate = {
                "rank": rank,
                "esco_id": row[f"match_{rank}_esco_id"],
                "label": row[f"match_{rank}_occupation"],
                "description": row[f"match_{rank}_description"],
                "similarity_score": round(float(row[f"match_{rank}_score"]), 2),
            }
            esco_candidates.append(candidate)

        # Build the record
        record = {
            "record_id": row["pad_id"],
            "pad_occupation": row["identified_occupation"],
            "pad_activity": row["activity_description_in_pad"]
            if pd.notna(row["activity_description_in_pad"])
            else "",
            "pad_quote": row["source_material_quote"]
            if pd.notna(row["source_material_quote"])
            else "",
            "esco_candidates": esco_candidates,
        }
        records.append(record)

    # Split records into chunks and save
    num_chunks = (len(records) + chunk_size - 1) // chunk_size
    print(
        f"Splitting {len(records):,} records into {num_chunks} chunk(s) of up to {chunk_size} records"
    )

    saved_files = []
    for i in range(num_chunks):
        start_idx = i * chunk_size
        end_idx = min((i + 1) * chunk_size, len(records))
        chunk_records = records[start_idx:end_idx]

        # Format filename with leading zeros
        chunk_filename = f"{project_id}_{start_idx:03d}-{end_idx-1:03d}_esco_matches.json"
        chunk_file = json_output_dir / chunk_filename

        with open(chunk_file, "w", encoding="utf-8") as f:
            json.dump(chunk_records, f, indent=2, ensure_ascii=False)

        saved_files.append(chunk_filename)
        print(
            f"  ✓ Saved chunk {i+1}/{num_chunks}: {chunk_filename} ({len(chunk_records)} records, "
            f"{chunk_file.stat().st_size / 1024:.2f} KB)"
        )

    print(f"✓ Saved {num_chunks} JSON file(s) to: {json_output_dir}")
