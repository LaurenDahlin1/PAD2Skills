"""ESCO-NACE mapping utility.

Parses NACE RDF data and creates mappings between ESCO occupations and NACE groups.
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd
from rdflib import Graph
from rdflib.namespace import SKOS


class ESCONACEMapper:
    """Maps ESCO occupations to NACE groups using RDF data."""

    # Regular expressions for NACE code types
    SECTION_RE = re.compile(r"/[A-Z]$")
    DIV_RE = re.compile(r"/[0-9]{2}$")
    GROUP_RE = re.compile(r"/[0-9]{3}$")

    def __init__(self, nace_rdf_path: Path, esco_occupations_path: Path):
        """Initialize the mapper.

        Args:
            nace_rdf_path: Path to NACE RDF file
            esco_occupations_path: Path to ESCO occupations CSV file
        """
        self.nace_rdf_path = Path(nace_rdf_path)
        self.esco_occupations_path = Path(esco_occupations_path)
        self.graph: Optional[Graph] = None

    @lru_cache(maxsize=200_000)
    def _label_en(self, uri):
        """Return the English skos:prefLabel for a URI, if present."""
        for lbl in self.graph.objects(uri, SKOS.prefLabel):
            if getattr(lbl, "language", None) == "en":
                return str(lbl)
        return None

    def load_nace_rdf(self) -> None:
        """Load NACE RDF data into graph."""
        print(f"Loading NACE RDF data from: {self.nace_rdf_path}")
        self.graph = Graph()
        self.graph.parse(str(self.nace_rdf_path), format="xml")
        print(f"✓ Loaded NACE RDF data ({len(self.graph):,} triples)")

    def extract_nace_hierarchy(self) -> pd.DataFrame:
        """Extract NACE sections, divisions, and groups from RDF.

        Returns:
            DataFrame with columns: section_code, section_label_en, division_code,
            division_label_en, group_code, group_label_en, embedding_description
        """
        if self.graph is None:
            raise ValueError("Must call load_nace_rdf() first")

        sections = []
        divisions = []
        groups = []

        for concept_uri in self.graph.subjects(SKOS.inScheme, None):
            uri_str = str(concept_uri)
            label = self._label_en(concept_uri)

            if self.SECTION_RE.search(uri_str):
                sections.append((uri_str, label))
            elif self.DIV_RE.search(uri_str):
                divisions.append((uri_str, label))
            elif self.GROUP_RE.search(uri_str):
                groups.append((uri_str, label))

        print(f"Extracted {len(sections)} sections, {len(divisions)} divisions, {len(groups)} groups")

        # Build hierarchy mappings
        group_to_div = {}
        for g_uri, _ in groups:
            for broader in self.graph.objects(g_uri, SKOS.broader):
                broader_str = str(broader)
                if self.DIV_RE.search(broader_str):
                    group_to_div[g_uri] = broader_str
                    break

        div_to_sec = {}
        for d_uri, _ in divisions:
            for broader in self.graph.objects(d_uri, SKOS.broader):
                broader_str = str(broader)
                if self.SECTION_RE.search(broader_str):
                    div_to_sec[d_uri] = broader_str
                    break

        # Create dataframe
        rows = []
        for g_uri, g_label in groups:
            g_code = g_uri.split("/")[-1]
            d_uri = group_to_div.get(g_uri)
            if d_uri is None:
                continue

            d_code = d_uri.split("/")[-1]
            d_label = self._label_en(d_uri)

            s_uri = div_to_sec.get(d_uri)
            if s_uri is None:
                continue

            s_code = s_uri.split("/")[-1]
            s_label = self._label_en(s_uri)

            # Create embedding description
            embedding_desc = f"{s_code} {s_label} > {d_code} {d_label} > {g_code} {g_label}"

            rows.append({
                "section_code": s_code,
                "section_label_en": s_label,
                "division_code": d_code,
                "division_label_en": d_label,
                "group_code": g_code,
                "group_label_en": g_label,
                "embedding_description": embedding_desc,
            })

        df = pd.DataFrame(rows)
        print(f"✓ Created hierarchy dataframe with {len(df)} rows")
        return df

    def prepare_esco_data(self) -> pd.DataFrame:
        """Read and prepare ESCO data with NACE codes.

        Returns:
            DataFrame with columns: esco_id, nace_code
        """
        print(f"Reading ESCO occupations file: {self.esco_occupations_path}")
        esco_df = pd.read_csv(self.esco_occupations_path)
        print(f"✓ Loaded {len(esco_df)} ESCO occupations")

        # Extract esco_id from conceptUri and rename naceCode
        esco_df["esco_id"] = esco_df["conceptUri"].str.split("/").str[-1]
        esco_df = esco_df.rename(columns={"naceCode": "nace_code_raw"})

        # Keep only the required columns
        esco_df = esco_df[["esco_id", "nace_code_raw"]]

        # Split comma-separated NACE codes and explode
        print(f"Exploding NACE codes... (before: {len(esco_df)} rows)")
        esco_df["nace_code_raw"] = esco_df["nace_code_raw"].str.split(",")
        esco_df = esco_df.explode("nace_code_raw").reset_index(drop=True)
        print(f"After explode: {len(esco_df)} rows")

        # Extract nace_code from nace_code_raw (the part after the last slash)
        esco_df["nace_code"] = esco_df["nace_code_raw"].str.split("/").str[-1]
        esco_df = esco_df.drop(columns=["nace_code_raw"])

        return esco_df

    def expand_codes_to_groups(
        self, esco_df: pd.DataFrame, hierarchy_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Expand section and division codes to all their groups.

        Args:
            esco_df: DataFrame with esco_id and nace_code
            hierarchy_df: DataFrame with NACE hierarchy

        Returns:
            DataFrame with esco_id and group_code (expanded from sections/divisions)
        """
        print(f"Expanding codes to groups... (before: {len(esco_df)} rows)")

        # Create raw_nace_code to store the original code before expansion
        esco_df["raw_nace_code"] = esco_df["nace_code"]

        # Identify the three types of NACE codes
        esco_df["is_section"] = esco_df["nace_code"].str.match(r"^[A-Z]$")
        esco_df["is_division"] = esco_df["nace_code"].str.match(r"^\d{2}$")
        esco_df["is_group"] = esco_df["nace_code"].str.match(r"^\d{3,4}$")

        print(f"  Section codes (letters): {esco_df['is_section'].sum()}")
        print(f"  Division codes (2 digits): {esco_df['is_division'].sum()}")
        print(f"  Group codes (3-4 digits): {esco_df['is_group'].sum()}")

        # Split into three groups based on code type
        section_codes = esco_df[esco_df["is_section"]].copy()
        division_codes = esco_df[esco_df["is_division"]].copy()
        group_codes = esco_df[esco_df["is_group"]].copy()

        # For section codes, merge with all groups in that section
        section_expanded = section_codes.merge(
            hierarchy_df[["section_code", "division_code", "group_code"]],
            left_on="nace_code",
            right_on="section_code",
            how="left",
        )

        # For division codes, merge with all groups in that division
        division_expanded = division_codes.merge(
            hierarchy_df[["division_code", "group_code"]],
            left_on="nace_code",
            right_on="division_code",
            how="left",
        )

        # Update nace_code with group_code for both expanded dataframes
        section_expanded["nace_code"] = section_expanded["group_code"]
        division_expanded["nace_code"] = division_expanded["group_code"]

        # Keep only the columns we need from expanded dataframes
        section_expanded = section_expanded[["esco_id", "raw_nace_code", "nace_code"]]
        division_expanded = division_expanded[["esco_id", "raw_nace_code", "nace_code"]]

        # Combine all three groups back together
        result_df = pd.concat(
            [
                group_codes[["esco_id", "raw_nace_code", "nace_code"]],
                section_expanded,
                division_expanded,
            ],
            ignore_index=True,
        )

        print(f"After expansion: {len(result_df)} rows")

        # Extract group code (first 3 digits) from nace_code
        result_df["group_code"] = result_df["nace_code"].str[:3]

        # Drop intermediate columns
        result_df = result_df.drop(columns=["nace_code", "raw_nace_code"])

        return result_df

    def create_esco_nace_mapping(
        self, esco_df: pd.DataFrame, hierarchy_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Create final ESCO-NACE mapping with group metadata.

        Args:
            esco_df: DataFrame with esco_id and group_code
            hierarchy_df: DataFrame with NACE hierarchy

        Returns:
            DataFrame with complete ESCO-NACE group mapping
        """
        print(f"Merging group metadata... (before: {len(esco_df)} rows)")

        # Merge group metadata
        result_df = esco_df.merge(
            hierarchy_df[
                [
                    "group_code",
                    "section_code",
                    "section_label_en",
                    "division_code",
                    "division_label_en",
                    "group_label_en",
                    "embedding_description",
                ]
            ],
            on="group_code",
            how="left",
        )

        print(f"After merge: {len(result_df)} rows")

        # Check for unmatched groups
        unmatched = result_df["section_code"].isna().sum()
        print(f"Unmatched groups (no metadata): {unmatched} ({unmatched/len(result_df):.1%})")

        # Drop duplicates
        before_dedup = len(result_df)
        result_df = result_df.drop_duplicates()
        after_dedup = len(result_df)
        print(f"Duplicates removed: {before_dedup - after_dedup}")

        # Reorder columns
        result_df = result_df[
            [
                "esco_id",
                "section_code",
                "section_label_en",
                "division_code",
                "division_label_en",
                "group_code",
                "group_label_en",
                "embedding_description",
            ]
        ]

        return result_df

    def run(self, output_dir: Path) -> tuple[Path, Path]:
        """Run the complete ESCO-NACE mapping process.

        Args:
            output_dir: Directory to save output files

        Returns:
            Tuple of (main_output_path, inspect_output_path)
        """
        # Load NACE RDF
        self.load_nace_rdf()

        # Extract NACE hierarchy
        hierarchy_df = self.extract_nace_hierarchy()

        # Prepare ESCO data
        esco_df = self.prepare_esco_data()

        # Expand codes to groups
        expanded_df = self.expand_codes_to_groups(esco_df, hierarchy_df)

        # Create final mapping
        final_df = self.create_esco_nace_mapping(expanded_df, hierarchy_df)

        # Create output directory
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save main output
        main_output = output_dir / "esco_nace_groups.csv"
        final_df.to_csv(main_output, index=False)
        print(f"\n✓ Saved {len(final_df)} rows to: {main_output}")

        # Create inspection file (without esco_id to see unique groups)
        inspect_df = final_df.drop(columns=["esco_id"]).drop_duplicates()
        inspect_output = output_dir / "inspect_esco_nace_groups.csv"
        inspect_df.to_csv(inspect_output, index=False)
        print(f"✓ Saved {len(inspect_df)} unique NACE groups to: {inspect_output}")

        return main_output, inspect_output
