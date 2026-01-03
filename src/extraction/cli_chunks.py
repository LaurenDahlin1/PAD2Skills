"""CLI for creating chunked markdown files from document sections."""

import argparse
from pathlib import Path

from src.config import load_config
from src.extraction.extractor import create_chunks


def main():
    """CLI entry point for creating chunked markdown files."""
    parser = argparse.ArgumentParser(
        description="Create chunked markdown files from document sections"
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
    sections_dir = project_root / "data" / "silver" / "document_sections"
    output_dir = project_root / "data" / "silver" / "pads_md_chunks"

    # Verify directories exist
    if not markdown_dir.exists():
        print(f"Error: Markdown directory not found: {markdown_dir}")
        return 1

    if not sections_dir.exists():
        print(f"Error: Sections directory not found: {sections_dir}")
        print(
            "Run section extraction first: uv run python -m src.extraction.cli_sections"
        )
        return 1

    # Run chunking
    print("Creating chunked markdown files")
    print(f"  Markdown directory: {markdown_dir}")
    print(f"  Sections directory: {sections_dir}")
    if args.markdown:
        print(f"  Processing: {args.markdown}")
    else:
        print("  Processing: all markdown files")
    print(f"  Output directory: {output_dir}")
    print()

    results = create_chunks(
        markdown_dir=markdown_dir,
        sections_dir=sections_dir,
        output_dir=output_dir,
        specific_file=args.markdown,
        overwrite=args.overwrite,
    )

    # Print results
    print(f"\n{'=' * 60}")
    print("Chunking Summary:")
    print(f"  Chunked: {len(results['chunked'])}")
    print(f"  Skipped: {len(results['skipped'])}")
    print(f"  Failed: {len(results['failed'])}")

    if results["chunked"]:
        print("\nChunked projects:")
        for project_id in results["chunked"]:
            # Count chunks created for this project
            chunk_files = list(output_dir.glob(f"{project_id}_*.md"))
            print(f"  ✓ {project_id} ({len(chunk_files)} chunks)")

    if results["skipped"]:
        print("\nSkipped (no sections file or already exists):")
        for project_id in results["skipped"]:
            print(f"  ○ {project_id}")

    if results["failed"]:
        print("\nFailed:")
        for project_id, error in results["failed"]:
            print(f"  ✗ {project_id}: {error}")

    return 0 if not results["failed"] else 1


if __name__ == "__main__":
    exit(main())
