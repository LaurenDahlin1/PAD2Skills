"""CLI for PAD to ESCO matching."""

import argparse
from pathlib import Path

from src.config import load_config
from src.matching.pad_matcher import match_pad_to_esco


def main():
    """Match PAD occupations to ESCO taxonomy."""
    parser = argparse.ArgumentParser(
        description="Match PAD occupations to ESCO taxonomy using embeddings"
    )
    parser.add_argument("project_id", type=str, help="Project ID (e.g., P075941)")
    parser.add_argument(
        "--model",
        type=str,
        default="intfloat/e5-small-v2",
        help="Sentence transformer model name (default: intfloat/e5-small-v2)",
    )
    parser.add_argument(
        "--top-k", type=int, default=20, help="Number of top matches to retrieve (default: 20)"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=75,
        help="Number of records per JSON file (default: 75)",
    )
    parser.add_argument(
        "--no-diagnostics",
        action="store_true",
        help="Skip saving diagnostic CSV file",
    )

    args = parser.parse_args()

    # Load config and setup paths
    config = load_config()
    project_root = Path(__file__).parent.parent.parent

    pad_occupations_dir = project_root / "data" / "silver" / "occupations_skills_json"
    esco_csv = project_root / "data" / "silver" / "esco_occupations_prepared.csv"
    esco_embeddings = project_root / "data" / "silver" / "embeddings" / "esco_embeddings.npy"
    output_dir = project_root / "data" / "silver"

    # Match PAD to ESCO
    print("=" * 80)
    print("PAD to ESCO Matching")
    print("=" * 80)
    print(f"Project ID: {args.project_id}")
    print(f"PAD occupations directory: {pad_occupations_dir}")
    print(f"ESCO CSV: {esco_csv}")
    print(f"ESCO embeddings: {esco_embeddings}")
    print(f"Output directory: {output_dir}")
    print(f"Model: {args.model}")
    print(f"Top K matches: {args.top_k}")
    print(f"JSON chunk size: {args.chunk_size}")
    print(f"Save diagnostics: {not args.no_diagnostics}")
    print("=" * 80)
    print()

    try:
        results_df = match_pad_to_esco(
            pad_occupations_dir=pad_occupations_dir,
            project_id=args.project_id,
            esco_csv=esco_csv,
            esco_embeddings=esco_embeddings,
            output_dir=output_dir,
            model_name=args.model,
            top_k=args.top_k,
            chunk_size=args.chunk_size,
            save_diagnostics=not args.no_diagnostics,
        )

        print()
        print("=" * 80)
        print("✓ PAD to ESCO matching complete")
        print(f"  Matched {len(results_df):,} PAD occupations")
        print(f"  Top {args.top_k} ESCO matches per occupation")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ Error during matching: {e}")
        raise


if __name__ == "__main__":
    main()
