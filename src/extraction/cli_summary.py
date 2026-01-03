"""CLI for generating PAD document summaries."""

import argparse
from pathlib import Path

from src.extraction.summarizer import generate_all_summaries


def main():
    """CLI entry point for generating PAD summaries."""
    parser = argparse.ArgumentParser(
        description="Generate summaries of PAD documents using OpenAI API"
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
    parser.add_argument(
        "--num-chunks",
        type=int,
        default=4,
        help="Number of chunks to load per project (default: 4)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/base.yaml",
        help="Path to config file (default: configs/base.yaml)",
    )

    args = parser.parse_args()

    # Get project root (assuming we're running from project root)
    project_root = Path.cwd()

    # Set up paths
    chunks_dir = project_root / "data" / "silver" / "pads_md_chunks"
    abbr_dir = project_root / "data" / "silver" / "abbreviations_md"
    output_dir = project_root / "data" / "silver" / "pad_summaries"

    # Verify chunks directory exists
    if not chunks_dir.exists():
        print(f"Error: Chunks directory not found: {chunks_dir}")
        return 1

    # Run summary generation
    print(f"Generating PAD summaries from: {chunks_dir}")
    if args.project:
        print(f"  Processing: {args.project}")
    else:
        print("  Processing: all projects")
    print(f"  Abbreviations directory: {abbr_dir}")
    print(f"  Output directory: {output_dir}")
    print(f"  Number of chunks: {args.num_chunks}")
    print()

    results = generate_all_summaries(
        chunks_dir=chunks_dir,
        output_dir=output_dir,
        abbr_dir=abbr_dir,
        specific_project=args.project,
        num_chunks=args.num_chunks,
        overwrite=args.overwrite,
    )

    # Print results
    print(f"\n{'='*60}")
    print("Summary Generation Results:")
    print(f"  Generated: {len(results['generated'])}")
    print(f"  Skipped: {len(results['skipped'])}")
    print(f"  Failed: {len(results['failed'])}")

    if results["generated"]:
        print("\nGenerated summaries:")
        for project_id in results["generated"]:
            print(f"  ✓ {project_id}")

    if results["skipped"]:
        print("\nSkipped (already exists, use --overwrite to force):")
        for project_id in results["skipped"]:
            print(f"  ○ {project_id}")

    if results["failed"]:
        print("\nFailed:")
        for project_id, error in results["failed"]:
            print(f"  ✗ {project_id}: {error}")

    return 0 if not results["failed"] else 1


if __name__ == "__main__":
    exit(main())
