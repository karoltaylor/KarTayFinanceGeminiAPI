"""Main data processing pipeline."""

from pathlib import Path
from typing import Optional, Dict, List
import pandas as pd

from ..loaders import FileLoaderFactory
from ..services import TableDetector, ColumnMapper
from ..models import FinancialDataModel
from ..config.settings import Settings


class DataPipeline:
    """Orchestrates the complete data import and transformation pipeline."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        max_rows_to_scan: Optional[int] = None,
    ):
        """
        Initialize pipeline with required services.

        Args:
            api_key: Google API key (uses Settings if None)
            model_name: GenAI model name (uses Settings if None)
            max_rows_to_scan: Max rows to scan for header detection
        """
        self.file_loader = FileLoaderFactory()
        self.table_detector = TableDetector(
            max_rows_to_scan=max_rows_to_scan or Settings.MAX_ROWS_TO_SCAN
        )
        self.column_mapper = ColumnMapper(api_key=api_key, model_name=model_name)
        self.target_columns = Settings.TARGET_COLUMNS

    def process_file(
        self, filepath: str | Path, default_values: Optional[Dict[str, any]] = None
    ) -> FinancialDataModel:
        """
        Process a file through the complete pipeline.

        Steps:
        1. Load file with automatic header detection (csv, txt, xls, xlsx)
        2. Map columns using AI
        3. Transform to target schema
        4. Validate and load into FinancialDataModel

        Args:
            filepath: Path to the file to process
            default_values: Default values for unmapped columns

        Returns:
            FinancialDataModel with loaded and validated data
        """
        filepath = Path(filepath)

        # Step 1: Load file with automatic header detection
        # The FileLoaderFactory now automatically detects headers
        table_df = self.file_loader.load_file(filepath)

        # Step 2: Map columns using AI
        column_mapping = self.column_mapper.map_columns(table_df, self.target_columns)

        # Step 3: Apply mapping
        mapped_df = self.column_mapper.apply_mapping(
            table_df, column_mapping, default_values
        )

        # Step 4: Load into data model with validation
        data_model = FinancialDataModel()
        errors = data_model.load_from_dataframe(mapped_df)

        if errors:
            print(f"Warning: {len(errors)} records failed validation:")
            for error in errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")

        return data_model

    def process_multiple_files(
        self,
        filepaths: List[str | Path],
        default_values: Optional[Dict[str, any]] = None,
    ) -> FinancialDataModel:
        """
        Process multiple files and combine into single data model.

        Args:
            filepaths: List of file paths to process
            default_values: Default values for unmapped columns

        Returns:
            Combined FinancialDataModel
        """
        combined_model = FinancialDataModel()

        for filepath in filepaths:
            print(f"Processing: {filepath}")
            try:
                file_model = self.process_file(filepath, default_values)

                # Merge into combined model
                if not file_model.df.empty:
                    combined_model.df = pd.concat(
                        [combined_model.df, file_model.df], ignore_index=True
                    )

            except Exception as e:
                print(f"Error processing {filepath}: {str(e)}")
                continue

        return combined_model

    def get_column_mapping_preview(self, filepath: str | Path) -> Dict:
        """
        Preview the column mapping without full processing.

        Useful for debugging and validation.

        Returns:
            Dictionary with source columns, detected mapping, and sample data
        """
        filepath = Path(filepath)

        # Load table with automatic header detection
        table_df = self.file_loader.load_file(filepath)

        # Get header info if needed for debugging
        raw_df = self.file_loader.load_raw(filepath)
        _, header_row = self.table_detector.extract_table(raw_df)

        # Get mapping
        column_mapping = self.column_mapper.map_columns(table_df, self.target_columns)

        return {
            "header_row_index": header_row,
            "source_columns": table_df.columns.tolist(),
            "column_mapping": column_mapping,
            "sample_data": table_df.head(3).to_dict("records"),
            "total_rows": len(table_df),
        }
