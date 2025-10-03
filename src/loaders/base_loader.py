"""Base file loader interface."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator, List, Any
import pandas as pd


class BaseFileLoader(ABC):
    """Abstract base class for file loaders."""

    @abstractmethod
    def load(self, filepath: Path) -> pd.DataFrame:
        """
        Load file and return as pandas DataFrame.

        Args:
            filepath: Path to the file to load

        Returns:
            DataFrame with raw file contents
        """
        pass

    @abstractmethod
    def supports_extension(self, extension: str) -> bool:
        """
        Check if this loader supports the given file extension.

        Args:
            extension: File extension (e.g., '.csv', '.xlsx')

        Returns:
            True if supported, False otherwise
        """
        pass

    @abstractmethod
    def read_rows(self, filepath: Path, max_rows: int = 50) -> Iterator[List[Any]]:
        """
        Read file row by row (for header detection).

        Args:
            filepath: Path to the file to load
            max_rows: Maximum number of rows to read

        Yields:
            List of values for each row
        """
        pass

    @abstractmethod
    def load_from_row(self, filepath: Path, header_row: int) -> pd.DataFrame:
        """
        Load file starting from a specific header row.

        Args:
            filepath: Path to the file to load
            header_row: Row index where header is located (0-based)

        Returns:
            DataFrame with proper header and data
        """
        pass

    def validate_file(self, filepath: Path) -> None:
        """
        Validate that the file exists and is readable.

        Args:
            filepath: Path to the file

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not readable
        """
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        if not filepath.is_file():
            raise ValueError(f"Path is not a file: {filepath}")
