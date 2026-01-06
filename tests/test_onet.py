"""Tests for O*NET integration module."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from src.onet.onet_crosswalk import OnetCrosswalkCreator
from src.onet.onet_merger import OnetMerger


class TestOnetCrosswalkCreator:
    """Tests for OnetCrosswalkCreator."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock OpenAI client."""
        return MagicMock()

    @pytest.fixture
    def creator(self, mock_client):
        """Create OnetCrosswalkCreator instance with mock client."""
        return OnetCrosswalkCreator(mock_client)

    @pytest.fixture
    def sample_crosswalk_df(self):
        """Create sample crosswalk data."""
        return pd.DataFrame(
            {
                "O*NET Id": ["11-1011.00", "11-1021.00"],
                "O*NET Title": ["Chief Executives", "General and Operations Managers"],
                "O*NET Description": [
                    "Determine and formulate policies",
                    "Plan, direct",
                ],
                "ESCO or ISCO URI": [
                    "http://data.europa.eu/esco/occupation/1234",
                    "http://data.europa.eu/esco/occupation/5678",
                ],
                "ESCO or ISCO Title": ["Chief Executive Officer", "Operations Manager"],
                "ESCO or ISCO Description": [
                    "Manages organization",
                    "Oversees operations",
                ],
                "Type of Match": ["Exact", "Close"],
                "Date": ["2021-01-01", "2021-01-01"],
                "Domain Source": ["ESCO", "ESCO"],
            }
        )

    @pytest.fixture
    def sample_job_zones_df(self):
        """Create sample job zones data."""
        return pd.DataFrame(
            {
                "O*NET-SOC Code": ["11-1011.00", "11-1021.00"],
                "Job Zone": [5, 4],
            }
        )

    @pytest.fixture
    def sample_esco_prepared_df(self):
        """Create sample prepared ESCO data."""
        return pd.DataFrame(
            {
                "esco_id": ["1234", "5678", "9999"],
                "preferredLabel": [
                    "Chief Executive Officer",
                    "Operations Manager",
                    "Missing Occupation",
                ],
                "description": [
                    "Manages organization",
                    "Oversees operations",
                    "Not in crosswalk",
                ],
            }
        )

    def test_load_onet_data(
        self, creator, tmp_path, sample_crosswalk_df, sample_job_zones_df
    ):
        """Test loading and merging O*NET data."""
        # Create temporary files
        crosswalk_file = tmp_path / "crosswalk.csv"
        job_zones_file = tmp_path / "job_zones.txt"

        sample_crosswalk_df.to_csv(crosswalk_file, index=False)
        sample_job_zones_df.to_csv(job_zones_file, sep="\t", index=False)

        # Load data
        result = creator.load_onet_data(crosswalk_file, job_zones_file)

        # Verify
        assert len(result) == 2
        assert "esco_id" in result.columns
        assert "onet_id" in result.columns
        assert "job_zone" in result.columns
        assert result["esco_id"].tolist() == ["1234", "5678"]

    def test_merge_with_esco_prepared(self, creator, tmp_path, sample_esco_prepared_df):
        """Test merging O*NET data with prepared ESCO occupations."""
        # Create sample merged O*NET data
        onet_merged_df = pd.DataFrame(
            {
                "esco_id": ["1234", "5678"],
                "onet_id": ["11-1011.00", "11-1021.00"],
                "onet_title": ["Chief Executives", "General and Operations Managers"],
                "job_zone": [5, 4],
                "esco_title": ["CEO", "Manager"],
                "esco_description": ["Manages", "Oversees"],
            }
        )

        # Create temporary ESCO prepared file
        esco_file = tmp_path / "esco_prepared.csv"
        sample_esco_prepared_df.to_csv(esco_file, index=False)

        # Merge
        result = creator.merge_with_esco_prepared(onet_merged_df, esco_file)

        # Verify
        assert len(result) == 3
        assert "job_zone_min" in result.columns
        assert "onet_titles" in result.columns
        assert result[result["esco_id"] == "9999"]["job_zone_min"].iloc[0] == 9

    def test_combine_job_zones(self, creator, sample_esco_prepared_df):
        """Test combining O*NET and LLM job zones."""
        # Create sample data
        df_final = pd.DataFrame(
            {
                "esco_id": ["1234", "5678", "9999"],
                "preferredLabel": ["CEO", "Manager", "Missing"],
                "job_zone_min": [5, 4, 9],
                "onet_titles": [
                    ["Chief Executives"],
                    ["Manager"],
                    ["None, Missing Crosswalk"],
                ],
            }
        )

        df_labeled = pd.DataFrame({"esco_id": ["9999"], "job_zone": [3]})

        # Combine
        result = creator.combine_job_zones(df_final, df_labeled)

        # Verify
        assert len(result) == 3
        assert "onet_job_zone" in result.columns
        assert "onet_job_zone_label" in result.columns
        assert "onet_job_zone_est" in result.columns
        assert result[result["esco_id"] == "9999"]["onet_job_zone"].iloc[0] == 3
        assert result[result["esco_id"] == "9999"]["onet_job_zone_est"].iloc[0] == "llm"


