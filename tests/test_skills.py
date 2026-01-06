"""Tests for skills refinement utilities."""

import pandas as pd
import pytest
from pathlib import Path

from src.skills.skills_refiner import SkillsRefiner


class TestSkillsRefiner:
    """Tests for SkillsRefiner."""

    def test_refiner_initialization(self, tmp_path):
        """Test that refiner can be initialized."""
        unique_esco_nace_file = tmp_path / "unique_esco_nace.csv"
        esco_skills_file = tmp_path / "skills.csv"
        pad_summary_file = tmp_path / "summary.txt"
        
        # Create mock files
        unique_esco_nace_file.touch()
        esco_skills_file.touch()
        pad_summary_file.write_text("Project summary")
        
        refiner = SkillsRefiner(
            unique_esco_nace_file=unique_esco_nace_file,
            esco_skills_file=esco_skills_file,
            pad_summary_file=pad_summary_file,
            project_id="P123456",
            openai_api_key="test-key",
            chunk_size=3,
        )
        
        assert refiner.unique_esco_nace_file == unique_esco_nace_file
        assert refiner.esco_skills_file == esco_skills_file
        assert refiner.pad_summary_file == pad_summary_file
        assert refiner.project_id == "P123456"
        assert refiner.chunk_size == 3
        assert refiner.df_occupations is None
        assert refiner.df_skills is None

    def test_chunk_list(self, tmp_path):
        """Test that chunk_list splits lists correctly."""
        unique_esco_nace_file = tmp_path / "unique_esco_nace.csv"
        esco_skills_file = tmp_path / "skills.csv"
        pad_summary_file = tmp_path / "summary.txt"
        
        # Create mock files
        unique_esco_nace_file.touch()
        esco_skills_file.touch()
        pad_summary_file.write_text("Project summary")
        
        refiner = SkillsRefiner(
            unique_esco_nace_file=unique_esco_nace_file,
            esco_skills_file=esco_skills_file,
            pad_summary_file=pad_summary_file,
            project_id="P123456",
            openai_api_key="test-key",
            chunk_size=3,
        )
        
        # Test chunking
        test_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        chunks = refiner.chunk_list(test_list, 3)
        
        assert len(chunks) == 4
        assert chunks[0] == [1, 2, 3]
        assert chunks[1] == [4, 5, 6]
        assert chunks[2] == [7, 8, 9]
        assert chunks[3] == [10]

    def test_result_to_dataframe(self, tmp_path):
        """Test that result_to_dataframe converts JSON to DataFrame correctly."""
        unique_esco_nace_file = tmp_path / "unique_esco_nace.csv"
        esco_skills_file = tmp_path / "skills.csv"
        pad_summary_file = tmp_path / "summary.txt"
        
        # Create mock files
        unique_esco_nace_file.touch()
        esco_skills_file.touch()
        pad_summary_file.write_text("Project summary")
        
        refiner = SkillsRefiner(
            unique_esco_nace_file=unique_esco_nace_file,
            esco_skills_file=esco_skills_file,
            pad_summary_file=pad_summary_file,
            project_id="P123456",
            openai_api_key="test-key",
        )
        
        # Test result conversion
        result_json = {
            "project_id": "P123456",
            "occupations": [
                {
                    "esco_id": "esco1",
                    "skills": [
                        {"skill_code": "s1", "relevant": True, "top_five": True},
                        {"skill_code": "s2", "relevant": True, "top_five": False},
                    ],
                },
                {
                    "esco_id": "esco2",
                    "skills": [
                        {"skill_code": "s3", "relevant": False, "top_five": False},
                    ],
                },
            ],
        }
        
        df = refiner.result_to_dataframe(result_json)
        
        assert len(df) == 3
        assert list(df.columns) == ["esco_id", "skill_code", "relevant", "top_five"]
        assert df.iloc[0]["esco_id"] == "esco1"
        assert df.iloc[0]["skill_code"] == "s1"
        assert df.iloc[0]["relevant"] == True
        assert df.iloc[0]["top_five"] == True
