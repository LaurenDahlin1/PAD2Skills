"""Refine ESCO skills by evaluating relevance to PAD project context."""

import json
from pathlib import Path
from typing import Dict, List

import pandas as pd
from openai import OpenAI


class SkillsRefiner:
    """Refine ESCO skills by evaluating relevance using OpenAI API.

    This class loads ESCO occupations with NACE codes, merges with skills from
    the ESCO skills relation table, creates JSON chunks for API processing, and
    evaluates skill relevance for each occupation.
    """

    def __init__(
        self,
        unique_esco_nace_file: Path,
        esco_skills_file: Path,
        pad_summary_file: Path,
        project_id: str,
        openai_api_key: str,
        chunk_size: int = 3,
    ):
        """Initialize the SkillsRefiner.

        Args:
            unique_esco_nace_file: Path to unique ESCO occupations with NACE codes CSV
            esco_skills_file: Path to ESCO occupation-skill relations CSV
            pad_summary_file: Path to project summary text file
            project_id: Project identifier
            openai_api_key: OpenAI API key for skill evaluation
            chunk_size: Number of occupations per API chunk (default: 3)
        """
        self.unique_esco_nace_file = unique_esco_nace_file
        self.esco_skills_file = esco_skills_file
        self.pad_summary_file = pad_summary_file
        self.project_id = project_id
        self.chunk_size = chunk_size

        # Initialize OpenAI client
        self.client = OpenAI(api_key=openai_api_key)

        # Data storage
        self.df_occupations = None
        self.df_skills = None
        self.df_merged_sorted = None
        self.project_summary = None

    def load_data(self) -> None:
        """Load all required data files."""
        print("Loading data files...")

        # Load unique ESCO occupations with NACE codes
        self.df_occupations = pd.read_csv(self.unique_esco_nace_file)
        print(f"  ✓ Loaded {len(self.df_occupations)} unique ESCO occupations")

        # Load ESCO skills relations
        df_skills_raw = pd.read_csv(self.esco_skills_file)
        print(f"  ✓ Loaded {len(df_skills_raw)} occupation-skill relations")

        # Filter for essential skills only
        self.df_skills = df_skills_raw[df_skills_raw["relationType"] == "essential"]
        print(f"  ✓ Filtered to {len(self.df_skills)} essential skills")

        # Load project summary
        with open(self.pad_summary_file, "r") as f:
            self.project_summary = f.read()
        print(f"  ✓ Loaded project summary ({len(self.project_summary)} characters)")

    def merge_and_prepare(self) -> None:
        """Merge occupations with skills and prepare data structure."""
        print("\nMerging occupations with skills...")

        # Extract UUID from skills file occupationUri
        # Skills file has: http://data.europa.eu/esco/occupation/{uuid}
        # Occupations file has: {uuid}
        self.df_skills["occupation_uuid"] = (
            self.df_skills["occupationUri"].str.split("/").str[-1]
        )

        # Merge on UUID
        df_merged = self.df_occupations.merge(
            self.df_skills,
            left_on="esco_id",
            right_on="occupation_uuid",
            how="left",
        )

        # Extract skill_code from skillUri
        df_merged["skill_code"] = df_merged["skillUri"].str.split("/").str[-1]

        # Sort by esco_id and skill_code
        df_merged = df_merged.sort_values(["esco_id", "skill_code"]).reset_index(
            drop=True
        )

        # Create esco_num (three-digit ordered ID for each unique esco_id)
        unique_esco_ids = df_merged["esco_id"].unique()
        esco_num_map = {
            esco_id: f"{i + 1:03d}" for i, esco_id in enumerate(unique_esco_ids)
        }
        df_merged["esco_num"] = df_merged["esco_id"].map(esco_num_map)

        self.df_merged_sorted = df_merged

        print(f"  ✓ Merged data shape: {self.df_merged_sorted.shape}")
        print(f"  ✓ Unique occupations: {len(unique_esco_ids)}")

    def create_json_chunk(self, chunk_esco_ids: List[str]) -> Dict:
        """Create a JSON structure for a chunk of occupations.

        Args:
            chunk_esco_ids: List of ESCO IDs in this chunk

        Returns:
            Dictionary representing the JSON structure
        """
        occupations = []

        for esco_id in chunk_esco_ids:
            # Get occupation details
            occ_row = self.df_occupations[
                self.df_occupations["esco_id"] == esco_id
            ].iloc[0]

            # Get all skills for this occupation
            occ_skills = self.df_merged_sorted[
                self.df_merged_sorted["esco_id"] == esco_id
            ]

            # Build skills list
            skills_list = []
            for _, skill_row in occ_skills.iterrows():
                skills_list.append(
                    {
                        "skill_code": skill_row["skill_code"],
                        "skill_label": skill_row["skillLabel"],
                    }
                )

            # Build occupation dict
            occupation_dict = {
                "esco_num": occ_skills.iloc[0]["esco_num"],
                "esco_id": esco_id,
                "esco_label": occ_row["esco_label"],
                "pad_occupations": occ_row.get("pad_occupations", ""),
                "pad_activities": occ_row.get("pad_activities", ""),
                "pad_skills": occ_row.get("pad_skills", ""),
                "skills": skills_list,
            }

            occupations.append(occupation_dict)

        # Build the final JSON structure
        json_chunk = {
            "project_id": self.project_id,
            "project_summary": self.project_summary,
            "occupations": occupations,
        }

        return json_chunk

    def evaluate_skills_with_api(self, chunk_json: Dict) -> Dict:
        """Call OpenAI API to evaluate skills for a chunk of occupations.

        Args:
            chunk_json: Dictionary containing the input JSON structure

        Returns:
            Dictionary with evaluation results
        """
        # Convert to JSON string for input message
        input_message = json.dumps(chunk_json, indent=2, ensure_ascii=False)

        # Call OpenAI API with prompt
        response = self.client.responses.create(
            prompt={
                "id": "pmpt_695c42b522b8819683a2e305c9886b2a0a31f94fbd8aa0d8",
                "version": "1",
            },
            input=[{"role": "user", "content": input_message}],
            reasoning={"summary": None},
            store=False,
            include=["reasoning.encrypted_content", "web_search_call.action.sources"],
        )

        # Extract the text from the response
        result_text = None
        for item in response.output:
            if hasattr(item, "content") and hasattr(item, "role"):
                result_text = item.content[0].text
                break

        if result_text is None:
            raise ValueError("No content found in API response")

        # Parse the JSON response
        result_json = json.loads(result_text)

        return result_json

    def result_to_dataframe(self, result_json: Dict) -> pd.DataFrame:
        """Convert API result JSON to a flat DataFrame.

        Args:
            result_json: Dictionary with project_id and occupations array

        Returns:
            DataFrame with columns: esco_id, skill_code, relevant, top_five
        """
        rows = []

        for occupation in result_json["occupations"]:
            esco_id = occupation["esco_id"]

            for skill in occupation["skills"]:
                rows.append(
                    {
                        "esco_id": esco_id,
                        "skill_code": skill["skill_code"],
                        "relevant": skill["relevant"],
                        "top_five": skill["top_five"],
                    }
                )

        return pd.DataFrame(rows)

    def chunk_list(self, lst: List, chunk_size: int) -> List[List]:
        """Split a list into chunks of specified size.

        Args:
            lst: List to split
            chunk_size: Size of each chunk

        Returns:
            List of chunks
        """
        chunks = []
        for i in range(0, len(lst), chunk_size):
            chunks.append(lst[i : i + chunk_size])
        return chunks

    def process_all_chunks(self) -> pd.DataFrame:
        """Process all occupation chunks through the API.

        Returns:
            DataFrame with all evaluation results
        """
        # Get unique ESCO IDs
        unique_esco_ids = self.df_merged_sorted["esco_id"].unique()

        # Split into chunks
        esco_chunks = self.chunk_list(list(unique_esco_ids), self.chunk_size)

        print(f"\nProcessing {len(esco_chunks)} chunks...")
        print("=" * 80)

        all_evaluation_results = []

        for i, chunk_esco_ids in enumerate(esco_chunks, 1):
            print(f"\nChunk {i}/{len(esco_chunks)}: {len(chunk_esco_ids)} occupations")

            # Create JSON for this chunk
            chunk_json = self.create_json_chunk(chunk_esco_ids)

            # Call API to evaluate skills
            print("  Calling API...")
            result_json = self.evaluate_skills_with_api(chunk_json)

            # Convert result to dataframe
            df_chunk_evaluation = self.result_to_dataframe(result_json)

            print(f"  ✓ Evaluation rows: {len(df_chunk_evaluation)}")

            all_evaluation_results.append(df_chunk_evaluation)

        # Combine all results
        df_all_evaluations = pd.concat(all_evaluation_results, ignore_index=True)

        print("\n" + "=" * 80)
        print(f"✓ Total evaluation rows: {len(df_all_evaluations)}")
        print(
            f"✓ Unique occupations evaluated: {df_all_evaluations['esco_id'].nunique()}"
        )

        return df_all_evaluations

    def run(self, output_dir: Path, overwrite: bool = False) -> Path:
        """Run the complete skills refinement pipeline.

        Args:
            output_dir: Directory to save output CSV file
            overwrite: If False, skip processing if output file exists

        Returns:
            Path to the output CSV file
        """
        # Prepare output path
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{self.project_id}_esco_nace_with_skills.csv"

        # Check if output already exists and skip if not overwriting
        if output_file.exists() and not overwrite:
            print(f"○ Skipped (already exists): {output_file.name}")
            return output_file

        print("=" * 80)
        print("ESCO Skills Refiner")
        print("=" * 80)
        print(f"Project ID: {self.project_id}")
        print(f"Chunk size: {self.chunk_size} occupations")
        print()

        # Load data
        self.load_data()

        # Merge and prepare
        self.merge_and_prepare()

        # Process all chunks through API
        df_all_evaluations = self.process_all_chunks()

        # Merge evaluation results back to main dataframe
        print("\nMerging evaluation results...")
        df_with_evaluation = self.df_merged_sorted.merge(
            df_all_evaluations, on=["esco_id", "skill_code"], how="left"
        )
        print(f"  ✓ Final dataframe shape: {df_with_evaluation.shape}")

        # Save to CSV
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{self.project_id}_esco_nace_with_skills.csv"
        df_with_evaluation.to_csv(output_file, index=False)

        print("\n" + "=" * 80)
        print("✓ Results saved!")
        print("=" * 80)
        print(f"Output file: {output_file}")
        print(f"  Rows: {len(df_with_evaluation):,}")
        print(f"  Columns: {len(df_with_evaluation.columns)}")
        print(f"  Unique occupations: {df_with_evaluation['esco_id'].nunique()}")
        print(f"  File size: {output_file.stat().st_size / 1024:.1f} KB")

        return output_file
