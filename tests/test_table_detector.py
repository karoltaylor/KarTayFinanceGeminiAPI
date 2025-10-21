"""Tests for table detection service."""

import pandas as pd
import pytest

from src.services.table_detector import TableDetector

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestTableDetector:
    """Tests for TableDetector."""

    def test_detect_header_at_top(self):
        """Test detecting header when it's at the top."""
        df = pd.DataFrame(
            [["Name", "Age", "City"], ["Alice", 30, "NYC"], ["Bob", 25, "LA"]]
        )

        detector = TableDetector()
        header_row = detector.detect_header_row(df)

        assert header_row == 0

    def test_detect_header_not_at_top(self):
        """Test detecting header when it's not at the top."""
        df = pd.DataFrame(
            [
                ["Report Title", None, None],
                ["Generated: 2024-01-01", None, None],
                [None, None, None],
                ["Name", "Age", "City"],
                ["Alice", 30, "NYC"],
                ["Bob", 25, "LA"],
            ]
        )

        detector = TableDetector()
        header_row = detector.detect_header_row(df)

        assert header_row == 3

    def test_extract_table_with_header_at_top(self):
        """Test extracting table when header is at top."""
        df = pd.DataFrame(
            [["Name", "Age", "City"], ["Alice", 30, "NYC"], ["Bob", 25, "LA"]]
        )

        detector = TableDetector()
        extracted_df, header_idx = detector.extract_table(df)

        assert header_idx == 0
        assert "name" in extracted_df.columns
        assert len(extracted_df) == 2

    def test_extract_table_with_header_not_at_top(self):
        """Test extracting table when header is not at top."""
        df = pd.DataFrame(
            [
                ["Title Row", None, None],
                ["Subtitle", None, None],
                ["Name", "Age", "City"],
                ["Alice", 30, "NYC"],
                ["Bob", 25, "LA"],
            ]
        )

        detector = TableDetector()
        extracted_df, header_idx = detector.extract_table(df)

        assert header_idx == 2
        assert "name" in extracted_df.columns
        assert len(extracted_df) == 2
        assert extracted_df.iloc[0]["name"] == "Alice"

    def test_clean_header_names(self):
        """Test that header names are cleaned properly."""
        df = pd.DataFrame(
            [["User Name", "Age (years)", "Home-City"], ["Alice", 30, "NYC"]]
        )

        detector = TableDetector()
        extracted_df, _ = detector.extract_table(df)

        assert "user_name" in extracted_df.columns
        assert "age_years" in extracted_df.columns
        assert "home_city" in extracted_df.columns

    def test_make_headers_unique(self):
        """Test that duplicate headers are made unique."""
        df = pd.DataFrame([["Name", "Name", "Age"], ["Alice", "Smith", 30]])

        detector = TableDetector()
        extracted_df, _ = detector.extract_table(df)

        # Should have unique column names
        assert len(extracted_df.columns) == len(set(extracted_df.columns))
        assert "name" in extracted_df.columns
        assert "name_1" in extracted_df.columns

    def test_empty_dataframe(self):
        """Test handling empty DataFrame."""
        df = pd.DataFrame()

        detector = TableDetector()
        extracted_df, header_idx = detector.extract_table(df)

        assert extracted_df.empty
        assert header_idx == 0

    def test_score_header_row_with_strings(self):
        """Test that rows with strings score higher."""
        df = pd.DataFrame(
            [
                [1, 2, 3],  # numeric row
                ["Name", "Age", "City"],  # string row (likely header)
                [10, 20, 30],
            ]
        )

        detector = TableDetector()
        score_numeric = detector._score_header_row(df, 0)
        score_string = detector._score_header_row(df, 1)

        assert score_string > score_numeric

    def test_drop_empty_rows(self):
        """Test that empty rows are dropped from extracted table."""
        df = pd.DataFrame(
            [["Name", "Age"], ["Alice", 30], [None, None], ["Bob", 25]]  # empty row
        )

        detector = TableDetector()
        extracted_df, _ = detector.extract_table(df)

        # Should have 2 data rows (empty row dropped)
        assert len(extracted_df) == 2

    def test_is_numeric_string(self):
        """Test numeric string detection."""
        detector = TableDetector()

        assert detector._is_numeric_string("123")
        assert detector._is_numeric_string("123.45")
        assert detector._is_numeric_string("$100.50")
        assert detector._is_numeric_string("1,234.56")
        assert not detector._is_numeric_string("abc")
        assert not detector._is_numeric_string("12abc")
