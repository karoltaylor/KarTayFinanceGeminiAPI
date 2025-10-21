"""Main data processing pipeline."""

from pathlib import Path
from typing import Optional, Dict, List

from ..loaders import FileLoaderFactory
from ..services import ColumnMapper, TransactionMapper
from ..models import (
    Transaction,
    TransactionType,
    AssetType,
    PyObjectId,
)
from ..config.settings import Settings


class DataPipeline:
    """Orchestrates the complete data import and transformation pipeline."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        db=None,
        user_id=None,
    ):
        """
        Initialize pipeline with required services.

        Args:
            api_key: Google API key (uses Settings if None)
            model_name: GenAI model name (uses Settings if None)
            db: MongoDB database instance for caching (optional)
            user_id: User ID for per-user cache isolation (optional)
        """
        self.file_loader = FileLoaderFactory()
        self.column_mapper = ColumnMapper(
            api_key=api_key, model_name=model_name, db=db, user_id=user_id
        )
        self.transaction_mapper = TransactionMapper(
            api_key=api_key, model_name=model_name
        )
        self.target_columns = Settings.TARGET_COLUMNS

    def process_file_to_transactions(
        self,
        filepath: str | Path,
        wallet_id: PyObjectId,
        user_id: PyObjectId,
        default_values: Optional[Dict[str, any]] = None,
        wallets_collection=None,
        assets_collection=None,
    ) -> tuple[List[Transaction], List[dict]]:
        """
        Process a file and convert to Transaction models.

        Steps:
        1. Load file with automatic header detection
        2. Map columns using AI to TransactionRecord schema (including transaction_type detection)
        3. Calculate missing values (asset_price from volume & amount)
        4. Determine asset types automatically
        5. Convert to Transaction models with wallet/asset references

        Args:
            filepath: Path to the file to process
            wallet_id: ID of the wallet for these transactions
            user_id: User ID who owns the wallet
            default_values: Default values for unmapped columns
            wallets_collection: MongoDB wallets collection (optional)
            assets_collection: MongoDB assets collection (optional)

        Returns:
            Tuple of (successful_transactions, error_records)
        """
        filepath = Path(filepath)

        # Step 1: Load file with automatic header detection
        table_df = self.file_loader.load_file(filepath)

        # Step 2: Map columns using AI (with caching based on file type)
        file_type = filepath.suffix.lower().lstrip(".")
        column_mapping = self.column_mapper.map_columns(
            table_df, self.target_columns, file_type=file_type
        )

        # Step 3: Apply mapping
        mapped_df = self.column_mapper.apply_mapping(
            table_df, column_mapping, default_values
        )

        # Step 4: Convert to Transaction models (returns transactions and errors)
        transactions, error_records = self.transaction_mapper.dataframe_to_transactions(
            df=mapped_df,
            wallet_id=wallet_id,
            user_id=user_id,
            wallets_collection=wallets_collection,
            assets_collection=assets_collection,
        )

        return transactions, error_records
