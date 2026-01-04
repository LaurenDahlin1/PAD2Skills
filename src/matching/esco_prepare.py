"""Prepare ESCO occupations data with embeddings for matching."""

from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


def prepare_esco_data(
    esco_dir: Path,
    output_csv: Path,
    embeddings_file: Path,
    overwrite_embeddings: bool = False,
    model_name: str = "intfloat/e5-small-v2",
) -> tuple[pd.DataFrame, np.ndarray]:
    """
    Prepare ESCO occupations data with embeddings.

    Reads ESCO occupations and skills, filters essential skills/competences,
    merges and flattens them, creates combined text representations,
    and generates embeddings using a sentence transformer model.

    Args:
        esco_dir: Directory containing ESCO CSV files (occupations_en.csv, occupationSkillRelations_en.csv)
        output_csv: Path to save prepared ESCO CSV file
        embeddings_file: Path to save/load embeddings (npy format)
        overwrite_embeddings: Whether to regenerate embeddings even if cached version exists
        model_name: Name of sentence transformer model to use (default: intfloat/e5-small-v2)

    Returns:
        Tuple of (prepared DataFrame, embeddings array)
            - DataFrame columns: esco_id, conceptUri, preferredLabel, description, combined_text
            - Embeddings array: normalized embeddings for cosine similarity via dot product

    Raises:
        FileNotFoundError: If required ESCO files don't exist
    """
    # File paths
    occupations_file = esco_dir / "occupations_en.csv"
    skills_relations_file = esco_dir / "occupationSkillRelations_en.csv"

    # Validate files exist
    if not occupations_file.exists():
        raise FileNotFoundError(f"ESCO occupations file not found: {occupations_file}")
    if not skills_relations_file.exists():
        raise FileNotFoundError(f"ESCO skills relations file not found: {skills_relations_file}")

    # Read ESCO data
    print(f"Loading ESCO occupations from {occupations_file}...")
    occ_df = pd.read_csv(occupations_file)
    print(f"✓ Loaded {len(occ_df):,} ESCO occupations")

    print(f"Loading ESCO skills relations from {skills_relations_file}...")
    skills_df = pd.read_csv(skills_relations_file)
    print(f"✓ Loaded {len(skills_df):,} skill relations")

    # Filter for essential skills/competences only
    skills_filtered = skills_df[
        (skills_df["relationType"] == "essential") & (skills_df["skillType"] == "skill/competence")
    ].copy()
    print(
        f"✓ Filtered to {len(skills_filtered):,} essential skill/competence relations "
        f"(from {len(skills_df):,} total)"
    )

    # Merge skills onto occupations
    merged_df = occ_df.merge(
        skills_filtered, right_on="occupationUri", left_on="conceptUri", how="left"
    )
    print(f"✓ Merged skills onto occupations: {len(merged_df):,} rows")

    # Flatten skills by occupation
    flattened_df = (
        merged_df.groupby("occupationUri")
        .agg(
            {
                "conceptUri": "first",
                "preferredLabel": "first",
                "altLabels": "first",
                "description": "first",
                "skillLabel": lambda x: ", ".join(x.dropna().astype(str)),
            }
        )
        .reset_index()
    )
    flattened_df = flattened_df.rename(columns={"skillLabel": "skills_list"})
    print(f"✓ Flattened to {len(flattened_df):,} unique occupations")

    # Combine fields into single text column
    flattened_df["combined_text"] = flattened_df.apply(_combine_fields, axis=1)
    print("✓ Created combined_text column with prioritized fields")

    # Extract ESCO UUID from conceptUri
    flattened_df["esco_id"] = flattened_df["conceptUri"].apply(lambda uri: uri.split("/")[-1])

    # Select columns for export
    export_df = flattened_df[
        ["esco_id", "conceptUri", "preferredLabel", "description", "combined_text"]
    ].copy()

    # Save prepared data
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    export_df.to_csv(output_csv, index=False)
    print(f"✓ Saved prepared ESCO data to: {output_csv}")
    print(f"  Rows: {len(export_df):,}, Columns: {len(export_df.columns)}")

    # Load or generate embeddings
    embeddings_file.parent.mkdir(parents=True, exist_ok=True)

    if embeddings_file.exists() and not overwrite_embeddings:
        print(f"✓ Loading cached ESCO embeddings from: {embeddings_file}")
        embeddings = np.load(embeddings_file)
        print(f"  Loaded embeddings shape: {embeddings.shape}")
    else:
        if overwrite_embeddings and embeddings_file.exists():
            print("⚠ Overwriting existing embeddings (overwrite_embeddings=True)")
        else:
            print("No cached embeddings found. Encoding...")

        # Load model and encode
        print(f"Loading model: {model_name}...")
        model = SentenceTransformer(model_name)
        print(f"  Max sequence length: {model.max_seq_length}")
        print(f"  Embedding dimension: {model.get_sentence_embedding_dimension()}")

        # Prepare texts with "passage: " prefix for e5 model
        esco_texts = ["passage: " + text for text in export_df["combined_text"].tolist()]
        print(f"Encoding {len(esco_texts):,} ESCO occupations...")

        # Encode (normalized for cosine similarity via dot product)
        embeddings = model.encode(
            esco_texts, normalize_embeddings=True, batch_size=64, show_progress_bar=True
        )

        # Save embeddings
        np.save(embeddings_file, embeddings)
        print(f"✓ Saved embeddings to: {embeddings_file}")

    print(
        f"✓ ESCO embeddings ready: shape={embeddings.shape}, "
        f"size={embeddings.nbytes / 1024 / 1024:.2f} MB"
    )

    return export_df, embeddings


def _combine_fields(row: pd.Series) -> str:
    """
    Combine multiple ESCO fields into prioritized space-separated string.

    Fields are ordered by importance to minimize impact of model truncation:
    1. Preferred label (most important)
    2. First 5 alternative labels
    3. Description
    4. Skills list (truncated to 1500 chars)
    5. Remaining alternative labels (6+)

    Args:
        row: DataFrame row with ESCO fields (preferredLabel, altLabels, description, skills_list)

    Returns:
        Combined text string with all fields space-separated
    """
    parts = []

    # 1. Add preferredLabel (most important)
    if pd.notna(row["preferredLabel"]):
        parts.append(str(row["preferredLabel"]))

    # 2. Add first 5 altLabels
    first_alt_labels = []
    remaining_alt_labels = []
    if pd.notna(row["altLabels"]):
        alt_labels_str = str(row["altLabels"])
        # Split by newline first, then by comma if no newlines
        if "\n" in alt_labels_str:
            alt_labels_list = [
                label.strip() for label in alt_labels_str.split("\n") if label.strip()
            ]
        else:
            alt_labels_list = [
                label.strip() for label in alt_labels_str.split(",") if label.strip()
            ]

        first_alt_labels = alt_labels_list[:5]
        remaining_alt_labels = alt_labels_list[5:]

        if first_alt_labels:
            parts.append(" ".join(first_alt_labels))

    # 3. Add description
    if pd.notna(row["description"]):
        parts.append(str(row["description"]))

    # 4. Add skills_list truncated to 1500 characters
    if pd.notna(row["skills_list"]):
        skills_str = str(row["skills_list"])
        if len(skills_str) > 1500:
            skills_str = skills_str[:1500]
        parts.append(skills_str)

    # 5. Add remaining altLabels (6+) if they exist
    if remaining_alt_labels:
        parts.append(" ".join(remaining_alt_labels))

    return " ".join(parts)
