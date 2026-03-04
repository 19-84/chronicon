# ABOUTME: Storage module for Chronicon
# ABOUTME: Handles SQLite and PostgreSQL database operations and schema management

"""
Database storage layer for Discourse archives.

This module provides both SQLite and PostgreSQL-based storage with efficient indexing,
migrations, and CRUD operations for all Discourse entities.

Classes:
    ArchiveDatabase: SQLite database implementation (default)
    PostgresArchiveDatabase: PostgreSQL database implementation
    ArchiveDatabaseBase: Abstract base class for database implementations
"""

from .database import ArchiveDatabase
from .database_base import ArchiveDatabaseBase
from .schema import create_schema

# PostgreSQL is optional - only import if psycopg is available
try:
    from .postgres_database import PostgresArchiveDatabase

    __all__ = [
        "ArchiveDatabase",
        "PostgresArchiveDatabase",
        "ArchiveDatabaseBase",
        "create_schema",
    ]
except ImportError:
    __all__ = ["ArchiveDatabase", "ArchiveDatabaseBase", "create_schema"]
