"""MongoDB data models for financial tracking system."""

from datetime import datetime, timezone
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, info):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema

        return core_schema.union_schema(
            [
                core_schema.is_instance_schema(ObjectId),
                core_schema.no_info_plain_validator_function(cls.validate),
            ],
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
        )


class AssetType(str, Enum):
    """Enumeration of supported asset types."""

    BOND = "bond"
    STOCK = "stock"
    ETF = "etf"
    MANAGED_MUTUAL_FUND = "managed mutual fund"
    REAL_ESTATE = "real_estate"
    CRYPTOCURRENCY = "cryptocurrency"
    COMMODITY = "commodity"
    CASH = "cash"
    OTHER = "other"


class TransactionType(str, Enum):
    """Enumeration of transaction types."""

    BUY = "buy"
    SELL = "sell"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    FEE = "fee"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    OTHER = "other"


class User(BaseModel):
    """User model for authentication and authorization (OAuth-based)."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str},
    )

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    email: str = Field(..., min_length=3, max_length=255, description="User email")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    full_name: Optional[str] = Field(None, max_length=200, description="Full name")
    oauth_provider: Optional[str] = Field(None, max_length=50, description="OAuth provider (google, meta, etc.)")
    oauth_id: Optional[str] = Field(None, max_length=255, description="OAuth provider's user ID")
    is_active: bool = Field(default=True, description="Is user active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        v = v.strip().lower()
        
        # Basic email validation
        if not v:
            raise ValueError("Email cannot be empty")
        
        if "@" not in v:
            raise ValueError("Email must contain @")
        
        parts = v.split("@")
        if len(parts) != 2:
            raise ValueError("Email must have exactly one @")
        
        local, domain = parts
        
        if not local:
            raise ValueError("Email local part cannot be empty")
        
        if not domain:
            raise ValueError("Email domain cannot be empty")
        
        if "." not in domain:
            raise ValueError("Email domain must contain a dot")
        
        # Check for common invalid patterns
        if v.startswith("@") or v.endswith("@"):
            raise ValueError("Invalid email format")
        
        if v.startswith(".") or v.endswith("."):
            raise ValueError("Invalid email format")
        
        if ".." in v:
            raise ValueError("Invalid email format")
        
        # Additional strict validation
        if domain.startswith(".") or domain.endswith("."):
            raise ValueError("Invalid email format")
        
        # Check for valid domain structure (must have at least 2 parts after the dot)
        domain_parts = domain.split(".")
        if len(domain_parts) < 2:
            raise ValueError("Invalid email format")
        
        # Each domain part must be non-empty
        for part in domain_parts:
            if not part:
                raise ValueError("Invalid email format")
        
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Ensure username is alphanumeric and valid."""
        v = v.strip().lower()
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username must be alphanumeric (with _ or - allowed)")
        return v


class Wallet(BaseModel):
    """Wallet model for storing wallet information."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str},
    )

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId = Field(..., description="Reference to User who owns this wallet")
    name: str = Field(..., min_length=1, max_length=200, description="Wallet name")
    description: Optional[str] = Field(None, max_length=1000, description="Wallet description")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure wallet name is not empty after stripping."""
        if not v.strip():
            raise ValueError("Wallet name cannot be empty")
        return v.strip()


class Asset(BaseModel):
    """Asset model for storing asset information."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str},
    )

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    asset_name: str = Field(..., min_length=1, max_length=200, description="Asset name")
    asset_type: AssetType = Field(..., description="Type of asset")
    symbol: Optional[str] = Field(None, max_length=20, description="Asset symbol/ticker")
    url: Optional[str] = Field(None, max_length=500, description="URL to get current value")
    description: Optional[str] = Field(None, max_length=1000, description="Asset description")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("asset_name")
    @classmethod
    def validate_asset_name(cls, v: str) -> str:
        """Ensure asset name is not empty after stripping."""
        if not v.strip():
            raise ValueError("Asset name cannot be empty")
        return v.strip()

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format if provided."""
        if v is not None and v.strip():
            v = v.strip()
            if not (v.startswith("http://") or v.startswith("https://")):
                raise ValueError("URL must start with http:// or https://")
            return v
        return v


