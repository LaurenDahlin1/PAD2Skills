"""Single-project pipeline orchestrator.

Runs all 13 pipeline steps for a single project ID, tracking timing and status.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from src.config import load_config
from src.pdf_conversion.converter import convert_pdfs
from src.extraction.extractor import (
    extract_all_sections,
    extract_all_abbreviations,
    create_chunks,
)
from src.extraction.summarizer import generate_all_summaries
from src.extraction.short_summarizer import generate_all_short_summaries
from src.extraction.occupations_extractor import (
    extract_all_occupations,
    prepare_pad_occupations_csv,
)
from src.matching.esco_prepare import prepare_esco_data
from src.matching.pad_matcher import match_pad_to_esco
from src.matching.esco_selector import select_best_esco_matches
from src.matching.unique_esco import create_unique_esco_matches
from src.nace.esco_nace_mapper import ESCONACEMapper
from src.nace.nace_selector import NACESelector
from src.skills.skills_refiner import SkillsRefiner
from src.onet.onet_crosswalk import OnetCrosswalkCreator
from src.onet.onet_merger import OnetMerger


class SingleProjectPipeline:
    """Pipeline orchestrator for processing a single project through all stages."""

    def __init__(
        self,
        project_id: str,
        config_path: Optional[Path] = None,
        print_progress: bool = True,
        # Overwrite flags for each step
        ow_pdf: bool = False,
        ow_sections: bool = False,
        ow_abbr: bool = False,
        ow_chunks: bool = False,
        ow_long_summary: bool = False,
        ow_short_summary: bool = False,
        ow_occupations: bool = False,
        ow_occs_csv: bool = False,
        ow_esco_prep: bool = False,
        ow_esco_match: bool = False,
        ow_esco_select: bool = False,
        ow_unique_esco: bool = False,
        ow_nace_prep: bool = False,
        ow_nace_select: bool = False,
        ow_skills: bool = False,
        ow_onet_prep: bool = False,
        ow_onet_merge: bool = False,
    ):
        """Initialize pipeline for a single project.

        Args:
            project_id: The project ID to process (e.g., 'P075941')
            config_path: Optional path to custom config file
            print_progress: Whether to print progress indicators (default True)
            ow_*: Overwrite flags for each step (default False for all)
        """
        self.project_id = project_id
        self.print_progress = print_progress

        # Load configuration
        self.config = load_config(config_path) if config_path else load_config()
        # Calculate project root (same as config loader does)
        self.project_root = Path(__file__).parent.parent.parent

        # Store overwrite flags
        self.ow_pdf = ow_pdf
        self.ow_sections = ow_sections
        self.ow_abbr = ow_abbr
        self.ow_chunks = ow_chunks
        self.ow_long_summary = ow_long_summary
        self.ow_short_summary = ow_short_summary
        self.ow_occupations = ow_occupations
        self.ow_occs_csv = ow_occs_csv
        self.ow_esco_prep = ow_esco_prep
        self.ow_esco_match = ow_esco_match
        self.ow_esco_select = ow_esco_select
        self.ow_unique_esco = ow_unique_esco
        self.ow_nace_prep = ow_nace_prep
        self.ow_nace_select = ow_nace_select
        self.ow_skills = ow_skills
        self.ow_onet_prep = ow_onet_prep
        self.ow_onet_merge = ow_onet_merge

        # Get OpenAI API key
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError(
                "Missing required environment variable: OPENAI_API_KEY. "
                "Please set it in your .env file."
            )

        # Initialize timing tracker
        self.timing_data = []
        self.run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def _print(self, message: str):
        """Print message if print_progress is enabled."""
        if self.print_progress:
            print(message)

    def _run_step(
        self,
        step_code: str,
        step_name: str,
        func,
        *args,
        **kwargs,
    ):
        """Run a single pipeline step with timing and error handling.

        Args:
            step_code: Short code for the step (e.g., '01_pdf')
            step_name: Descriptive name for the step
            func: Function to execute
            *args, **kwargs: Arguments to pass to the function

        Returns:
            Tuple of (success: bool, status: str, error_message: str)
        """
        start_time = datetime.now()

        try:
            result = func(*args, **kwargs)

            # Determine status based on result
            if isinstance(result, dict):
                # Standard result dictionary from batch functions
                if result.get("converted") or result.get("extracted") or result.get("generated") or result.get("chunked"):
                    status = "New"
                elif result.get("skipped"):
                    status = "Exists - No Overwrite"
                else:
                    status = "New"
            elif result is True:
                status = "New"
            elif result == "skipped":
                status = "Exists - No Overwrite"
            elif result == "overwritten":
                status = "Exists - Overwrite"
            else:
                status = "New"

            end_time = datetime.now()
            elapsed_seconds = (end_time - start_time).total_seconds()
            elapsed = elapsed_seconds / 60
            
            # Format time display
            if elapsed_seconds < 60:
                time_display = f"{elapsed_seconds:.1f} seconds"
            else:
                time_display = f"{elapsed:.2f} minutes"
            
            self._print(f"{self.project_id} Step {step_code} ({step_name}): {time_display}")

            self.timing_data.append(
                {
                    "step_code": step_code,
                    "step_name": step_name,
                    "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "elapsed_minutes": round(elapsed, 2),
                    "status": status,
                    "error_occurred": False,
                    "error_message": "",
                }
            )

            return True, status, ""

        except Exception as e:
            end_time = datetime.now()
            elapsed_seconds = (end_time - start_time).total_seconds()
            elapsed = elapsed_seconds / 60
            error_msg = str(e)

            # Format time display
            if elapsed_seconds < 60:
                time_display = f"{elapsed_seconds:.1f} seconds"
            else:
                time_display = f"{elapsed:.2f} minutes"
            
            self._print(f"{self.project_id} Step {step_code} ({step_name}): {time_display} - FAILED: {error_msg}")

            self.timing_data.append(
                {
                    "step_code": step_code,
                    "step_name": step_name,
                    "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "elapsed_minutes": round(elapsed, 2),
                    "status": "Failed",
                    "error_occurred": True,
                    "error_message": error_msg,
                }
            )

            return False, "Failed", error_msg

    def _step_01_pdf(self):
        """Step 1: Convert PDF to Markdown."""
        pdf_dir = self.project_root / self.config.paths.raw_pdfs
        markdown_dir = self.project_root / self.config.paths.markdown
        pdf_file = f"{self.project_id}_1.pdf"

        if not (pdf_dir / pdf_file).exists():
            raise FileNotFoundError(f"PDF not found: {pdf_dir / pdf_file}")

        results = convert_pdfs(
            pdf_dir=pdf_dir,
            output_dir=markdown_dir,
            specific_pdf=pdf_file,
            overwrite=self.ow_pdf,
            accurate_tables=True,
        )

        return results

    def _step_02_sections(self):
        """Step 2: Extract document sections."""
        markdown_dir = self.project_root / self.config.paths.markdown
        sections_dir = self.project_root / "data" / "silver" / "document_sections"
        md_file = f"{self.project_id}_1.md"

        if not (markdown_dir / md_file).exists():
            raise FileNotFoundError(
                f"Markdown not found: {markdown_dir / md_file}. Run step 01_pdf first."
            )

        results = extract_all_sections(
            markdown_dir=markdown_dir,
            output_dir=sections_dir,
            specific_file=md_file,
            overwrite=self.ow_sections,
        )

        return results

    def _step_03_abbr(self):
        """Step 3: Extract abbreviations."""
        markdown_dir = self.project_root / self.config.paths.markdown
        abbr_dir = self.project_root / "data" / "silver" / "abbreviations_md"
        md_file = f"{self.project_id}_1.md"

        if not (markdown_dir / md_file).exists():
            raise FileNotFoundError(
                f"Markdown not found: {markdown_dir / md_file}. Run step 01_pdf first."
            )

        results = extract_all_abbreviations(
            markdown_dir=markdown_dir,
            output_dir=abbr_dir,
            specific_file=md_file,
            overwrite=self.ow_abbr,
        )

        return results

    def _step_04_chunks(self):
        """Step 4: Create markdown chunks."""
        markdown_dir = self.project_root / self.config.paths.markdown
        sections_dir = self.project_root / "data" / "silver" / "document_sections"
        chunks_dir = self.project_root / "data" / "silver" / "pads_md_chunks"
        md_file = f"{self.project_id}_1.md"

        if not (markdown_dir / md_file).exists():
            raise FileNotFoundError(
                f"Markdown not found: {markdown_dir / md_file}. Run step 01_pdf first."
            )

        results = create_chunks(
            markdown_dir=markdown_dir,
            sections_dir=sections_dir,
            output_dir=chunks_dir,
            specific_file=md_file,
            overwrite=self.ow_chunks,
        )

        return results

    def _step_05_long_summary(self):
        """Step 5: Generate long summary."""
        chunks_dir = self.project_root / "data" / "silver" / "pads_md_chunks"
        abbr_dir = self.project_root / "data" / "silver" / "abbreviations_md"
        summaries_dir = self.project_root / "data" / "silver" / "pad_summaries"

        chunk_files = list(chunks_dir.glob(f"{self.project_id}_*.md"))
        if not chunk_files:
            raise FileNotFoundError(
                f"No chunks found for {self.project_id}. Run step 04_chunks first."
            )

        results = generate_all_summaries(
            chunks_dir=chunks_dir,
            output_dir=summaries_dir,
            abbr_dir=abbr_dir,
            specific_project=self.project_id,
            num_chunks=4,
            overwrite=self.ow_long_summary,
        )

        return results

    def _step_05b_short_summary(self):
        """Step 5b: Generate short summary."""
        summaries_dir = self.project_root / "data" / "silver" / "pad_summaries"
        short_summary_dir = self.project_root / "data" / "silver" / "short_summary_json"
        summary_file = summaries_dir / f"{self.project_id}_summary.txt"

        if not summary_file.exists():
            raise FileNotFoundError(
                f"Summary not found: {summary_file}. Run step 05_long_summary first."
            )

        results = generate_all_short_summaries(
            summaries_dir=summaries_dir,
            output_dir=short_summary_dir,
            specific_project=self.project_id,
            overwrite=self.ow_short_summary,
        )

        return results

    def _step_06_occupations(self):
        """Step 6: Extract occupations."""
        chunks_dir = self.project_root / "data" / "silver" / "pads_md_chunks"
        abbr_dir = self.project_root / "data" / "silver" / "abbreviations_md"
        summaries_dir = self.project_root / "data" / "silver" / "pad_summaries"
        occupations_dir = self.project_root / "data" / "silver" / "occupations_skills_json"

        chunk_files = list(chunks_dir.glob(f"{self.project_id}_*.md"))
        if not chunk_files:
            raise FileNotFoundError(
                f"No chunks found for {self.project_id}. Run step 04_chunks first."
            )

        results = extract_all_occupations(
            chunks_dir=chunks_dir,
            output_dir=occupations_dir,
            abbr_dir=abbr_dir,
            summary_dir=summaries_dir,
            specific_project=self.project_id,
            overwrite=self.ow_occupations,
        )

        return results

    def _step_06b_occs_csv(self):
        """Step 6b: Prepare occupations CSV (optional, for debugging)."""
        occupations_dir = self.project_root / "data" / "silver" / "occupations_skills_json"
        csv_dir = self.project_root / "data" / "silver" / "occupation_skills_csv"

        occupation_files = list(occupations_dir.glob(f"{self.project_id}_*.json"))
        if not occupation_files:
            raise FileNotFoundError(
                f"No occupation files found for {self.project_id}. Run step 06_occupations first."
            )

        results = prepare_pad_occupations_csv(
            json_dir=occupations_dir,
            output_dir=csv_dir,
            specific_project=self.project_id,
            overwrite=self.ow_occs_csv,
        )

        return results

    def _step_07_esco_prep(self):
        """Step 7: Prepare ESCO data (one-time setup)."""
        esco_csv = self.project_root / "data" / "bronze" / "esco" / "occupations_en.csv"
        esco_relations = (
            self.project_root / "data" / "bronze" / "esco" / "occupationSkillRelations_en.csv"
        )
        esco_output = (
            self.project_root / "data" / "silver" / "clean_esco" / "esco_occupations_prepared.csv"
        )
        esco_embeddings = (
            self.project_root / "data" / "silver" / "embeddings" / "esco_embeddings.npy"
        )

        # Check if already exists
        if esco_output.exists() and esco_embeddings.exists() and not self.ow_esco_prep:
            return "skipped"

        if esco_output.exists() and esco_embeddings.exists() and self.ow_esco_prep:
            status = "overwritten"
        else:
            status = True

        prepare_esco_data(
            esco_csv=esco_csv,
            esco_relations_csv=esco_relations,
            output_csv=esco_output,
            embeddings_file=esco_embeddings,
            model_name="intfloat/e5-small-v2",
            overwrite_embeddings=self.ow_esco_prep,
        )

        return status

    def _step_07b_esco_match(self):
        """Step 7b: Match PAD occupations to ESCO."""
        occupations_dir = self.project_root / "data" / "silver" / "occupations_skills_json"
        esco_csv = (
            self.project_root / "data" / "silver" / "clean_esco" / "esco_occupations_prepared.csv"
        )
        esco_embeddings = (
            self.project_root / "data" / "silver" / "embeddings" / "esco_embeddings.npy"
        )

        occupation_files = list(occupations_dir.glob(f"{self.project_id}_*.json"))
        if not occupation_files:
            raise FileNotFoundError(
                f"No occupation files found for {self.project_id}. Run step 06_occupations first."
            )

        match_pad_to_esco(
            pad_occupations_dir=occupations_dir,
            project_id=self.project_id,
            esco_csv=esco_csv,
            esco_embeddings=esco_embeddings,
            output_dir=self.project_root / "data" / "silver",
            model_name="intfloat/e5-small-v2",
            top_k=20,
            chunk_size=75,
            save_diagnostics=True,
            overwrite=self.ow_esco_match,
        )

        return True

    def _step_08_esco_select(self):
        """Step 8: Select best ESCO match."""
        esco_matching_dir = self.project_root / "data" / "silver" / "esco_matching_json"
        occupations_dir = self.project_root / "data" / "silver" / "occupations_skills_json"
        selection_json_dir = self.project_root / "data" / "silver" / "choose_esco_json"
        selection_csv_dir = self.project_root / "data" / "silver" / "choose_esco_csv"

        matching_files = list(esco_matching_dir.glob(f"{self.project_id}_*_esco_matches.json"))
        if not matching_files:
            raise FileNotFoundError(
                f"No ESCO matching files found for {self.project_id}. Run step 07b_esco_match first."
            )

        select_best_esco_matches(
            input_dir=esco_matching_dir,
            project_id=self.project_id,
            pad_occupations_dir=occupations_dir,
            output_json_dir=selection_json_dir,
            output_csv_dir=selection_csv_dir,
            overwrite=self.ow_esco_select,
        )

        return True

    def _step_08b_unique_esco(self):
        """Step 8b: Create unique ESCO matches."""
        selection_csv_dir = self.project_root / "data" / "silver" / "choose_esco_csv"
        esco_occupations = self.project_root / "data" / "bronze" / "esco" / "occupations_en.csv"
        sections_json = (
            self.project_root
            / "data"
            / "silver"
            / "document_sections"
            / f"{self.project_id}_1_sections.json"
        )
        unique_esco_dir = self.project_root / "data" / "silver" / "unique_esco_csv"
        output_path = unique_esco_dir / f"{self.project_id}_unique_matched.csv"

        selections_csv = selection_csv_dir / f"{self.project_id}_esco_selections.csv"
        if not selections_csv.exists():
            raise FileNotFoundError(
                f"ESCO selections not found: {selections_csv}. Run step 08_esco_select first."
            )

        create_unique_esco_matches(
            project_id=self.project_id,
            selections_csv_path=selections_csv,
            esco_occupations_path=esco_occupations,
            sections_json_path=sections_json,
            output_path=output_path,
            overwrite=self.ow_unique_esco,
        )

        return True

    def _step_09_nace_prep(self):
        """Step 9: Create ESCO-NACE groups (one-time setup)."""
        nace_rdf = self.project_root / "data" / "bronze" / "nace" / "NACE_Rev.2.1.rdf"
        esco_occupations = self.project_root / "data" / "bronze" / "esco" / "occupations_en.csv"
        esco_nace_dir = self.project_root / "data" / "silver" / "esco_nace_csv"
        esco_nace_groups = esco_nace_dir / "esco_nace_groups.csv"

        # Check if already exists
        if esco_nace_groups.exists() and not self.ow_nace_prep:
            return "skipped"

        if esco_nace_groups.exists() and self.ow_nace_prep:
            status = "overwritten"
        else:
            status = True

        mapper = ESCONACEMapper(nace_rdf, esco_occupations)
        mapper.run(esco_nace_dir)

        return status

    def _step_09b_nace_select(self):
        """Step 9b: Select best NACE group."""
        unique_esco_dir = self.project_root / "data" / "silver" / "unique_esco_csv"
        esco_nace_groups = (
            self.project_root / "data" / "silver" / "esco_nace_csv" / "esco_nace_groups.csv"
        )
        unique_esco_nace_dir = self.project_root / "data" / "silver" / "unique_esco_nace_csv"

        unique_esco_path = unique_esco_dir / f"{self.project_id}_unique_matched.csv"
        if not unique_esco_path.exists():
            raise FileNotFoundError(
                f"Unique ESCO file not found: {unique_esco_path}. Run step 08b_unique_esco first."
            )

        selector = NACESelector(
            unique_esco_path=unique_esco_path,
            esco_nace_groups_path=esco_nace_groups,
            model_name="intfloat/e5-small-v2",
        )

        selector.run(
            output_dir=unique_esco_nace_dir,
            project_id=self.project_id,
            overwrite=self.ow_nace_select,
        )

        return True

    def _step_10_skills(self):
        """Step 10: Refine ESCO skills."""
        unique_esco_nace_dir = self.project_root / "data" / "silver" / "unique_esco_nace_csv"
        esco_skills = (
            self.project_root / "data" / "bronze" / "esco" / "occupationSkillRelations_en.csv"
        )
        summaries_dir = self.project_root / "data" / "silver" / "pad_summaries"
        skills_output_dir = self.project_root / "data" / "silver" / "esco_nace_w_skills_csv"

        unique_esco_nace_path = (
            unique_esco_nace_dir / f"{self.project_id}_unique_matched_with_nace.csv"
        )
        summary_path = summaries_dir / f"{self.project_id}_summary.txt"

        if not unique_esco_nace_path.exists():
            raise FileNotFoundError(
                f"Unique ESCO with NACE not found: {unique_esco_nace_path}. Run step 09b_nace_select first."
            )

        if not summary_path.exists():
            raise FileNotFoundError(
                f"PAD summary not found: {summary_path}. Run step 05_long_summary first."
            )

        refiner = SkillsRefiner(
            unique_esco_nace_file=unique_esco_nace_path,
            esco_skills_file=esco_skills,
            pad_summary_file=summary_path,
            project_id=self.project_id,
            openai_api_key=self.openai_api_key,
            chunk_size=3,
        )

        refiner.run(
            output_dir=skills_output_dir,
            overwrite=self.ow_skills,
        )

        return True

    def _step_11_onet_prep(self):
        """Step 11: Create ESCO-ONET crosswalk (one-time setup)."""
        from openai import OpenAI

        onet_crosswalk = self.project_root / "data" / "bronze" / "onet" / "esco_onet_crosswalk.csv"
        onet_job_zones = self.project_root / "data" / "bronze" / "onet" / "onet_job_zones.txt"
        esco_prepared = (
            self.project_root / "data" / "silver" / "clean_esco" / "esco_occupations_prepared.csv"
        )
        esco_onet_output = (
            self.project_root / "data" / "silver" / "clean_esco" / "esco_onet_job_zones.csv"
        )

        # Check if already exists
        if esco_onet_output.exists() and not self.ow_onet_prep:
            return "skipped"

        if esco_onet_output.exists() and self.ow_onet_prep:
            status = "overwritten"
        else:
            status = True

        client = OpenAI(api_key=self.openai_api_key)
        crosswalk_creator = OnetCrosswalkCreator(client)

        crosswalk_creator.create_crosswalk(
            crosswalk_file=onet_crosswalk,
            job_zones_file=onet_job_zones,
            esco_prepared_file=esco_prepared,
            output_file=esco_onet_output,
            chunk_size=50,
            overwrite=self.ow_onet_prep,
        )

        return status

    def _step_11b_onet_merge(self):
        """Step 11b: Merge ONET job zones."""
        esco_onet = (
            self.project_root / "data" / "silver" / "clean_esco" / "esco_onet_job_zones.csv"
        )
        unique_esco_nace_dir = self.project_root / "data" / "silver" / "unique_esco_nace_csv"
        onet_output_dir = self.project_root / "data" / "silver" / "unique_esco_nace_onet_csv"

        input_file = unique_esco_nace_dir / f"{self.project_id}_unique_matched_with_nace.csv"
        output_file = onet_output_dir / f"{self.project_id}_esco_nace_onet.csv"

        if not input_file.exists():
            raise FileNotFoundError(
                f"Unique ESCO with NACE not found: {input_file}. Run step 09b_nace_select first."
            )

        merger = OnetMerger()
        merger.merge_job_zones_to_project(
            job_zones_file=esco_onet,
            project_esco_nace_file=input_file,
            output_file=output_file,
            overwrite=self.ow_onet_merge,
        )

        return True

    def run(self):
        """Run the complete pipeline for the project."""
        self._print(f"\n{'=' * 80}")
        self._print(f"SINGLE-PROJECT PIPELINE: {self.project_id}")
        self._print(f"{'=' * 80}")

        # Define all steps
        steps = [
            ("01_pdf", "PDF Conversion", self._step_01_pdf),
            ("02_sections", "Extract Sections", self._step_02_sections),
            ("03_abbr", "Extract Abbreviations", self._step_03_abbr),
            ("04_chunks", "Create Chunks", self._step_04_chunks),
            ("05_long_summary", "Generate Long Summary", self._step_05_long_summary),
            ("05b_short_summary", "Generate Short Summary", self._step_05b_short_summary),
            ("06_occupations", "Extract Occupations", self._step_06_occupations),
            ("06b_occs_csv", "Prepare Occupations CSV", self._step_06b_occs_csv),
            ("07_esco_prep", "Prepare ESCO Data", self._step_07_esco_prep),
            ("07b_esco_match", "Match to ESCO", self._step_07b_esco_match),
            ("08_esco_select", "Select Best ESCO", self._step_08_esco_select),
            ("08b_unique_esco", "Create Unique ESCO", self._step_08b_unique_esco),
            ("09_nace_prep", "Prepare ESCO-NACE Groups", self._step_09_nace_prep),
            ("09b_nace_select", "Select NACE Groups", self._step_09b_nace_select),
            ("10_skills", "Refine Skills", self._step_10_skills),
            ("11_onet_prep", "Prepare ESCO-ONET Crosswalk", self._step_11_onet_prep),
            ("11b_onet_merge", "Merge ONET Job Zones", self._step_11b_onet_merge),
        ]

        # Run each step
        for step_code, step_name, step_func in steps:
            self._run_step(step_code, step_name, step_func)

        # Save timing data
        self._save_timing_data()

        self._print(f"\n{'=' * 80}")
        self._print("PIPELINE COMPLETE")
        self._print(f"{'=' * 80}")
        self._print(f"Timing data saved to: {self._get_timing_path()}")

    def _get_timing_path(self) -> Path:
        """Get the path for the timing CSV file."""
        timing_dir = self.project_root / "data" / "silver" / "zz_status_timing"
        timing_dir.mkdir(parents=True, exist_ok=True)
        return timing_dir / f"{self.project_id}_{self.run_timestamp}_timing.csv"

    def _save_timing_data(self):
        """Save timing data to CSV."""
        df = pd.DataFrame(self.timing_data)
        output_path = self._get_timing_path()
        df.to_csv(output_path, index=False)
