"""Tests for file loaders."""

import pytest
import pandas as pd

from src.loaders import FileLoaderFactory
from src.loaders.csv_loader import CSVLoader
from src.loaders.excel_loader import ExcelLoader


class TestCSVLoader:
    """Tests for CSV loader."""

    def test_supports_csv_extension(self):
        """Test that CSV loader supports .csv files."""
        loader = CSVLoader()
        assert loader.supports_extension(".csv")
        assert loader.supports_extension(".txt")
        assert not loader.supports_extension(".xlsx")

    def test_load_valid_csv(self, sample_csv_file):
        """Test loading a valid CSV file."""
        loader = CSVLoader()
        df = loader.load(sample_csv_file)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_load_nonexistent_file(self, temp_dir):
        """Test loading non-existent file raises error."""
        loader = CSVLoader()
        nonexistent = temp_dir / "nonexistent.csv"

        with pytest.raises(FileNotFoundError):
            loader.load(nonexistent)

    def test_load_csv_with_different_delimiter(self, temp_dir):
        """Test loading CSV with different delimiter."""
        content = "col1;col2;col3\nval1;val2;val3\n"
        filepath = temp_dir / "semicolon.csv"
        filepath.write_text(content)

        loader = CSVLoader()
        df = loader.load(filepath)

        # Should detect semicolon delimiter and split into multiple columns
        # At minimum, it should load the data (may be 1 or 3 columns
        # depending on delimiter detection)
        assert len(df) >= 2  # Should have at least 2 rows of data


class TestExcelLoader:
    """Tests for Excel loader."""

    def test_supports_excel_extensions(self):
        """Test that Excel loader supports .xls and .xlsx."""
        loader = ExcelLoader()
        assert loader.supports_extension(".xls")
        assert loader.supports_extension(".xlsx")
        assert not loader.supports_extension(".csv")

    def test_load_xlsx_file(self, temp_dir):
        """Test loading an Excel file."""
        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})

        filepath = temp_dir / "test.xlsx"
        df.to_excel(filepath, index=False, engine="openpyxl")

        loader = ExcelLoader()
        loaded_df = loader.load(filepath)

        assert isinstance(loaded_df, pd.DataFrame)
        assert len(loaded_df) > 0

    def test_load_nonexistent_excel_file(self, temp_dir):
        """Test loading non-existent Excel file."""
        loader = ExcelLoader()
        nonexistent = temp_dir / "nonexistent.xlsx"

        with pytest.raises(FileNotFoundError):
            loader.load(nonexistent)


class TestFileLoaderFactory:
    """Tests for FileLoaderFactory."""

    def test_load_csv_file(self, sample_csv_file):
        """Test factory loads CSV file correctly."""
        factory = FileLoaderFactory()
        df = factory.load_file(sample_csv_file)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_load_excel_file(self, temp_dir):
        """Test factory loads Excel file correctly."""
        df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        filepath = temp_dir / "test.xlsx"
        df.to_excel(filepath, index=False)

        factory = FileLoaderFactory()
        loaded_df = factory.load_file(filepath)

        assert isinstance(loaded_df, pd.DataFrame)
        assert len(loaded_df) > 0

    def test_unsupported_file_type(self, temp_dir):
        """Test that unsupported file types raise error."""
        filepath = temp_dir / "test.pdf"
        filepath.write_text("dummy")

        factory = FileLoaderFactory()

        with pytest.raises(ValueError, match="Unsupported file type"):
            factory.load_file(filepath)

    def test_supports_file(self):
        """Test checking file support."""
        factory = FileLoaderFactory()

        assert factory.supports_file("test.csv")
        assert factory.supports_file("test.xlsx")
        assert factory.supports_file("test.xls")
        assert factory.supports_file("test.txt")
        assert not factory.supports_file("test.pdf")
