"""Create ESCO-ONET crosswalk with LLM-generated job zones for missing values."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from openai import OpenAI


class OnetCrosswalkCreator:
    """Creates ESCO-ONET crosswalk with job zones, filling missing values with LLM."""

    def __init__(self, client: OpenAI):
        """Initialize the crosswalk creator.

        Args:
            client: OpenAI client instance for API calls
        """
        self.client = client

    def load_onet_data(
        self, crosswalk_file: Path, job_zones_file: Path
    ) -> pd.DataFrame:
        """Load and merge O*NET crosswalk with job zones data.

        Args:
            crosswalk_file: Path to ESCO-ONET crosswalk CSV
            job_zones_file: Path to O*NET job zones file (tab-separated)

        Returns:
            DataFrame with merged O*NET data
        """
        # Load crosswalk
        crosswalk_df = pd.read_csv(crosswalk_file)
        print(f"✓ Loaded {len(crosswalk_df)} crosswalk records")

        # Load job zones
        job_zones_df = pd.read_csv(job_zones_file, sep="\t")
        print(f"✓ Loaded {len(job_zones_df)} job zone records")

        # Merge on O*NET ID
        onet_merged_df = crosswalk_df.merge(
            job_zones_df,
            left_on="O*NET Id",
            right_on="O*NET-SOC Code",
            how="left",
        )

        # Rename columns
        onet_merged_df = onet_merged_df.rename(
            columns={
                "O*NET Id": "onet_id",
                "O*NET Title": "onet_title",
                "O*NET Description": "onet_description",
                "ESCO or ISCO URI": "uri",
                "Job Zone": "job_zone",
                "ESCO or ISCO Title": "esco_title",
                "ESCO or ISCO Description": "esco_description",
            }
        )

        # Drop unnecessary columns
        columns_to_drop = ["Type of Match", "O*NET-SOC Code", "Date", "Domain Source"]
        onet_merged_df = onet_merged_df.drop(columns=columns_to_drop)

        # Extract ESCO ID from URI
        onet_merged_df["esco_id"] = onet_merged_df["uri"].str.split("/").str[-1]
        onet_merged_df = onet_merged_df.drop(columns=["uri"])

        print(f"✓ Merged and cleaned {len(onet_merged_df)} O*NET records")
        return onet_merged_df

    def merge_with_esco_prepared(
        self, onet_merged_df: pd.DataFrame, esco_prepared_file: Path
    ) -> pd.DataFrame:
        """Merge O*NET data with prepared ESCO occupations.

        Args:
            onet_merged_df: DataFrame with O*NET crosswalk and job zones
            esco_prepared_file: Path to prepared ESCO occupations CSV

        Returns:
            DataFrame with ESCO occupations and aggregated O*NET job zones
        """
        # Load prepared ESCO occupations
        df_occupations = pd.read_csv(esco_prepared_file)
        print(f"✓ Loaded {len(df_occupations)} ESCO occupations")

        # Prepare onet_merged_df for merge
        onet_for_merge = onet_merged_df.drop(columns=["esco_title", "esco_description"])

        # Merge O*NET data onto ESCO occupations
        df_with_onet = df_occupations.merge(onet_for_merge, on="esco_id", how="left")

        # Calculate minimum job zone and collect O*NET titles for each esco_id
        df_with_onet_min = (
            df_with_onet.groupby("esco_id")
            .agg(
                {
                    "job_zone": "min",
                    "onet_title": lambda x: (
                        list(x.dropna().unique()) if x.notna().any() else []
                    ),
                }
            )
            .reset_index()
        )

        # Rename columns
        df_with_onet_min = df_with_onet_min.rename(
            columns={"job_zone": "job_zone_min", "onet_title": "onet_titles"}
        )

        # Convert empty lists to "None, Missing Crosswalk"
        df_with_onet_min["onet_titles"] = df_with_onet_min["onet_titles"].apply(
            lambda x: x if len(x) > 0 else ["None, Missing Crosswalk"]
        )

        # Merge back to original ESCO occupations
        df_final = df_occupations.merge(df_with_onet_min, on="esco_id", how="left")

        # Handle cases with no match
        df_final["onet_titles"] = df_final["onet_titles"].apply(
            lambda x: (
                x if isinstance(x, list) and len(x) > 0 else ["None, Missing Crosswalk"]
            )
        )

        # Fill missing job zones with 9 and convert to int
        df_final["job_zone_min"] = df_final["job_zone_min"].fillna(9).astype(int)

        print(f"✓ Merged O*NET data onto ESCO occupations: {len(df_final)} rows")
        print(f"  Missing job zones (value 9): {(df_final['job_zone_min'] == 9).sum()}")

        return df_final

    def label_missing_job_zones(
        self, df_final: pd.DataFrame, chunk_size: int = 50
    ) -> pd.DataFrame:
        """Label missing job zones using LLM.

        Args:
            df_final: DataFrame with ESCO occupations and job zones
            chunk_size: Number of occupations per API call

        Returns:
            DataFrame with LLM-labeled job zones for missing values
        """
        # Filter occupations with missing job zones
        df_missing = df_final[df_final["job_zone_min"] == 9].copy()

        if len(df_missing) == 0:
            print("✓ No missing job zones to label")
            return pd.DataFrame(columns=["esco_id", "job_zone"])

        print(f"Labeling {len(df_missing)} occupations with missing job zones...")

        # Prepare API input
        df_missing["combined_text"] = (
            df_missing["preferredLabel"] + ". " + df_missing["description"].fillna("")
        )
        df_api_input = df_missing[["esco_id", "combined_text"]].copy()

        # Split into chunks
        num_chunks = int(np.ceil(len(df_api_input) / chunk_size))
        chunks = [
            df_api_input.iloc[i * chunk_size : (i + 1) * chunk_size]
            for i in range(num_chunks)
        ]

        print(f"  Processing {num_chunks} chunks...")

        # Process all chunks
        all_labeled_results = []
        for i, chunk_df in enumerate(chunks, 1):
            print(f"  Chunk {i}/{num_chunks}: {len(chunk_df)} occupations")
            result_df = self._label_job_zones_with_api(chunk_df)
            all_labeled_results.append(result_df)

        # Combine results
        df_all_labeled = pd.concat(all_labeled_results, ignore_index=True)

        print(f"✓ Labeled {len(df_all_labeled)} occupations")
        print("  Job zone distribution:")
        for zone, count in sorted(df_all_labeled["job_zone"].value_counts().items()):
            print(f"    Zone {zone}: {count}")

        return df_all_labeled

    def _label_job_zones_with_api(self, chunk_df: pd.DataFrame) -> pd.DataFrame:
        """Call OpenAI API to label job zones for a chunk.

        Args:
            chunk_df: DataFrame with esco_id and combined_text columns

        Returns:
            DataFrame with esco_id and job_zone columns
        """
        # Convert chunk to JSON format
        records = chunk_df.to_dict("records")
        input_json = json.dumps({"records": records}, indent=2)

        # Call OpenAI API
        response = self.client.responses.create(
            prompt={
                "id": "pmpt_695d532bf6c081938296db5067b3d0b6015bedad79cdc6ce",
                "version": "1",
            },
            input=[{"role": "user", "content": input_json}],
            reasoning={"summary": None},
            store=False,
            include=["reasoning.encrypted_content", "web_search_call.action.sources"],
        )

        # Extract response
        result_text = None
        for item in response.output:
            if hasattr(item, "content") and hasattr(item, "role"):
                result_text = item.content[0].text
                break

        if result_text is None:
            raise ValueError("No content found in API response")

        # Parse JSON response
        result_json = json.loads(result_text)
        result_df = pd.DataFrame(result_json["records"])

        return result_df

    def combine_job_zones(
        self, df_final: pd.DataFrame, df_labeled: pd.DataFrame
    ) -> pd.DataFrame:
        """Combine O*NET and LLM job zones into final dataset.

        Args:
            df_final: DataFrame with ESCO occupations and O*NET job zones
            df_labeled: DataFrame with LLM-labeled job zones

        Returns:
            DataFrame with combined job zones and metadata
        """
        # Rename LLM column
        df_labeled = df_labeled.rename(columns={"job_zone": "onet_job_zone_llm"})

        # Merge LLM labels
        df_merged = df_final.merge(df_labeled, on="esco_id", how="left")

        # Rename and combine job zones
        df_merged = df_merged.rename(columns={"job_zone_min": "onet_job_zone"})

        # Replace with LLM value where O*NET is 9
        df_merged["onet_job_zone"] = df_merged.apply(
            lambda row: (
                row["onet_job_zone_llm"]
                if row["onet_job_zone"] == 9 and pd.notna(row["onet_job_zone_llm"])
                else row["onet_job_zone"]
            ),
            axis=1,
        )

        # Create descriptive labels
        job_zone_labels = {
            1: "1: Little or No Preparation Needed",
            2: "2: Some Preparation Needed",
            3: "3: Medium Preparation Needed",
            4: "4: Considerable Preparation Needed",
            5: "5: Extensive Preparation Needed",
        }
        df_merged["onet_job_zone_label"] = df_merged["onet_job_zone"].map(
            job_zone_labels
        )

        # Create estimation method column
        def categorize_estimation_method(row):
            if pd.notna(row.get("onet_job_zone_llm")):
                return "llm"
            elif (
                len(row["onet_titles"]) == 1
                and row["onet_titles"][0] != "None, Missing Crosswalk"
            ):
                return "unique"
            elif len(row["onet_titles"]) > 1:
                return "minimum"
            else:
                return "unknown"

        df_merged["onet_job_zone_est"] = df_merged.apply(
            categorize_estimation_method, axis=1
        )

        # Create final output with essential columns
        df_final_output = df_merged[
            ["esco_id", "onet_job_zone", "onet_job_zone_label", "onet_job_zone_est"]
        ].copy()

        print(f"✓ Combined job zones: {len(df_final_output)} occupations")
        print("\nJob zone distribution:")
        for zone, count in sorted(
            df_final_output["onet_job_zone"].value_counts().items()
        ):
            print(f"  Zone {zone}: {count}")
        print("\nEstimation method distribution:")
        for method, count in (
            df_final_output["onet_job_zone_est"].value_counts().items()
        ):
            print(f"  {method}: {count}")

        return df_final_output

    def create_crosswalk(
        self,
        crosswalk_file: Path,
        job_zones_file: Path,
        esco_prepared_file: Path,
        output_file: Path,
        chunk_size: int = 50,
        overwrite: bool = False,
    ) -> Path:
        """Create ESCO-ONET crosswalk with job zones.

        Args:
            crosswalk_file: Path to ESCO-ONET crosswalk CSV
            job_zones_file: Path to O*NET job zones file
            esco_prepared_file: Path to prepared ESCO occupations CSV
            output_file: Path to save output CSV
            chunk_size: Number of occupations per API call for missing values
            overwrite: Whether to overwrite existing output file

        Returns:
            Path to output file
        """
        # Check if output exists and overwrite is False
        if output_file.exists() and not overwrite:
            print(f"Output file already exists: {output_file}")
            print("Use --overwrite to force recreation")
            return output_file

        # Load and merge O*NET data
        onet_merged_df = self.load_onet_data(crosswalk_file, job_zones_file)

        # Merge with ESCO prepared data
        df_final = self.merge_with_esco_prepared(onet_merged_df, esco_prepared_file)

        # Label missing job zones with LLM
        df_labeled = self.label_missing_job_zones(df_final, chunk_size=chunk_size)

        # Combine job zones
        df_output = self.combine_job_zones(df_final, df_labeled)

        # Save to CSV
        output_file.parent.mkdir(parents=True, exist_ok=True)
        df_output.to_csv(output_file, index=False)

        print(f"\n✓ Saved ESCO-ONET crosswalk to: {output_file}")
        print(f"  Rows: {len(df_output):,}")
        print(f"  File size: {output_file.stat().st_size / 1024:.1f} KB")

        return output_file
