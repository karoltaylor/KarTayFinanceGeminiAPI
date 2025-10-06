"""Service for mapping TransactionRecords to MongoDB Transaction models."""

from typing import Dict, List, Optional
import pandas as pd
from bson import ObjectId

from ..models import (
    TransactionRecord,
    Transaction,
    TransactionType,
    Wallet,
    Asset,
    AssetType,
    PyObjectId,
)


class TransactionMapper:
    """Maps TransactionRecords to MongoDB Transaction models."""

    def __init__(self):
        """Initialize transaction mapper."""
        self._wallet_cache: Dict[str, PyObjectId] = {}
        self._asset_cache: Dict[str, PyObjectId] = {}

    def _convert_to_numeric(self, series: pd.Series) -> pd.Series:
        """
        Convert a series to numeric, handling various formats.

        Handles:
        - Comma decimal separators (e.g., "1,50" -> 1.50)
        - Thousands separators (e.g., "1 000,50" -> 1000.50)
        - Already numeric values

        Args:
            series: Pandas Series to convert

        Returns:
            Series with numeric values
        """
        if pd.api.types.is_numeric_dtype(series):
            return series

        def convert_value(val):
            if pd.isna(val) or val is None:
                return None
            if isinstance(val, (int, float)):
                return float(val)

            # Convert to string and clean
            str_val = str(val).strip()
            if not str_val:
                return None

            # Replace comma with dot (European decimal separator)
            str_val = str_val.replace(",", ".")
            # Remove spaces (thousands separator)
            str_val = str_val.replace(" ", "")

            try:
                return float(str_val)
            except ValueError:
                return None

        return series.apply(convert_value)

    def calculate_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate missing values in the DataFrame.

        If asset_price is missing but volume and transaction_amount exist,
        calculate: asset_price = transaction_amount / volume

        Args:
            df: DataFrame with TransactionRecord data

        Returns:
            DataFrame with calculated values
        """
        df = df.copy()

        # Convert numeric columns to proper numeric types
        numeric_cols = ["asset_price", "volume", "transaction_amount", "fee"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = self._convert_to_numeric(df[col])

        # Calculate asset_price if missing
        if "asset_price" not in df.columns:
            if "volume" in df.columns and "transaction_amount" in df.columns:
                df["asset_price"] = df["transaction_amount"] / df["volume"]
        else:
            # Fill missing asset_price values
            mask = pd.isna(df["asset_price"]) | (df["asset_price"] == 0)
            if mask.any():
                valid_calc = (
                    pd.notna(df["volume"])
                    & pd.notna(df["transaction_amount"])
                    & (df["volume"] != 0)
                )
                df.loc[mask & valid_calc, "asset_price"] = (
                    df.loc[mask & valid_calc, "transaction_amount"]
                    / df.loc[mask & valid_calc, "volume"]
                )

        # Calculate transaction_amount if missing
        if "transaction_amount" not in df.columns:
            if "asset_price" in df.columns and "volume" in df.columns:
                df["transaction_amount"] = df["asset_price"] * df["volume"]
        else:
            # Fill missing transaction_amount values
            mask = pd.isna(df["transaction_amount"]) | (df["transaction_amount"] == 0)
            if mask.any():
                valid_calc = (
                    pd.notna(df["volume"])
                    & pd.notna(df["asset_price"])
                    & (df["volume"] != 0)
                )
                df.loc[mask & valid_calc, "transaction_amount"] = (
                    df.loc[mask & valid_calc, "asset_price"]
                    * df.loc[mask & valid_calc, "volume"]
                )

        # Ensure fee column exists with default value
        if "fee" not in df.columns:
            df["fee"] = 0.0
        else:
            df["fee"] = df["fee"].fillna(0.0)

        # Ensure currency column exists with default value
        if "currency" not in df.columns:
            df["currency"] = "USD"  # Default currency
        else:
            df["currency"] = df["currency"].fillna("USD")

        return df

    def get_or_create_wallet(
        self, wallet_name: str, user_id: PyObjectId, wallets_collection=None
    ) -> PyObjectId:
        """
        Get or create a wallet by name for a specific user.

        Args:
            wallet_name: Name of the wallet
            user_id: User ID who owns the wallet
            wallets_collection: MongoDB collection (if None, creates in memory)

        Returns:
            PyObjectId of the wallet
        """
        cache_key = f"{user_id}:{wallet_name}"
        if cache_key in self._wallet_cache:
            return self._wallet_cache[cache_key]

        # If collection is provided, try to find in DB
        if wallets_collection is not None:
            existing = wallets_collection.find_one({"name": wallet_name, "user_id": user_id})
            if existing:
                wallet_id = PyObjectId(existing["_id"])
                self._wallet_cache[cache_key] = wallet_id
                return wallet_id

            # Create new wallet in DB
            wallet = Wallet(user_id=user_id, name=wallet_name)
            result = wallets_collection.insert_one(wallet.model_dump(by_alias=True, exclude={"id"}, mode='python'))
            wallet_id = PyObjectId(result.inserted_id)
            self._wallet_cache[cache_key] = wallet_id
            return wallet_id

        # Create in-memory wallet
        wallet = Wallet(user_id=user_id, name=wallet_name)
        self._wallet_cache[cache_key] = wallet.id
        return wallet.id

    def get_or_create_asset(
        self,
        asset_name: str,
        asset_type: AssetType = AssetType.OTHER,
        symbol: Optional[str] = None,
        assets_collection=None,
    ) -> PyObjectId:
        """
        Get or create an asset by name.

        Args:
            asset_name: Name of the asset
            asset_type: Type of the asset
            symbol: Asset symbol/ticker
            assets_collection: MongoDB collection (if None, creates in memory)

        Returns:
            PyObjectId of the asset
        """
        cache_key = f"{asset_name}:{asset_type.value}"
        if cache_key in self._asset_cache:
            return self._asset_cache[cache_key]

        # If collection is provided, try to find in DB
        if assets_collection is not None:
            existing = assets_collection.find_one({"asset_name": asset_name})
            if existing:
                asset_id = PyObjectId(existing["_id"])
                self._asset_cache[cache_key] = asset_id
                return asset_id

            # Create new asset in DB
            asset = Asset(asset_name=asset_name, asset_type=asset_type, symbol=symbol)
            result = assets_collection.insert_one(asset.model_dump(by_alias=True))
            asset_id = PyObjectId(result.inserted_id)
            self._asset_cache[cache_key] = asset_id
            return asset_id

        # Create in-memory asset
        asset = Asset(asset_name=asset_name, asset_type=asset_type, symbol=symbol)
        self._asset_cache[cache_key] = asset.id
        return asset.id

    def dataframe_to_transactions(
        self,
        df: pd.DataFrame,
        wallet_name: str,
        user_id: PyObjectId,
        transaction_type: TransactionType = TransactionType.BUY,
        asset_type: AssetType = AssetType.OTHER,
        wallets_collection=None,
        assets_collection=None,
    ) -> List[Transaction]:
        """
        Convert a DataFrame of TransactionRecords to Transaction models.

        Args:
            df: DataFrame with TransactionRecord columns
            wallet_name: Name of the wallet for these transactions
            user_id: User ID who owns the wallet
            transaction_type: Type of transactions (default: BUY)
            asset_type: Default asset type if not specified
            wallets_collection: MongoDB wallets collection (optional)
            assets_collection: MongoDB assets collection (optional)

        Returns:
            List of Transaction models
        """
        # Calculate missing values
        df = self.calculate_missing_values(df)

        # Get or create wallet
        wallet_id = self.get_or_create_wallet(wallet_name, user_id, wallets_collection)

        transactions = []
        errors = []

        for idx, row in df.iterrows():
            try:
                # Create TransactionRecord first for validation
                record = TransactionRecord(**row.to_dict())

                # Get or create asset
                asset_id = self.get_or_create_asset(
                    asset_name=record.asset_name,
                    asset_type=asset_type,
                    assets_collection=assets_collection,
                )

                # Convert to Transaction
                transaction = Transaction.from_transaction_record(
                    record=record,
                    wallet_id=wallet_id,
                    asset_id=asset_id,
                    transaction_type=transaction_type,
                )

                transactions.append(transaction)

            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")
                continue

        if errors:
            print(f"Warning: {len(errors)} records failed conversion:")
            for error in errors[:5]:
                print(f"  - {error}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more errors")

        return transactions

    def transaction_records_to_transactions(
        self,
        records: List[TransactionRecord],
        wallet_name: str,
        user_id: PyObjectId,
        transaction_type: TransactionType = TransactionType.BUY,
        asset_type: AssetType = AssetType.OTHER,
        wallets_collection=None,
        assets_collection=None,
    ) -> List[Transaction]:
        """
        Convert a list of TransactionRecords to Transaction models.

        Args:
            records: List of TransactionRecord instances
            wallet_name: Name of the wallet for these transactions
            user_id: User ID who owns the wallet
            transaction_type: Type of transactions (default: BUY)
            asset_type: Default asset type if not specified
            wallets_collection: MongoDB wallets collection (optional)
            assets_collection: MongoDB assets collection (optional)

        Returns:
            List of Transaction models
        """
        # Get or create wallet
        wallet_id = self.get_or_create_wallet(wallet_name, user_id, wallets_collection)

        transactions = []

        for record in records:
            # Get or create asset
            asset_id = self.get_or_create_asset(
                asset_name=record.asset_name,
                asset_type=asset_type,
                assets_collection=assets_collection,
            )

            # Convert to Transaction
            transaction = Transaction.from_transaction_record(
                record=record,
                wallet_id=wallet_id,
                asset_id=asset_id,
                transaction_type=transaction_type,
            )

            transactions.append(transaction)

        return transactions

    def insert_transactions(
        self, transactions: List[Transaction], transactions_collection
    ) -> List[ObjectId]:
        """
        Insert transactions into MongoDB.

        Args:
            transactions: List of Transaction models
            transactions_collection: MongoDB transactions collection

        Returns:
            List of inserted ObjectIds
        """
        if not transactions:
            return []

        # Convert to dicts for MongoDB
        transaction_dicts = [t.model_dump(by_alias=True) for t in transactions]

        # Insert into MongoDB
        result = transactions_collection.insert_many(transaction_dicts)

        return result.inserted_ids

    def clear_cache(self):
        """Clear wallet and asset caches."""
        self._wallet_cache.clear()
        self._asset_cache.clear()
