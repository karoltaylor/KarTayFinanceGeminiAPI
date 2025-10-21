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
from .asset_type_mapper import AssetTypeMapper


class TransactionMapper:
    """Maps TransactionRecords to MongoDB Transaction models."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """Initialize transaction mapper."""
        self._wallet_cache: Dict[str, PyObjectId] = {}
        self._asset_cache: Dict[str, PyObjectId] = {}
        self.asset_type_mapper = AssetTypeMapper(api_key=api_key, model_name=model_name)

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
            # Convert to numeric first to avoid dtype warnings
            df["fee"] = pd.to_numeric(df["fee"], errors='coerce').fillna(0.0)

        # Ensure currency column exists with default value
        if "currency" not in df.columns:
            df["currency"] = "USD"  # Default currency
        else:
            df["currency"] = df["currency"].fillna("USD")

        # Ensure transaction_type column exists with default value
        if "transaction_type" not in df.columns:
            df["transaction_type"] = "buy"  # Default transaction type
        else:
            df["transaction_type"] = df["transaction_type"].fillna("buy")

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
            # Search with both ObjectId and string user_id to handle type inconsistencies
            existing = wallets_collection.find_one({
                "name": wallet_name, 
                "$or": [
                    {"user_id": user_id},
                    {"user_id": str(user_id)}
                ]
            })
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

            # Create new asset in DB - use AI to infer asset type and symbol
            ai_result = self.asset_type_mapper.infer_asset_info(asset_name)
            
            if ai_result:
                # Use AI-determined asset type and symbol
                inferred_asset_type = AssetType(ai_result["asset_type"])
                inferred_symbol = ai_result["symbol"] if ai_result["symbol"] else symbol
                asset = Asset(
                    asset_name=asset_name, 
                    asset_type=inferred_asset_type, 
                    symbol=inferred_symbol
                )
            else:
                # Fallback to provided values or OTHER if AI fails
                fallback_asset_type = asset_type if asset_type != AssetType.OTHER else AssetType.OTHER
                asset = Asset(
                    asset_name=asset_name, 
                    asset_type=fallback_asset_type, 
                    symbol=symbol
                )
            
            result = assets_collection.insert_one(asset.model_dump(by_alias=True, exclude={'id'}, mode='python'))
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
        wallet_id: PyObjectId,
        user_id: PyObjectId,
        wallets_collection=None,
        assets_collection=None,
    ) -> tuple[List[Transaction], List[dict]]:
        """
        Convert a DataFrame of TransactionRecords to Transaction models.

        Args:
            df: DataFrame with TransactionRecord columns (including transaction_type)
            wallet_id: ID of the wallet for these transactions
            user_id: User ID who owns the wallet
            wallets_collection: MongoDB wallets collection (optional)
            assets_collection: MongoDB assets collection (optional)

        Returns:
            Tuple of (successful_transactions, error_records)
        """
        # Calculate missing values
        df = self.calculate_missing_values(df)

        transactions = []
        error_records = []

        for idx, row in df.iterrows():
            try:
                # Create TransactionRecord first for validation
                record = TransactionRecord(**row.to_dict())

                # Determine transaction type from the record
                detected_transaction_type = self._parse_transaction_type(record.transaction_type)

                # Determine asset type automatically with caching and fallback
                asset_name_lower = record.asset_name.lower()
                
                # Simple heuristic-based detection to reduce API calls
                if any(keyword in asset_name_lower for keyword in ['akcji', 'stock', 'equity', 'share']):
                    detected_asset_type = AssetType.STOCK
                elif any(keyword in asset_name_lower for keyword in ['obligacje', 'bond', 'debt']):
                    detected_asset_type = AssetType.BOND
                elif any(keyword in asset_name_lower for keyword in ['krypto', 'crypto', 'bitcoin', 'ethereum']):
                    detected_asset_type = AssetType.CRYPTOCURRENCY
                elif any(keyword in asset_name_lower for keyword in ['złoto', 'gold', 'srebro', 'silver', 'commodity']):
                    detected_asset_type = AssetType.COMMODITY
                else:
                    # Only use AI for unclear cases, with fallback
                    try:
                        asset_info = self.asset_type_mapper.infer_asset_info(record.asset_name)
                        if asset_info and 'asset_type' in asset_info:
                            detected_asset_type = AssetType(asset_info['asset_type'])
                        else:
                            detected_asset_type = AssetType.OTHER
                    except Exception as e:
                        # Fallback to OTHER if AI fails (rate limits, etc.)
                        print(f"Warning: Asset type inference failed for '{record.asset_name}': {e}")
                        detected_asset_type = AssetType.OTHER

                # Get or create asset
                asset_id = self.get_or_create_asset(
                    asset_name=record.asset_name,
                    asset_type=detected_asset_type,
                    assets_collection=assets_collection,
                )

                # Convert to Transaction
                transaction = Transaction.from_transaction_record(
                    record=record,
                    wallet_id=wallet_id,
                    asset_id=asset_id,
                    transaction_type=detected_transaction_type,
                )

                transactions.append(transaction)

            except Exception as e:
                error_records.append({
                    "row_index": int(idx),
                    "raw_data": row.to_dict(),
                    "error_message": str(e),
                    "error_type": type(e).__name__
                })
                continue

        if error_records:
            print(f"Warning: {len(error_records)} records failed conversion:")
            for error in error_records[:5]:
                print(f"  - Row {error['row_index']}: {error['error_message']}")
            if len(error_records) > 5:
                print(f"  ... and {len(error_records) - 5} more errors")

        return transactions, error_records

    def _parse_transaction_type(self, transaction_type_str: str) -> TransactionType:
        """
        Parse transaction type string to TransactionType enum.
        
        Args:
            transaction_type_str: String representation of transaction type
            
        Returns:
            TransactionType enum value
        """
        if not transaction_type_str:
            return TransactionType.BUY  # Default fallback
            
        # Normalize the string
        normalized = str(transaction_type_str).strip().lower()
        
        # Map common transaction type strings to enum values
        type_mapping = {
            'buy': TransactionType.BUY,
            'purchase': TransactionType.BUY,
            'kupno': TransactionType.BUY,
            'nabycie': TransactionType.BUY,
            'sell': TransactionType.SELL,
            'sale': TransactionType.SELL,
            'sprzedaż': TransactionType.SELL,
            'odkupienie': TransactionType.SELL,
            'dividend': TransactionType.DIVIDEND,
            'dywidenda': TransactionType.DIVIDEND,
            'transfer_in': TransactionType.TRANSFER_IN,
            'transfer_out': TransactionType.TRANSFER_OUT,
            'deposit': TransactionType.TRANSFER_IN,
            'withdrawal': TransactionType.TRANSFER_OUT,
        }
        
        return type_mapping.get(normalized, TransactionType.BUY)

    def transaction_records_to_transactions(
        self,
        records: List[TransactionRecord],
        wallet_id: PyObjectId,
        user_id: PyObjectId,
        wallets_collection=None,
        assets_collection=None,
    ) -> List[Transaction]:
        """
        Convert a list of TransactionRecords to Transaction models.

        Args:
            records: List of TransactionRecord instances
            wallet_id: ID of the wallet for these transactions
            user_id: User ID who owns the wallet
            wallets_collection: MongoDB wallets collection (optional)
            assets_collection: MongoDB assets collection (optional)

        Returns:
            List of Transaction models
        """

        transactions = []

        for record in records:
            # Get or create asset
            asset_id = self.get_or_create_asset(
                asset_name=record.asset_name,
                asset_type=AssetType.OTHER,  # Default asset type
                assets_collection=assets_collection,
            )

            # Convert to Transaction
            transaction = Transaction.from_transaction_record(
                record=record,
                wallet_id=wallet_id,
                asset_id=asset_id,
                transaction_type=TransactionType(record.transaction_type),
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
        transaction_dicts = [t.model_dump(by_alias=True, exclude={'id'}, mode='python') for t in transactions]

        # Insert into MongoDB
        result = transactions_collection.insert_many(transaction_dicts)

        return result.inserted_ids


    def clear_cache(self):
        """Clear wallet and asset caches."""
        self._wallet_cache.clear()
        self._asset_cache.clear()
