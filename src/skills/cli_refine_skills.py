"""CLI for refining ESCO skills by evaluating relevance to PAD projects."""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from src.config import load_config
from src.skills.skills_refiner import SkillsRefiner


def main():
    """Refine ESCO skills by evaluating relevance using OpenAI API."""
    parser = argparse.ArgumentParser(
        description="Refine ESCO skills by evaluating relevance to PAD project context"
    )
    parser.add_argument(
        "--project-id",
        type=str,
        required=True,
        help="Project ID (e.g., P075941)",
    )
    parser.add_argument(
        "--unique-esco-nace",
        type=Path,
        help="Path to unique ESCO with NACE codes CSV (default: data/silver/unique_esco_nace_csv/{project_id}_unique_matched_with_nace.csv)",
    )
    parser.add_argument(
        "--esco-skills",
        type=Path,
        help="Path to ESCO skills relations CSV (default: data/bronze/esco/occupationSkillRelations_en.csv)",
    )
    parser.add_argument(
        "--pad-summary",
        type=Path,
        help="Path to PAD summary text file (default: data/silver/pad_summaries/{project_id}_summary.txt)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for results (default: data/silver/esco_nace_w_skills_csv)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=3,
        help="Number of occupations per API chunk (default: 3)",
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
    unique_esco_nace_path = args.unique_esco_nace or (
        project_root
        / "data"
        / "silver"
        / "unique_esco_nace_csv"
        / f"{args.project_id}_unique_matched_with_nace.csv"
    )
    esco_skills_path = args.esco_skills or (
        project_root / "data" / "bronze" / "esco" / "occupationSkillRelations_en.csv"
    )
    pad_summary_path = args.pad_summary or (
        project_root
        / "data"
        / "silver"
        / "pad_summaries"
        / f"{args.project_id}_summary.txt"
    )
    output_dir = args.output_dir or (
        project_root / "data" / "silver" / "esco_nace_w_skills_csv"
    )

    # Validate input files
    if not unique_esco_nace_path.exists():
        print(f"Error: Unique ESCO with NACE file not found: {unique_esco_nace_path}")
        print("\nMake sure to run the NACE selection step first:")
        print(
            f"  uv run python -m src.nace.cli_select_nace --project-id {args.project_id}"
        )
        return 1

    if not esco_skills_path.exists():
        print(f"Error: ESCO skills file not found: {esco_skills_path}")
        print("\nMake sure ESCO skills data is available in data/bronze/esco/")
        return 1

    if not pad_summary_path.exists():
        print(f"Error: PAD summary file not found: {pad_summary_path}")
        print("\nMake sure to run the summary generation step first:")
        print(
            f"  uv run python -m src.extraction.cli_summary --project {args.project_id}"
        )
        return 1

    # Load OpenAI API key
    env_path = project_root / ".env"
    if not env_path.exists():
        print(f"Error: .env file not found at {env_path}")
        print("Please copy .env.example to .env and add your OpenAI API key.")
        return 1

    load_dotenv(env_path, override=True)
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not openai_api_key:
        print("Error: OPENAI_API_KEY not found in .env file")
        return 1

    print("=" * 80)
    print("ESCO Skills Refiner")
    print("=" * 80)
    print(f"Project ID: {args.project_id}")
    print(f"Unique ESCO with NACE file: {unique_esco_nace_path}")
    print(f"ESCO skills file: {esco_skills_path}")
    print(f"PAD summary file: {pad_summary_path}")
    print(f"Output directory: {output_dir}")
    print(f"Chunk size: {args.chunk_size}")
    print()

    # Create refiner and run
    refiner = SkillsRefiner(
        unique_esco_nace_file=unique_esco_nace_path,
        esco_skills_file=esco_skills_path,
        pad_summary_file=pad_summary_path,
        project_id=args.project_id,
        openai_api_key=openai_api_key,
        chunk_size=args.chunk_size,
    )
    output_file = refiner.run(output_dir, overwrite=args.overwrite)

    print()
    print("=" * 80)
    print("✓ Complete!")
    print("=" * 80)
    print(f"Output file: {output_file}")

    return 0


if __name__ == "__main__":
    exit(main())
