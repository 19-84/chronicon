# ABOUTME: Factory module for creating database instances based on connection string
# ABOUTME: Supports SQLite (sqlite:///) and PostgreSQL (postgresql://) backends

from pathlib import Path

from chronicon.storage.database_base import ArchiveDatabaseBase


def get_database(connection_string: str) -> ArchiveDatabaseBase:
    """
    Create a database instance based on the connection string.

    Supports two backends:
    - SQLite: connection_string starts with "sqlite:///" or is a file path
    - PostgreSQL: connection_string starts with "postgresql://" or "postgres://"

    Args:
        connection_string: Database connection string or file path
            - SQLite: "sqlite:///path/to/db.sqlite" or "/path/to/db.sqlite"
            - PostgreSQL: "postgresql://user:pass@host:port/dbname"

    Returns:
        ArchiveDatabase instance (SQLite or PostgreSQL implementation)

    Raises:
        ValueError: If connection string format is not recognized

    Examples:
        >>> db = get_database("sqlite:///archive.db")
        >>> db = get_database("/path/to/archive.db")
        >>> db = get_database("postgresql://localhost/chronicon")
    """
    # PostgreSQL connection strings
    if connection_string.startswith(("postgresql://", "postgres://")):
        try:
            from chronicon.storage.postgres_database import PostgresArchiveDatabase
        except ImportError as e:
            raise ImportError(
                "PostgreSQL support requires psycopg. "
                "Install with: pip install chronicon[postgres]"
            ) from e
        return PostgresArchiveDatabase(connection_string)

    # SQLite connection strings or plain file paths
    if connection_string.startswith("sqlite:///"):
        # Remove sqlite:/// prefix
        db_path = connection_string.replace("sqlite:///", "")
    else:
        # Treat as plain file path
        db_path = connection_string

    # Import SQLite database
    from chronicon.storage.database import ArchiveDatabase

    return ArchiveDatabase(Path(db_path))
