"""Tests for NACE utilities."""

import pandas as pd
import pytest
from pathlib import Path

from src.nace.esco_nace_mapper import ESCONACEMapper
from src.nace.nace_selector import NACESelector


class TestESCONACEMapper:
    """Tests for ESCO-NACE mapper."""

    def test_mapper_initialization(self, tmp_path):
        """Test that mapper can be initialized."""
        nace_rdf_path = tmp_path / "nace.rdf"
        esco_path = tmp_path / "esco.csv"
        
        mapper = ESCONACEMapper(nace_rdf_path, esco_path)
        
        assert mapper.nace_rdf_path == nace_rdf_path
        assert mapper.esco_occupations_path == esco_path
        assert mapper.graph is None


class TestNACESelector:
    """Tests for NACE selector."""

    def test_selector_initialization(self, tmp_path):
        """Test that selector can be initialized."""
        unique_esco_path = tmp_path / "unique_esco.csv"
        esco_nace_groups_path = tmp_path / "esco_nace_groups.csv"
        
        selector = NACESelector(unique_esco_path, esco_nace_groups_path)
        
        assert selector.unique_esco_path == unique_esco_path
        assert selector.esco_nace_groups_path == esco_nace_groups_path
        assert selector.model is None
        assert selector.G is None
        assert selector.E_esco is None

    def test_pick_best_groups_returns_empty_for_unknown_esco(self, tmp_path):
        """Test that pick_best_groups returns empty list for unknown ESCO ID."""
        unique_esco_path = tmp_path / "unique_esco.csv"
        esco_nace_groups_path = tmp_path / "esco_nace_groups.csv"
        
        # Create minimal CSV files
        pd.DataFrame({"esco_id": ["id1"], "combined_text": ["text1"]}).to_csv(
            unique_esco_path, index=False
        )
        pd.DataFrame({
            "esco_id": ["id1"],
            "group_code": ["123"],
            "embedding_description": ["desc"],
        }).to_csv(esco_nace_groups_path, index=False)
        
        selector = NACESelector(unique_esco_path, esco_nace_groups_path)
        selector.esco_to_idx = {"id1": 0}  # Mock mapping
        
        # Test with unknown ESCO ID
        result = selector.pick_best_groups_for_esco("unknown_id", k=1)
        
        assert result == []
