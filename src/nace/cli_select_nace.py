"""CLI for selecting best NACE group for each ESCO occupation."""

import argparse
from pathlib import Path

from src.config import load_config
from src.nace.nace_selector import NACESelector


def main():
    """Select best NACE group for each ESCO occupation using semantic similarity."""
    parser = argparse.ArgumentParser(
        description="Select best NACE group for ESCO occupations"
    )
    parser.add_argument(
        "--project-id",
        type=str,
        required=True,
        help="Project ID (e.g., P075941)",
    )
    parser.add_argument(
        "--unique-esco",
        type=Path,
        help="Path to unique ESCO matches CSV (default: data/silver/unique_esco_csv/{project_id}_unique_matched.csv)",
    )
    parser.add_argument(
        "--esco-nace-groups",
        type=Path,
        help="Path to ESCO-NACE groups CSV (default: data/silver/esco_nace_csv/esco_nace_groups.csv)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for results (default: data/silver/unique_esco_nace_csv)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="intfloat/e5-small-v2",
        help="Sentence transformer model name (default: intfloat/e5-small-v2)",
    )

    args = parser.parse_args()

    # Load config
    config = load_config()
    project_root = Path(config["paths"]["project_root"])

    # Set defaults from config if not provided
    unique_esco_path = args.unique_esco or (
        project_root
        / "data"
        / "silver"
        / "unique_esco_csv"
        / f"{args.project_id}_unique_matched.csv"
    )
    esco_nace_groups_path = args.esco_nace_groups or (
        project_root / "data" / "silver" / "esco_nace_csv" / "esco_nace_groups.csv"
    )
    output_dir = args.output_dir or (
        project_root / "data" / "silver" / "unique_esco_nace_csv"
    )

    # Validate input files
    if not unique_esco_path.exists():
        print(f"Error: Unique ESCO file not found: {unique_esco_path}")
        print("\nMake sure to run the ESCO selection step first:")
        print(f"  python -m src.matching.cli_select_esco --project-id {args.project_id}")
        return 1

    if not esco_nace_groups_path.exists():
        print(f"Error: ESCO-NACE groups file not found: {esco_nace_groups_path}")
        print("\nMake sure to run the ESCO-NACE mapper first:")
        print("  python -m src.nace.cli_esco_nace")
        return 1

    print("=" * 80)
    print("NACE Group Selector")
    print("=" * 80)
    print(f"Project ID: {args.project_id}")
    print(f"Unique ESCO file: {unique_esco_path}")
    print(f"ESCO-NACE groups file: {esco_nace_groups_path}")
    print(f"Output directory: {output_dir}")
    print(f"Model: {args.model}")
    print()

    # Create selector and run
    selector = NACESelector(
        unique_esco_path=unique_esco_path,
        esco_nace_groups_path=esco_nace_groups_path,
        model_name=args.model,
    )
    output_file = selector.run(output_dir, args.project_id)

    print()
    print("=" * 80)
    print("✓ Complete!")
    print("=" * 80)
    print(f"Output file: {output_file}")

    return 0


if __name__ == "__main__":
    exit(main())
