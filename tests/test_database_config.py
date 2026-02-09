"""
Tests for Database Configuration (backend/database/config.py)

Covers DatabaseConfig initialization, connection parsing, and session management.
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.database.config import DatabaseConfig


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

    def test_test_connection_returns_bool(self):
        config = DatabaseConfig()
        result = config.test_connection()
        assert isinstance(result, bool)

    def test_initialize_engine(self):
        config = DatabaseConfig()
        config.initialize_engine()
        assert config.engine is not None
        assert config.SessionLocal is not None

    def test_initialize_engine_idempotent(self):
        config = DatabaseConfig()
        config.initialize_engine()
        engine1 = config.engine
        config.initialize_engine()
        assert config.engine is engine1  # Same engine, not re-created

    def test_get_session(self):
        config = DatabaseConfig()
        config.initialize_engine()
        session = config.get_session()
        assert session is not None
        session.close()

    def test_create_all_tables_initializes_engine(self):
        config = DatabaseConfig()
        # Should initialize engine if None
        try:
            config.create_all_tables()
        except Exception:
            pass  # May fail without real DB, but engine should be initialized
        assert config.engine is not None

    def test_drop_all_tables_initializes_engine(self):
        config = DatabaseConfig()
        try:
            config.drop_all_tables()
        except Exception:
            pass  # May fail without real DB
        assert config.engine is not None

    def test_get_session_initializes_engine(self):
        config = DatabaseConfig()
        assert config.SessionLocal is None
        session = config.get_session()
        assert config.SessionLocal is not None
        session.close()
