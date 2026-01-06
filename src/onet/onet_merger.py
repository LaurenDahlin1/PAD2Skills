"""Merge O*NET job zones onto project ESCO-NACE files."""

from pathlib import Path

import pandas as pd


class OnetMerger:
    """Merges O*NET job zones onto project ESCO-NACE files."""

    def merge_job_zones_to_project(
        self,
        job_zones_file: Path,
        project_esco_nace_file: Path,
        output_file: Path,
        overwrite: bool = False,
    ) -> Path:
        """Merge O*NET job zones onto a project's ESCO-NACE file.

        Args:
            job_zones_file: Path to ESCO-ONET job zones CSV
            project_esco_nace_file: Path to project's unique ESCO-NACE CSV
            output_file: Path to save output CSV
            overwrite: Whether to overwrite existing output file

        Returns:
            Path to output file
        """
        # Check if output exists and overwrite is False
        if output_file.exists() and not overwrite:
            print(f"Output file already exists: {output_file}")
            print("Use --overwrite to force recreation")
            return output_file

        # Load ESCO-ONET job zones
        df_job_zones = pd.read_csv(job_zones_file)
        print(f"✓ Loaded {len(df_job_zones)} ESCO-ONET job zones")

        # Load project's unique ESCO-NACE file
        df_project = pd.read_csv(project_esco_nace_file)
        print(f"✓ Loaded project data: {len(df_project)} rows")

        # Merge job zones onto project data
        df_merged = df_project.merge(df_job_zones, on="esco_id", how="left")

        print("✓ Merged job zones onto project data")
        print(f"  Original rows: {len(df_project)}")
        print(f"  Merged rows: {len(df_merged)}")

        if len(df_merged) != len(df_project):
            print("  ⚠️  Row count changed! Check for duplicates or data issues.")

        # Save to CSV
        output_file.parent.mkdir(parents=True, exist_ok=True)
        df_merged.to_csv(output_file, index=False)

        print(f"\n✓ Saved project data with job zones to: {output_file}")
        print(f"  Rows: {len(df_merged):,}")
        print(f"  Columns: {len(df_merged.columns)}")
        print(f"  File size: {output_file.stat().st_size / 1024:.1f} KB")

        # Show job zone distribution
        if "onet_job_zone" in df_merged.columns:
            print("\nJob zone distribution:")
            for zone, count in sorted(
                df_merged["onet_job_zone"].value_counts().items()
            ):
                print(f"  Zone {zone}: {count}")

            if "onet_job_zone_est" in df_merged.columns:
                print("\nEstimation method distribution:")
                for method, count in (
                    df_merged["onet_job_zone_est"].value_counts().items()
                ):
                    print(f"  {method}: {count}")

        return output_file

    def merge_all_projects(
        self,
        job_zones_file: Path,
        input_dir: Path,
        output_dir: Path,
        overwrite: bool = False,
    ) -> list[Path]:
        """Merge job zones onto all project files in a directory.

        Args:
            job_zones_file: Path to ESCO-ONET job zones CSV
            input_dir: Directory containing project ESCO-NACE CSV files
            output_dir: Directory to save output CSV files
            overwrite: Whether to overwrite existing output files

        Returns:
            List of output file paths
        """
        # Find all project files
        project_files = sorted(input_dir.glob("*_unique_matched_with_nace.csv"))

        if not project_files:
            print(f"No project files found in {input_dir}")
            return []

        print(f"Found {len(project_files)} project files to process\n")

        output_files = []
        for project_file in project_files:
            # Extract project ID from filename
            project_id = project_file.stem.replace("_unique_matched_with_nace", "")

            print(f"Processing {project_id}...")

            # Create output filename
            output_file = output_dir / f"{project_id}_esco_nace_onet.csv"

            try:
                result_file = self.merge_job_zones_to_project(
                    job_zones_file=job_zones_file,
                    project_esco_nace_file=project_file,
                    output_file=output_file,
                    overwrite=overwrite,
                )
                output_files.append(result_file)
            except Exception as e:
                print(f"  ✗ Error processing {project_id}: {e}")
                continue

            print()  # Blank line between projects

        print(f"Completed processing {len(output_files)}/{len(project_files)} projects")
        return output_files
