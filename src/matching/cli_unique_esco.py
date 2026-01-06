"""CLI for creating unique ESCO matches from selection results."""

import argparse
from pathlib import Path

from ..config import load_config
from .unique_esco import create_unique_esco_matches


def main() -> int:
    """Run unique ESCO matches CLI."""
    parser = argparse.ArgumentParser(
        description="Create unique ESCO matches file from selection results"
    )
    parser.add_argument(
        "project_id",
        type=str,
        help="Project ID (e.g., P075941)",
    )
    parser.add_argument(
        "--selections-dir",
        type=Path,
        help="Directory containing _esco_selections.csv files (default: data/silver/choose_esco_csv/)",
    )
    parser.add_argument(
        "--esco-dir",
        type=Path,
        help="Directory containing ESCO data (default: data/bronze/esco/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to save unique matches CSV (default: data/silver/unique_esco_csv/)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file (default: configs/base.yaml)",
    )

    args = parser.parse_args()

    # Load configuration
    project_root = Path(__file__).parents[2]
    config_path = args.config or project_root / "configs" / "base.yaml"
    _ = load_config(config_path)  # Load config to validate it exists

    # Set paths
    selections_dir = (
        args.selections_dir or project_root / "data" / "silver" / "choose_esco_csv"
    )
    esco_dir = args.esco_dir or project_root / "data" / "bronze" / "esco"
    output_dir = args.output_dir or project_root / "data" / "silver" / "unique_esco_csv"

    # Construct file paths
    selections_csv_path = selections_dir / f"{args.project_id}_esco_selections.csv"
    esco_occupations_path = esco_dir / "occupations_en.csv"
    sections_json_path = (
        project_root
        / "data"
        / "silver"
        / "document_sections"
        / f"{args.project_id}_1_sections.json"
    )
    output_path = output_dir / f"{args.project_id}_unique_matched.csv"

    # Check if selections file exists
    if not selections_csv_path.exists():
        print(f"✗ Error: Selections file not found: {selections_csv_path}")
        print(
            f"  Run ESCO selection first: uv run python -m src.matching.cli_select_esco {args.project_id}"
        )
        return 1

    # Check if ESCO file exists
    if not esco_occupations_path.exists():
        print(f"✗ Error: ESCO occupations file not found: {esco_occupations_path}")
        return 1

    # Check if sections file exists
    if not sections_json_path.exists():
        print(f"⚠ Warning: Sections file not found: {sections_json_path}")
        print("  Section names will be empty in output")

    # Check if output already exists
    if output_path.exists():
        print(f"✓ Unique matches file already exists: {output_path}")
        print("  To regenerate, delete the file and run again")
        return 0

    print(f"\n{'=' * 70}")
    print(f"Creating Unique ESCO Matches for Project: {args.project_id}")
    print(f"{'=' * 70}\n")

    try:
        # Create unique matches
        create_unique_esco_matches(
            project_id=args.project_id,
            selections_csv_path=selections_csv_path,
            esco_occupations_path=esco_occupations_path,
            sections_json_path=sections_json_path,
            output_path=output_path,
        )

        print(f"\n{'=' * 70}")
        print("✓ Successfully created unique ESCO matches")
        print(f"{'=' * 70}\n")
        return 0

    except Exception as e:
        print(f"\n✗ Error creating unique matches: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
