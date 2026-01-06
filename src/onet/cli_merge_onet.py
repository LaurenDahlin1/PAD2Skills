"""CLI for merging O*NET job zones onto project ESCO-NACE files."""

import argparse
from pathlib import Path

from src.config import load_config
from src.onet.onet_merger import OnetMerger


def main():
    """Merge O*NET job zones onto project ESCO-NACE files."""
    parser = argparse.ArgumentParser(
        description="Merge O*NET job zones onto project ESCO-NACE files"
    )
    parser.add_argument(
        "--project-id",
        type=str,
        help="Project ID (e.g., P075941). If not provided, processes all projects.",
    )
    parser.add_argument(
        "--job-zones-file",
        type=Path,
        help="Path to ESCO-ONET job zones CSV (default: data/silver/clean_esco/esco_onet_job_zones.csv)",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        help="Directory containing project ESCO-NACE CSV files (default: data/silver/unique_esco_nace_csv)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to save output CSV files (default: data/silver/unique_esco_nace_onet_csv)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files",
    )

    args = parser.parse_args()

    # Load config
    config = load_config()
    project_root = Path(config["paths"]["project_root"])

    # Set defaults from config if not provided
    job_zones_file = args.job_zones_file or (
        project_root / "data" / "silver" / "clean_esco" / "esco_onet_job_zones.csv"
    )
    input_dir = args.input_dir or (
        project_root / "data" / "silver" / "unique_esco_nace_csv"
    )
    output_dir = args.output_dir or (
        project_root / "data" / "silver" / "unique_esco_nace_onet_csv"
    )

    # Validate input files
    if not job_zones_file.exists():
        print(f"Error: ESCO-ONET job zones file not found: {job_zones_file}")
        print("\nMake sure to run the crosswalk creation step first:")
        print("  uv run python -m src.onet.cli_create_crosswalk")
        return 1

    if not input_dir.exists():
        print(f"Error: Input directory not found: {input_dir}")
        print("\nMake sure projects have been processed through the NACE step.")
        return 1

    # Initialize merger
    merger = OnetMerger()

    print("=" * 80)
    print("Merging O*NET Job Zones onto Project Files")
    print("=" * 80)
    print(f"Job zones file: {job_zones_file}")
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Overwrite: {args.overwrite}")

    if args.project_id:
        print(f"Project ID: {args.project_id}")
    else:
        print("Processing: All projects in input directory")

    print("=" * 80)
    print()

    try:
        if args.project_id:
            # Process single project
            project_file = input_dir / f"{args.project_id}_unique_matched_with_nace.csv"
            if not project_file.exists():
                print(f"Error: Project file not found: {project_file}")
                print(
                    f"\nMake sure {args.project_id} has been processed through the NACE step:"
                )
                print(
                    f"  uv run python -m src.nace.cli_select_nace --project-id {args.project_id}"
                )
                return 1

            output_file = output_dir / f"{args.project_id}_esco_nace_onet.csv"

            output_path = merger.merge_job_zones_to_project(
                job_zones_file=job_zones_file,
                project_esco_nace_file=project_file,
                output_file=output_file,
                overwrite=args.overwrite,
            )

            print("\n" + "=" * 80)
            print("✓ Merge complete!")
            print(f"  Output: {output_path}")
            print("=" * 80)

        else:
            # Process all projects
            output_files = merger.merge_all_projects(
                job_zones_file=job_zones_file,
                input_dir=input_dir,
                output_dir=output_dir,
                overwrite=args.overwrite,
            )

            print("\n" + "=" * 80)
            print(f"✓ Merge complete! Processed {len(output_files)} projects")
            print(f"  Output directory: {output_dir}")
            print("=" * 80)

        return 0

    except Exception as e:
        print(f"\n✗ Error merging job zones: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
