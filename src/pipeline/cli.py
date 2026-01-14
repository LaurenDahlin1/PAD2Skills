"""Command-line interface for single-project pipeline.

Usage:
    python -m src.pipeline.cli P075941
    python -m src.pipeline.cli P075941 --overwrite-all
    python -m src.pipeline.cli P075941 --ow-pdf --ow-sections
"""

import argparse
import sys
from pathlib import Path

from src.pipeline.single_project_pipeline import SingleProjectPipeline


def main():
    """Run the single-project pipeline from command line."""
    parser = argparse.ArgumentParser(
        description="Run the PAD2Skills pipeline for a single project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run pipeline for project P075941 (skip existing files)
  python -m src.pipeline.cli P075941

  # Run pipeline with all overwrites enabled
  python -m src.pipeline.cli P075941 --overwrite-all

  # Run pipeline with specific step overwrites
  python -m src.pipeline.cli P075941 --ow-pdf --ow-sections --ow-occupations

  # Run pipeline without progress output
  python -m src.pipeline.cli P075941 --no-progress

  # Use custom config file
  python -m src.pipeline.cli P075941 --config configs/custom.yaml
        """,
    )

    # Required arguments
    parser.add_argument(
        "project_id",
        type=str,
        help="Project ID to process (e.g., P075941)",
    )

    # Optional arguments
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to custom config file (default: configs/base.yaml)",
    )

    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress output",
    )

    # Global overwrite flag
    parser.add_argument(
        "--overwrite-all",
        action="store_true",
        help="Overwrite all existing files (sets all --ow-* flags to True)",
    )

    # Individual step overwrite flags
    parser.add_argument(
        "--ow-pdf",
        action="store_true",
        help="Overwrite existing PDF conversions",
    )

    parser.add_argument(
        "--ow-sections",
        action="store_true",
        help="Overwrite existing section extractions",
    )

    parser.add_argument(
        "--ow-abbr",
        action="store_true",
        help="Overwrite existing abbreviation extractions",
    )

    parser.add_argument(
        "--ow-chunks",
        action="store_true",
        help="Overwrite existing markdown chunks",
    )

    parser.add_argument(
        "--ow-long-summary",
        action="store_true",
        help="Overwrite existing long summaries",
    )

    parser.add_argument(
        "--ow-short-summary",
        action="store_true",
        help="Overwrite existing short summaries",
    )

    parser.add_argument(
        "--ow-occupations",
        action="store_true",
        help="Overwrite existing occupation extractions",
    )

    parser.add_argument(
        "--ow-occs-csv",
        action="store_true",
        help="Overwrite existing occupation CSV files",
    )

    parser.add_argument(
        "--ow-esco-prep",
        action="store_true",
        help="Overwrite existing ESCO preparation (embeddings)",
    )

    parser.add_argument(
        "--ow-esco-match",
        action="store_true",
        help="Overwrite existing ESCO matching results",
    )

    parser.add_argument(
        "--ow-esco-select",
        action="store_true",
        help="Overwrite existing ESCO selections",
    )

    parser.add_argument(
        "--ow-unique-esco",
        action="store_true",
        help="Overwrite existing unique ESCO matches",
    )

    parser.add_argument(
        "--ow-nace-prep",
        action="store_true",
        help="Overwrite existing ESCO-NACE groups",
    )

    parser.add_argument(
        "--ow-nace-select",
        action="store_true",
        help="Overwrite existing NACE selections",
    )

    parser.add_argument(
        "--ow-skills",
        action="store_true",
        help="Overwrite existing skills refinements",
    )

    parser.add_argument(
        "--ow-onet-prep",
        action="store_true",
        help="Overwrite existing ESCO-ONET crosswalk",
    )

    parser.add_argument(
        "--ow-onet-merge",
        action="store_true",
        help="Overwrite existing ONET job zone merges",
    )

    args = parser.parse_args()

    # If --overwrite-all is set, enable all overwrite flags
    if args.overwrite_all:
        ow_pdf = True
        ow_sections = True
        ow_abbr = True
        ow_chunks = True
        ow_long_summary = True
        ow_short_summary = True
        ow_occupations = True
        ow_occs_csv = True
        ow_esco_prep = True
        ow_esco_match = True
        ow_esco_select = True
        ow_unique_esco = True
        ow_nace_prep = True
        ow_nace_select = True
        ow_skills = True
        ow_onet_prep = True
        ow_onet_merge = True
    else:
        # Use individual flags
        ow_pdf = args.ow_pdf
        ow_sections = args.ow_sections
        ow_abbr = args.ow_abbr
        ow_chunks = args.ow_chunks
        ow_long_summary = args.ow_long_summary
        ow_short_summary = args.ow_short_summary
        ow_occupations = args.ow_occupations
        ow_occs_csv = args.ow_occs_csv
        ow_esco_prep = args.ow_esco_prep
        ow_esco_match = args.ow_esco_match
        ow_esco_select = args.ow_esco_select
        ow_unique_esco = args.ow_unique_esco
        ow_nace_prep = args.ow_nace_prep
        ow_nace_select = args.ow_nace_select
        ow_skills = args.ow_skills
        ow_onet_prep = args.ow_onet_prep
        ow_onet_merge = args.ow_onet_merge

    try:
        # Create pipeline instance
        pipeline = SingleProjectPipeline(
            project_id=args.project_id,
            config_path=args.config,
            print_progress=not args.no_progress,
            ow_pdf=ow_pdf,
            ow_sections=ow_sections,
            ow_abbr=ow_abbr,
            ow_chunks=ow_chunks,
            ow_long_summary=ow_long_summary,
            ow_short_summary=ow_short_summary,
            ow_occupations=ow_occupations,
            ow_occs_csv=ow_occs_csv,
            ow_esco_prep=ow_esco_prep,
            ow_esco_match=ow_esco_match,
            ow_esco_select=ow_esco_select,
            ow_unique_esco=ow_unique_esco,
            ow_nace_prep=ow_nace_prep,
            ow_nace_select=ow_nace_select,
            ow_skills=ow_skills,
            ow_onet_prep=ow_onet_prep,
            ow_onet_merge=ow_onet_merge,
        )

        # Run the pipeline
        pipeline.run()

        # Print summary
        if not args.no_progress:
            print("\n" + "=" * 80)
            print("PIPELINE SUMMARY")
            print("=" * 80)

            # Count successes and failures
            import pandas as pd

            df = pd.DataFrame(pipeline.timing_data)
            total_steps = len(df)
            failed_steps = df["error_occurred"].sum()
            success_steps = total_steps - failed_steps
            total_time = df["elapsed_minutes"].sum()

            print(f"Total steps: {total_steps}")
            print(f"Successful: {success_steps}")
            print(f"Failed: {failed_steps}")
            print(f"Total elapsed time: {total_time:.2f} minutes")

            if failed_steps > 0:
                print("\nFailed steps:")
                failed = df[df["error_occurred"] == True]
                for _, row in failed.iterrows():
                    print(f"  - {row['step_code']}: {row['step_name']}")
                    print(f"    Error: {row['error_message']}")

            print(f"\nTiming data saved to: {pipeline._get_timing_path()}")
            print("=" * 80)

        return 0

    except Exception as e:
        print(f"\n✗ Pipeline failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
