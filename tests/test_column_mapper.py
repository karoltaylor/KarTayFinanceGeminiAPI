"""Tests for column mapper service."""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from src.services.column_mapper import ColumnMapper


class TestColumnMapper:
    """Tests for ColumnMapper."""

    def test_init_without_api_key_raises_error(self, monkeypatch):
        """Test that missing API key raises error."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        with pytest.raises(ValueError, match="Google API key is required"):
            ColumnMapper()

    def test_init_with_api_key(self, set_test_env_vars):
        """Test initialization with API key."""
        mapper = ColumnMapper(api_key="test_key")
        assert mapper.api_key == "test_key"

    @patch("src.services.column_mapper.genai")
    def test_map_columns_success(self, mock_genai, set_test_env_vars):
        """Test successful column mapping."""
        # Mock the AI response
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = """{
            "wallet_name": "account",
            "asset_name": "stock",
            "asset_type": "type",
            "date": "date",
            "asset_item_price": "price",
            "volume": "quantity",
            "currency": "curr"
        }"""
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        df = pd.DataFrame(
            {
                "account": ["Wallet1"],
                "stock": ["AAPL"],
                "type": ["Stock"],
                "date": ["2024-01-10"],
                "price": [150.50],
                "quantity": [10],
                "curr": ["USD"],
            }
        )

        mapper = ColumnMapper(api_key="test_key")
        target_columns = [
            "wallet_name",
            "asset_name",
            "asset_type",
            "date",
            "asset_item_price",
            "volume",
            "currency",
        ]

        mapping = mapper.map_columns(df, target_columns)

        assert mapping["wallet_name"] == "account"
        assert mapping["asset_name"] == "stock"
        assert mapping["currency"] == "curr"

    def test_map_columns_empty_dataframe(self, set_test_env_vars):
        """Test that empty DataFrame raises error."""
        df = pd.DataFrame()
        mapper = ColumnMapper(api_key="test_key")

        with pytest.raises(ValueError, match="Cannot map columns from empty DataFrame"):
            mapper.map_columns(df, ["col1", "col2"])

    @patch("src.services.column_mapper.genai")
    def test_parse_mapping_response_with_markdown(self, mock_genai, set_test_env_vars):
        """Test parsing response with markdown code blocks."""
        mapper = ColumnMapper(api_key="test_key")

        response = """```json
        {
            "wallet_name": "account",
            "asset_name": "stock"
        }
        ```"""

        mapping = mapper._parse_mapping_response(response)

        assert mapping["wallet_name"] == "account"
        assert mapping["asset_name"] == "stock"

    def test_validate_mapping_missing_target_columns(self, set_test_env_vars):
        """Test validation catches missing target columns."""
        mapper = ColumnMapper(api_key="test_key")

        mapping = {"wallet_name": "account"}
        source_cols = ["account", "stock"]
        target_cols = ["wallet_name", "asset_name"]

        with pytest.raises(ValueError, match="missing target columns"):
            mapper._validate_mapping(mapping, source_cols, target_cols)

    def test_validate_mapping_invalid_source_column(self, set_test_env_vars):
        """Test validation catches non-existent source columns."""
        mapper = ColumnMapper(api_key="test_key")

        mapping = {"wallet_name": "nonexistent_column", "asset_name": "stock"}
        source_cols = ["account", "stock"]
        target_cols = ["wallet_name", "asset_name"]

        with pytest.raises(ValueError, match="non-existent source column"):
            mapper._validate_mapping(mapping, source_cols, target_cols)

    def test_apply_mapping_success(self, set_test_env_vars):
        """Test applying column mapping."""
        mapper = ColumnMapper(api_key="test_key")

        source_df = pd.DataFrame(
            {
                "account": ["Wallet1", "Wallet2"],
                "stock": ["AAPL", "MSFT"],
                "price": [150.50, 380.25],
            }
        )

        mapping = {
            "wallet_name": "account",
            "asset_name": "stock",
            "asset_item_price": "price",
            "asset_type": None,
            "date": None,
            "volume": None,
            "currency": None,
        }

        result_df = mapper.apply_mapping(source_df, mapping)

        assert "wallet_name" in result_df.columns
        assert "asset_name" in result_df.columns
        assert len(result_df) == 2
        assert result_df.iloc[0]["wallet_name"] == "Wallet1"

    def test_apply_mapping_with_defaults(self, set_test_env_vars):
        """Test applying mapping with default values."""
        mapper = ColumnMapper(api_key="test_key")

        source_df = pd.DataFrame({"stock": ["AAPL"], "price": [150.50]})

        mapping = {"asset_name": "stock", "asset_item_price": "price", "currency": None}

        defaults = {"currency": "USD"}

        result_df = mapper.apply_mapping(source_df, mapping, defaults)

        assert result_df.iloc[0]["currency"] == "USD"

    def test_build_mapping_prompt(self, set_test_env_vars):
        """Test that prompt is built correctly."""
        mapper = ColumnMapper(api_key="test_key")

        source_cols = ["col1", "col2"]
        target_cols = ["target1", "target2"]
        sample_data = [{"col1": "val1", "col2": "val2"}]

        prompt = mapper._build_mapping_prompt(source_cols, target_cols, sample_data)

        assert "col1" in prompt
        assert "target1" in prompt
        assert "asset_name" in prompt
        assert "asset_price" in prompt
        assert "JSON" in prompt
