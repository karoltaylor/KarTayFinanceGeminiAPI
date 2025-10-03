"""Data models for financial records."""

from datetime import datetime
from typing import List
from pydantic import BaseModel, Field, field_validator
import pandas as pd


class FinancialRecord(BaseModel):
    """Individual financial record with validation."""

    wallet_name: str = Field(..., min_length=1, description="Name of the wallet")
    asset_name: str = Field(..., min_length=1, description="Name of the asset")
    asset_type: str = Field(..., min_length=1, description="Type of the asset")
    date: datetime = Field(..., description="Transaction date")
    asset_item_price: float = Field(..., description="Price per item")
    volume: float = Field(..., description="Number of assets/volume")
    currency: str = Field(..., min_length=1, max_length=10, description="Currency code")

    @field_validator("asset_item_price", "volume")
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
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            # Try common date formats
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"]:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue
            raise ValueError(f"Unable to parse date: {v}")
        if pd.notna(v):
            return pd.to_datetime(v)
        raise ValueError(f"Invalid date value: {v}")


class FinancialDataModel:
    """Data model handler for financial records using pandas."""

    def __init__(self):
        """Initialize empty DataFrame with required columns."""
        self.columns = [
            "wallet_name",
            "asset_name",
            "asset_type",
            "date",
            "asset_item_price",
            "volume",
            "currency",
        ]
        self.df: pd.DataFrame = pd.DataFrame(columns=self.columns)

    def add_record(self, record: FinancialRecord) -> None:
        """Add a single validated record to the DataFrame."""
        record_dict = record.model_dump()
        new_row = pd.DataFrame([record_dict])
        self.df = pd.concat([self.df, new_row], ignore_index=True)

    def add_records(self, records: List[FinancialRecord]) -> None:
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
                record = FinancialRecord(**row.to_dict())
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
            "unique_wallets": (
                self.df["wallet_name"].nunique() if len(self.df) > 0 else 0
            ),
            "unique_assets": self.df["asset_name"].nunique() if len(self.df) > 0 else 0,
            "date_range": {
                "min": self.df["date"].min() if len(self.df) > 0 else None,
                "max": self.df["date"].max() if len(self.df) > 0 else None,
            },
        }