class AssetCurrentValue(BaseModel):
    """Asset current value model for tracking historical prices."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str},
    )

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    asset_id: PyObjectId = Field(..., description="Reference to Asset")
    date: datetime = Field(..., description="Date of the price")
    price: float = Field(..., gt=0, description="Price of the asset")
    currency: str = Field(
        ..., min_length=3, max_length=3, description="Currency code (ISO 4217)"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Ensure currency is uppercase and valid."""
        v = v.strip().upper()
        if len(v) != 3:
            raise ValueError("Currency code must be 3 characters (ISO 4217)")
        return v

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, v):
        """Parse various date formats."""
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Date cannot be empty")
            
            # Try common date formats with strict validation
            for fmt in [
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%m/%d/%Y",
                "%Y/%m/%d",
                "%d-%m-%Y",
                "%Y-%m-%d %H:%M:%S",
            ]:
                try:
                    parsed_date = datetime.strptime(v, fmt)
                    # Additional validation for reasonable date ranges
                    if parsed_date.year < 1900 or parsed_date.year > 2100:
                        raise ValueError(f"Date year {parsed_date.year} is out of reasonable range")
                    
                    # Additional validation for month/day ranges
                    if parsed_date.month < 1 or parsed_date.month > 12:
                        raise ValueError(f"Invalid month: {parsed_date.month}")
                    
                    if parsed_date.day < 1 or parsed_date.day > 31:
                        raise ValueError(f"Invalid day: {parsed_date.day}")
                    
                    return parsed_date
                except ValueError as e:
                    if "unconverted data remains" in str(e) or "time data" in str(e):
                        continue
                    raise
            raise ValueError(f"Unable to parse date: {v}")
        raise ValueError(f"Invalid date value: {v}")


class Transaction(BaseModel):
    """Transaction model for recording financial transactions."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str},
    )

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    wallet_id: PyObjectId = Field(..., description="Reference to Wallet")
    asset_id: PyObjectId = Field(..., description="Reference to Asset")
    date: datetime = Field(..., description="Transaction date")
    transaction_type: TransactionType = Field(..., description="Type of transaction")
    volume: float = Field(..., ge=0, description="Quantity/volume of assets")
    item_price: float = Field(..., ge=0, description="Price per item at transaction")
    transaction_amount: float = Field(..., description="Total transaction amount")
    currency: str = Field(
        ..., min_length=3, max_length=3, description="Currency code (ISO 4217)"
    )
    fee: float = Field(default=0.0, ge=0, description="Transaction fee")
    notes: Optional[str] = Field(None, max_length=1000, description="Transaction notes")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Ensure currency is uppercase and valid."""
        v = v.strip().upper()
        if len(v) != 3:
            raise ValueError("Currency code must be 3 characters (ISO 4217)")
        return v

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, v):
        """Parse various date formats."""
        import pandas as pd
        
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            # Try common date formats
            for fmt in [
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%m/%d/%Y",
                "%Y/%m/%d",
                "%d-%m-%Y",
                "%Y-%m-%d %H:%M:%S",
            ]:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue
            raise ValueError(f"Unable to parse date: {v}")
        
        # Handle pandas datetime objects (including NaT)
        if hasattr(v, '__class__') and 'pandas' in str(type(v)):
            if pd.isna(v):
                raise ValueError(f"Invalid date value: {v}")
            return v
            
        raise ValueError(f"Invalid date value: {v}")

    @field_validator("transaction_amount")
    @classmethod
    def validate_transaction_amount(cls, v: float, info) -> float:
        """Validate transaction amount consistency."""
        # Note: This validator runs after all fields are set in Pydantic v2
        # For cross-field validation, use model_validator
        return v

    @classmethod
    def from_transaction_record(
        cls,
        record,
        wallet_id: PyObjectId,
        asset_id: PyObjectId,
        transaction_type: TransactionType = TransactionType.BUY,
    ) -> "Transaction":
        """
        Create a Transaction from a TransactionRecord.

        Args:
            record: TransactionRecord instance
            wallet_id: MongoDB ObjectId of the wallet
            asset_id: MongoDB ObjectId of the asset
            transaction_type: Type of transaction (default: BUY)

        Returns:
            Transaction instance
        """
        return cls(
            wallet_id=wallet_id,
            asset_id=asset_id,
            date=record.date,
            transaction_type=transaction_type,
            volume=record.volume,
            item_price=record.asset_price,
            transaction_amount=record.transaction_amount,
            currency=record.currency,
            fee=record.fee,
        )


class TransactionError(BaseModel):
    """Model for storing failed transaction imports."""
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str},
    )
    
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId = Field(..., description="User who attempted the import")
    wallet_name: str = Field(..., description="Target wallet name")
    filename: str = Field(..., description="Original filename")
    row_index: int = Field(..., description="Row number in original file")
    raw_data: dict = Field(..., description="Raw row data that failed")
    error_message: str = Field(..., description="Error description")
    error_type: str = Field(..., description="Type of error (validation, parsing, etc)")
    transaction_type: str = Field(..., description="Intended transaction type")
    asset_type: str = Field(..., description="Intended asset type")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = Field(default=False, description="Whether error has been fixed")