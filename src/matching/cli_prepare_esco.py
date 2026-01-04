"""CLI for ESCO data preparation."""

import argparse
from pathlib import Path

from src.config import load_config
from src.matching.esco_prepare import prepare_esco_data


def main():
    """Prepare ESCO occupations data with embeddings."""
    parser = argparse.ArgumentParser(
        description="Prepare ESCO occupations data with embeddings for matching"
    )
    parser.add_argument(
        "--overwrite-embeddings",
        action="store_true",
        help="Regenerate embeddings even if cached version exists",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="intfloat/e5-small-v2",
        help="Sentence transformer model name (default: intfloat/e5-small-v2)",
    )

    args = parser.parse_args()

    # Load config and setup paths
    config = load_config()
    project_root = Path(__file__).parent.parent.parent

    esco_dir = project_root / "data" / "bronze" / "esco"
    output_csv = project_root / "data" / "silver" / "esco_occupations_prepared.csv"
    embeddings_file = project_root / "data" / "silver" / "embeddings" / "esco_embeddings.npy"

    # Prepare ESCO data
    print("=" * 80)
    print("ESCO Data Preparation")
    print("=" * 80)
    print(f"ESCO directory: {esco_dir}")
    print(f"Output CSV: {output_csv}")
    print(f"Embeddings file: {embeddings_file}")
    print(f"Model: {args.model}")
    print(f"Overwrite embeddings: {args.overwrite_embeddings}")
    print("=" * 80)
    print()

    try:
        df, embeddings = prepare_esco_data(
            esco_dir=esco_dir,
            output_csv=output_csv,
            embeddings_file=embeddings_file,
            overwrite_embeddings=args.overwrite_embeddings,
            model_name=args.model,
        )

        print()
        print("=" * 80)
        print("✓ ESCO data preparation complete")
        print(f"  Prepared occupations: {len(df):,}")
        print(f"  Embedding dimension: {embeddings.shape[1]}")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ Error during ESCO preparation: {e}")
        raise


if __name__ == "__main__":
    main()
