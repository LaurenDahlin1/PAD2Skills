"""CLI for extracting abbreviations from PAD markdown files."""

import argparse
from pathlib import Path

from src.config import load_config
from src.extraction.extractor import extract_all_abbreviations


def main():
    """CLI entry point for extracting abbreviations."""
    parser = argparse.ArgumentParser(
        description="Extract abbreviations from PAD markdown files using OpenAI API"
    )
    parser.add_argument(
        "--markdown",
        type=str,
        help="Specific markdown filename to process (processes all if not specified)",
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

    # Load configuration
    config = load_config(args.config)

    # Get project root (assuming we're running from project root)
    project_root = Path.cwd()

    # Set up paths
    markdown_dir = project_root / config.paths.markdown
    output_dir = project_root / "data" / "silver" / "abbreviations_md"

    # Verify markdown directory exists
    if not markdown_dir.exists():
        print(f"Error: Markdown directory not found: {markdown_dir}")
        return 1

    # Run extraction
    print(f"Extracting abbreviations from: {markdown_dir}")
    if args.markdown:
        print(f"  Processing: {args.markdown}")
    else:
        print("  Processing: all markdown files")
    print(f"  Output directory: {output_dir}")
    print()

    results = extract_all_abbreviations(
        markdown_dir=markdown_dir,
        output_dir=output_dir,
        specific_file=args.markdown,
        overwrite=args.overwrite,
    )

    # Print results
    print(f"\n{'='*60}")
    print("Extraction Summary:")
    print(f"  Extracted: {len(results['extracted'])}")
    print(f"  Skipped: {len(results['skipped'])}")
    print(f"  Failed: {len(results['failed'])}")

    if results["extracted"]:
        print("\nExtracted files:")
        for filename in results["extracted"]:
            print(f"  ✓ {filename}")

    if results["skipped"]:
        print("\nSkipped (already exists, use --overwrite to force):")
        for filename in results["skipped"]:
            print(f"  ○ {filename}")

    if results["failed"]:
        print("\nFailed:")
        for filename, error in results["failed"]:
            print(f"  ✗ {filename}: {error}")

    return 0 if not results["failed"] else 1


if __name__ == "__main__":
    exit(main())
