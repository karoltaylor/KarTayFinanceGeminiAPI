"""Data models for financial records."""

from datetime import datetime
from typing import List
from pydantic import BaseModel, Field, field_validator
import pandas as pd


class TransactionRecord(BaseModel):
    """Individual transaction record with validation."""

    asset_name: str = Field(..., min_length=1, description="Name of the asset")
    date: datetime = Field(..., description="Transaction date")
    asset_price: float = Field(..., description="Price per item")
    volume: float = Field(..., description="Number of assets/volume")
    transaction_amount: float = Field(..., description="Total transaction amount")
    fee: float = Field(default=0.0, ge=0, description="Transaction fee")
    currency: str = Field(..., min_length=1, max_length=10, description="Currency code")
    transaction_type: str = Field(
        ..., description="Type of transaction (buy, sell, dividend, etc.)"
    )

    @field_validator("asset_price", "volume", "transaction_amount")
    @classmethod
    def validate_positive_numbers(cls, v: float, info) -> float:
        """Ensure financial values are positive."""
        if v < 0:
            raise ValueError(f"{info.field_name} must be non-negative")
        return v

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, v):
        """Parse various date formats."""
        # Check for pandas NaT first
        if hasattr(v, "__class__") and "pandas" in str(type(v)):
            if pd.isna(v):
                raise ValueError(f"Invalid date value: {v}")
            return v

        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            # Try common date formats (including European DD.MM.YYYY)
            for fmt in [
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%m/%d/%Y",
                "%Y/%m/%d",
                "%d-%m-%Y",
                "%d.%m.%Y",
                "%Y.%m.%d",
            ]:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue
            raise ValueError(f"Unable to parse date: {v}")

        if pd.notna(v):
            parsed_date = pd.to_datetime(v)
            # Check if pandas returned NaT (Not a Time) for invalid dates
            if pd.isna(parsed_date):
                raise ValueError(f"Invalid date value: {v}")
            return parsed_date

        raise ValueError(f"Invalid date value: {v}")


class FinancialDataModel:
    """Data model handler for transaction records using pandas."""

    def __init__(self):
        """Initialize empty DataFrame with required columns."""
        self.columns = [
            "asset_name",
            "date",
            "asset_price",
            "volume",
            "transaction_amount",
            "fee",
            "currency",
        ]
        self.df: pd.DataFrame = pd.DataFrame(columns=self.columns)

    def add_record(self, record: TransactionRecord) -> None:
        """Add a single validated record to the DataFrame."""
        record_dict = record.model_dump()
        new_row = pd.DataFrame([record_dict])
        self.df = pd.concat([self.df, new_row], ignore_index=True)

    def add_records(self, records: List[TransactionRecord]) -> None:
        """Add multiple validated records to the DataFrame."""
        if not records:
            return

        records_data = [record.model_dump() for record in records]
        new_df = pd.DataFrame(records_data)
        self.df = pd.concat([self.df, new_df], ignore_index=True)

    def load_from_dataframe(self, df: pd.DataFrame) -> List[str]:
        """
        Load data from a pandas DataFrame with validation.

        Returns:
            List of error messages for invalid records.
        """
        errors = []
        valid_records = []

        for idx, row in df.iterrows():
            try:
                record = TransactionRecord(**row.to_dict())
                valid_records.append(record)
            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")

        if valid_records:
            self.add_records(valid_records)

        return errors

    def to_dataframe(self) -> pd.DataFrame:
        """Return the underlying DataFrame."""
        return self.df.copy()

    def to_csv(self, filepath: str) -> None:
        """Export data to CSV."""
        self.df.to_csv(filepath, index=False)

    def to_excel(self, filepath: str) -> None:
        """Export data to Excel."""
        self.df.to_excel(filepath, index=False)

    def get_summary(self) -> dict:
        """Get summary statistics of the data."""
        return {
            "total_records": len(self.df),
            "unique_assets": (
                self.df["asset_name"].nunique() if len(self.df) > 0 else 0
            ),
            "total_transaction_amount": (
                self.df["transaction_amount"].sum() if len(self.df) > 0 else 0.0
            ),
            "total_fees": self.df["fee"].sum() if len(self.df) > 0 else 0.0,
            "date_range": {
                "min": self.df["date"].min() if len(self.df) > 0 else None,
                "max": self.df["date"].max() if len(self.df) > 0 else None,
            },
        }
