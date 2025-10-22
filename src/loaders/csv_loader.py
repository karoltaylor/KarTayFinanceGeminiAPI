"""CSV and TXT file loader."""

from pathlib import Path
from typing import Iterator, List, Any
import csv
import pandas as pd
import chardet
from .base_loader import BaseFileLoader


class CSVLoader(BaseFileLoader):
    """Loader for CSV and TXT files."""

    SUPPORTED_EXTENSIONS = {".csv", ".txt"}

    def supports_extension(self, extension: str) -> bool:
        """Check if extension is supported."""
        return extension.lower() in self.SUPPORTED_EXTENSIONS

    def _detect_delimiter(self, filepath: Path) -> str:
        """Detect the delimiter used in the CSV file."""
        self.validate_file(filepath)

        # First detect the encoding
        encoding = self._detect_encoding(filepath)

        # Try reading first few lines to detect delimiter
        try:
            with open(filepath, "r", encoding=encoding) as f:
                sample = f.read(8192)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                return delimiter
        except Exception:
            pass

        # If sniffer fails, try each delimiter and pick the one with most columns
        delimiters = [",", "\t", ";", "|"]
        best_delimiter = ","
        max_columns = 0

        for delimiter in delimiters:
            try:
                with open(filepath, "r", encoding=encoding) as f:
                    reader = csv.reader(f, delimiter=delimiter)
                    first_row = next(reader)
                    if len(first_row) > max_columns:
                        max_columns = len(first_row)
                        best_delimiter = delimiter
            except Exception:
                continue

        return best_delimiter

    def _detect_encoding(self, filepath: Path) -> str:
        """Detect file encoding using chardet."""
        # Read a sample of the file in binary mode
        with open(filepath, "rb") as f:
            raw_data = f.read(10000)  # Read first 10KB for detection

        # Detect encoding
        result = chardet.detect(raw_data)
        encoding = result["encoding"]

        # Fallback to utf-8 if detection fails
        if encoding is None:
            return "utf-8"

        # Handle common encoding aliases
        encoding = encoding.lower()
        if encoding in ("ascii", "us-ascii"):
            return "utf-8"  # ASCII is a subset of UTF-8

        return encoding

    def read_rows(self, filepath: Path, max_rows: int = 50) -> Iterator[List[Any]]:
        """
        Read CSV file row by row.

        Args:
            filepath: Path to the CSV file
            max_rows: Maximum number of rows to read

        Yields:
            List of values for each row
        """
        self.validate_file(filepath)

        delimiter = self._detect_delimiter(filepath)
        encoding = self._detect_encoding(filepath)

        with open(filepath, "r", encoding=encoding) as f:
            reader = csv.reader(f, delimiter=delimiter)
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                yield row

    def load_from_row(self, filepath: Path, header_row: int) -> pd.DataFrame:
        """
        Load CSV starting from a specific header row.

        Args:
            filepath: Path to the CSV file
            header_row: Row index where header is located (0-based)

        Returns:
            DataFrame with proper header and data
        """
        self.validate_file(filepath)

        delimiter = self._detect_delimiter(filepath)
        encoding = self._detect_encoding(filepath)

        # Skip rows before the header, then use the next row as header
        # Note: skiprows=header_row means skip rows 0 to header_row-1,
        # then row header_row becomes the header (header=0)
        if header_row > 0:
            df = pd.read_csv(
                filepath,
                delimiter=delimiter,
                encoding=encoding,
                skiprows=header_row,
                header=0,
                on_bad_lines="skip",
            )
        else:
            # If header is at row 0, no need to skip
            df = pd.read_csv(
                filepath,
                delimiter=delimiter,
                encoding=encoding,
                header=0,
                on_bad_lines="skip",
            )

        return df

    def load(self, filepath: Path) -> pd.DataFrame:
        """
        Load CSV or TXT file into DataFrame.

        Attempts to detect delimiter automatically.
        """
        self.validate_file(filepath)

        # Try different delimiters
        delimiters = [",", "\t", ";", "|"]

        for delimiter in delimiters:
            try:
                df = pd.read_csv(
                    filepath,
                    delimiter=delimiter,
                    header=None,
                    on_bad_lines="skip",
                    encoding="utf-8",
                )

                # Check if we got a reasonable table
                if len(df.columns) > 1 or len(df) > 0:
                    return df

            except Exception:
                continue

        # Fallback: try with default settings
        try:
            df = pd.read_csv(filepath, header=None, on_bad_lines="skip", encoding="utf-8")
            return df
        except UnicodeDecodeError:
            # Try different encoding
            df = pd.read_csv(filepath, header=None, on_bad_lines="skip", encoding="latin-1")
            return df
