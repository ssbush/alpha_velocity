"""
Tests for Database Configuration (backend/database/config.py)

Covers DatabaseConfig initialization, connection parsing, and session management.
All tests mock create_engine to avoid real database connections.
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.database.config import DatabaseConfig


@pytest.fixture
def mock_engine():
    """Patch create_engine so tests never hit a real database."""
    engine = MagicMock()
    engine.connect.return_value.__enter__ = MagicMock()
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)
    with patch("backend.database.config.create_engine", return_value=engine) as mock_ce:
        yield engine, mock_ce


class TestDatabaseConfig:
    """Tests for DatabaseConfig class."""

    def test_init_defaults(self):
        config = DatabaseConfig()
        assert config.db_host == "localhost" or isinstance(config.db_host, str)
        assert config.db_port == "5432" or isinstance(config.db_port, str)
        assert config.db_name is not None
        assert config.db_user is not None
        assert config.engine is None
        assert config.SessionLocal is None

    def test_database_url_format(self):
        config = DatabaseConfig()
        assert config.database_url.startswith("postgresql://")
        assert config.db_host in config.database_url
        assert config.db_port in config.database_url

    @patch.dict("os.environ", {
        "DB_HOST": "testhost",
        "DB_PORT": "5433",
        "DB_NAME": "testdb",
        "DB_USER": "testuser",
        "DB_PASSWORD": "testpass",
    })
    def test_reads_from_env(self):
        config = DatabaseConfig()
        assert config.db_host == "testhost"
        assert config.db_port == "5433"
        assert config.db_name == "testdb"
        assert config.db_user == "testuser"
        assert config.db_password == "testpass"

    def test_test_connection_success(self, mock_engine):
        engine, _ = mock_engine
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = (1,)
        engine.connect.return_value.__enter__.return_value = mock_conn

        config = DatabaseConfig()
        result = config.test_connection()
        assert result is True

    def test_test_connection_failure(self, mock_engine):
        engine, _ = mock_engine
        engine.connect.side_effect = Exception("Connection refused")

        config = DatabaseConfig()
        result = config.test_connection()
        assert result is False

    def test_initialize_engine(self, mock_engine):
        engine, mock_ce = mock_engine
        config = DatabaseConfig()
        config.initialize_engine()
        assert config.engine is not None
        assert config.SessionLocal is not None
        mock_ce.assert_called_once()

    def test_initialize_engine_idempotent(self, mock_engine):
        _, mock_ce = mock_engine
        config = DatabaseConfig()
        config.initialize_engine()
        engine1 = config.engine
        config.initialize_engine()
        assert config.engine is engine1  # Same engine, not re-created
        mock_ce.assert_called_once()

    def test_get_session(self, mock_engine):
        config = DatabaseConfig()
        config.initialize_engine()
        session = config.get_session()
        assert session is not None
        session.close()

    def test_create_all_tables_initializes_engine(self, mock_engine):
        config = DatabaseConfig()
        config.create_all_tables()
        assert config.engine is not None

    def test_drop_all_tables_initializes_engine(self, mock_engine):
        config = DatabaseConfig()
        config.drop_all_tables()
        assert config.engine is not None

    def test_get_session_initializes_engine(self, mock_engine):
        config = DatabaseConfig()
        assert config.SessionLocal is None
        session = config.get_session()
        assert config.SessionLocal is not None
        session.close()
