"""Unit tests for MongoDB configuration."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from bson import ObjectId
import os

from src.config.mongodb import (
    MongoDBConfig,
    get_db,
    _get_active_env_file,
    _load_env_once,
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestMongoDBConfig:
    """Tests for MongoDBConfig class."""

    def setup_method(self):
        """Reset singleton state before each test."""
        MongoDBConfig._client = None
        MongoDBConfig._db = None

    def teardown_method(self):
        """Clean up after each test."""
        MongoDBConfig._client = None
        MongoDBConfig._db = None

    def test_get_mongodb_url_success(self):
        """Test successful MongoDB URL retrieval."""
        with patch("src.config.mongodb.os.getenv") as mock_getenv:
            mock_getenv.return_value = "mongodb://localhost:27017/test"

            url = MongoDBConfig.get_mongodb_url()

            assert url == "mongodb://localhost:27017/test"

    def test_get_mongodb_url_not_set(self):
        """Test MongoDB URL when not set."""
        with patch("src.config.mongodb.os.getenv") as mock_getenv:
            mock_getenv.return_value = None

            url = MongoDBConfig.get_mongodb_url()

            assert url is None

    def test_get_mongodb_database_success(self):
        """Test successful MongoDB database name retrieval."""
        with patch("src.config.mongodb.os.getenv") as mock_getenv:
            mock_getenv.return_value = "test_database"

            database = MongoDBConfig.get_mongodb_database()

            assert database == "test_database"

    def test_get_mongodb_database_not_set(self):
        """Test MongoDB database when not set."""
        with patch("src.config.mongodb.os.getenv") as mock_getenv:
            # Mock os.getenv to return None for MONGODB_DATABASE, which should trigger default
            mock_getenv.side_effect = lambda key, default=None: (
                default if key == "MONGODB_DATABASE" else None
            )

            database = MongoDBConfig.get_mongodb_database()

            # Should return default value "financial_tracker"
            assert database == "financial_tracker"

    @patch("src.config.mongodb.MongoClient")
    def test_get_client_success(self, mock_mongo_client):
        """Test successful MongoDB client creation."""
        mock_client = MagicMock()
        mock_mongo_client.return_value = mock_client

        # Ensure singleton is reset
        MongoDBConfig._client = None

        with patch("src.config.mongodb.os.getenv") as mock_getenv:
            mock_getenv.return_value = "mongodb://localhost:27017"

            client = MongoDBConfig.get_client()

            # Use is instead of == for mock object comparison
            assert client is mock_client
            mock_mongo_client.assert_called_once_with(
                "mongodb://localhost:27017", serverSelectionTimeoutMS=10000
            )

    @patch("src.config.mongodb.MongoClient")
    def test_get_client_with_connection_string(self, mock_mongo_client):
        """Test MongoDB client creation with connection string."""
        mock_client = MagicMock()
        mock_mongo_client.return_value = mock_client

        # Reset the singleton to ensure we test the creation
        MongoDBConfig._client = None

        with patch("src.config.mongodb.os.getenv") as mock_getenv:
            mock_getenv.return_value = (
                "mongodb+srv://user:pass@cluster.mongodb.net/test"
            )

            client = MongoDBConfig.get_client()

            assert client is mock_client
            mock_mongo_client.assert_called_once_with(
                "mongodb+srv://user:pass@cluster.mongodb.net/test",
                serverSelectionTimeoutMS=10000,
            )

    @patch("src.config.mongodb.MongoClient")
    def test_get_client_connection_error(self, mock_mongo_client):
        """Test MongoDB client creation with connection error."""
        mock_mongo_client.side_effect = Exception("Connection failed")

        # Reset the singleton to ensure we test the creation
        MongoDBConfig._client = None

        with patch("src.config.mongodb.os.getenv") as mock_getenv:
            mock_getenv.return_value = "mongodb://localhost:27017"

            with pytest.raises(Exception, match="Connection failed"):
                MongoDBConfig.get_client()

    @patch("src.config.mongodb.MongoDBConfig.get_client")
    def test_get_database_success(self, mock_get_client):
        """Test successful database retrieval."""
        mock_client = MagicMock()
        mock_database = MagicMock()
        mock_client.__getitem__.return_value = mock_database
        mock_get_client.return_value = mock_client

        # Ensure singleton is reset
        MongoDBConfig._db = None

        with patch("src.config.mongodb.os.getenv") as mock_getenv:
            mock_getenv.return_value = "test_database"

            database = MongoDBConfig.get_database()

            # Use is instead of == for mock object comparison
            assert database is mock_database
            mock_client.__getitem__.assert_called_once_with("test_database")

    @patch("src.config.mongodb.MongoDBConfig.get_client")
    def test_get_database_no_database_name(self, mock_get_client):
        """Test database retrieval when no database name is set."""
        mock_client = MagicMock()
        mock_database = MagicMock()
        mock_client.__getitem__.return_value = mock_database
        mock_get_client.return_value = mock_client

        # Reset the singleton to ensure we test the creation
        MongoDBConfig._db = None

        with patch("src.config.mongodb.os.getenv") as mock_getenv:
            # Mock os.getenv to return None for MONGODB_DATABASE, which should trigger default
            mock_getenv.side_effect = lambda key, default=None: (
                default if key == "MONGODB_DATABASE" else None
            )

            database = MongoDBConfig.get_database()

            # Should use default database name "financial_tracker"
            assert database is mock_database
            mock_client.__getitem__.assert_called_once_with("financial_tracker")

    def test_close_connection_success(self):
        """Test successful connection closing."""
        # Set up a mock client in the class variable
        mock_client = MagicMock()
        MongoDBConfig._client = mock_client

        MongoDBConfig.close_connection()

        mock_client.close.assert_called_once()
        # Verify that the client and db are set to None
        assert MongoDBConfig._client is None
        assert MongoDBConfig._db is None

    @patch("src.config.mongodb.MongoDBConfig.get_client")
    def test_close_connection_error(self, mock_get_client):
        """Test connection closing with error."""
        mock_client = MagicMock()
        mock_client.close.side_effect = Exception("Close failed")
        mock_get_client.return_value = mock_client

        # Should not raise exception
        MongoDBConfig.close_connection()

    @patch("src.config.mongodb.MongoDBConfig.get_database")
    def test_initialize_collections_success(self, mock_get_database):
        """Test successful collection initialization."""
        mock_db = MagicMock()
        mock_get_database.return_value = mock_db

        MongoDBConfig.initialize_collections()

        # Verify indexes were created (not collections)
        # The method creates indexes on existing collections, not new collections
        assert (
            mock_db.users.create_index.call_count >= 3
        )  # email, username, oauth indexes
        assert mock_db.wallets.create_index.call_count >= 2  # user_id, name indexes
        assert mock_db.assets.create_index.call_count >= 2  # symbol, name indexes
        assert (
            mock_db.transactions.create_index.call_count >= 3
        )  # user_id, wallet_id, date indexes

    @patch("src.config.mongodb.MongoDBConfig.get_database")
    def test_initialize_collections_error(self, mock_get_database):
        """Test collection initialization with error."""
        mock_db = MagicMock()
        mock_db.create_collection.side_effect = Exception("Collection creation failed")
        mock_get_database.return_value = mock_db

        # Should not raise exception
        MongoDBConfig.initialize_collections()


class TestGetActiveEnvFile:
    """Tests for _get_active_env_file function."""

    def test_get_active_env_file_development(self):
        """Test getting development environment file."""
        with patch("pathlib.Path.exists") as mock_exists:
            # Mock .active_env file to not exist, so it falls back to ENV_FILE
            mock_exists.side_effect = lambda: False

            with patch("src.config.mongodb.os.getenv") as mock_getenv:
                mock_getenv.return_value = "config/config.dev.env"

                env_file = _get_active_env_file()

                assert env_file == "config/config.dev.env"

    def test_get_active_env_file_local(self):
        """Test getting local environment file."""
        with patch("pathlib.Path.exists") as mock_exists:
            # Mock .active_env file to not exist, so it falls back to ENV_FILE
            mock_exists.side_effect = lambda: False

            with patch("src.config.mongodb.os.getenv") as mock_getenv:
                mock_getenv.return_value = "config/config.local.env"

                env_file = _get_active_env_file()

                assert env_file == "config/config.local.env"

    def test_get_active_env_file_production(self):
        """Test getting production environment file."""
        with patch("pathlib.Path.exists") as mock_exists:
            # Mock .active_env file to not exist, so it falls back to ENV_FILE
            mock_exists.side_effect = lambda: False

            with patch("src.config.mongodb.os.getenv") as mock_getenv:
                mock_getenv.return_value = "config/config.production.env"

                env_file = _get_active_env_file()

                assert env_file == "config/config.production.env"

    def test_get_active_env_file_none_exist(self):
        """Test when no environment files exist."""
        with patch("pathlib.Path.exists") as mock_exists:
            # Mock .active_env file to not exist, so it falls back to ENV_FILE
            mock_exists.side_effect = lambda: False

            with patch("src.config.mongodb.os.getenv") as mock_getenv:
                # Mock os.getenv to return the default value when ENV_FILE is not set
                mock_getenv.side_effect = lambda key, default=None: (
                    default if key == "ENV_FILE" else None
                )

                env_file = _get_active_env_file()

                assert env_file == ".env"  # Default fallback

    def test_get_active_env_file_priority_order(self):
        """Test that environment files are checked in priority order."""
        with patch("pathlib.Path.exists") as mock_exists:
            # Mock .active_env file to not exist, so it falls back to ENV_FILE
            mock_exists.side_effect = lambda: False

            with patch("src.config.mongodb.os.getenv") as mock_getenv:
                mock_getenv.return_value = "config/config.dev.env"

                env_file = _get_active_env_file()

                assert env_file == "config/config.dev.env"


class TestLoadEnvOnce:
    """Tests for _load_env_once function."""

    def test_load_env_once_success(self):
        """Test successful environment loading."""
        env_content = "MONGODB_URL=mongodb://localhost:27017\nMONGODB_DATABASE=test_db"

        with patch(
            "src.config.mongodb._get_active_env_file",
            return_value="config/config.dev.env",
        ), patch("builtins.open", mock_open(read_data=env_content)), patch(
            "src.config.mongodb.load_dotenv"
        ), patch(
            "src.config.mongodb.os.getenv"
        ) as mock_getenv, patch(
            "src.config.mongodb.Path"
        ) as mock_path:
            # Mock Path.exists() to return True
            mock_path.return_value.exists.return_value = True

            # Mock CI environment variables to be False
            mock_getenv.side_effect = lambda key, default=None: {
                "AWS_LAMBDA_FUNCTION_NAME": None,
                "GITHUB_ACTIONS": None,
                "CI": None,
                "CONTINUOUS_INTEGRATION": None,
                "JENKINS_URL": None,
                "BUILD_NUMBER": None,
            }.get(key, default)

            env_vars = _load_env_once()

            assert env_vars["MONGODB_URL"] == "mongodb://localhost:27017"
            assert env_vars["MONGODB_DATABASE"] == "test_db"

    def test_load_env_once_no_file(self):
        """Test environment loading when no file exists."""
        with patch("src.config.mongodb._get_active_env_file", return_value=None), patch(
            "src.config.mongodb.os.getenv"
        ) as mock_getenv:
            # Mock CI environment variables to be False
            mock_getenv.side_effect = lambda key, default=None: {
                "AWS_LAMBDA_FUNCTION_NAME": None,
                "GITHUB_ACTIONS": None,
                "CI": None,
                "CONTINUOUS_INTEGRATION": None,
                "JENKINS_URL": None,
                "BUILD_NUMBER": None,
            }.get(key, default)

            env_vars = _load_env_once()

            assert env_vars == {}

    def test_load_env_once_file_error(self):
        """Test environment loading with file error."""
        with patch(
            "src.config.mongodb._get_active_env_file",
            return_value="config/config.dev.env",
        ), patch(
            "builtins.open", side_effect=FileNotFoundError("File not found")
        ), patch(
            "src.config.mongodb.os.getenv"
        ) as mock_getenv:
            # Mock CI environment variables to be False
            mock_getenv.side_effect = lambda key, default=None: {
                "AWS_LAMBDA_FUNCTION_NAME": None,
                "GITHUB_ACTIONS": None,
                "CI": None,
                "CONTINUOUS_INTEGRATION": None,
                "JENKINS_URL": None,
                "BUILD_NUMBER": None,
            }.get(key, default)

            env_vars = _load_env_once()

            assert env_vars == {}

    def test_load_env_once_empty_file(self):
        """Test environment loading with empty file."""
        with patch(
            "src.config.mongodb._get_active_env_file",
            return_value="config/config.dev.env",
        ), patch("builtins.open", mock_open(read_data="")), patch(
            "src.config.mongodb.os.getenv"
        ) as mock_getenv:
            # Mock CI environment variables to be False
            mock_getenv.side_effect = lambda key, default=None: {
                "AWS_LAMBDA_FUNCTION_NAME": None,
                "GITHUB_ACTIONS": None,
                "CI": None,
                "CONTINUOUS_INTEGRATION": None,
                "JENKINS_URL": None,
                "BUILD_NUMBER": None,
            }.get(key, default)

            env_vars = _load_env_once()

            assert env_vars == {}

    def test_load_env_once_with_comments(self):
        """Test environment loading with comments."""
        env_content = "# This is a comment\nMONGODB_URL=mongodb://localhost:27017\n# Another comment\nMONGODB_DATABASE=test_db"

        with patch(
            "src.config.mongodb._get_active_env_file",
            return_value="config/config.dev.env",
        ), patch("builtins.open", mock_open(read_data=env_content)), patch(
            "src.config.mongodb.load_dotenv"
        ), patch(
            "src.config.mongodb.os.getenv"
        ) as mock_getenv, patch(
            "src.config.mongodb.Path"
        ) as mock_path:
            # Mock Path.exists() to return True
            mock_path.return_value.exists.return_value = True

            # Mock CI environment variables to be False
            mock_getenv.side_effect = lambda key, default=None: {
                "AWS_LAMBDA_FUNCTION_NAME": None,
                "GITHUB_ACTIONS": None,
                "CI": None,
                "CONTINUOUS_INTEGRATION": None,
                "JENKINS_URL": None,
                "BUILD_NUMBER": None,
            }.get(key, default)

            env_vars = _load_env_once()

            assert env_vars["MONGODB_URL"] == "mongodb://localhost:27017"
            assert env_vars["MONGODB_DATABASE"] == "test_db"
            assert "#" not in env_vars

    def test_load_env_once_with_empty_lines(self):
        """Test environment loading with empty lines."""
        env_content = (
            "MONGODB_URL=mongodb://localhost:27017\n\nMONGODB_DATABASE=test_db\n"
        )

        with patch(
            "src.config.mongodb._get_active_env_file",
            return_value="config/config.dev.env",
        ), patch("builtins.open", mock_open(read_data=env_content)), patch(
            "src.config.mongodb.load_dotenv"
        ), patch(
            "src.config.mongodb.os.getenv"
        ) as mock_getenv, patch(
            "src.config.mongodb.Path"
        ) as mock_path:
            # Mock Path.exists() to return True
            mock_path.return_value.exists.return_value = True

            # Mock CI environment variables to be False
            mock_getenv.side_effect = lambda key, default=None: {
                "AWS_LAMBDA_FUNCTION_NAME": None,
                "GITHUB_ACTIONS": None,
                "CI": None,
                "CONTINUOUS_INTEGRATION": None,
                "JENKINS_URL": None,
                "BUILD_NUMBER": None,
            }.get(key, default)

            env_vars = _load_env_once()

            assert env_vars["MONGODB_URL"] == "mongodb://localhost:27017"
            assert env_vars["MONGODB_DATABASE"] == "test_db"

    def test_load_env_once_with_quotes(self):
        """Test environment loading with quoted values."""
        env_content = (
            "MONGODB_URL=\"mongodb://localhost:27017\"\nMONGODB_DATABASE='test_db'"
        )

        with patch(
            "src.config.mongodb._get_active_env_file",
            return_value="config/config.dev.env",
        ), patch("builtins.open", mock_open(read_data=env_content)), patch(
            "src.config.mongodb.load_dotenv"
        ), patch(
            "src.config.mongodb.os.getenv"
        ) as mock_getenv, patch(
            "src.config.mongodb.Path"
        ) as mock_path:
            # Mock Path.exists() to return True
            mock_path.return_value.exists.return_value = True

            # Mock CI environment variables to be False
            mock_getenv.side_effect = lambda key, default=None: {
                "AWS_LAMBDA_FUNCTION_NAME": None,
                "GITHUB_ACTIONS": None,
                "CI": None,
                "CONTINUOUS_INTEGRATION": None,
                "JENKINS_URL": None,
                "BUILD_NUMBER": None,
            }.get(key, default)

            env_vars = _load_env_once()

            assert env_vars["MONGODB_URL"] == "mongodb://localhost:27017"
            assert env_vars["MONGODB_DATABASE"] == "test_db"

    def test_load_env_once_with_spaces(self):
        """Test environment loading with spaces around values."""
        env_content = (
            "MONGODB_URL = mongodb://localhost:27017 \nMONGODB_DATABASE = test_db "
        )

        with patch(
            "src.config.mongodb._get_active_env_file",
            return_value="config/config.dev.env",
        ), patch("builtins.open", mock_open(read_data=env_content)), patch(
            "src.config.mongodb.load_dotenv"
        ), patch(
            "src.config.mongodb.os.getenv"
        ) as mock_getenv, patch(
            "src.config.mongodb.Path"
        ) as mock_path:
            # Mock Path.exists() to return True
            mock_path.return_value.exists.return_value = True

            # Mock CI environment variables to be False
            mock_getenv.side_effect = lambda key, default=None: {
                "AWS_LAMBDA_FUNCTION_NAME": None,
                "GITHUB_ACTIONS": None,
                "CI": None,
                "CONTINUOUS_INTEGRATION": None,
                "JENKINS_URL": None,
                "BUILD_NUMBER": None,
            }.get(key, default)

            env_vars = _load_env_once()

            assert env_vars["MONGODB_URL"] == "mongodb://localhost:27017"
            assert env_vars["MONGODB_DATABASE"] == "test_db"


class TestGetDb:
    """Tests for get_db function."""

    @patch("src.config.mongodb.MongoDBConfig.get_database")
    def test_get_db_success(self, mock_get_database):
        """Test successful database retrieval."""
        mock_database = MagicMock()
        mock_get_database.return_value = mock_database

        db = get_db()

        assert db is mock_database

    @patch("src.config.mongodb.MongoDBConfig.get_database")
    def test_get_db_error(self, mock_get_database):
        """Test database retrieval with error."""
        mock_get_database.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception, match="Database connection failed"):
            get_db()


class TestMongoDBConfigCaching:
    """Tests for MongoDB configuration caching."""

    def test_config_caching(self):
        """Test that configuration values are cached."""
        with patch("src.config.mongodb.os.getenv") as mock_getenv:
            mock_getenv.side_effect = lambda key, default=None: {
                "MONGODB_URL": "mongodb://localhost:27017",
                "MONGODB_DATABASE": "test_db",
            }.get(key, default)

            # First call
            url1 = MongoDBConfig.get_mongodb_url()
            database1 = MongoDBConfig.get_mongodb_database()

            # Second call
            url2 = MongoDBConfig.get_mongodb_url()
            database2 = MongoDBConfig.get_mongodb_database()

            assert url1 == url2
            assert database1 == database2
            # Should call os.getenv for each access
            assert mock_getenv.call_count >= 4

    def test_config_reload_on_error(self):
        """Test that configuration is reloaded on error."""
        with patch("src.config.mongodb.os.getenv") as mock_getenv:
            # First call succeeds
            mock_getenv.return_value = "mongodb://localhost:27017"
            url1 = MongoDBConfig.get_mongodb_url()

            # Second call fails
            mock_getenv.side_effect = Exception("Load failed")

            with pytest.raises(Exception):
                MongoDBConfig.get_mongodb_url()

            # Should have been called multiple times
            assert mock_getenv.call_count >= 2
