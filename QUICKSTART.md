# Quick Start Guide

## Installation

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up your Google API key:**
   - Get a free API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a `.env` file in the project root:
   ```env
   GOOGLE_API_KEY=your_api_key_here
   GENAI_MODEL=gemini-1.5-flash
   ```

## Basic Usage

### Example 1: Process a Single File

```python
from src.pipeline import DataPipeline

# Initialize pipeline
pipeline = DataPipeline()

# Process a file (CSV, TXT, XLS, or XLSX)
result = pipeline.process_file("path/to/your/financial_data.csv")

# Access the data as pandas DataFrame
df = result.to_dataframe()
print(df.head())

# Get summary statistics
summary = result.get_summary()
print(f"Total records: {summary['total_records']}")
print(f"Unique wallets: {summary['unique_wallets']}")
print(f"Date range: {summary['date_range']['min']} to {summary['date_range']['max']}")

# Export results
result.to_csv("output.csv")
result.to_excel("output.xlsx")
```

### Example 2: Preview Column Mapping

Before processing, you can preview how columns will be mapped:

```python
from src.pipeline import DataPipeline

pipeline = DataPipeline()

# Get a preview of the mapping
preview = pipeline.get_column_mapping_preview("your_file.csv")

print("Detected header at row:", preview['header_row_index'])
print("\nSource columns found:")
for col in preview['source_columns']:
    print(f"  - {col}")

print("\nColumn mapping:")
for target, source in preview['column_mapping'].items():
    print(f"  {target:20s} <- {source}")

print(f"\nTotal data rows: {preview['total_rows']}")
```

### Example 3: Process Multiple Files

```python
from src.pipeline import DataPipeline

pipeline = DataPipeline()

# Process multiple files at once
files = [
    "january_transactions.csv",
    "february_transactions.xlsx",
    "march_transactions.txt"
]

# Optional: provide default values for unmapped columns
defaults = {
    "currency": "USD",
    "asset_type": "Unknown"
}

result = pipeline.process_multiple_files(files, default_values=defaults)

print(f"Processed {len(result.df)} total records from {len(files)} files")

# Export combined data
result.to_excel("combined_report.xlsx")
```

### Example 4: Working with the Data Model Directly

```python
from src.models import FinancialRecord, FinancialDataModel
from datetime import datetime

# Create individual records
record1 = FinancialRecord(
    wallet_name="MyWallet",
    asset_name="AAPL",
    asset_type="Stock",
    date=datetime(2024, 1, 10),
    asset_item_price=150.50,
    volume=10,
    currency="USD"
)

record2 = FinancialRecord(
    wallet_name="CryptoWallet",
    asset_name="BTC",
    asset_type="Cryptocurrency",
    date="2024-01-15",  # String dates work too!
    asset_item_price=45000.00,
    volume=0.5,
    currency="USD"
)

# Create model and add records
model = FinancialDataModel()
model.add_records([record1, record2])

# Export
model.to_csv("manual_records.csv")
```

### Example 5: Load from Pandas DataFrame

```python
import pandas as pd
from src.models import FinancialDataModel

# You have data in a pandas DataFrame
df = pd.DataFrame({
    "wallet_name": ["Wallet1", "Wallet2"],
    "asset_name": ["AAPL", "GOOGL"],
    "asset_type": ["Stock", "Stock"],
    "date": ["2024-01-10", "2024-01-11"],
    "asset_item_price": [150.50, 2800.00],
    "volume": [10, 5],
    "currency": ["USD", "USD"]
})

# Load into model (with validation)
model = FinancialDataModel()
errors = model.load_from_dataframe(df)

if errors:
    print("Validation errors:")
    for error in errors:
        print(f"  - {error}")
else:
    print(f"Successfully loaded {len(model.df)} records!")
```

## Expected Data Format

The pipeline maps your data to this schema:

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `wallet_name` | string | Wallet/account name | "MyWallet" |
| `asset_name` | string | Asset name | "AAPL", "BTC" |
| `asset_type` | string | Type of asset | "Stock", "Crypto" |
| `date` | datetime | Transaction date | "2024-01-10" |
| `asset_item_price` | float | Price per unit | 150.50 |
| `volume` | float | Quantity | 10 or 0.5 |
| `currency` | string | Currency code | "USD", "EUR" |

**Your source file can have ANY column names** - the AI will map them automatically!

## Sample Input Files

### CSV Example (`financial_data.csv`)
```csv
Account,Stock Symbol,Type,Date,Price per Share,Shares,Curr
MyWallet,AAPL,Stock,2024-01-10,150.50,10,USD
MyWallet,MSFT,Stock,2024-01-11,380.25,5,USD
CryptoWallet,BTC,Crypto,2024-01-12,45000.00,0.5,USD
```

### Excel Example
Same structure works in Excel files (.xls, .xlsx):
- First row can be anywhere (AI finds the header)
- Supports metadata rows above the table
- Handles empty rows and columns

## Testing

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=src --cov-report=html
```

Run specific test file:
```bash
pytest tests/test_pipeline.py -v
```

## Troubleshooting

### Issue: "GOOGLE_API_KEY must be set"
**Solution**: Create a `.env` file with your Google API key

### Issue: File not loading
**Solution**: 
- Check file path is correct
- Verify file isn't corrupted
- Try different file format (CSV, XLSX)
- Check file encoding

### Issue: Column mapping seems wrong
**Solution**: Use `get_column_mapping_preview()` to inspect the mapping before processing

### Issue: Validation errors
**Solution**:
- Check date formats are valid
- Ensure numeric fields don't have negative values
- Verify required fields aren't empty
- Review error messages for specific issues

## Next Steps

1. Read the full [README.md](README.md) for detailed documentation
2. Check [example_usage.py](example_usage.py) for more examples
3. Review [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) for technical details
4. Explore the test files in `tests/` to understand all features

## Support

For issues or questions:
1. Check the README.md documentation
2. Review test examples in `tests/`
3. Open an issue on GitHub
4. Check that all dependencies are installed correctly

## License

[Your License Here]

