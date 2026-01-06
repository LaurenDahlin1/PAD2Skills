"""Select best ESCO occupation matches using OpenAI API."""

import json
import logging
import re
from pathlib import Path
from typing import Any

import pandas as pd
from openai import OpenAI


class EscoSelector:
    """Select best ESCO match for each PAD occupation using OpenAI API."""

    def __init__(
        self,
        client: OpenAI | None = None,
        prompt_id: str = "pmpt_69570f3e44488197ae85998b411c848b035ce9f8e4648a29",
        prompt_version: str = "1",
    ):
        """
        Initialize ESCO selector.

        Args:
            client: OpenAI client (if None, will create default client)
            prompt_id: OpenAI prompt ID for ESCO selection
            prompt_version: Version of the prompt to use
        """
        # Suppress verbose HTTP logging from OpenAI client
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)
        
        self.client = client or OpenAI()
        self.prompt_id = prompt_id
        self.prompt_version = prompt_version

    def process_chunk(self, chunk_data: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Process a single JSON chunk through OpenAI API.

        Args:
            chunk_data: List of records with PAD occupations and ESCO candidates

        Returns:
            Dict with 'results' key containing selection results
        """
        # Convert to JSON string for input message
        input_message = json.dumps(chunk_data, indent=2, ensure_ascii=False)

        # Call OpenAI API with prompt
        response = self.client.responses.create(
            prompt={"id": self.prompt_id, "version": self.prompt_version},
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
            raise ValueError("No content found in OpenAI response")

        # Parse JSON response
        result_data = json.loads(result_text)
        return result_data

    def process_all_chunks(
        self,
        input_dir: Path,
        project_id: str,
        output_dir: Path,
        overwrite: bool = False,
    ) -> list[Path]:
        """
        Process all JSON chunks for a project through OpenAI API.

        Args:
            input_dir: Directory containing esco_matching JSON files
            project_id: Project ID (e.g., "P075941")
            output_dir: Directory to save selection results
            overwrite: Whether to overwrite existing files

        Returns:
            List of paths to created output files

        Raises:
            FileNotFoundError: If no input files found
        """
        # Find all JSON chunk files for this project
        json_files = sorted(input_dir.glob(f"{project_id}_*_esco_matches.json"))

        if not json_files:
            raise FileNotFoundError(
                f"No ESCO matching files found for project {project_id} in {input_dir}"
            )

        print(f"Found {len(json_files)} JSON chunk files for project {project_id}")

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Clean up any existing output files for this project to avoid stale chunk files
        # Only do this when overwriting to prevent stale chunks from previous runs
        if overwrite:
            existing_files = list(output_dir.glob(f"{project_id}_*_esco_selection.json"))
            if existing_files:
                print(f"Cleaning up {len(existing_files)} existing output files for {project_id}")
                for old_file in existing_files:
                    old_file.unlink()

        output_files = []

        for i, json_file in enumerate(json_files, 1):
            # Parse filename to extract chunk identifier
            filename_stem = json_file.stem  # e.g., P075941_000-074_esco_matches
            parts = filename_stem.split("_")
            chunk_id = parts[1]  # e.g., 000-074

            # Define output file path
            output_file = output_dir / f"{project_id}_{chunk_id}_esco_selection.json"

            # Check if file exists and handle overwrite
            if output_file.exists() and not overwrite:
                print(
                    f"[{i}/{len(json_files)}] Skipping existing: {output_file.name}"
                )
                output_files.append(output_file)
                continue

            # Read JSON chunk content
            with open(json_file, "r", encoding="utf-8") as f:
                chunk_data = json.load(f)

            print(f"[{i}/{len(json_files)}] Processing: {json_file.name}")
            print(f"  Chunk ID: {chunk_id}")
            print(f"  Records: {len(chunk_data)}")

            # Process chunk through OpenAI API
            result_data = self.process_chunk(chunk_data)

            # Save result to file
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)

            print(f"  ✓ Saved to: {output_file.name}")
            output_files.append(output_file)

        print(f"✓ Processed {len(json_files)} chunks")
        print(f"✓ Results saved to: {output_dir}")

        return output_files

    def combine_to_csv(
        self,
        json_selection_dir: Path,
        project_id: str,
        pad_occupations_dir: Path,
        output_dir: Path,
    ) -> pd.DataFrame:
        """
        Combine JSON selection files into a CSV with PAD context.

        Args:
            json_selection_dir: Directory containing selection JSON files
            project_id: Project ID (e.g., "P075941")
            pad_occupations_dir: Directory containing PAD occupation JSON files
            output_dir: Directory to save combined CSV

        Returns:
            DataFrame with combined selections and PAD data

        Raises:
            FileNotFoundError: If required files not found
        """
        # Load original PAD data from JSON files
        pad_df = _load_pad_occupations(pad_occupations_dir, project_id)
        print(f"✓ Loaded original PAD data: {len(pad_df)} rows")

        # Load all JSON selection files
        json_selection_files = sorted(
            json_selection_dir.glob(f"{project_id}_*_esco_selection.json")
        )

        if not json_selection_files:
            raise FileNotFoundError(
                f"No selection files found for {project_id} in {json_selection_dir}"
            )

        print(f"Loading {len(json_selection_files)} JSON selection files...")

        all_records = []
        for json_file in json_selection_files:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Extract records from the "results" key
            if isinstance(data, dict) and "results" in data:
                records = data["results"]
                all_records.extend(records)
            elif isinstance(data, list):
                all_records.extend(data)
            else:
                all_records.append(data)

        print(f"✓ Combined {len(all_records)} records from {len(json_selection_files)} files")

        # Convert records to DataFrame
        df_records = []
        for record in all_records:
            chosen_esco = record.get("chosen_esco") or {}

            flat_record = {
                "record_id": record.get("record_id", ""),
                "esco_id": chosen_esco.get("esco_id", ""),
                "esco_label": chosen_esco.get("label", ""),
                "rank": chosen_esco.get("rank", ""),
                "confidence": chosen_esco.get("confidence", ""),
                "needs_manual_review": record.get("needs_manual_review", ""),
            }
            df_records.append(flat_record)

        selections_df = pd.DataFrame(df_records)
        selections_df["record_id"] = selections_df["record_id"].astype(str).str.zfill(3)

        # Prepare PAD data
        pad_df_prepared = pad_df[
            [
                "pad_id",
                "project_id",
                "section_id",
                "identified_occupation",
                "activity_description_in_pad",
                "skills_needed_for_activity",
                "source_material_quote",
            ]
        ].copy()

        pad_df_prepared["pad_id"] = pad_df_prepared["pad_id"].astype(str).str.zfill(3)
        pad_df_prepared = pad_df_prepared.rename(
            columns={
                "pad_id": "record_id",
                "identified_occupation": "pad_occupation",
                "activity_description_in_pad": "pad_activity",
                "skills_needed_for_activity": "pad_skills",
                "source_material_quote": "pad_quote",
                "section_id": "pad_section_id",
            }
        )

        # Join selections with PAD data
        df = selections_df.merge(pad_df_prepared, on="record_id", how="left")

        # Reorder columns
        column_order = [
            "project_id",
            "record_id",
            "esco_id",
            "esco_label",
            "rank",
            "confidence",
            "needs_manual_review",
            "pad_occupation",
            "pad_activity",
            "pad_skills",
            "pad_quote",
            "pad_section_id",
        ]
        df = df[column_order]

        # Save to CSV
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{project_id}_esco_selections.csv"
        df.to_csv(output_file, index=False)

        print(f"✓ Saved combined selections to: {output_file}")
        print(f"  Rows: {len(df):,}, Columns: {len(df.columns)}")

        return df


def _load_pad_occupations(pad_occupations_dir: Path, project_id: str) -> pd.DataFrame:
    """
    Load PAD occupation extractions from JSON files.

    Args:
        pad_occupations_dir: Directory containing occupation JSON files
        project_id: Project ID to filter files

    Returns:
        DataFrame with PAD occupations and pad_id

    Raises:
        FileNotFoundError: If no matching JSON files found
    """
    import json
    
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

    return df


def select_best_esco_matches(
    input_dir: Path,
    project_id: str,
    pad_occupations_dir: Path,
    output_json_dir: Path,
    output_csv_dir: Path,
    client: OpenAI | None = None,
    overwrite: bool = False,
) -> pd.DataFrame:
    """
    Select best ESCO matches for PAD occupations using OpenAI API.

    High-level function that processes JSON chunks through the API and
    combines results into a CSV with PAD context.

    Args:
        input_dir: Directory containing esco_matching JSON files
        project_id: Project ID (e.g., "P075941")
        pad_occupations_dir: Directory containing PAD occupation JSON files
        output_json_dir: Directory to save selection JSON files
        output_csv_dir: Directory to save combined CSV
        client: OpenAI client (if None, will create default client)
        overwrite: Whether to overwrite existing files

    Returns:
        DataFrame with selections and PAD context

    Raises:
        FileNotFoundError: If required input files not found
    """
    selector = EscoSelector(client=client)

    # Process all chunks through API
    selector.process_all_chunks(
        input_dir=input_dir,
        project_id=project_id,
        output_dir=output_json_dir,
        overwrite=overwrite,
    )

    # Combine results into CSV
    df = selector.combine_to_csv(
        json_selection_dir=output_json_dir,
        project_id=project_id,
        pad_occupations_dir=pad_occupations_dir,
        output_dir=output_csv_dir,
    )

    return df
