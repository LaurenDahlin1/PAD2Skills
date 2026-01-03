"""Generate summaries of PAD documents using OpenAI API."""

from pathlib import Path
from typing import Dict, List, Optional

from openai import OpenAI


class PADSummarizer:
    """Generate concise summaries of PAD documents."""

    # Prompt ID for custom GPT
    SUMMARY_PROMPT_ID = "pmpt_6958a3a9da908190b195df7be708793008cf7519acf777ba"
    SUMMARY_PROMPT_VERSION = "3"

    def __init__(self):
        """Initialize the PAD summarizer with OpenAI client."""
        self.client = OpenAI()

    def generate_summary(
        self,
        project_id: str,
        chunks_dir: Path,
        abbr_dir: Optional[Path] = None,
        num_chunks: int = 4,
    ) -> str:
        """
        Generate a summary of a PAD document.

        Args:
            project_id: Project ID (e.g., "P075941")
            chunks_dir: Directory containing markdown chunk files
            abbr_dir: Directory containing abbreviation files (optional)
            num_chunks: Number of chunks to load (default: 4)

        Returns:
            Summary text as a string

        Raises:
            FileNotFoundError: If chunks not found
            ValueError: If API response is invalid
        """
        # Load abbreviations if available
        abbreviations_text = ""
        if abbr_dir:
            abbr_file = abbr_dir / f"{project_id}_abbr.md"
            if abbr_file.exists():
                abbreviations_text = abbr_file.read_text(encoding="utf-8")

        # Load first N chunks
        chunks_text = self._load_chunks(project_id, chunks_dir, num_chunks)

        # Build pad_text: abbreviations + chunks
        pad_text_parts = []
        if abbreviations_text:
            pad_text_parts.append(abbreviations_text)
        pad_text_parts.extend(chunks_text)

        pad_text = "\n\n".join(pad_text_parts)

        # Prepare input message
        input_message = f"project_id: {project_id}\npad_text: {pad_text}"

        # Call custom GPT
        response = self.client.responses.create(
            prompt={
                "id": self.SUMMARY_PROMPT_ID,
                "version": self.SUMMARY_PROMPT_VERSION,
            },
            input=[{"role": "user", "content": input_message}],
            reasoning={"summary": None},
            store=False,
            include=[
                "reasoning.encrypted_content",
                "web_search_call.action.sources",
            ],
        )

        # Extract response text
        return response.output_text

    def _load_chunks(
        self, project_id: str, chunks_dir: Path, num_chunks: int
    ) -> List[str]:
        """
        Load the first N chunks for a project.

        Args:
            project_id: Project ID
            chunks_dir: Directory containing chunk files
            num_chunks: Number of chunks to load

        Returns:
            List of chunk texts

        Raises:
            FileNotFoundError: If no chunks found
        """
        if not chunks_dir.exists():
            raise FileNotFoundError(f"Chunks directory not found: {chunks_dir}")

        # Find all chunk files for this project
        chunk_files = sorted(chunks_dir.glob("*.md"))
        project_chunks = sorted([f for f in chunk_files if f.stem.startswith(project_id)])

        if not project_chunks:
            raise FileNotFoundError(f"No chunks found for project {project_id}")

        # Load first N chunks (0, 1, 2, ...)
        chunks_to_load = []
        for i in range(num_chunks):
            chunk_pattern = f"{project_id}_{i}_"
            matching_chunks = [
                f for f in project_chunks if f.stem.startswith(chunk_pattern)
            ]

            if matching_chunks:
                chunk_file = matching_chunks[0]
                chunk_text = chunk_file.read_text(encoding="utf-8")
                chunks_to_load.append(chunk_text)
            else:
                # Stop if we can't find the next chunk
                break

        if not chunks_to_load:
            raise FileNotFoundError(
                f"No valid chunks found for project {project_id}"
            )

        return chunks_to_load


def generate_all_summaries(
    chunks_dir: Path,
    output_dir: Path,
    abbr_dir: Optional[Path] = None,
    specific_project: Optional[str] = None,
    num_chunks: int = 4,
    overwrite: bool = False,
) -> Dict[str, List]:
    """
    Generate summaries for multiple PAD documents.

    Args:
        chunks_dir: Directory containing markdown chunk files
        output_dir: Directory to save summary text files
        abbr_dir: Directory containing abbreviation files (optional)
        specific_project: Specific project ID to process (None = process all)
        num_chunks: Number of chunks to load per project (default: 4)
        overwrite: Whether to overwrite existing output files

    Returns:
        Dictionary with summarization results:
            - generated: List of successfully processed project IDs
            - skipped: List of skipped project IDs (already exists)
            - failed: List of tuples (project_id, error_message)
    """
    # Initialize summarizer
    summarizer = PADSummarizer()

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get list of projects to process
    if specific_project:
        projects_to_process = [specific_project]
    else:
        # Find all unique project IDs from chunk files
        chunk_files = list(chunks_dir.glob("*.md"))
        project_ids = set()
        for chunk_file in chunk_files:
            # Extract project ID from chunk filename (e.g., "P075941_0_...")
            parts = chunk_file.stem.split("_")
            if parts:
                project_ids.add(parts[0])
        projects_to_process = sorted(project_ids)

    # Track results
    results = {"generated": [], "skipped": [], "failed": []}

    # Process each project
    for project_id in projects_to_process:
        output_file = output_dir / f"{project_id}_summary.txt"

        # Check if output already exists
        if output_file.exists() and not overwrite:
            results["skipped"].append(project_id)
            continue

        try:
            # Generate summary
            summary_text = summarizer.generate_summary(
                project_id=project_id,
                chunks_dir=chunks_dir,
                abbr_dir=abbr_dir,
                num_chunks=num_chunks,
            )

            # Save summary
            output_file.write_text(summary_text, encoding="utf-8")
            results["generated"].append(project_id)

        except Exception as e:
            results["failed"].append((project_id, str(e)))

    return results
