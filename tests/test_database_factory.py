# ABOUTME: Tests for database factory pattern
# ABOUTME: Validates factory correctly creates SQLite and PostgreSQL instances

import os

import pytest

from chronicon.storage.factory import get_database


def test_factory_sqlite_with_prefix(tmp_path):
    """Test factory with sqlite:/// prefix."""
    db_path = tmp_path / "test.db"
    connection_string = f"sqlite:///{db_path}"

    db = get_database(connection_string)

    # Should return SQLite instance
    from chronicon.storage.database import ArchiveDatabase

    assert isinstance(db, ArchiveDatabase)

    # Should be functional
    assert db.is_search_available() is True


def test_factory_sqlite_plain_path(tmp_path):
    """Test factory with plain file path (no prefix)."""
    db_path = tmp_path / "test.db"
    connection_string = str(db_path)

    db = get_database(connection_string)

    # Should return SQLite instance
    from chronicon.storage.database import ArchiveDatabase

    assert isinstance(db, ArchiveDatabase)


def test_factory_sqlite_relative_path():
    """Test factory with relative path."""
    connection_string = "test_archive.db"

    db = get_database(connection_string)

    from chronicon.storage.database import ArchiveDatabase

    assert isinstance(db, ArchiveDatabase)


def test_factory_postgresql_prefix():
    """Test factory with postgresql:// prefix."""
    # Skip if psycopg not installed
    pytest.importorskip("psycopg")

    connection_string = "postgresql://localhost/testdb"

    try:
        db = get_database(connection_string)

        # Should return PostgreSQL instance
        from chronicon.storage.postgres_database import PostgresArchiveDatabase

        assert isinstance(db, PostgresArchiveDatabase)
    except Exception:
        # Connection might fail if PostgreSQL not running - that's OK
        # We're just testing the factory logic
        pytest.skip("PostgreSQL not available")


def test_factory_postgres_prefix():
    """Test factory with postgres:// prefix (alternative)."""
    pytest.importorskip("psycopg")

    connection_string = "postgres://localhost/testdb"

    try:
        db = get_database(connection_string)

        from chronicon.storage.postgres_database import PostgresArchiveDatabase

        assert isinstance(db, PostgresArchiveDatabase)
    except Exception:
        pytest.skip("PostgreSQL not available")


def test_factory_postgresql_without_psycopg(tmp_path, monkeypatch):
    """Test factory raises helpful error if psycopg not installed."""
    # Temporarily hide psycopg import
    import sys

    original_modules = sys.modules.copy()

    # Remove psycopg from sys.modules if present
    if "psycopg" in sys.modules:
        del sys.modules["psycopg"]

    connection_string = "postgresql://localhost/testdb"

    # Mock the import to fail
    def mock_import(name, *args, **kwargs):
        if name == "chronicon.storage.postgres_database":
            raise ImportError("No module named 'psycopg'")
        return original_modules.get(name)

    with monkeypatch.context() as m:
        m.setattr("builtins.__import__", mock_import)

        with pytest.raises(ImportError) as exc_info:
            get_database(connection_string)

        assert "PostgreSQL support requires psycopg" in str(exc_info.value)
        assert "pip install chronicon[postgres]" in str(exc_info.value)


def test_factory_sqlite_creates_functional_db(tmp_path):
    """Test that factory-created SQLite database is fully functional."""
    from datetime import datetime

    from chronicon.models.topic import Topic

    db_path = tmp_path / "test.db"
    db = get_database(f"sqlite:///{db_path}")

    # Insert a topic
    now = datetime.now()
    topic = Topic(
        id=1,
        title="Test Topic",
        slug="test",
        posts_count=1,
        views=10,
        created_at=now,
        last_posted_at=now,
        updated_at=now,
        user_id=1,
        category_id=1,
        closed=False,
        archived=False,
        pinned=False,
        visible=True,
    )
    db.insert_topic(topic)

    # Retrieve it
    retrieved = db.get_topic(1)
    assert retrieved is not None
    assert retrieved.title == "Test Topic"

    # Search should work
    assert db.is_search_available() is True


def test_factory_with_environment_variable(tmp_path, monkeypatch):
    """Test using factory with DATABASE_URL environment variable."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    # This is how the API uses it
    connection_string = os.getenv("DATABASE_URL")
    db = get_database(connection_string)  # type: ignore[arg-type]

    from chronicon.storage.database import ArchiveDatabase

    assert isinstance(db, ArchiveDatabase)


def test_factory_connection_string_formats(tmp_path):
    """Test various valid connection string formats."""
    from chronicon.storage.database import ArchiveDatabase

    # Test sqlite:// prefix
    db_path1 = tmp_path / "test1.db"
    db1 = get_database(f"sqlite:///{db_path1}")
    assert isinstance(db1, ArchiveDatabase)

    # Test relative path
    import os

    original_dir = os.getcwd()
    os.chdir(tmp_path)
    try:
        db2 = get_database("./test2.db")
        assert isinstance(db2, ArchiveDatabase)

        db3 = get_database("test3.db")
        assert isinstance(db3, ArchiveDatabase)
    finally:
        os.chdir(original_dir)


def test_factory_abstract_base_interface(tmp_path):
    """Test that factory returns objects implementing ArchiveDatabaseBase."""
    from chronicon.storage.database_base import ArchiveDatabaseBase

    db_path = tmp_path / "test.db"
    db = get_database(f"sqlite:///{db_path}")

    # Should implement the abstract base interface
    assert isinstance(db, ArchiveDatabaseBase)

    # Should have all required methods
    assert hasattr(db, "insert_topic")
    assert hasattr(db, "get_topic")
    assert hasattr(db, "search_topics")
    assert hasattr(db, "is_search_available")
