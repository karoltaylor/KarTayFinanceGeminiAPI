# KarTayFinance Google API Data Importer

A modularized Python application for importing financial data from various file formats (CSV, TXT, XLS, XLSX), intelligently mapping columns using Google GenAI, and loading into a validated data model.

## Features

- **Multi-Format Support**: Load data from CSV, TXT, XLS, and XLSX files
- **Smart Table Detection**: Automatically finds table headers even when they're not at the top of the file
- **AI-Powered Column Mapping**: Uses Google's Generative AI to intelligently map source columns to target schema
- **Data Validation**: Pydantic-based validation ensures data quality
- **Pandas Integration**: Seamless data manipulation and export capabilities
- **High Test Coverage**: >80% code coverage with comprehensive unit tests
- **Best Practices**: Modular design, type hints, documentation, and error handling

## Project Structure

```
KarTayFinanceGoogleAPI/
├── src/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          # Configuration and environment variables
│   ├── models/
│   │   ├── __init__.py
│   │   └── data_model.py        # Financial data models with validation
│   ├── loaders/
│   │   ├── __init__.py
│   │   ├── base_loader.py       # Abstract base loader
│   │   ├── csv_loader.py        # CSV/TXT loader
│   │   ├── excel_loader.py      # Excel loader
│   │   └── file_loader_factory.py  # Factory pattern for loaders
│   ├── services/
│   │   ├── __init__.py
│   │   ├── table_detector.py    # Smart table header detection
│   │   └── column_mapper.py     # AI-powered column mapping
│   └── pipeline/
│       ├── __init__.py
│       └── data_pipeline.py     # Main orchestration pipeline
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── test_config.py
│   ├── test_data_model.py
│   ├── test_loaders.py
│   ├── test_table_detector.py
│   ├── test_column_mapper.py
│   └── test_pipeline.py
├── requirements.txt
├── pytest.ini
├── .env.example
├── .gitignore
└── README.md
```

## Target Data Model

The application maps imported data to the following schema:

| Column | Type | Description |
|--------|------|-------------|
| `wallet_name` | string | Name of the wallet or account |
| `asset_name` | string | Name of the asset (stock, crypto, etc.) |
| `asset_type` | string | Type of asset (stock, crypto, bond, etc.) |
| `date` | datetime | Transaction or record date |
| `asset_item_price` | float | Price per unit/item of the asset |
| `volume` | float | Quantity or number of assets |
| `currency` | string | Currency code (USD, EUR, etc.) |

## Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd KarTayFinanceGoogleAPI
```

2. **Create a virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env and add your Google API key
```

## Configuration

Create a `.env` file in the project root with the following variables:

```env
GOOGLE_API_KEY=your_google_api_key_here
GENAI_MODEL=gemini-1.5-flash
```

To get a Google API key:
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add it to your `.env` file

## Usage

### Basic Usage

```python
from src.pipeline import DataPipeline

# Initialize pipeline
pipeline = DataPipeline()

# Process a single file
result = pipeline.process_file("path/to/your/file.csv")

# Access the data
df = result.to_dataframe()
print(df.head())

# Get summary statistics
summary = result.get_summary()
print(summary)

# Export results
result.to_csv("output.csv")
result.to_excel("output.xlsx")
```

### Processing Multiple Files

```python
from src.pipeline import DataPipeline

pipeline = DataPipeline()

files = ["file1.csv", "file2.xlsx", "file3.txt"]
result = pipeline.process_multiple_files(files)

print(f"Processed {len(result.df)} total records")
```

### Preview Column Mapping

```python
from src.pipeline import DataPipeline

pipeline = DataPipeline()

# Preview how columns will be mapped before processing
preview = pipeline.get_column_mapping_preview("data.csv")

print("Source columns:", preview["source_columns"])
print("Column mapping:", preview["column_mapping"])
print("Sample data:", preview["sample_data"])
```

### Using Default Values

```python
from src.pipeline import DataPipeline

pipeline = DataPipeline()

# Provide default values for unmapped columns
defaults = {
    "wallet_name": "DefaultWallet",
    "currency": "USD",
    "asset_type": "Unknown"
}

result = pipeline.process_file("data.csv", default_values=defaults)
```

### Direct Model Usage

```python
from src.models import FinancialRecord, FinancialDataModel

# Create individual records
record = FinancialRecord(
    wallet_name="MyWallet",
    asset_name="AAPL",
    asset_type="Stock",
    date="2024-01-10",
    asset_item_price=150.50,
    volume=10,
    currency="USD"
)

# Create and populate data model
model = FinancialDataModel()
model.add_record(record)

# Load from pandas DataFrame
import pandas as pd
df = pd.DataFrame({...})
errors = model.load_from_dataframe(df)
if errors:
    print("Validation errors:", errors)
```

## Running Tests

Run all tests with coverage:

```bash
pytest
```

Run specific test file:

```bash
pytest tests/test_pipeline.py
```

Run with verbose output:

```bash
pytest -v
```

Generate HTML coverage report:

```bash
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in your browser
```

## Architecture

### Design Patterns

- **Factory Pattern**: `FileLoaderFactory` creates appropriate loaders based on file type
- **Strategy Pattern**: Different loaders implement `BaseFileLoader` interface
- **Pipeline Pattern**: `DataPipeline` orchestrates the complete workflow
- **Repository Pattern**: `FinancialDataModel` abstracts data storage

### Key Components

1. **File Loaders**: Modular loaders for different file formats
   - Automatic delimiter detection for CSV/TXT
   - Support for various Excel formats
   - Extensible to add new formats

2. **Table Detector**: Intelligent header detection
   - Scans rows to find most likely header
   - Scores based on data types and patterns
   - Handles metadata rows before tables

3. **Column Mapper**: AI-powered mapping
   - Uses Google GenAI to understand column semantics
   - Maps source columns to target schema
   - Provides confidence and validation

4. **Data Model**: Type-safe data handling
   - Pydantic validation for data quality
   - Multiple date format support
   - Export to various formats

## Best Practices Implemented

- ✅ **Type Hints**: Full type annotations throughout
- ✅ **Documentation**: Comprehensive docstrings
- ✅ **Error Handling**: Graceful error handling and validation
- ✅ **Logging**: Structured error reporting
- ✅ **Testing**: >80% test coverage
- ✅ **Modularity**: Single Responsibility Principle
- ✅ **Configuration**: Environment-based config
- ✅ **Dependency Injection**: Testable components
- ✅ **Design Patterns**: Factory, Strategy, Pipeline
- ✅ **Clean Code**: PEP 8 compliant

## Troubleshooting

### Common Issues

**Issue**: `ValueError: GOOGLE_API_KEY must be set`
- **Solution**: Create `.env` file with your Google API key

**Issue**: File not loading correctly
- **Solution**: Check file encoding, try different formats, verify file isn't corrupted

**Issue**: Column mapping seems incorrect
- **Solution**: Use `get_column_mapping_preview()` to inspect mapping before processing

**Issue**: Validation errors on data load
- **Solution**: Check data types, date formats, and ensure numeric fields don't have negative values

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure tests pass and coverage remains >80%
6. Submit a pull request

## License

[Your License Here]

## Support

For issues, questions, or contributions, please open an issue on the GitHub repository.

