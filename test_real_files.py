"""
Manual testing script for load_file method with real files.

This script creates sample files and tests the file loading functionality.
Run this to verify the file loaders work with actual files.
"""

import pandas as pd
from pathlib import Path
from src.loaders import FileLoaderFactory
import os
from src.pipeline import DataPipeline
from src.services import TableDetector, ColumnMapper
from src.config.settings import Settings


def test_load_file(filepath, show_mapping=True):
    """Test loading a single file with automatic header detection and column mapping."""
    print(f"\n{'=' * 70}")
    print(f"Testing: {filepath}")
    print(f"{'=' * 70}")

    try:
        # Initialize the factory with automatic header detection
        factory = FileLoaderFactory(detect_header=True)
        factory_raw = FileLoaderFactory(detect_header=False)

        # Check if file is supported
        if not factory.supports_file(filepath):
            print(f"[ERROR] File type not supported: {filepath.suffix}")
            return None, None

        # Step 1: Load raw file (for debugging info)
        print("\n[Step 1] Loading file...")
        raw_df = factory_raw.load_file(filepath)
        print(f"   Raw file shape: {raw_df.shape} (rows x columns)")

        # Step 2: Load with automatic header detection
        print("\n[Step 2] Loading with automatic header detection...")
        table_df = factory.load_file(filepath)

        # Detect header row for informational purposes
        detector = TableDetector()
        _, header_row = detector.extract_table(raw_df)

        print(f"   [OK] Header detected at row: {header_row}")
        print(f"   Loaded table shape: {table_df.shape} (rows x columns)")

        # Display detected headers
        print(f"\n[Headers] Detected {len(table_df.columns)} columns:")
        for i, col in enumerate(table_df.columns, 1):
            print(f"   {i:2d}. {col}")

        # Show sample data
        print(f"\n[Sample Data] First 3 rows:")
        print(table_df.head(3).to_string())

        # Step 3: Map to data model (if API key is available)
        mapping = None
        if show_mapping:
            print(f"\n[Step 3] AI Column Mapping to Data Model...")
            try:
                # Check if we have API key
                if (
                    Settings.GOOGLE_API_KEY
                    and Settings.GOOGLE_API_KEY != "your_google_api_key_here"
                ):
                    mapper = ColumnMapper()
                    mapping = mapper.map_columns(
                        table_df, Settings.TARGET_COLUMNS, sample_rows=3
                    )

                    print(f"   [OK] Mapping complete!")
                    print(f"\n[Column Mapping] Source -> Target:")
                    print(f"   {'Source Column':<30} -> {'Target Column':<25}")
                    print(f"   {'-' * 30}    {'-' * 25}")

                    for target_col in Settings.TARGET_COLUMNS:
                        source_col = mapping.get(target_col)
                        if source_col:
                            print(f"   {source_col:<30} -> {target_col:<25}")
                        else:
                            print(f"   {'[UNMAPPED]':<30} -> {target_col:<25} [!]")

                    # Show which source columns weren't mapped
                    mapped_sources = set(v for v in mapping.values() if v)
                    unmapped_sources = set(table_df.columns) - mapped_sources
                    if unmapped_sources:
                        print(
                            f"\n   [!] Unmapped source columns: {
                                ', '.join(unmapped_sources)}"
                        )
                else:
                    print(f"   [!] Skipping: No Google API key configured")
                    print(f"   To enable mapping: Set GOOGLE_API_KEY in .env file")

            except Exception as e:
                print(f"   [!] Mapping failed: {str(e)}")

        return table_df, mapping

    except Exception as e:
        print(f"[ERROR] Error loading file: {str(e)}")
        import traceback

        traceback.print_exc()
        return None, None


def test_all_files():
    """Test loading all sample files."""
    print("=" * 70)
    print("FILE LOADER TESTING - Real File Test")
    print("=" * 70)

    test_dir = Path("test_data")

    # Check if test_data directory exists
    if not test_dir.exists():
        print(f"⚠️  Test directory not found: {test_dir}")
        print("No files to test.")
        return

    # Get all files in test_data directory
    test_files = [f for f in test_dir.iterdir() if f.is_file()]

    if not test_files:
        print(f"⚠️  No files found in {test_dir}")
        return

    print(f"\nFound {len(test_files)} files to test:\n")
    for f in test_files:
        print(f"  - {f.name}")

    results = {}
    for filepath in test_files:
        table_df, mapping = test_load_file(filepath, show_mapping=True)
        results[filepath.name] = table_df is not None

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for filename, success in results.items():
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} - {filename}")

    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} files loaded successfully")


def test_with_pipeline():
    """Test with the complete pipeline (including table detection)."""

    print("\n" + "=" * 70)
    print("PIPELINE TEST - With Table Detection")
    print("=" * 70)

    test_dir = Path("test_data")

    # We need API key for column mapping, so we'll just test the preview
    try:
        pipeline = DataPipeline(api_key="test_key")

        test_file = test_dir / "sample_with_metadata.csv"
        if test_file.exists():
            print(f"\nTesting table detection on: {test_file}")

            # Load and detect table
            from src.loaders import FileLoaderFactory
            from src.services import TableDetector

            loader = FileLoaderFactory()
            raw_df = loader.load_file(test_file)

            print(f"\n📊 Raw data shape: {raw_df.shape}")
            print("\nRaw data (first 10 rows):")
            print(raw_df.head(10))

            detector = TableDetector()
            extracted_df, header_row = detector.extract_table(raw_df)

            print(f"\n✅ Table detected!")
            print(f"   Header found at row: {header_row}")
            print(f"   Extracted data shape: {extracted_df.shape}")
            print("\nExtracted table:")
            print(extracted_df.head())

    except Exception as e:
        print(f"Note: Pipeline test requires Google API key.")
        print(
            f"Use get_column_mapping_preview() with a real API key to test full pipeline."
        )


def test_single_file(filepath):
    """Quick test for a single file with full details."""
    print("=" * 70)
    print("SINGLE FILE TEST")
    print("=" * 70)

    filepath = Path(filepath)
    if not filepath.exists():
        print(f"[ERROR] File not found: {filepath}")
        return

    table_df, mapping = test_load_file(filepath, show_mapping=True)

    if table_df is not None:
        print("\n" + "=" * 70)
        print("[SUCCESS] Test Complete!")
        print("=" * 70)
        print(f"File: {filepath.name}")
        print(f"Rows: {len(table_df)}")
        print(f"Columns: {len(table_df.columns)}")
        if mapping:
            mapped_count = sum(1 for v in mapping.values() if v)
            print(f"Mapped columns: {mapped_count}/{len(mapping)}")


if __name__ == "__main__":
    import sys

    # Check if a specific file was provided as argument
    if len(sys.argv) > 1:
        # Test single file from command line argument
        test_single_file(sys.argv[1])
    else:
        # Run all tests
        test_all_files()

        # Test with pipeline
        test_with_pipeline()

    print("\n" + "=" * 70)
    print("[DONE] Testing complete!")
    print("=" * 70)
    print("\nUsage:")
    print("  Test all files:       python test_real_files.py")
    print("  Test single file:     python test_real_files.py path/to/file.xlsx")
    print("\nIn Python:")
    print("  from test_real_files import test_single_file")
    print("  test_single_file('test_data/your_file.csv')")
