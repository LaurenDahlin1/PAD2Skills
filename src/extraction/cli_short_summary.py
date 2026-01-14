"""CLI for generating short PAD summaries from long summaries."""

import argparse
from pathlib import Path

from src.extraction.short_summarizer import generate_all_short_summaries


def main():
    """CLI entry point for generating short PAD summaries."""
    parser = argparse.ArgumentParser(
        description="Generate short summaries from long PAD summaries using OpenAI API"
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
        "--config",
        type=str,
        default="configs/base.yaml",
        help="Path to config file (default: configs/base.yaml)",
    )

    args = parser.parse_args()

    # Get project root (assuming we're running from project root)
    project_root = Path.cwd()

    # Set up paths
    summaries_dir = project_root / "data" / "silver" / "pad_summaries"
    output_dir = project_root / "data" / "silver" / "short_summary_json"

    # Verify summaries directory exists
    if not summaries_dir.exists():
        print(f"Error: Summaries directory not found: {summaries_dir}")
        return 1

    # Run short summary generation
    print(f"Generating short summaries from: {summaries_dir}")
    if args.project:
        print(f"  Processing: {args.project}")
    else:
        print("  Processing: all projects")
    print(f"  Output directory: {output_dir}")
    print()

    results = generate_all_short_summaries(
        summaries_dir=summaries_dir,
        output_dir=output_dir,
        specific_project=args.project,
        overwrite=args.overwrite,
    )

    # Print results
    print(f"\n{'=' * 60}")
    print("Short Summary Generation Results:")
    print(f"  Generated: {len(results['generated'])}")
    print(f"  Skipped: {len(results['skipped'])}")
    print(f"  Failed: {len(results['failed'])}")

    if results["generated"]:
        print("\nGenerated short summaries:")
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
