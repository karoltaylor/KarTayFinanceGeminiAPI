"""Asset type mapper service using Google GenAI."""

from typing import Dict, Optional
import json
import google.generativeai as genai

from ..config.settings import Settings
from ..models.mongodb_models import AssetType


class AssetTypeMapper:
    """Maps asset names to asset types and symbols using Google GenAI."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """
        Initialize asset type mapper with Google GenAI.

        Args:
            api_key: Google API key (uses Settings.GOOGLE_API_KEY if None)
            model_name: GenAI model name (uses Settings.GENAI_MODEL if None)
        """
        self.api_key = api_key if api_key is not None else Settings.GOOGLE_API_KEY
        self.model_name = model_name if model_name is not None else Settings.GENAI_MODEL

        if not self.api_key or not self.api_key.strip():
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY environment variable.")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def infer_asset_info(self, asset_name: str) -> Optional[Dict[str, str]]:
        """
        Infer asset type and symbol from asset name using Google GenAI.

        Args:
            asset_name: Name of the asset to classify

        Returns:
            Dictionary with 'asset_type' and 'symbol' keys, or None if inference fails
            Example: {"asset_type": "stock", "symbol": "AAPL"}
        """
        if not asset_name or not asset_name.strip():
            return None

        try:
            prompt = self._build_asset_classification_prompt(asset_name.strip())
            response = self.model.generate_content(prompt)
            result = self._parse_asset_response(response.text)

            # Validate the result
            if self._validate_asset_result(result):
                return result
            else:
                return None

        except Exception as e:
            # Log error but don't raise - allow fallback to OTHER
            print(f"Warning: Asset type inference failed for '{asset_name}': {str(e)}")
            return None

    def _build_asset_classification_prompt(self, asset_name: str) -> str:
        """Build prompt for asset classification."""

        valid_asset_types = [asset_type.value for asset_type in AssetType]

        prompt = f"""You are an asset classification expert. Classify the asset type and provide ticker symbol.

ASSET NAME: {asset_name}

ASSET TYPES (valid options):
{chr(10).join(f"- {asset_type}" for asset_type in valid_asset_types)}

INSTRUCTIONS:
1. Determine the most likely asset type from the list above
2. Suggest a ticker/symbol if available (empty string if none)
3. Return ONLY valid JSON: {{"asset_type": "...", "symbol": "..."}}

Example: {{"asset_type": "stock", "symbol": "AAPL"}}

IMPORTANT: Return ONLY the JSON object, no additional text or explanation."""

        return prompt

    def _parse_asset_response(self, response_text: str) -> Optional[Dict[str, str]]:
        """Parse the AI response and extract asset information."""
        if not response_text or not response_text.strip():
            return None

        # Clean the response text
        cleaned_text = response_text.strip()

        # Try to find JSON in the response
        start_idx = cleaned_text.find("{")
        end_idx = cleaned_text.rfind("}") + 1

        if start_idx == -1 or end_idx == 0:
            return None

        json_text = cleaned_text[start_idx:end_idx]

        try:
            result = json.loads(json_text)

            # Ensure we have the expected structure
            if isinstance(result, dict) and "asset_type" in result:
                return {
                    "asset_type": str(result.get("asset_type", "")).strip(),
                    "symbol": str(result.get("symbol", "")).strip(),
                }
            else:
                return None

        except json.JSONDecodeError:
            return None

    def _validate_asset_result(self, result: Optional[Dict[str, str]]) -> bool:
        """Validate that the asset classification result is valid."""
        if not result or not isinstance(result, dict):
            return False

        asset_type = result.get("asset_type", "").strip().lower()

        # Check if asset_type is valid
        valid_types = [asset_type.value for asset_type in AssetType]
        if asset_type not in valid_types:
            return False

        # Symbol is optional, but if present should be reasonable
        symbol = result.get("symbol", "").strip()
        if symbol and len(symbol) > 20:  # Reasonable ticker length limit
            return False

        return True
