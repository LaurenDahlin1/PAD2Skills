"""CLI for selecting best ESCO matches using OpenAI API."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from ..config import load_config
from .esco_selector import select_best_esco_matches


def main() -> int:
    """Run ESCO selection CLI."""
    parser = argparse.ArgumentParser(
        description="Select best ESCO matches for PAD occupations using OpenAI API"
    )
    parser.add_argument(
        "project_id",
        type=str,
        help="Project ID (e.g., P075941)",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        help="Directory containing esco_matching JSON files (default: data/silver/esco_matching_json/)",
    )
    parser.add_argument(
        "--output-json-dir",
        type=Path,
        help="Directory to save selection JSON files (default: data/silver/choose_esco_json/)",
    )
    parser.add_argument(
        "--output-csv-dir",
        type=Path,
        help="Directory to save combined CSV (default: data/silver/choose_esco_csv/)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files",
    )

    args = parser.parse_args()

    # Load environment variables
    project_root = Path(__file__).parents[2]
    env_path = project_root / ".env"

    if not env_path.exists():
        print(f"Error: .env file not found at {env_path}", file=sys.stderr)
        print("Please copy .env.example to .env and add your OpenAI API key.")
        return 1

    load_dotenv(env_path, override=True)

    # Get OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set in .env file", file=sys.stderr)
        return 1

    # Load config
    config = load_config()

    # Set paths
    input_dir = args.input_dir or (
        project_root / "data" / "silver" / "esco_matching_json"
    )
    output_json_dir = args.output_json_dir or (
        project_root / "data" / "silver" / "choose_esco_json"
    )
    output_csv_dir = args.output_csv_dir or (
        project_root / "data" / "silver" / "choose_esco_csv"
    )

    # PAD occupations directory
    pad_occupations_dir = (
        project_root / "data" / "silver" / "occupations_skills_json"
    )

    # Validate input files exist
    if not input_dir.exists():
        print(f"Error: Input directory not found: {input_dir}", file=sys.stderr)
        return 1

    if not pad_occupations_dir.exists():
        print(f"Error: PAD occupations directory not found: {pad_occupations_dir}", file=sys.stderr)
        return 1

    # Run selection
    print(f"Selecting best ESCO matches for project {args.project_id}...")
    print(f"  Input: {input_dir}")
    print(f"  Output JSON: {output_json_dir}")
    print(f"  Output CSV: {output_csv_dir}")
    print()

    try:
        df = select_best_esco_matches(
            input_dir=input_dir,
            project_id=args.project_id,
            pad_occupations_dir=pad_occupations_dir,
            output_json_dir=output_json_dir,
            output_csv_dir=output_csv_dir,
            overwrite=args.overwrite,
        )

        print()
        print("✓ Selection complete!")
        print(f"  Total records: {len(df):,}")
        print(
            f"  Selected ESCO matches: {df['esco_id'].notna().sum():,}"
        )
        print(
            f"  Needs manual review: {df['needs_manual_review'].sum():,}"
        )

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
