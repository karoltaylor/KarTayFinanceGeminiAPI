"""Tests for AssetTypeMapper service."""

import pytest
from unittest.mock import Mock, patch
from src.services.asset_type_mapper import AssetTypeMapper
from src.models.mongodb_models import AssetType


class TestAssetTypeMapper:
    """Tests for AssetTypeMapper."""

    @pytest.fixture
    def mock_genai_model(self):
        """Mock GenAI model for testing."""
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = '{"asset_type": "stock", "symbol": "AAPL"}'
        mock_model.generate_content.return_value = mock_response
        return mock_model

    @pytest.fixture
    def asset_type_mapper(self, set_test_env_vars):
        """Create AssetTypeMapper instance for testing."""
        with patch('src.services.asset_type_mapper.Settings') as mock_settings:
            mock_settings.GOOGLE_API_KEY = "test_api_key_12345"
            mock_settings.GENAI_MODEL = "gemini-1.5-flash"
            yield AssetTypeMapper()

    def test_init_with_api_key(self):
        """Test AssetTypeMapper initialization with API key."""
        mapper = AssetTypeMapper(api_key="test_key", model_name="test_model")
        assert mapper.api_key == "test_key"
        assert mapper.model_name == "test_model"

    @patch('src.services.asset_type_mapper.Settings')
    def test_init_without_api_key_uses_settings(self, mock_settings):
        """Test AssetTypeMapper initialization without API key uses Settings."""
        mock_settings.GOOGLE_API_KEY = "test_api_key_12345"
        mock_settings.GENAI_MODEL = "gemini-1.5-flash"
        
        mapper = AssetTypeMapper()
        assert mapper.api_key == "test_api_key_12345"
        assert mapper.model_name == "gemini-1.5-flash"

    @patch('src.services.asset_type_mapper.Settings')
    def test_init_without_api_key_raises_error(self, mock_settings):
        """Test AssetTypeMapper initialization without API key raises error."""
        mock_settings.GOOGLE_API_KEY = None
        mock_settings.GENAI_MODEL = "gemini-1.5-flash"
        
        with pytest.raises(ValueError, match="Google API key is required"):
            AssetTypeMapper()

    @patch('src.services.asset_type_mapper.genai.configure')
    @patch('src.services.asset_type_mapper.genai.GenerativeModel')
    def test_infer_asset_info_success(self, mock_genai_model_class, mock_configure, asset_type_mapper, mock_genai_model):
        """Test successful asset type inference."""
        mock_genai_model_class.return_value = mock_genai_model
        asset_type_mapper.model = mock_genai_model

        result = asset_type_mapper.infer_asset_info("Apple Inc.")
        
        assert result == {"asset_type": "stock", "symbol": "AAPL"}
        mock_genai_model.generate_content.assert_called_once()

    @patch('src.services.asset_type_mapper.genai.configure')
    @patch('src.services.asset_type_mapper.genai.GenerativeModel')
    def test_infer_asset_info_cryptocurrency(self, mock_genai_model_class, mock_configure, asset_type_mapper, mock_genai_model):
        """Test cryptocurrency asset type inference."""
        mock_response = Mock()
        mock_response.text = '{"asset_type": "cryptocurrency", "symbol": "BTC"}'
        mock_genai_model.generate_content.return_value = mock_response
        mock_genai_model_class.return_value = mock_genai_model
        asset_type_mapper.model = mock_genai_model

        result = asset_type_mapper.infer_asset_info("Bitcoin")
        
        assert result == {"asset_type": "cryptocurrency", "symbol": "BTC"}

    @patch('src.services.asset_type_mapper.genai.configure')
    @patch('src.services.asset_type_mapper.genai.GenerativeModel')
    def test_infer_asset_info_without_symbol(self, mock_genai_model_class, mock_configure, asset_type_mapper, mock_genai_model):
        """Test asset type inference without symbol."""
        mock_response = Mock()
        mock_response.text = '{"asset_type": "bond", "symbol": ""}'
        mock_genai_model.generate_content.return_value = mock_response
        mock_genai_model_class.return_value = mock_genai_model
        asset_type_mapper.model = mock_genai_model

        result = asset_type_mapper.infer_asset_info("US Treasury Bond")
        
        assert result == {"asset_type": "bond", "symbol": ""}

    def test_infer_asset_info_empty_name(self, asset_type_mapper):
        """Test inference with empty asset name returns None."""
        result = asset_type_mapper.infer_asset_info("")
        assert result is None

        result = asset_type_mapper.infer_asset_info(None)
        assert result is None

    @patch('src.services.asset_type_mapper.genai.configure')
    @patch('src.services.asset_type_mapper.genai.GenerativeModel')
    def test_infer_asset_info_api_failure(self, mock_genai_model_class, mock_configure, asset_type_mapper, mock_genai_model):
        """Test asset type inference handles API failure gracefully."""
        mock_genai_model.generate_content.side_effect = Exception("API Error")
        mock_genai_model_class.return_value = mock_genai_model
        asset_type_mapper.model = mock_genai_model

        result = asset_type_mapper.infer_asset_info("Test Asset")
        
        assert result is None

    @patch('src.services.asset_type_mapper.genai.configure')
    @patch('src.services.asset_type_mapper.genai.GenerativeModel')
    def test_infer_asset_info_invalid_json(self, mock_genai_model_class, mock_configure, asset_type_mapper, mock_genai_model):
        """Test asset type inference handles invalid JSON response."""
        mock_response = Mock()
        mock_response.text = "Invalid JSON response"
        mock_genai_model.generate_content.return_value = mock_response
        mock_genai_model_class.return_value = mock_genai_model
        asset_type_mapper.model = mock_genai_model

        result = asset_type_mapper.infer_asset_info("Test Asset")
        
        assert result is None

    @patch('src.services.asset_type_mapper.genai.configure')
    @patch('src.services.asset_type_mapper.genai.GenerativeModel')
    def test_infer_asset_info_invalid_asset_type(self, mock_genai_model_class, mock_configure, asset_type_mapper, mock_genai_model):
        """Test asset type inference handles invalid asset type."""
        mock_response = Mock()
        mock_response.text = '{"asset_type": "invalid_type", "symbol": "TEST"}'
        mock_genai_model.generate_content.return_value = mock_response
        mock_genai_model_class.return_value = mock_genai_model
        asset_type_mapper.model = mock_genai_model

        result = asset_type_mapper.infer_asset_info("Test Asset")
        
        assert result is None

    @patch('src.services.asset_type_mapper.genai.configure')
    @patch('src.services.asset_type_mapper.genai.GenerativeModel')
    def test_infer_asset_info_malformed_response(self, mock_genai_model_class, mock_configure, asset_type_mapper, mock_genai_model):
        """Test asset type inference handles malformed response."""
        mock_response = Mock()
        mock_response.text = '{"asset_type": "stock"}'  # Missing symbol field
        mock_genai_model.generate_content.return_value = mock_response
        mock_genai_model_class.return_value = mock_genai_model
        asset_type_mapper.model = mock_genai_model

        result = asset_type_mapper.infer_asset_info("Test Asset")
        
        assert result == {"asset_type": "stock", "symbol": ""}  # Should default empty symbol

    @patch('src.services.asset_type_mapper.genai.configure')
    @patch('src.services.asset_type_mapper.genai.GenerativeModel')
    def test_infer_asset_info_long_symbol_rejected(self, mock_genai_model_class, mock_configure, asset_type_mapper, mock_genai_model):
        """Test asset type inference rejects overly long symbols."""
        mock_response = Mock()
        long_symbol = "A" * 25  # Too long
        mock_response.text = f'{{"asset_type": "stock", "symbol": "{long_symbol}"}}'
        mock_genai_model.generate_content.return_value = mock_response
        mock_genai_model_class.return_value = mock_genai_model
        asset_type_mapper.model = mock_genai_model

        result = asset_type_mapper.infer_asset_info("Test Asset")
        
        assert result is None

    def test_build_asset_classification_prompt(self, asset_type_mapper):
        """Test prompt building for asset classification."""
        prompt = asset_type_mapper._build_asset_classification_prompt("Apple Inc.")
        
        assert "Apple Inc." in prompt
        assert "ASSET NAME:" in prompt
        assert "asset_type" in prompt
        assert "symbol" in prompt
        assert "stock" in prompt
        assert "cryptocurrency" in prompt
        assert "bond" in prompt

    def test_parse_asset_response_valid(self, asset_type_mapper):
        """Test parsing valid asset response."""
        response_text = '{"asset_type": "stock", "symbol": "AAPL"}'
        result = asset_type_mapper._parse_asset_response(response_text)
        
        assert result == {"asset_type": "stock", "symbol": "AAPL"}

    def test_parse_asset_response_with_extra_text(self, asset_type_mapper):
        """Test parsing asset response with extra text."""
        response_text = 'Here is the result: {"asset_type": "stock", "symbol": "AAPL"} and some extra text'
        result = asset_type_mapper._parse_asset_response(response_text)
        
        assert result == {"asset_type": "stock", "symbol": "AAPL"}

    def test_parse_asset_response_invalid_json(self, asset_type_mapper):
        """Test parsing invalid JSON response."""
        response_text = "Not valid JSON"
        result = asset_type_mapper._parse_asset_response(response_text)
        
        assert result is None

    def test_parse_asset_response_empty(self, asset_type_mapper):
        """Test parsing empty response."""
        result = asset_type_mapper._parse_asset_response("")
        assert result is None
        
        result = asset_type_mapper._parse_asset_response(None)
        assert result is None

    def test_validate_asset_result_valid(self, asset_type_mapper):
        """Test validation of valid asset result."""
        valid_result = {"asset_type": "stock", "symbol": "AAPL"}
        assert asset_type_mapper._validate_asset_result(valid_result) is True

    def test_validate_asset_result_invalid_type(self, asset_type_mapper):
        """Test validation of asset result with invalid type."""
        invalid_result = {"asset_type": "invalid_type", "symbol": "TEST"}
        assert asset_type_mapper._validate_asset_result(invalid_result) is False

    def test_validate_asset_result_long_symbol(self, asset_type_mapper):
        """Test validation of asset result with overly long symbol."""
        invalid_result = {"asset_type": "stock", "symbol": "A" * 25}
        assert asset_type_mapper._validate_asset_result(invalid_result) is False

    def test_validate_asset_result_none(self, asset_type_mapper):
        """Test validation of None result."""
        assert asset_type_mapper._validate_asset_result(None) is False

    def test_validate_asset_result_empty_dict(self, asset_type_mapper):
        """Test validation of empty dict result."""
        assert asset_type_mapper._validate_asset_result({}) is False

    def test_all_valid_asset_types_recognized(self, asset_type_mapper):
        """Test that all valid asset types are recognized."""
        for asset_type in AssetType:
            valid_result = {"asset_type": asset_type.value, "symbol": "TEST"}
            assert asset_type_mapper._validate_asset_result(valid_result) is True
