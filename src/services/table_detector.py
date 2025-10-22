"""Table detection service to find headers in raw data."""

from typing import Tuple, List, Any
import pandas as pd


class TableDetector:
    """Detects table headers in raw DataFrames where header may not be at top."""

    def __init__(self, max_rows_to_scan: int = 50, min_columns: int = 2):
        """
        Initialize table detector.

        Args:
            max_rows_to_scan: Maximum number of rows to scan for header
            min_columns: Minimum number of columns for valid table
        """
        self.max_rows_to_scan = max_rows_to_scan
        self.min_columns = min_columns

    def detect_header_row_from_rows(self, rows: List[List[Any]]) -> int:
        """
        Detect which row contains the table header from raw row data.

        This is more efficient than loading into DataFrame first.

        Args:
            rows: List of rows (each row is a list of values)

        Returns:
            Row index where header is located (0-based)
        """
        if not rows:
            return 0

        best_score = -1
        best_row = 0

        for idx, row in enumerate(rows):
            score = self._score_header_row_from_list(rows, idx)
            if score > best_score:
                best_score = score
                best_row = idx

        return best_row

    def _score_header_row_from_list(self, rows: List[List[Any]], row_idx: int) -> float:
        """
        Score a row's likelihood of being a header from raw row data.

        Higher score = more likely to be header.
        """
        if row_idx >= len(rows):
            return 0.0

        row = rows[row_idx]
        score = 0.0

        if not row or len(row) == 0:
            return 0.0

        # Factor 1: Non-null/non-empty values (weight: 30%)
        non_null_count = sum(
            1 for val in row if val is not None and str(val).strip() != ""
        )
        non_null_ratio = non_null_count / len(row)
        score += non_null_ratio * 0.3

        # Factor 2: String values (weight: 25%)
        string_count = sum(
            1 for val in row if isinstance(val, str) and val.strip() != ""
        )
        string_ratio = string_count / len(row)
        score += string_ratio * 0.25

        # Factor 3: Unique values (weight: 20%)
        non_null_values = [
            val for val in row if val is not None and str(val).strip() != ""
        ]
        if non_null_values:
            unique_ratio = len(set(str(v) for v in non_null_values)) / len(
                non_null_values
            )
            score += unique_ratio * 0.2

        # Factor 4: Subsequent rows have numeric data (weight: 25%)
        if row_idx + 1 < len(rows):
            next_rows = rows[row_idx + 1 : min(row_idx + 6, len(rows))]
            if next_rows:
                numeric_score = self._score_numeric_content_from_lists(next_rows)
                score += numeric_score * 0.25

        return score

    def _score_numeric_content_from_lists(self, rows: List[List[Any]]) -> float:
        """Score how much numeric content is in the raw rows."""
        if not rows:
            return 0.0

        numeric_cells = 0
        total_cells = 0

        for row in rows:
            for val in row:
                if val is not None and str(val).strip() != "":
                    total_cells += 1
                    if isinstance(val, (int, float)) or self._is_numeric_string(val):
                        numeric_cells += 1

        return numeric_cells / max(total_cells, 1)

    def detect_header_row(self, df: pd.DataFrame) -> int:
        """
        Detect which row contains the table header.

        Strategy:
        1. Find rows with mostly non-null, string values
        2. Check for consistent data types in subsequent rows
        3. Prefer rows with unique values

        Args:
            df: Raw DataFrame with no assumed header

        Returns:
            Row index where header is located (0-based)
        """
        if df.empty:
            return 0

        rows_to_scan = min(self.max_rows_to_scan, len(df))
        best_score = -1
        best_row = 0

        for idx in range(rows_to_scan):
            score = self._score_header_row(df, idx)
            if score > best_score:
                best_score = score
                best_row = idx

        return best_row

    def _score_header_row(self, df: pd.DataFrame, row_idx: int) -> float:
        """
        Score a row's likelihood of being a header.

        Higher score = more likely to be header.
        """
        if row_idx >= len(df):
            return 0.0

        row = df.iloc[row_idx]
        score = 0.0

        # Factor 1: Non-null values (weight: 30%)
        non_null_ratio = row.notna().sum() / len(row)
        score += non_null_ratio * 0.3

        # Factor 2: String values (weight: 25%)
        string_ratio = sum(isinstance(val, str) for val in row) / len(row)
        score += string_ratio * 0.25

        # Factor 3: Unique values (weight: 20%)
        unique_ratio = len(set(row.dropna())) / max(len(row.dropna()), 1)
        score += unique_ratio * 0.2

        # Factor 4: Subsequent rows have numeric data (weight: 25%)
        if row_idx + 1 < len(df):
            next_rows = df.iloc[row_idx + 1 : row_idx + 6]  # Check next 5 rows
            if not next_rows.empty:
                numeric_score = self._score_numeric_content(next_rows)
                score += numeric_score * 0.25

        return score

    def _score_numeric_content(self, df: pd.DataFrame) -> float:
        """Score how much numeric content is in the DataFrame."""
        if df.empty:
            return 0.0

        numeric_cells = 0
        total_cells = 0

        for col in df.columns:
            for val in df[col]:
                if pd.notna(val):
                    total_cells += 1
                    if isinstance(val, (int, float)) or self._is_numeric_string(val):
                        numeric_cells += 1

        return numeric_cells / max(total_cells, 1)

    def _is_numeric_string(self, val) -> bool:
        """Check if a string value represents a number."""
        if not isinstance(val, str):
            return False

        # Remove common formatting
        cleaned = val.replace(",", "").replace("$", "").replace("€", "").strip()

        try:
            float(cleaned)
            return True
        except ValueError:
            return False

    def extract_table(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """
        Extract the table from raw DataFrame by detecting header.

        Args:
            df: Raw DataFrame

        Returns:
            Tuple of (extracted DataFrame with proper header, header row index)
        """
        if df.empty:
            return df, 0

        header_row = self.detect_header_row(df)

        # Extract header names
        headers = df.iloc[header_row].astype(str).tolist()

        # Clean header names
        headers = [self._clean_header_name(h) for h in headers]

        # Make headers unique
        headers = self._make_headers_unique(headers)

        # Extract data rows (everything after header)
        data_df = df.iloc[header_row + 1 :].copy()
        data_df.columns = headers

        # Reset index
        data_df.reset_index(drop=True, inplace=True)

        # Drop completely empty rows
        data_df.dropna(how="all", inplace=True)

        return data_df, header_row

    def _clean_header_name(self, name: str) -> str:
        """Clean and normalize header name."""
        # Handle NaN and None
        if pd.isna(name) or name == "nan":
            return "unnamed"

        # Convert to string and clean
        name = str(name).strip().lower()

        # Replace spaces and special chars with underscore
        name = name.replace(" ", "_").replace("-", "_")

        # Remove non-alphanumeric except underscore
        name = "".join(c for c in name if c.isalnum() or c == "_")

        return name if name else "unnamed"

    def _make_headers_unique(self, headers: list) -> list:
        """Make header names unique by appending numbers to duplicates."""
        seen = {}
        unique_headers = []

        for header in headers:
            if header not in seen:
                seen[header] = 0
                unique_headers.append(header)
            else:
                seen[header] += 1
                unique_headers.append(f"{header}_{seen[header]}")

        return unique_headers
