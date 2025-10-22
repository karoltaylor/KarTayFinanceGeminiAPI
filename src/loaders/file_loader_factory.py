"""Factory for creating appropriate file loaders."""

from pathlib import Path
from typing import List, Optional
import pandas as pd

from .base_loader import BaseFileLoader
from .csv_loader import CSVLoader
from .excel_loader import ExcelLoader


class FileLoaderFactory:
    """Factory for creating and managing file loaders."""

    def __init__(self, detect_header: bool = True):
        """
        Initialize factory with all available loaders.

        Args:
            detect_header: If True, automatically detect and extract table headers
        """
        self._loaders: List[BaseFileLoader] = [CSVLoader(), ExcelLoader()]
        self.detect_header = detect_header

    def load_file(self, filepath: str | Path, detect_header: Optional[bool] = None) -> pd.DataFrame:
        """
        Load a file using the appropriate loader with automatic header detection.

        Args:
            filepath: Path to the file to load
            detect_header: Override the instance setting for header detection

        Returns:
            DataFrame with properly detected headers and data

        Raises:
            ValueError: If file type is not supported
            FileNotFoundError: If file doesn't exist
        """
        filepath = Path(filepath)
        extension = filepath.suffix

        # Find appropriate loader
        loader = None
        for loader_impl in self._loaders:
            if loader_impl.supports_extension(extension):
                loader = loader_impl
                break

        if loader is None:
            raise ValueError(f"Unsupported file type: {extension}. " f"Supported types: .csv, .txt, .xls, .xlsx")

        return self._load_with_header_detection(loader, filepath)

    def _load_with_header_detection(self, loader: BaseFileLoader, filepath: Path) -> pd.DataFrame:
        """
        Load file with automatic header detection.

        New efficient approach:
        1. Read file row by row (not into DataFrame)
        2. Detect header row from raw rows
        3. Load file into pandas starting from header row

        Args:
            loader: The file loader to use
            filepath: Path to the file

        Returns:
            DataFrame with detected headers
        """
        from ..services.table_detector import TableDetector

        # Step 1: Read file row by row to find header
        detector = TableDetector()
        rows = list(loader.read_rows(filepath, max_rows=detector.max_rows_to_scan))

        # Step 2: Detect header row from raw rows
        header_row = detector.detect_header_row_from_rows(rows)

        # Step 3: Load file into pandas starting from header row
        df = loader.load_from_row(filepath, header_row)

        # Clean up the DataFrame
        # Drop completely empty rows
        df = df.dropna(how="all")

        # Reset index
        df = df.reset_index(drop=True)

        return df

    def load_raw(self, filepath: str | Path) -> pd.DataFrame:
        """
        Load a file without header detection (raw data).

        Args:
            filepath: Path to the file to load

        Returns:
            DataFrame with raw file contents (no header detection)

        Raises:
            ValueError: If file type is not supported
            FileNotFoundError: If file doesn't exist
        """
        return self.load_file(filepath, detect_header=False)

    def supports_file(self, filepath: str | Path) -> bool:
        """
        Check if a file type is supported.

        Args:
            filepath: Path to check

        Returns:
            True if file type is supported
        """
        filepath = Path(filepath)
        extension = filepath.suffix

        return any(loader.supports_extension(extension) for loader in self._loaders)
