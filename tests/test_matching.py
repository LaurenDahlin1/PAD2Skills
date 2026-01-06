"""Tests for ESCO data preparation."""

import pandas as pd
import pytest

from src.matching.esco_prepare import _combine_fields
from src.matching.esco_selector import EscoSelector
from src.matching.pad_matcher import _combine_pad_fields


class TestEscoPrepare:
    """Tests for ESCO data preparation functions."""

    def test_combine_fields_all_present(self):
        """Test combining fields when all fields are present."""
        row = pd.Series(
            {
                "preferredLabel": "Software developer",
                "altLabels": "Programmer\nCoder\nSoftware engineer\nDev\nEngineer\nExtra1",
                "description": "Develops software applications",
                "skills_list": "Python, Java, C++",
            }
        )

        result = _combine_fields(row)

        # Check that preferredLabel comes first
        assert result.startswith("Software developer")
        # Check that first 5 altLabels are included early
        assert "Programmer" in result
        assert "Coder" in result
        # Check that description is included
        assert "Develops software applications" in result
        # Check that skills are included
        assert "Python, Java, C++" in result
        # Check that 6th altLabel (Extra1) appears at the end
        assert "Extra1" in result

    def test_combine_fields_missing_fields(self):
        """Test combining fields when some fields are missing."""
        row = pd.Series(
            {
                "preferredLabel": "Software developer",
                "altLabels": None,
                "description": None,
                "skills_list": None,
            }
        )

        result = _combine_fields(row)

        assert result == "Software developer"

    def test_combine_fields_long_skills_truncated(self):
        """Test that long skills list is truncated to 1500 chars."""
        row = pd.Series(
            {
                "preferredLabel": "Developer",
                "altLabels": None,
                "description": None,
                "skills_list": "x" * 2000,  # Long string
            }
        )

        result = _combine_fields(row)

        # Skills should be truncated to 1500 chars
        # Result should be "Developer " + 1500 x's
        assert len(result) == len("Developer") + 1 + 1500

    def test_combine_fields_comma_separated_altlabels(self):
        """Test altLabels with comma separation instead of newlines."""
        row = pd.Series(
            {
                "preferredLabel": "Teacher",
                "altLabels": "Educator, Instructor, Tutor",
                "description": "Teaches students",
                "skills_list": None,
            }
        )

        result = _combine_fields(row)

        assert "Teacher" in result
        assert "Educator" in result
        assert "Instructor" in result
        assert "Tutor" in result
        assert "Teaches students" in result

    def test_combine_fields_more_than_five_altlabels(self):
        """Test that first 5 altLabels come early, rest at end."""
        row = pd.Series(
            {
                "preferredLabel": "Manager",
                "altLabels": "Label1\nLabel2\nLabel3\nLabel4\nLabel5\nLabel6\nLabel7",
                "description": "Manages team",
                "skills_list": None,
            }
        )

        result = _combine_fields(row)

        # Split result into parts
        parts = result.split("Manages team")
        before_description = parts[0]
        after_description = parts[1] if len(parts) > 1 else ""

        # First 5 labels should appear before description
        assert "Label1" in before_description
        assert "Label2" in before_description
        assert "Label3" in before_description
        assert "Label4" in before_description
        assert "Label5" in before_description

        # Labels 6 and 7 should appear after description
        assert "Label6" in after_description
        assert "Label7" in after_description


class TestPadMatcher:
    """Tests for PAD matching functions."""

    def test_combine_pad_fields_all_present(self):
        """Test combining PAD fields when all present."""
        row = pd.Series(
            {
                "identified_occupation": "Teacher",
                "activity_description_in_pad": "Teaching students",
                "skills_needed_for_activity": ["Communication", "Planning"],
            }
        )

        result = _combine_pad_fields(row)

        assert "Teacher" in result
        assert "Teaching students" in result
        assert "Communication, Planning" in result

    def test_combine_pad_fields_string_skills(self):
        """Test combining PAD fields with string representation of skills."""
        row = pd.Series(
            {
                "identified_occupation": "Teacher",
                "activity_description_in_pad": "Teaching",
                "skills_needed_for_activity": "['Communication', 'Planning']",
            }
        )

        result = _combine_pad_fields(row)

        # String list should be cleaned up
        assert "Communication" in result
        assert "Planning" in result

    def test_combine_pad_fields_missing_fields(self):
        """Test combining PAD fields when some are missing."""
        row = pd.Series(
            {
                "identified_occupation": "Teacher",
                "activity_description_in_pad": None,
                "skills_needed_for_activity": None,
            }
        )

        result = _combine_pad_fields(row)

        assert result == "Teacher"

    def test_combine_pad_fields_empty_skills_list(self):
        """Test combining PAD fields with empty skills list."""
        row = pd.Series(
            {
                "identified_occupation": "Manager",
                "activity_description_in_pad": "Managing team",
                "skills_needed_for_activity": [],
            }
        )

        result = _combine_pad_fields(row)

        assert "Manager" in result
        assert "Managing team" in result
        # Empty list joins to empty string, which adds trailing space
        assert result.strip() == "Manager Managing team"


class TestEscoSelector:
    """Tests for ESCO selection functions."""

    def test_load_section_names(self):
        """Test loading and cleaning section names."""
        import json
        import tempfile
        from pathlib import Path

        from src.matching.unique_esco import _load_section_names

        # Create a temporary JSON file
        sections_data = {
            "sections": [
                {"section_id": 0, "header_text": "## Project Description  "},
                {"section_id": 1, "header_text": "###  Implementation   Plan"},
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sections_data, f)
            temp_path = Path(f.name)

        try:
            section_mapping = _load_section_names(temp_path)

            assert len(section_mapping) == 2
            # Check that pound signs and extra whitespace are removed
            assert section_mapping[0] == "Project Description"
            assert section_mapping[1] == "Implementation Plan"

        finally:
            temp_path.unlink()

    def test_load_section_names_missing_file(self):
        """Test loading section names when file doesn't exist."""
        from pathlib import Path

        from src.matching.unique_esco import _load_section_names

        section_mapping = _load_section_names(Path("/nonexistent/file.json"))

        # Should return empty dict without raising error
        assert section_mapping == {}


class TestUniqueEsco:
    """Tests for unique ESCO matches creation."""

    def test_format_skills_valid_list(self):
        """Test formatting skills from a valid list string."""
        from src.matching.unique_esco import format_skills

        skills_str = "['Python', 'Java', 'C++']"
        result = format_skills(skills_str)

        assert result == '"Python", "Java", "C++"'

    def test_format_skills_empty(self):
        """Test formatting skills with empty/null input."""
        from src.matching.unique_esco import format_skills

        assert format_skills(None) == ""
        assert format_skills(pd.NA) == ""

    def test_format_skills_invalid(self):
        """Test formatting skills with invalid input."""
        from src.matching.unique_esco import format_skills

        # Should return as-is if parsing fails
        invalid_str = "not a list"
        result = format_skills(invalid_str)
        assert result == invalid_str
