"""CLI interface for PDF to Markdown conversion."""

import argparse
import sys
from pathlib import Path

from src.config import load_config
from src.pdf_conversion.converter import convert_pdfs


def main():
    """Run PDF to Markdown conversion from command line."""
    parser = argparse.ArgumentParser(
        description="Convert World Bank PAD PDFs to Markdown using docling"
    )
    parser.add_argument(
        "--pdf",
        type=str,
        help="Specific PDF filename to convert (default: convert all PDFs)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing markdown files",
    )
    parser.add_argument(
        "--no-accurate-tables",
        action="store_true",
        help="Disable TableFormer ACCURATE mode for faster but less accurate table extraction",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to config file (default: configs/base.yaml)",
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Get project root and paths
    project_root = Path(__file__).parent.parent.parent
    pdf_dir = project_root / config.paths.raw_pdfs
    md_dir = project_root / config.paths.markdown

    # Check if PDF directory exists
    if not pdf_dir.exists():
        print(f"Error: PDF directory not found: {pdf_dir}", file=sys.stderr)
        return 1

    # Display conversion settings
    print("PDF to Markdown Conversion")
    print("=" * 60)
    print(f"PDF directory:  {pdf_dir}")
    print(f"Output directory: {md_dir}")
    print(f"Mode: {'Convert specific PDF' if args.pdf else 'Convert all PDFs'}")
    if args.pdf:
        print(f"  PDF: {args.pdf}")
    print(f"Overwrite existing: {args.overwrite}")
    print(f"Accurate tables: {not args.no_accurate_tables}")
    print("=" * 60)
    print()

    # Convert PDFs
    results = convert_pdfs(
        pdf_dir=pdf_dir,
        output_dir=md_dir,
        specific_pdf=args.pdf,
        overwrite=args.overwrite,
        accurate_tables=not args.no_accurate_tables,
    )

    # Display results
    print("\nConversion Results:")
    print("-" * 60)

    if results["converted"]:
        print(f"\n✓ Converted ({len(results['converted'])}):")
        for name in results["converted"]:
            md_file = md_dir / f"{Path(name).stem}.md"
            size_kb = md_file.stat().st_size / 1024
            print(f"  - {name} ({size_kb:.1f} KB)")

    if results["skipped"]:
        print(f"\n⊘ Skipped ({len(results['skipped'])}):")
        for name in results["skipped"]:
            print(f"  - {name} (already exists)")

    if results["failed"]:
        print(f"\n✗ Failed ({len(results['failed'])}):")
        for name, error in results["failed"]:
            print(f"  - {name}: {error}")

    print("\n" + "=" * 60)
    print(
        f"Summary: {len(results['converted'])} converted, "
        f"{len(results['skipped'])} skipped, {len(results['failed'])} failed"
    )
    print("=" * 60)

    # Return error code if any conversions failed
    return 1 if results["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