class TestOnetMerger:
    """Tests for OnetMerger."""

    @pytest.fixture
    def merger(self):
        """Create OnetMerger instance."""
        return OnetMerger()

    @pytest.fixture
    def sample_job_zones_df(self):
        """Create sample job zones data."""
        return pd.DataFrame(
            {
                "esco_id": ["1234", "5678"],
                "onet_job_zone": [5, 4],
                "onet_job_zone_label": [
                    "5: Extensive Preparation Needed",
                    "4: Considerable Preparation Needed",
                ],
                "onet_job_zone_est": ["unique", "minimum"],
            }
        )

    @pytest.fixture
    def sample_project_df(self):
        """Create sample project data."""
        return pd.DataFrame(
            {
                "esco_id": ["1234", "5678"],
                "preferredLabel": ["Chief Executive Officer", "Operations Manager"],
                "nace_group": ["70.10", "70.22"],
            }
        )

    def test_merge_job_zones_to_project(
        self, merger, tmp_path, sample_job_zones_df, sample_project_df
    ):
        """Test merging job zones onto project file."""
        # Create temporary files
        job_zones_file = tmp_path / "job_zones.csv"
        project_file = tmp_path / "project.csv"
        output_file = tmp_path / "output.csv"

        sample_job_zones_df.to_csv(job_zones_file, index=False)
        sample_project_df.to_csv(project_file, index=False)

        # Merge
        result_path = merger.merge_job_zones_to_project(
            job_zones_file=job_zones_file,
            project_esco_nace_file=project_file,
            output_file=output_file,
            overwrite=True,
        )

        # Verify
        assert result_path.exists()
        result_df = pd.read_csv(result_path)
        assert len(result_df) == 2
        assert "onet_job_zone" in result_df.columns
        assert "nace_group" in result_df.columns

    def test_merge_job_zones_skip_existing(
        self, merger, tmp_path, sample_job_zones_df, sample_project_df
    ):
        """Test that merge skips existing files when overwrite=False."""
        # Create temporary files
        job_zones_file = tmp_path / "job_zones.csv"
        project_file = tmp_path / "project.csv"
        output_file = tmp_path / "output.csv"

        sample_job_zones_df.to_csv(job_zones_file, index=False)
        sample_project_df.to_csv(project_file, index=False)

        # Create existing output file
        output_file.write_text("existing")

        # Merge with overwrite=False
        result_path = merger.merge_job_zones_to_project(
            job_zones_file=job_zones_file,
            project_esco_nace_file=project_file,
            output_file=output_file,
            overwrite=False,
        )

        # Verify file was not overwritten
        assert result_path.read_text() == "existing"
