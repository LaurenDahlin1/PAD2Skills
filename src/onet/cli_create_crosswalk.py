"""CLI for creating ESCO-ONET crosswalk with job zones."""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from src.config import load_config
from src.onet.onet_crosswalk import OnetCrosswalkCreator


def main():
    """Create ESCO-ONET crosswalk with job zones."""
    parser = argparse.ArgumentParser(
        description="Create ESCO-ONET crosswalk with job zones, filling missing values with LLM"
    )
    parser.add_argument(
        "--crosswalk-file",
        type=Path,
        help="Path to ESCO-ONET crosswalk CSV (default: data/bronze/onet/esco_onet_crosswalk.csv)",
    )
    parser.add_argument(
        "--job-zones-file",
        type=Path,
        help="Path to O*NET job zones file (default: data/bronze/onet/onet_job_zones.txt)",
    )
    parser.add_argument(
        "--esco-prepared-file",
        type=Path,
        help="Path to prepared ESCO occupations CSV (default: data/silver/clean_esco/esco_occupations_prepared.csv)",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        help="Path to save output CSV (default: data/silver/clean_esco/esco_onet_job_zones.csv)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=50,
        help="Number of occupations per API call for missing values (default: 50)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output file",
    )

    args = parser.parse_args()

    # Load config
    config = load_config()
    project_root = Path(config["paths"]["project_root"])

    # Set defaults from config if not provided
    crosswalk_file = args.crosswalk_file or (
        project_root / "data" / "bronze" / "onet" / "esco_onet_crosswalk.csv"
    )
    job_zones_file = args.job_zones_file or (
        project_root / "data" / "bronze" / "onet" / "onet_job_zones.txt"
    )
    esco_prepared_file = args.esco_prepared_file or (
        project_root
        / "data"
        / "silver"
        / "clean_esco"
        / "esco_occupations_prepared.csv"
    )
    output_file = args.output_file or (
        project_root / "data" / "silver" / "clean_esco" / "esco_onet_job_zones.csv"
    )

    # Validate input files
    if not crosswalk_file.exists():
        print(f"Error: ESCO-ONET crosswalk file not found: {crosswalk_file}")
        print("\nMake sure O*NET crosswalk data is available in data/bronze/onet/")
        return 1

    if not job_zones_file.exists():
        print(f"Error: O*NET job zones file not found: {job_zones_file}")
        print("\nMake sure O*NET job zones data is available in data/bronze/onet/")
        return 1

    if not esco_prepared_file.exists():
        print(f"Error: Prepared ESCO file not found: {esco_prepared_file}")
        print("\nMake sure to run the ESCO preparation step first:")
        print("  uv run python -m src.matching.cli_prepare_esco")
        return 1

    # Load environment variables
    env_path = project_root / ".env"
    if not env_path.exists():
        print(f"Error: .env file not found at {env_path}")
        print("Please copy .env.example to .env and add your OpenAI API key.")
        return 1

    load_dotenv(env_path, override=True)
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("Error: Missing required environment variable: OPENAI_API_KEY")
        return 1

    # Initialize OpenAI client
    client = OpenAI()

    print("=" * 80)
    print("Creating ESCO-ONET Crosswalk with Job Zones")
    print("=" * 80)
    print(f"Crosswalk file: {crosswalk_file}")
    print(f"Job zones file: {job_zones_file}")
    print(f"ESCO prepared file: {esco_prepared_file}")
    print(f"Output file: {output_file}")
    print(f"Chunk size: {args.chunk_size}")
    print(f"Overwrite: {args.overwrite}")
    print("=" * 80)
    print()

    # Create crosswalk
    creator = OnetCrosswalkCreator(client)

    try:
        output_path = creator.create_crosswalk(
            crosswalk_file=crosswalk_file,
            job_zones_file=job_zones_file,
            esco_prepared_file=esco_prepared_file,
            output_file=output_file,
            chunk_size=args.chunk_size,
            overwrite=args.overwrite,
        )

        print("\n" + "=" * 80)
        print("✓ Crosswalk creation complete!")
        print(f"  Output: {output_path}")
        print("=" * 80)

        return 0

    except Exception as e:
        print(f"\n✗ Error creating crosswalk: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
