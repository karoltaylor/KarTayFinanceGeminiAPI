"""Column mapper service using Google GenAI."""

from typing import Dict, List, Optional
import json
from datetime import datetime, date
import google.generativeai as genai
import pandas as pd
import numpy as np

from ..config.settings import Settings


class ColumnMapper:
    """Maps source columns to target schema using Google GenAI."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """
        Initialize column mapper with Google GenAI.

        Args:
            api_key: Google API key (uses Settings.GOOGLE_API_KEY if None)
            model_name: GenAI model name (uses Settings.GENAI_MODEL if None)
        """
        self.api_key = api_key if api_key is not None else Settings.GOOGLE_API_KEY
        self.model_name = model_name if model_name is not None else Settings.GENAI_MODEL

        if not self.api_key or not self.api_key.strip():
            raise ValueError(
                "Google API key is required. Set GOOGLE_API_KEY environment variable."
            )

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def map_columns(
        self, source_df: pd.DataFrame, target_columns: List[str], sample_rows: int = 5
    ) -> Dict[str, str]:
        """
        Map source DataFrame columns to target schema columns.

        Args:
            source_df: Source DataFrame with unknown column structure
            target_columns: List of target column names to map to
            sample_rows: Number of sample rows to provide as context

        Returns:
            Dictionary mapping target column names to source column names
            Example: {"wallet_name": "account", "asset_name": "stock_name"}
        """
        if source_df.empty:
            raise ValueError("Cannot map columns from empty DataFrame")

        # Prepare context for AI
        source_columns = source_df.columns.tolist()

        # Convert sample data to JSON-serializable format
        sample_df = source_df.head(sample_rows).copy()

        # Convert all non-serializable types to strings
        for col in sample_df.columns:
            # Convert datetime columns
            if pd.api.types.is_datetime64_any_dtype(sample_df[col]):
                sample_df[col] = sample_df[col].astype(str)
            # Replace NaN/NaT with None for JSON
            sample_df[col] = sample_df[col].replace({pd.NaT: None, pd.NA: None})

        # Fill remaining NaN with None
        sample_df = sample_df.where(pd.notna(sample_df), None)

        sample_data = sample_df.to_dict("records")

        prompt = self._build_mapping_prompt(source_columns, target_columns, sample_data)

        try:
            response = self.model.generate_content(prompt)
            mapping = self._parse_mapping_response(response.text)

            # Validate mapping
            self._validate_mapping(mapping, source_columns, target_columns)

            return mapping

        except Exception as e:
            raise RuntimeError(f"Failed to map columns using GenAI: {str(e)}")

    def _serialize_for_json(self, obj):
        """Convert objects to JSON-serializable format."""
        if isinstance(obj, (datetime, date, pd.Timestamp)):
            return str(obj)
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._serialize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_for_json(item) for item in obj]
        elif obj is None or (isinstance(obj, float) and np.isnan(obj)):
            return None
        return obj

    def _build_mapping_prompt(
        self,
        source_columns: List[str],
        target_columns: List[str],
        sample_data: List[Dict],
    ) -> str:
        """Build prompt for the AI model."""
        # Ensure all sample data is JSON-serializable
        serialized_sample = self._serialize_for_json(sample_data)

        prompt = f"""You are a data mapping expert. Your task is to map source \
columns to target columns based on their meaning and content.

TARGET SCHEMA (required columns):
{json.dumps(target_columns, indent=2)}

TARGET COLUMN DESCRIPTIONS:
- asset_name: Name of the asset (stock, crypto, etc.)
- date: Transaction or record date
- asset_price: Price per unit/item of the asset
- volume: Quantity or number of assets
- transaction_amount: Total transaction amount (can be calculated if missing)
- fee: Transaction fee (set to 0 if not available)
- currency: Currency code (USD, EUR, etc.)

SOURCE COLUMNS:
{json.dumps(source_columns, indent=2)}

SAMPLE DATA FROM SOURCE (first few rows):
{json.dumps(serialized_sample, indent=2)}

INSTRUCTIONS:
1. Analyze the source column names and sample data
2. Map each TARGET column to the most appropriate SOURCE column
3. If no appropriate source column exists, set the value to null
4. Return ONLY a valid JSON object with the mapping
5. The JSON should map TARGET column names (keys) to SOURCE column names (values)

IMPORTANT: Return ONLY the JSON object, no additional text or explanation.

Example output format:
{{"asset_name": "stock_symbol",
  "date": "transaction_date",
  "asset_price": "price_per_share",
  "volume": "quantity",
  "transaction_amount": "total_amount",
  "fee": "transaction_fee",
  "currency": "curr"
}}

If a target column cannot be mapped, use null:
{{"asset_name": "stock_name",
  "fee": null,
  "transaction_amount": null
}}

Now provide the mapping:"""

        return prompt

    def _parse_mapping_response(self, response_text: str) -> Dict[str, Optional[str]]:
        """Parse AI response to extract column mapping."""
        # Clean response text
        response_text = response_text.strip()

        # Extract JSON from response (it might be wrapped in markdown code blocks)
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()

        try:
            mapping = json.loads(response_text)
            return mapping
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse AI response as JSON: {
                    str(e)}\nResponse: {response_text}"
            )

    def _validate_mapping(
        self,
        mapping: Dict[str, Optional[str]],
        source_columns: List[str],
        target_columns: List[str],
    ) -> None:
        """Validate that the mapping is reasonable."""
        # Check that all target columns are present in mapping
        missing_targets = set(target_columns) - set(mapping.keys())
        if missing_targets:
            raise ValueError(f"Mapping is missing target columns: {missing_targets}")

        # Check that mapped source columns actually exist
        for target, source in mapping.items():
            if source is not None and source not in source_columns:
                raise ValueError(
                    f"Mapping references non-existent source column '{source}' "
                    f"for target column '{target}'"
                )

    def apply_mapping(
        self,
        source_df: pd.DataFrame,
        mapping: Dict[str, Optional[str]],
        default_values: Optional[Dict[str, any]] = None,
    ) -> pd.DataFrame:
        """
        Apply column mapping to create a DataFrame with target schema.

        Args:
            source_df: Source DataFrame
            mapping: Column mapping from map_columns()
            default_values: Default values for unmapped columns

        Returns:
            DataFrame with target column structure
        """
        default_values = default_values or {}
        result_data = {}

        for target_col, source_col in mapping.items():
            if source_col is not None and source_col in source_df.columns:
                result_data[target_col] = source_df[source_col]
            elif target_col in default_values:
                result_data[target_col] = default_values[target_col]
            else:
                # Create column with None values
                result_data[target_col] = None

        result_df = pd.DataFrame(result_data)
        return result_df
