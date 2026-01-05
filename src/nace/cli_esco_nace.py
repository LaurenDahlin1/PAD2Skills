"""CLI for creating ESCO-NACE group mappings from RDF data."""

import argparse
from pathlib import Path

from src.config import load_config
from src.nace.esco_nace_mapper import ESCONACEMapper


def main():
    """Create ESCO-NACE group mappings from NACE RDF and ESCO occupations data."""
    parser = argparse.ArgumentParser(
        description="Create ESCO-NACE group mappings from RDF data"
    )
    parser.add_argument(
        "--nace-rdf",
        type=Path,
        help="Path to NACE RDF file (default: from config)",
    )
    parser.add_argument(
        "--esco-occupations",
        type=Path,
        help="Path to ESCO occupations CSV file (default: from config)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for CSV files (default: data/silver/esco_nace_csv)",
    )

    args = parser.parse_args()

    # Load config
    config = load_config()
    project_root = Path(config["paths"]["project_root"])

    # Set defaults from config if not provided
    nace_rdf_path = args.nace_rdf or (
        project_root / "data" / "bronze" / "nace" / "NACE_Rev.2.1.rdf"
    )
    esco_occupations_path = args.esco_occupations or (
        project_root / "data" / "bronze" / "esco" / "occupations_en.csv"
    )
    output_dir = args.output_dir or (project_root / "data" / "silver" / "esco_nace_csv")

    # Validate input files
    if not nace_rdf_path.exists():
        print(f"Error: NACE RDF file not found: {nace_rdf_path}")
        return 1

    if not esco_occupations_path.exists():
        print(f"Error: ESCO occupations file not found: {esco_occupations_path}")
        return 1

    print("=" * 80)
    print("ESCO-NACE Mapper")
    print("=" * 80)
    print(f"NACE RDF file: {nace_rdf_path}")
    print(f"ESCO occupations file: {esco_occupations_path}")
    print(f"Output directory: {output_dir}")
    print()

    # Create mapper and run
    mapper = ESCONACEMapper(nace_rdf_path, esco_occupations_path)
    main_output, inspect_output = mapper.run(output_dir)

    print()
    print("=" * 80)
    print("✓ Complete!")
    print("=" * 80)
    print(f"Main output: {main_output}")
    print(f"Inspection output: {inspect_output}")

    return 0


if __name__ == "__main__":
    exit(main())
