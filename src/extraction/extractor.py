"""Extract document sections and abbreviations from PAD markdown files using OpenAI API."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from openai import OpenAI


class DocumentExtractor:
    """Extract structured information from PAD documents using OpenAI API."""

    # Prompt IDs for custom GPTs
    SECTIONS_PROMPT_ID = "pmpt_6950b4992fcc8194b89fc2d87be08bf8088afcd3c3f3a4d7"
    SECTIONS_PROMPT_VERSION = "6"
    ABBREVIATIONS_PROMPT_ID = "pmpt_69574fe1ff748195b16eca5fcc20d75202a70098695be261"
    ABBREVIATIONS_PROMPT_VERSION = "2"

    def __init__(self):
        """Initialize the document extractor with OpenAI client."""
        self.client = OpenAI()

    def extract_sections(self, markdown_path: Path, project_id: str) -> dict:
        """
        Extract document sections from a PAD markdown file.

        Args:
            markdown_path: Path to markdown file
            project_id: Project ID (e.g., "P075941")

        Returns:
            Dictionary with sections data

        Raises:
            FileNotFoundError: If markdown doesn't exist
            Exception: If extraction fails
        """
        if not markdown_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {markdown_path}")

        # Read markdown content
        markdown_content = markdown_path.read_text(encoding="utf-8")

        # Prepare input with project ID
        input_message = f"Project ID: {project_id}\n\n{markdown_content}"

        # Call custom GPT
        response = self.client.responses.create(
            prompt={
                "id": self.SECTIONS_PROMPT_ID,
                "version": self.SECTIONS_PROMPT_VERSION,
            },
            input=[{"role": "user", "content": input_message}],
            reasoning={"summary": None},
            store=True,
            include=[
                "reasoning.encrypted_content",
                "web_search_call.action.sources",
            ],
        )

        # Extract text from response
        result = None
        for item in response.output:
            if hasattr(item, "content") and hasattr(item, "role"):
                result = item.content[0].text
                break

        if result is None:
            raise ValueError("No valid response received from API")

        # Parse JSON result
        return json.loads(result)

    def extract_abbreviations(self, markdown_path: Path, project_id: str) -> str:
        """
        Extract abbreviations table from a PAD markdown file.

        Args:
            markdown_path: Path to markdown file
            project_id: Project ID (e.g., "P075941")

        Returns:
            Markdown table with abbreviations

        Raises:
            FileNotFoundError: If markdown doesn't exist
            Exception: If extraction fails
        """
        if not markdown_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {markdown_path}")

        # Read markdown content
        markdown_content = markdown_path.read_text(encoding="utf-8")

        # Extract text up to first table (where abbreviations usually end)
        match = re.search(r"\btable\b", markdown_content, re.IGNORECASE)
        if match:
            abbreviations_text = markdown_content[: match.start()].strip()
        else:
            # If no table found, use full content
            abbreviations_text = markdown_content

        # Call custom GPT
        response = self.client.responses.create(
            prompt={
                "id": self.ABBREVIATIONS_PROMPT_ID,
                "version": self.ABBREVIATIONS_PROMPT_VERSION,
            },
            input=[{"role": "user", "content": abbreviations_text}],
            reasoning={"summary": None},
            store=True,
            include=[
                "reasoning.encrypted_content",
                "web_search_call.action.sources",
            ],
        )

        # Extract markdown table from response
        result = None
        for item in response.output:
            if hasattr(item, "content") and hasattr(item, "role"):
                result = item.content[0].text
                break

        if result is None:
            raise ValueError("No valid response received from API")

        return result


def extract_all_sections(
    markdown_dir: Path,
    output_dir: Path,
    specific_file: Optional[str] = None,
    overwrite: bool = False,
) -> Dict[str, List]:
    """
    Extract document sections from markdown file(s).

    Args:
        markdown_dir: Directory containing markdown files
        output_dir: Directory to save JSON section files
        specific_file: Specific markdown filename to process (None = process all)
        overwrite: Whether to overwrite existing output files

    Returns:
        Dictionary with extraction results:
            - extracted: List of successfully processed filenames
            - skipped: List of skipped filenames (already exists)
            - failed: List of tuples (filename, error_message)
    """
    # Initialize extractor
    extractor = DocumentExtractor()

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get list of markdown files to process
    if specific_file:
        target_file = markdown_dir / specific_file
        files_to_process = [target_file] if target_file.exists() else []
    else:
        files_to_process = list(markdown_dir.glob("*.md"))

    # Track results
    results = {"extracted": [], "skipped": [], "failed": []}

    # Process each markdown file
    for md_file in files_to_process:
        # Extract project ID from filename (e.g., "P075941.md" -> "P075941")
        project_id = md_file.stem

        output_file = output_dir / f"{project_id}_sections.json"

        # Check if output already exists
        if output_file.exists() and not overwrite:
            results["skipped"].append(md_file.name)
            continue

        try:
            # Extract sections
            sections_data = extractor.extract_sections(md_file, project_id)

            # Save sections JSON
            output_file.write_text(
                json.dumps(sections_data, indent=2), encoding="utf-8"
            )
            results["extracted"].append(md_file.name)

        except Exception as e:
            results["failed"].append((md_file.name, str(e)))

    return results


def extract_all_abbreviations(
    markdown_dir: Path,
    output_dir: Path,
    specific_file: Optional[str] = None,
    overwrite: bool = False,
) -> Dict[str, List]:
    """
    Extract abbreviations from markdown file(s).

    Args:
        markdown_dir: Directory containing markdown files
        output_dir: Directory to save abbreviation markdown files
        specific_file: Specific markdown filename to process (None = process all)
        overwrite: Whether to overwrite existing output files

    Returns:
        Dictionary with extraction results:
            - extracted: List of successfully processed filenames
            - skipped: List of skipped filenames (already exists)
            - failed: List of tuples (filename, error_message)
    """
    # Initialize extractor
    extractor = DocumentExtractor()

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get list of markdown files to process
    if specific_file:
        target_file = markdown_dir / specific_file
        files_to_process = [target_file] if target_file.exists() else []
    else:
        files_to_process = list(markdown_dir.glob("*.md"))

    # Track results
    results = {"extracted": [], "skipped": [], "failed": []}

    # Process each markdown file
    for md_file in files_to_process:
        # Extract project ID from filename (e.g., "P075941.md" -> "P075941")
        project_id = md_file.stem

        output_file = output_dir / f"{project_id}_abbr.md"

        # Check if output already exists
        if output_file.exists() and not overwrite:
            results["skipped"].append(md_file.name)
            continue

        try:
            # Extract abbreviations
            abbr_table = extractor.extract_abbreviations(md_file, project_id)

            # Save abbreviations markdown
            output_file.write_text(abbr_table, encoding="utf-8")
            results["extracted"].append(md_file.name)

        except Exception as e:
            results["failed"].append((md_file.name, str(e)))

    return results


def to_snake_case(text: str) -> str:
    """Convert text to lower snake case."""
    # Replace spaces and special chars with underscores
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", "_", text)
    return text.lower()


def normalize_whitespace(text: str) -> str:
    """Normalize multiple spaces to single space."""
    return re.sub(r"\s+", " ", text)


def find_header_in_markdown(markdown: str, header_text: str) -> int:
    """
    Find header in markdown, handling whitespace differences.

    Args:
        markdown: Full markdown content
        header_text: Header text to find

    Returns:
        Position of header in markdown, or -1 if not found
    """
    # Try exact match first
    pos = markdown.find(header_text)
    if pos != -1:
        return pos

    # Try with normalized whitespace
    normalized_header = normalize_whitespace(header_text)

    # Search using regex to match any amount of whitespace
    pattern = re.escape(normalized_header).replace(r"\ ", r"\s+")
    match = re.search(pattern, markdown)

    if match:
        return match.start()

    return -1


def create_chunks(
    markdown_dir: Path,
    sections_dir: Path,
    output_dir: Path,
    specific_file: Optional[str] = None,
    overwrite: bool = False,
) -> Dict[str, List]:
    """
    Split markdown files into section chunks based on sections JSON.

    Args:
        markdown_dir: Directory containing markdown files (with _1 suffix)
        sections_dir: Directory containing sections JSON files
        output_dir: Directory to save chunked markdown files
        specific_file: Specific markdown filename to process (None = process all)
        overwrite: Whether to overwrite existing output files

    Returns:
        Dictionary with chunking results:
            - chunked: List of successfully processed project IDs
            - skipped: List of skipped project IDs (no sections or already exists)
            - failed: List of tuples (project_id, error_message)
    """
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get list of markdown files to process
    if specific_file:
        target_file = markdown_dir / specific_file
        files_to_process = [target_file] if target_file.exists() else []
    else:
        files_to_process = list(markdown_dir.glob("*_1.md"))

    # Track results
    results = {"chunked": [], "skipped": [], "failed": []}

    # Process each markdown file
    for md_file in files_to_process:
        # Extract project ID from filename (e.g., "P075941_1.md" -> "P075941")
        project_id = md_file.stem.replace("_1", "")

        sections_file = sections_dir / f"{project_id}_1_sections.json"

        # Check if sections file exists
        if not sections_file.exists():
            results["skipped"].append(project_id)
            continue

        try:
            # Load sections JSON
            with open(sections_file, "r", encoding="utf-8") as f:
                sections_data = json.load(f)

            sections = sections_data["sections"]

            # Read markdown content
            markdown_content = md_file.read_text(encoding="utf-8")

            # Split markdown by sections
            chunks_created = 0
            for i, section in enumerate(sections):
                header_text = section["header_text"]
                section_id = section["section_id"]
                section_title = section["section_title"]

                # Find the start position of this section
                start_pos = find_header_in_markdown(markdown_content, header_text)

                if start_pos == -1:
                    # Skip sections that can't be found
                    continue

                # Find the end position (start of next section, or end of document)
                if i < len(sections) - 1:
                    next_header = sections[i + 1]["header_text"]
                    end_pos = find_header_in_markdown(
                        markdown_content[start_pos + len(header_text) :], next_header
                    )
                    if end_pos == -1:
                        end_pos = len(markdown_content)
                    else:
                        end_pos = start_pos + len(header_text) + end_pos
                else:
                    end_pos = len(markdown_content)

                # Extract the section content
                section_content = markdown_content[start_pos:end_pos].rstrip()

                # Generate filename (without _1 suffix)
                snake_title = to_snake_case(section_title)
                filename = f"{project_id}_{section_id}_{snake_title}.md"
                chunk_file = output_dir / filename

                # Check if chunk already exists
                if chunk_file.exists() and not overwrite:
                    continue

                # Save the chunk
                chunk_file.write_text(section_content, encoding="utf-8")
                chunks_created += 1

            if chunks_created > 0:
                results["chunked"].append(project_id)
            else:
                results["skipped"].append(project_id)

        except Exception as e:
            results["failed"].append((project_id, str(e)))

    return results
