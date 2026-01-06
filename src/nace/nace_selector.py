"""NACE group selector utility.

Selects the best NACE group for each ESCO occupation using semantic similarity.
"""

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


class NACESelector:
    """Selects best NACE group for ESCO occupations using embeddings."""

    def __init__(
        self,
        unique_esco_path: Path,
        esco_nace_groups_path: Path,
        model_name: str = "intfloat/e5-small-v2",
    ):
        """Initialize the selector.

        Args:
            unique_esco_path: Path to unique ESCO matches CSV
            esco_nace_groups_path: Path to ESCO-NACE groups mapping CSV
            model_name: Name of sentence transformer model to use
        """
        self.unique_esco_path = Path(unique_esco_path)
        self.esco_nace_groups_path = Path(esco_nace_groups_path)
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None

        # Data storage
        self.unique_esco_df: Optional[pd.DataFrame] = None
        self.esco_nace_groups_df: Optional[pd.DataFrame] = None
        self.groups_df: Optional[pd.DataFrame] = None

        # Embeddings
        self.G: Optional[np.ndarray] = None  # Group embeddings
        self.E_esco: Optional[np.ndarray] = None  # ESCO embeddings
        self.group_to_idx: Optional[dict] = None
        self.esco_to_idx: Optional[dict] = None

    def load_data(self) -> None:
        """Load input data files."""
        print(f"Reading unique ESCO file: {self.unique_esco_path}")
        self.unique_esco_df = pd.read_csv(self.unique_esco_path)
        print(f"✓ Loaded {len(self.unique_esco_df)} unique ESCO occupations")

        print(f"\nReading ESCO-NACE groups file: {self.esco_nace_groups_path}")
        self.esco_nace_groups_df = pd.read_csv(
            self.esco_nace_groups_path,
            dtype={
                "esco_id": "string",
                "section_code": "string",
                "division_code": "string",
                "group_code": "string",
            },
        )
        print(f"✓ Loaded {len(self.esco_nace_groups_df)} ESCO-NACE group mappings")
        print(f"  Unique ESCO IDs: {self.esco_nace_groups_df['esco_id'].nunique()}")
        print(f"  Unique NACE groups: {self.esco_nace_groups_df['group_code'].nunique()}")

    def create_combined_text(self) -> None:
        """Create combined text for semantic matching."""

        def _combine_row(row):
            """Combine esco_label, esco_description, pad_occupations, and pad_activities."""
            parts = []

            if pd.notna(row.get("esco_label")):
                parts.append(str(row["esco_label"]))

            if pd.notna(row.get("esco_description")):
                parts.append(str(row["esco_description"]))

            if pd.notna(row.get("pad_occupations")):
                parts.append(str(row["pad_occupations"]))

            if pd.notna(row.get("pad_activities")):
                parts.append(str(row["pad_activities"]))

            return " ".join(parts) if parts else None

        self.unique_esco_df["combined_text"] = self.unique_esco_df.apply(
            _combine_row, axis=1
        )

        print(
            f"✓ Created combined_text column "
            f"({self.unique_esco_df['combined_text'].notna().mean():.1%} coverage)"
        )

    def load_model(self) -> None:
        """Load the sentence transformer model."""
        print(f"\nLoading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        print("✓ Model loaded")

    def encode_nace_groups(self) -> None:
        """Encode NACE groups once for efficiency."""
        if self.model is None:
            raise ValueError("Must call load_model() first")

        # Build group text table (unique group_code)
        self.groups_df = (
            self.esco_nace_groups_df[["group_code", "embedding_description"]]
            .drop_duplicates("group_code")
            .dropna(subset=["embedding_description"])
            .copy()
        )

        print(f"\nPreparing {len(self.groups_df)} unique NACE groups for embedding")

        # E5 expects prefixes for best performance
        self.groups_df["group_text"] = (
            "passage: " + self.groups_df["embedding_description"].astype(str)
        )

        # Encode groups once
        print("Encoding NACE groups...")
        self.G = self.model.encode(
            self.groups_df["group_text"].tolist(),
            normalize_embeddings=True,
            batch_size=128,
            show_progress_bar=True,
        )

        print(f"✓ Encoded {len(self.groups_df)} NACE groups (shape: {self.G.shape})")

        # Map group_code -> row index in G
        self.group_to_idx = dict(zip(self.groups_df["group_code"], range(len(self.groups_df))))
        print("✓ Created group_code to index mapping")

    def encode_esco_texts(self) -> None:
        """Encode ESCO texts."""
        if self.model is None:
            raise ValueError("Must call load_model() first")

        # Unique ESCO texts
        esco_text_df = (
            self.unique_esco_df[["esco_id", "combined_text"]]
            .drop_duplicates("esco_id")
            .dropna(subset=["combined_text"])
            .copy()
        )

        print(f"\nPreparing {len(esco_text_df)} unique ESCO texts for embedding")

        # E5 expects "query: " prefix for queries (vs "passage: " for documents)
        esco_text_df["esco_text"] = "query: " + esco_text_df["combined_text"].astype(str)

        # Encode ESCO texts
        print("Encoding ESCO occupations...")
        self.E_esco = self.model.encode(
            esco_text_df["esco_text"].tolist(),
            normalize_embeddings=True,
            batch_size=128,
            show_progress_bar=True,
        )

        print(f"✓ Encoded {len(esco_text_df)} ESCO occupations (shape: {self.E_esco.shape})")

        # Map esco_id -> row index in E_esco
        self.esco_to_idx = dict(zip(esco_text_df["esco_id"], range(len(esco_text_df))))
        print("✓ Created esco_id to index mapping")

    def pick_best_groups_for_esco(self, esco_id: str, k: int = 1) -> list[tuple[str, float]]:
        """Return top-k NACE groups for a given ESCO ID using cosine similarity.

        Args:
            esco_id: The ESCO occupation ID
            k: Number of top groups to return

        Returns:
            List of tuples: [(group_code, similarity_score), ...]
        """
        if esco_id not in self.esco_to_idx:
            return []

        # Candidate group codes for this ESCO
        cand_groups = (
            self.esco_nace_groups_df.loc[
                self.esco_nace_groups_df["esco_id"] == esco_id, "group_code"
            ]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
        if not cand_groups:
            return []

        # Keep only groups we have embeddings for
        cand_groups = [gc for gc in cand_groups if gc in self.group_to_idx]
        if not cand_groups:
            return []

        e = self.E_esco[self.esco_to_idx[esco_id]]  # (dim,)
        idxs = np.array([self.group_to_idx[gc] for gc in cand_groups], dtype=int)
        scores = self.G[idxs] @ e  # (num_candidates,)

        topk_local = np.argsort(-scores)[:k]
        results = [(cand_groups[i], float(scores[i])) for i in topk_local]
        return results

    def select_best_groups(self) -> pd.DataFrame:
        """Select the best NACE group for each ESCO ID.

        Returns:
            DataFrame with esco_id, group_code, and similarity_score
        """
        print("\nSelecting best NACE group for each ESCO ID...")

        results = []
        for esco_id in self.unique_esco_df["esco_id"].unique():
            top_groups = self.pick_best_groups_for_esco(esco_id, k=1)

            if top_groups:
                group_code, similarity_score = top_groups[0]
                results.append({
                    "esco_id": esco_id,
                    "group_code": group_code,
                    "similarity_score": similarity_score,
                })
            else:
                # No result (no embeddings or no candidate groups)
                results.append({
                    "esco_id": esco_id,
                    "group_code": None,
                    "similarity_score": None,
                })

        best_groups_df = pd.DataFrame(results)

        print(f"✓ Selected best NACE group for {len(best_groups_df)} ESCO IDs")
        print(
            f"  ESCO IDs with a best group: {best_groups_df['group_code'].notna().sum()} "
            f"({best_groups_df['group_code'].notna().mean():.1%})"
        )
        print(f"  ESCO IDs with no group: {best_groups_df['group_code'].isna().sum()}")
        if best_groups_df["similarity_score"].notna().any():
            print(f"  Mean similarity score: {best_groups_df['similarity_score'].mean():.4f}")
            print(f"  Median similarity score: {best_groups_df['similarity_score'].median():.4f}")

        return best_groups_df

    def merge_results(self, best_groups_df: pd.DataFrame) -> pd.DataFrame:
        """Merge best groups back with ESCO data and add NACE metadata.

        Args:
            best_groups_df: DataFrame with esco_id, group_code, similarity_score

        Returns:
            DataFrame with complete results including NACE metadata
        """
        print("\nMerging results with ESCO data...")

        # Merge with unique ESCO data
        result_df = self.unique_esco_df.merge(
            best_groups_df[["esco_id", "group_code", "similarity_score"]],
            on="esco_id",
            how="left",
        )

        # Add NACE group metadata (section, division, group labels)
        result_df = result_df.merge(
            self.esco_nace_groups_df[
                [
                    "group_code",
                    "section_code",
                    "section_label_en",
                    "division_code",
                    "division_label_en",
                    "group_label_en",
                ]
            ].drop_duplicates("group_code"),
            on="group_code",
            how="left",
        )

        print("✓ Merged results")
        print(
            f"  Rows with NACE group: {result_df['group_code'].notna().sum()} "
            f"({result_df['group_code'].notna().mean():.1%})"
        )

        return result_df

    def run(self, output_dir: Path, project_id: str, overwrite: bool = False) -> Path:
        """Run the complete NACE selection process.

        Args:
            output_dir: Directory to save output file
            project_id: Project ID for output filename
            overwrite: If False, skip processing if output file exists

        Returns:
            Path to output file
        """
        # Prepare output path
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{project_id}_unique_matched_with_nace.csv"
        
        # Check if output already exists and skip if not overwriting
        if output_file.exists() and not overwrite:
            print(f"○ Skipped (already exists): {output_file.name}")
            return output_file
        
        # Load data
        self.load_data()

        # Create combined text
        self.create_combined_text()

        # Load model
        self.load_model()

        # Encode groups and ESCO texts
        self.encode_nace_groups()
        self.encode_esco_texts()

        # Select best groups
        best_groups_df = self.select_best_groups()

        # Merge results
        result_df = self.merge_results(best_groups_df)

        # Select final columns in a logical order
        final_columns = [
            "esco_id",
            "esco_label",
            "esco_description",
            "group_code",
            "group_label_en",
            "division_code",
            "division_label_en",
            "section_code",
            "section_label_en",
            "pad_occupations",
            "pad_activities",
            "pad_skills",
            "pad_quotes",
        ]

        # Keep only columns that exist
        final_columns = [col for col in final_columns if col in result_df.columns]

        result_df[final_columns].to_csv(output_file, index=False)

        print(f"\n✓ Saved results to: {output_file}")
        print(f"  Total rows: {len(result_df)}")
        print(f"  Unique ESCO IDs: {result_df['esco_id'].nunique()}")
        print(f"  ESCO IDs with NACE group: {result_df['group_code'].notna().sum()}")
        print(f"  Unique NACE sections: {result_df['section_code'].nunique()}")
        print(f"  Unique NACE divisions: {result_df['division_code'].nunique()}")
        print(f"  Unique NACE groups: {result_df['group_code'].nunique()}")

        return output_file
