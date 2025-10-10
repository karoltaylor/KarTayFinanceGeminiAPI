"""Tests for data pipeline."""

import pandas as pd
from unittest.mock import patch, MagicMock

from src.pipeline.data_pipeline import DataPipeline
from src.models import TransactionType, AssetType
from bson import ObjectId


class TestDataPipeline:
    """Tests for DataPipeline."""

    @patch("src.pipeline.data_pipeline.ColumnMapper")
    def test_pipeline_initialization(self, mock_mapper, set_test_env_vars):
        """Test pipeline initialization."""
        pipeline = DataPipeline(api_key="test_key")

        assert pipeline.file_loader is not None
        assert pipeline.column_mapper is not None
        assert pipeline.transaction_mapper is not None

    @patch("src.services.column_mapper.genai")
    def test_process_file_to_transactions(
        self, mock_genai, temp_dir, set_test_env_vars
    ):
        """Test processing file to transactions."""
        # Create a well-structured CSV file
        csv_content = """Date,Asset,Price,Quantity,Total,Fee,Currency
2024-01-10,AAPL,150.50,10,1505.00,5.00,USD
2024-01-11,GOOGL,140.00,5,700.00,3.00,USD
"""
        filepath = temp_dir / "transactions.csv"
        filepath.write_text(csv_content)

        # Mock GenAI response
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = """{
            "date": "Date",
            "asset_name": "Asset",
            "asset_price": "Price",
            "volume": "Quantity",
            "transaction_amount": "Total",
            "fee": "Fee",
            "currency": "Currency"
        }"""
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        pipeline = DataPipeline(api_key="test_key")
        user_id = ObjectId()

        # Process file to transactions
        transactions = pipeline.process_file_to_transactions(
            filepath=filepath,
            wallet_name="Test Wallet",
            user_id=user_id,
            transaction_type=TransactionType.BUY,
            asset_type=AssetType.STOCK,
        )

        # Should return list of Transaction models
        assert isinstance(transactions, list)
        assert len(transactions) > 0
