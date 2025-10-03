"""Example usage of the KarTayFinance Data Importer.

This script demonstrates how to use the data import pipeline.
"""

from pathlib import Path
from src.pipeline import DataPipeline
from src.config.settings import Settings


def main():
    """Main example function."""

    # Validate that API key is configured
    try:
        Settings.validate()
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("\nPlease:")
        print("1. Copy .env.example to .env")
        print("2. Add your Google API key to the .env file")
        return

    # Initialize the pipeline
    print("Initializing data import pipeline...")
    pipeline = DataPipeline()

    # Example 1: Preview column mapping without processing
    print("\n" + "=" * 80)
    print("Example 1: Preview Column Mapping")
    print("=" * 80)

    example_file = "path/to/your/data.csv"  # Change this to your file

    if Path(example_file).exists():
        try:
            preview = pipeline.get_column_mapping_preview(example_file)

            print(f"\nFile: {example_file}")
            print(f"Header detected at row: {preview['header_row_index']}")
            print(f"Total data rows: {preview['total_rows']}")
            print(f"\nSource columns: {preview['source_columns']}")
            print(f"\nColumn mapping:")
            for target, source in preview["column_mapping"].items():
                print(f"  {target:20s} <- {source}")
            print(f"\nSample data (first 3 rows):")
            for i, row in enumerate(preview["sample_data"], 1):
                print(f"  Row {i}: {row}")

        except Exception as e:
            print(f"Error previewing file: {e}")
    else:
        print(f"Example file not found: {example_file}")
        print("Update 'example_file' variable with path to your data file.")

    # Example 2: Process a single file
    print("\n" + "=" * 80)
    print("Example 2: Process Single File")
    print("=" * 80)

    if Path(example_file).exists():
        try:
            print(f"\nProcessing: {example_file}")

            # Optional: provide default values for unmapped columns
            defaults = {"currency": "USD", "asset_type": "Unknown"}

            result = pipeline.process_file(example_file, default_values=defaults)

            print(f"\nSuccessfully processed {len(result.df)} records")

            # Display summary
            summary = result.get_summary()
            print(f"\nSummary:")
            print(f"  Total records: {summary['total_records']}")
            print(f"  Unique wallets: {summary['unique_wallets']}")
            print(f"  Unique assets: {summary['unique_assets']}")
            print(
                f"  Date range: {
                    summary['date_range']['min']} to {
                    summary['date_range']['max']}"
            )

            # Show first few records
            if len(result.df) > 0:
                print(f"\nFirst 5 records:")
                print(result.df.head().to_string())

                # Export results
                result.to_csv("output_data.csv")
                print(f"\nData exported to: output_data.csv")

        except Exception as e:
            print(f"Error processing file: {e}")

    # Example 3: Process multiple files
    print("\n" + "=" * 80)
    print("Example 3: Process Multiple Files")
    print("=" * 80)

    files = ["data/file1.csv", "data/file2.xlsx", "data/file3.txt"]

    # Filter to only existing files
    existing_files = [f for f in files if Path(f).exists()]

    if existing_files:
        try:
            print(f"\nProcessing {len(existing_files)} files...")

            result = pipeline.process_multiple_files(
                existing_files, default_values={"currency": "USD"}
            )

            print(f"\nCombined result: {len(result.df)} total records")

            # Export combined data
            result.to_excel("combined_output.xlsx")
            print(f"Combined data exported to: combined_output.xlsx")

        except Exception as e:
            print(f"Error processing files: {e}")
    else:
        print("No example files found. Create some test files to try this example.")

    # Example 4: Working with the data model directly
    print("\n" + "=" * 80)
    print("Example 4: Direct Model Usage")
    print("=" * 80)

    from src.models import FinancialRecord, FinancialDataModel

    try:
        # Create individual records
        records = [
            FinancialRecord(
                wallet_name="MyWallet",
                asset_name="AAPL",
                asset_type="Stock",
                date="2024-01-10",
                asset_item_price=150.50,
                volume=10,
                currency="USD",
            ),
            FinancialRecord(
                wallet_name="MyWallet",
                asset_name="BTC",
                asset_type="Crypto",
                date="2024-01-11",
                asset_item_price=45000.00,
                volume=0.5,
                currency="USD",
            ),
        ]

        # Create model and add records
        model = FinancialDataModel()
        model.add_records(records)

        print(f"\nCreated {len(model.df)} records manually")
        print(model.df.to_string())

    except Exception as e:
        print(f"Error creating records: {e}")

    print("\n" + "=" * 80)
    print("Examples complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
