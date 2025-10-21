"""Tests for data pipeline."""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from src.pipeline.data_pipeline import DataPipeline
from src.models import TransactionType, AssetType
from bson import ObjectId

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


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
        csv_content = """Date,Asset,Price,Quantity,Total,Fee,Currency,Transaction Type
2024-01-10,AAPL,150.50,10,1505.00,5.00,USD,buy
2024-01-11,GOOGL,140.00,5,700.00,3.00,USD,sell
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
            "currency": "Currency",
            "transaction_type": "Transaction Type"
        }"""
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        pipeline = DataPipeline(api_key="test_key")
        user_id = ObjectId()
        wallet_id = ObjectId()  # Mock wallet ID

        # Process file to transactions
        transactions, errors = pipeline.process_file_to_transactions(
            filepath=filepath,
            wallet_id=wallet_id,
            user_id=user_id,
        )

        # Should return list of Transaction models
        assert isinstance(transactions, list)
        assert len(transactions) > 0

    @patch("src.pipeline.data_pipeline.ColumnMapper")
    @patch("src.pipeline.data_pipeline.TransactionMapper")
    @patch("src.pipeline.data_pipeline.FileLoaderFactory")
    def test_pipeline_initialization_with_mocks(
        self, mock_factory, mock_transaction_mapper, mock_column_mapper
    ):
        """Test pipeline initialization with mocked dependencies."""
        mock_loader = MagicMock()
        mock_factory.return_value = mock_loader

        pipeline = DataPipeline(api_key="test_key")

        assert pipeline.file_loader == mock_loader
        assert pipeline.column_mapper is not None
        assert pipeline.transaction_mapper is not None

    @patch("src.pipeline.data_pipeline.ColumnMapper")
    @patch("src.pipeline.data_pipeline.TransactionMapper")
    @patch("src.pipeline.data_pipeline.FileLoaderFactory")
    def test_process_file_with_empty_file(
        self, mock_factory, mock_transaction_mapper, mock_column_mapper, temp_dir
    ):
        """Test processing empty file."""
        mock_loader = MagicMock()
        mock_factory.return_value = mock_loader

        # Create empty CSV file
        filepath = temp_dir / "empty.csv"
        filepath.write_text("")

        mock_loader.load_file.return_value = pd.DataFrame()

        # Mock column mapper to return empty mapping
        mock_column_mapper_instance = MagicMock()
        mock_column_mapper_instance.map_columns.return_value = {}
        mock_column_mapper_instance.apply_mapping.return_value = pd.DataFrame()
        mock_column_mapper.return_value = mock_column_mapper_instance

        # Mock transaction mapper to raise ValueError for empty data
        mock_transaction_mapper_instance = MagicMock()
        mock_transaction_mapper_instance.dataframe_to_transactions.side_effect = (
            ValueError("No data to process")
        )
        mock_transaction_mapper.return_value = mock_transaction_mapper_instance

        pipeline = DataPipeline(api_key="test_key")

        with pytest.raises(ValueError, match="No data to process"):
            pipeline.process_file_to_transactions(str(filepath), ObjectId(), ObjectId())

    @patch("src.pipeline.data_pipeline.ColumnMapper")
    @patch("src.pipeline.data_pipeline.TransactionMapper")
    @patch("src.pipeline.data_pipeline.FileLoaderFactory")
    def test_process_file_with_invalid_file(
        self, mock_factory, mock_transaction_mapper, mock_column_mapper
    ):
        """Test processing invalid file."""
        mock_loader = MagicMock()
        mock_factory.return_value = mock_loader
        mock_loader.load_file.side_effect = Exception("File not found")

        pipeline = DataPipeline(api_key="test_key")

        with pytest.raises(Exception, match="File not found"):
            pipeline.process_file_to_transactions(
                "nonexistent.csv", ObjectId(), ObjectId()
            )

    @patch("src.pipeline.data_pipeline.ColumnMapper")
    @patch("src.pipeline.data_pipeline.TransactionMapper")
    @patch("src.pipeline.data_pipeline.FileLoaderFactory")
    def test_process_file_column_mapping_error(
        self, mock_factory, mock_transaction_mapper, mock_column_mapper, temp_dir
    ):
        """Test processing file with column mapping error."""
        mock_loader = MagicMock()
        mock_factory.create_loader.return_value = mock_loader

        # Create CSV file
        csv_content = "Date,Asset,Price\n2024-01-10,AAPL,150.50"
        filepath = temp_dir / "test.csv"
        filepath.write_text(csv_content)

        mock_loader.load_file.return_value = pd.DataFrame(
            {"Date": ["2024-01-10"], "Asset": ["AAPL"], "Price": [150.50]}
        )

        mock_column_mapper_instance = MagicMock()
        mock_column_mapper_instance.map_columns.side_effect = Exception(
            "Column mapping failed"
        )
        mock_column_mapper.return_value = mock_column_mapper_instance

        pipeline = DataPipeline(api_key="test_key")

        with pytest.raises(Exception, match="Column mapping failed"):
            pipeline.process_file_to_transactions(str(filepath), ObjectId(), ObjectId())

    @patch("src.pipeline.data_pipeline.ColumnMapper")
    @patch("src.pipeline.data_pipeline.TransactionMapper")
    @patch("src.pipeline.data_pipeline.FileLoaderFactory")
    def test_process_file_transaction_mapping_error(
        self, mock_factory, mock_transaction_mapper, mock_column_mapper, temp_dir
    ):
        """Test processing file with transaction mapping error."""
        mock_loader = MagicMock()
        mock_factory.return_value = mock_loader

        # Create CSV file
        csv_content = "Date,Asset,Price\n2024-01-10,AAPL,150.50"
        filepath = temp_dir / "test.csv"
        filepath.write_text(csv_content)

        mock_loader.load_file.return_value = pd.DataFrame(
            {"Date": ["2024-01-10"], "Asset": ["AAPL"], "Price": [150.50]}
        )

        mock_column_mapper_instance = MagicMock()
        mock_column_mapper_instance.map_columns.return_value = {
            "date": "Date",
            "asset_name": "Asset",
            "item_price": "Price",
        }
        mock_column_mapper_instance.apply_mapping.return_value = pd.DataFrame(
            {"date": ["2024-01-10"], "asset_name": ["AAPL"], "item_price": [150.50]}
        )
        mock_column_mapper.return_value = mock_column_mapper_instance

        mock_transaction_mapper_instance = MagicMock()
        mock_transaction_mapper_instance.dataframe_to_transactions.side_effect = (
            Exception("Transaction mapping failed")
        )
        mock_transaction_mapper.return_value = mock_transaction_mapper_instance

        pipeline = DataPipeline(api_key="test_key")

        with pytest.raises(Exception, match="Transaction mapping failed"):
            pipeline.process_file_to_transactions(str(filepath), ObjectId(), ObjectId())

    @patch("src.pipeline.data_pipeline.ColumnMapper")
    @patch("src.pipeline.data_pipeline.TransactionMapper")
    @patch("src.pipeline.data_pipeline.FileLoaderFactory")
    def test_process_file_with_large_dataset(
        self, mock_factory, mock_transaction_mapper, mock_column_mapper, temp_dir
    ):
        """Test processing file with large dataset."""
        mock_loader = MagicMock()
        mock_factory.return_value = mock_loader

        # Create CSV file with many rows
        csv_content = "Date,Asset,Price,Quantity,Total,Fee,Currency,Transaction Type\n"
        for i in range(100):
            csv_content += (
                f"2024-01-{i%30+1:02d},STOCK{i},100.00,10,1000.00,5.00,USD,buy\n"
            )

        filepath = temp_dir / "large.csv"
        filepath.write_text(csv_content)

        # Create large DataFrame
        data = []
        for i in range(100):
            data.append(
                {
                    "Date": f"2024-01-{i%30+1:02d}",
                    "Asset": f"STOCK{i}",
                    "Price": 100.00,
                    "Quantity": 10,
                    "Total": 1000.00,
                    "Fee": 5.00,
                    "Currency": "USD",
                    "Transaction Type": "buy",
                }
            )

        mock_loader.load_file.return_value = pd.DataFrame(data)

        mock_column_mapper_instance = MagicMock()
        mock_column_mapper_instance.map_columns.return_value = {
            "date": "Date",
            "asset_name": "Asset",
            "item_price": "Price",
            "volume": "Quantity",
            "transaction_amount": "Total",
            "fee": "Fee",
            "currency": "Currency",
            "transaction_type": "Transaction Type",
        }
        mock_column_mapper_instance.apply_mapping.return_value = pd.DataFrame(data)
        mock_column_mapper.return_value = mock_column_mapper_instance

        mock_transaction_mapper_instance = MagicMock()
        mock_transaction_mapper_instance.dataframe_to_transactions.return_value = (
            [
                {
                    "asset_name": f"STOCK{i}",
                    "date": f"2024-01-{i%30+1:02d}",
                    "item_price": 100.00,
                    "volume": 10,
                    "transaction_amount": 1000.00,
                    "fee": 5.00,
                    "currency": "USD",
                    "transaction_type": TransactionType.BUY,
                }
                for i in range(100)
            ],
            [],  # Empty error list
        )
        mock_transaction_mapper.return_value = mock_transaction_mapper_instance

        pipeline = DataPipeline(api_key="test_key")

        transactions, errors = pipeline.process_file_to_transactions(
            str(filepath), ObjectId(), ObjectId()
        )

        assert len(transactions) == 100
        assert all(tx["transaction_type"] == TransactionType.BUY for tx in transactions)

    @patch("src.pipeline.data_pipeline.ColumnMapper")
    @patch("src.pipeline.data_pipeline.TransactionMapper")
    @patch("src.pipeline.data_pipeline.FileLoaderFactory")
    def test_process_file_with_mixed_data_types(
        self, mock_factory, mock_transaction_mapper, mock_column_mapper, temp_dir
    ):
        """Test processing file with mixed data types."""
        mock_loader = MagicMock()
        mock_factory.return_value = mock_loader

        # Create CSV file with mixed data
        csv_content = """Date,Asset,Price,Quantity,Total,Fee,Currency,Transaction Type
2024-01-10,AAPL,150.50,10,1505.00,5.00,USD,buy
2024-01-11,GOOGL,140.00,5,700.00,3.00,USD,sell
2024-01-12,BTC,50000.00,0.1,5000.00,25.00,USD,buy
2024-01-13,ETH,3000.00,2,6000.00,30.00,USD,sell
"""
        filepath = temp_dir / "mixed.csv"
        filepath.write_text(csv_content)

        mock_loader.load_file.return_value = pd.DataFrame(
            {
                "Date": ["2024-01-10", "2024-01-11", "2024-01-12", "2024-01-13"],
                "Asset": ["AAPL", "GOOGL", "BTC", "ETH"],
                "Price": [150.50, 140.00, 50000.00, 3000.00],
                "Quantity": [10, 5, 0.1, 2],
                "Total": [1505.00, 700.00, 5000.00, 6000.00],
                "Fee": [5.00, 3.00, 25.00, 30.00],
                "Currency": ["USD", "USD", "USD", "USD"],
                "Transaction Type": ["buy", "sell", "buy", "sell"],
            }
        )

        mock_column_mapper_instance = MagicMock()
        mock_column_mapper_instance.map_columns.return_value = {
            "date": "Date",
            "asset_name": "Asset",
            "item_price": "Price",
            "volume": "Quantity",
            "transaction_amount": "Total",
            "fee": "Fee",
            "currency": "Currency",
            "transaction_type": "Transaction Type",
        }
        mock_column_mapper_instance.apply_mapping.return_value = pd.DataFrame(
            {
                "date": ["2024-01-10", "2024-01-11", "2024-01-12", "2024-01-13"],
                "asset_name": ["AAPL", "GOOGL", "BTC", "ETH"],
                "item_price": [150.50, 140.00, 50000.00, 3000.00],
                "volume": [10, 5, 0.1, 2],
                "transaction_amount": [1505.00, 700.00, 5000.00, 6000.00],
                "fee": [5.00, 3.00, 25.00, 30.00],
                "currency": ["USD", "USD", "USD", "USD"],
                "transaction_type": ["buy", "sell", "buy", "sell"],
            }
        )
        mock_column_mapper.return_value = mock_column_mapper_instance

        mock_transaction_mapper_instance = MagicMock()
        mock_transaction_mapper_instance.dataframe_to_transactions.return_value = (
            [
                {
                    "asset_name": "AAPL",
                    "date": "2024-01-10",
                    "item_price": 150.50,
                    "volume": 10,
                    "transaction_amount": 1505.00,
                    "fee": 5.00,
                    "currency": "USD",
                    "transaction_type": TransactionType.BUY,
                },
                {
                    "asset_name": "GOOGL",
                    "date": "2024-01-11",
                    "item_price": 140.00,
                    "volume": 5,
                    "transaction_amount": 700.00,
                    "fee": 3.00,
                    "currency": "USD",
                    "transaction_type": TransactionType.SELL,
                },
                {
                    "asset_name": "BTC",
                    "date": "2024-01-12",
                    "item_price": 50000.00,
                    "volume": 0.1,
                    "transaction_amount": 5000.00,
                    "fee": 25.00,
                    "currency": "USD",
                    "transaction_type": TransactionType.BUY,
                },
                {
                    "asset_name": "ETH",
                    "date": "2024-01-13",
                    "item_price": 3000.00,
                    "volume": 2,
                    "transaction_amount": 6000.00,
                    "fee": 30.00,
                    "currency": "USD",
                    "transaction_type": TransactionType.SELL,
                },
            ],
            [],  # Empty error list
        )
        mock_transaction_mapper.return_value = mock_transaction_mapper_instance

        pipeline = DataPipeline(api_key="test_key")

        transactions, errors = pipeline.process_file_to_transactions(
            str(filepath), ObjectId(), ObjectId()
        )

        assert len(transactions) == 4
        assert transactions[0]["asset_name"] == "AAPL"
        assert transactions[1]["asset_name"] == "GOOGL"
        assert transactions[2]["asset_name"] == "BTC"
        assert transactions[3]["asset_name"] == "ETH"
        assert transactions[0]["transaction_type"] == TransactionType.BUY
        assert transactions[1]["transaction_type"] == TransactionType.SELL
        assert transactions[2]["transaction_type"] == TransactionType.BUY
        assert transactions[3]["transaction_type"] == TransactionType.SELL

    @patch("src.pipeline.data_pipeline.ColumnMapper")
    @patch("src.pipeline.data_pipeline.TransactionMapper")
    @patch("src.pipeline.data_pipeline.FileLoaderFactory")
    def test_process_file_with_nonexistent_file(
        self, mock_factory, mock_transaction_mapper, mock_column_mapper
    ):
        """Test processing nonexistent file."""
        mock_loader = MagicMock()
        mock_factory.return_value = mock_loader
        mock_loader.load_file.side_effect = FileNotFoundError("File not found")

        pipeline = DataPipeline(api_key="test_key")

        with pytest.raises(FileNotFoundError, match="File not found"):
            pipeline.process_file_to_transactions(
                "nonexistent.csv", ObjectId(), ObjectId()
            )

    @patch("src.pipeline.data_pipeline.ColumnMapper")
    @patch("src.pipeline.data_pipeline.TransactionMapper")
    @patch("src.pipeline.data_pipeline.FileLoaderFactory")
    def test_process_file_with_permission_error(
        self, mock_factory, mock_transaction_mapper, mock_column_mapper
    ):
        """Test processing file with permission error."""
        mock_loader = MagicMock()
        mock_factory.return_value = mock_loader
        mock_loader.load_file.side_effect = PermissionError("Permission denied")

        pipeline = DataPipeline(api_key="test_key")

        with pytest.raises(PermissionError, match="Permission denied"):
            pipeline.process_file_to_transactions(
                "protected.csv", ObjectId(), ObjectId()
            )

    @patch("src.pipeline.data_pipeline.ColumnMapper")
    @patch("src.pipeline.data_pipeline.TransactionMapper")
    @patch("src.pipeline.data_pipeline.FileLoaderFactory")
    def test_process_file_with_corrupted_data(
        self, mock_factory, mock_transaction_mapper, mock_column_mapper, temp_dir
    ):
        """Test processing file with corrupted data."""
        mock_loader = MagicMock()
        mock_factory.return_value = mock_loader

        # Create CSV file with corrupted data
        csv_content = """Date,Asset,Price,Quantity,Total,Fee,Currency,Transaction Type
2024-01-10,AAPL,invalid_price,10,1505.00,5.00,USD,buy
2024-01-11,GOOGL,140.00,invalid_quantity,700.00,3.00,USD,sell
"""
        filepath = temp_dir / "corrupted.csv"
        filepath.write_text(csv_content)

        mock_loader.load_file.return_value = pd.DataFrame(
            {
                "Date": ["2024-01-10", "2024-01-11"],
                "Asset": ["AAPL", "GOOGL"],
                "Price": ["invalid_price", 140.00],
                "Quantity": [10, "invalid_quantity"],
                "Total": [1505.00, 700.00],
                "Fee": [5.00, 3.00],
                "Currency": ["USD", "USD"],
                "Transaction Type": ["buy", "sell"],
            }
        )

        mock_column_mapper_instance = MagicMock()
        mock_column_mapper_instance.map_columns.return_value = {
            "date": "Date",
            "asset_name": "Asset",
            "item_price": "Price",
            "volume": "Quantity",
            "transaction_amount": "Total",
            "fee": "Fee",
            "currency": "Currency",
            "transaction_type": "Transaction Type",
        }
        mock_column_mapper_instance.apply_mapping.return_value = pd.DataFrame(
            {
                "date": ["2024-01-10", "2024-01-11"],
                "asset_name": ["AAPL", "GOOGL"],
                "item_price": ["invalid_price", 140.00],
                "volume": [10, "invalid_quantity"],
                "transaction_amount": [1505.00, 700.00],
                "fee": [5.00, 3.00],
                "currency": ["USD", "USD"],
                "transaction_type": ["buy", "sell"],
            }
        )
        mock_column_mapper.return_value = mock_column_mapper_instance

        mock_transaction_mapper_instance = MagicMock()
        mock_transaction_mapper_instance.dataframe_to_transactions.side_effect = (
            ValueError("Invalid data format")
        )
        mock_transaction_mapper.return_value = mock_transaction_mapper_instance

        pipeline = DataPipeline(api_key="test_key")

        with pytest.raises(ValueError, match="Invalid data format"):
            pipeline.process_file_to_transactions(str(filepath), ObjectId(), ObjectId())
