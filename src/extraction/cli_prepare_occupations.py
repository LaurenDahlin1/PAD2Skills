"""CLI for preparing PAD occupations CSV files from JSON extractions."""

import argparse
from pathlib import Path

from src.extraction.occupations_extractor import prepare_pad_occupations_csv


def main():
    """CLI entry point for preparing PAD occupations CSV files."""
    parser = argparse.ArgumentParser(
        description="Prepare PAD occupations CSV files from JSON extractions"
    )
    parser.add_argument(
        "--project",
        type=str,
        help="Specific project ID to process (processes all if not specified)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files",
    )

    args = parser.parse_args()

    # Get project root (assuming we're running from project root)
    project_root = Path.cwd()

    # Set up paths
    json_dir = project_root / "data" / "silver" / "occupations_skills_json"
    output_dir = project_root / "data" / "silver" / "occupation_skills_csv"

    # Verify JSON directory exists
    if not json_dir.exists():
        print(f"Error: JSON directory not found: {json_dir}")
        return 1

    # Run CSV preparation
    print(f"Preparing PAD occupations CSV files from: {json_dir}")
    if args.project:
        print(f"  Processing: {args.project}")
    else:
        print("  Processing: all projects")
    print(f"  Output directory: {output_dir}")
    print()

    try:
        results = prepare_pad_occupations_csv(
            json_dir=json_dir,
            output_dir=output_dir,
            specific_project=args.project,
            overwrite=args.overwrite,
        )

        # Print results
        print(f"\n{'='*60}")
        print("PAD Occupations CSV Preparation Results:")
        print(f"  Generated: {len(results['generated'])}")
        print(f"  Skipped: {len(results['skipped'])}")
        print(f"  Failed: {len(results['failed'])}")

        if results["generated"]:
            print("\nGenerated CSV files:")
            for csv_name in results["generated"]:
                print(f"  ✓ {csv_name}")

        if results["skipped"]:
            print(
                f"\nSkipped {len(results['skipped'])} file(s) "
                "(already exist, use --overwrite to force)"
            )

        if results["failed"]:
            print("\nFailed:")
            for project_id, error in results["failed"]:
                print(f"  ✗ {project_id}: {error}")

        return 0 if not results["failed"] else 1

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
