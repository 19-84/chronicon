# ABOUTME: Integration tests for FTS5 search with FastAPI search server
# ABOUTME: Validates full search stack against real Theme category archive data

import re
import shutil
import sqlite3
from pathlib import Path

import pytest

# Skip all tests if FastAPI is not installed
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from chronicon.storage.database import ArchiveDatabase

ARCHIVE_DB_PATH = Path(__file__).parent.parent / "archives" / "archive.db"

# Skip entire module if archive.db doesn't exist
pytestmark = pytest.mark.skipif(
    not ARCHIVE_DB_PATH.exists(),
    reason="archives/archive.db not found (run archive command first)",
)


def _strip_html(html_text: str) -> str:
    """Strip HTML tags and normalize whitespace for populating raw column."""
    if not html_text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", html_text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def theme_archive_db(tmp_path):
    """Open a copy of the real archive.db for database-level FTS queries."""
    dest = tmp_path / "archive.db"
    shutil.copy2(ARCHIVE_DB_PATH, dest)
    db = ArchiveDatabase(dest)
    return db


@pytest.fixture
def theme_client(tmp_path, monkeypatch):
    """FastAPI TestClient backed by a copy of the real archive.db."""
    dest = tmp_path / "archive.db"
    shutil.copy2(ARCHIVE_DB_PATH, dest)

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{dest}")

    from chronicon.api.app import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def populated_fts_db(tmp_path):
    """
    Copy of archive.db with raw column populated from stripped cooked HTML.

    This enables post-level FTS search which otherwise returns 0 results
    because all posts in the original archive have raw = NULL.
    """
    dest = tmp_path / "archive.db"
    shutil.copy2(ARCHIVE_DB_PATH, dest)

    conn = sqlite3.connect(str(dest))
    cursor = conn.cursor()

    # Populate raw from stripped cooked for all posts
    cursor.execute(
        "SELECT id, cooked FROM posts WHERE raw IS NULL AND cooked IS NOT NULL"
    )
    rows = cursor.fetchall()
    for post_id, cooked in rows:
        raw_text = _strip_html(cooked)
        cursor.execute("UPDATE posts SET raw = ? WHERE id = ?", (raw_text, post_id))
    conn.commit()
    conn.close()

    db = ArchiveDatabase(dest)
    db.rebuild_search_index()
    return db


@pytest.fixture
def populated_fts_client(tmp_path, monkeypatch):
    """
    FastAPI TestClient backed by archive.db with raw column populated.

    Enables post search API testing.
    """
    dest = tmp_path / "archive.db"
    shutil.copy2(ARCHIVE_DB_PATH, dest)

    conn = sqlite3.connect(str(dest))
    cursor = conn.cursor()

    # Populate raw from stripped cooked for all posts
    cursor.execute(
        "SELECT id, cooked FROM posts WHERE raw IS NULL AND cooked IS NOT NULL"
    )
    rows = cursor.fetchall()
    for post_id, cooked in rows:
        raw_text = _strip_html(cooked)
        cursor.execute("UPDATE posts SET raw = ? WHERE id = ?", (raw_text, post_id))
    conn.commit()
    conn.close()

    # Rebuild FTS index with new raw data
    db = ArchiveDatabase(dest)
    db.rebuild_search_index()
    del db  # Close before handing to API

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{dest}")

    from chronicon.api.app import app

    with TestClient(app) as client:
        yield client


# ===========================================================================
# Group 1: Database FTS Validation
# ===========================================================================


class TestDatabaseFTSValidation:
    """Validate FTS5 tables and search at the database level."""

    def test_fts_tables_exist_in_archive(self, theme_archive_db):
        """FTS5 tables exist and is_search_available() returns True."""
        assert theme_archive_db.is_search_available() is True

        conn = theme_archive_db.connection
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_fts'"
        )
        fts_tables = sorted(row["name"] for row in cursor.fetchall())
        assert "posts_fts" in fts_tables
        assert "topics_fts" in fts_tables

    def test_topics_fts_row_count_matches_topics(self, theme_archive_db):
        """FTS topic row count matches the topics table count (65)."""
        conn = theme_archive_db.connection
        topic_count = conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
        fts_count = conn.execute("SELECT COUNT(*) FROM topics_fts").fetchone()[0]
        assert topic_count == 65
        assert fts_count == topic_count

    def test_topic_search_returns_results_for_theme(self, theme_archive_db):
        """Searching 'theme' returns most topics since they're all in Theme category."""
        results = theme_archive_db.search_topics("theme")
        count = theme_archive_db.search_topics_count("theme")
        assert len(results) >= 50
        assert count >= 50
        assert count == len(theme_archive_db.search_topics("theme", limit=100))

    def test_topic_search_bm25_ranking(self, theme_archive_db):
        """'dark theme' search ranks topics with both words in title higher."""
        results = theme_archive_db.search_topics("dark theme", limit=10)
        assert len(results) >= 1
        # Top results should contain "dark" in the title
        top_titles = [r.title.lower() for r in results[:3]]
        assert any("dark" in title for title in top_titles)

    def test_posts_fts_raw_null_documents_limitation(self, theme_archive_db):
        """Post search returns 0 results when all raw columns are NULL."""
        results = theme_archive_db.search_posts("theme")
        assert len(results) == 0
        count = theme_archive_db.search_posts_count("theme")
        assert count == 0


# ===========================================================================
# Group 2: Post FTS with Populated Raw
# ===========================================================================


class TestPostFTSWithPopulatedRaw:
    """Validate post search after populating raw from cooked HTML."""

    def test_post_search_with_populated_raw(self, populated_fts_db):
        """After populating raw from stripped cooked, search returns results."""
        results = populated_fts_db.search_posts("theme")
        assert len(results) > 0

    def test_post_search_count_matches(self, populated_fts_db):
        """search_posts_count matches the actual number of results."""
        query = "color"
        count = populated_fts_db.search_posts_count(query)
        # Fetch all results to compare
        all_results = populated_fts_db.search_posts(query, limit=count + 100)
        assert count == len(all_results)

    def test_post_search_pagination(self, populated_fts_db):
        """Paginated post search returns different posts for different offsets."""
        query = "theme"
        page1 = populated_fts_db.search_posts(query, limit=5, offset=0)
        page2 = populated_fts_db.search_posts(query, limit=5, offset=5)

        assert len(page1) == 5
        assert len(page2) > 0

        page1_ids = {p.id for p in page1}
        page2_ids = {p.id for p in page2}
        assert page1_ids.isdisjoint(page2_ids), "Pages should have different posts"


# ===========================================================================
# Group 3: API Topic Search
# ===========================================================================


class TestAPITopicSearch:
    """Test topic search API endpoints against real archive data."""

    def test_api_health_reports_search_available(self, theme_client):
        """GET /health reports search_available=true and correct counts."""
        response = theme_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert data["search_available"] is True
        assert data["total_topics"] == 65
        assert data["total_posts"] == 2505

    def test_api_search_topics_returns_results(self, theme_client):
        """GET /api/v1/search/topics?q=theme returns results with expected fields."""
        response = theme_client.get("/api/v1/search/topics?q=theme")
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "theme"
        assert data["total"] >= 50
        assert len(data["results"]) > 0

        # Check result structure
        result = data["results"][0]
        assert "id" in result
        assert "title" in result
        assert "slug" in result

    def test_api_search_topics_pagination(self, theme_client):
        """Page 1 and page 2 return different results with consistent total."""
        response1 = theme_client.get("/api/v1/search/topics?q=theme&page=1&per_page=5")
        response2 = theme_client.get("/api/v1/search/topics?q=theme&page=2&per_page=5")

        data1 = response1.json()
        data2 = response2.json()

        assert data1["total"] == data2["total"]
        assert data1["page"] == 1
        assert data2["page"] == 2

        ids1 = {r["id"] for r in data1["results"]}
        ids2 = {r["id"] for r in data2["results"]}
        assert ids1.isdisjoint(ids2), "Different pages should have different results"

    def test_api_search_topics_field_selection(self, theme_client):
        """fields=id,title filters response fields."""
        response = theme_client.get("/api/v1/search/topics?q=theme&fields=id,title")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0

        result = data["results"][0]
        assert "id" in result
        assert "title" in result
        # Other fields should be excluded
        assert "slug" not in result
        assert "views" not in result

    def test_api_search_topics_empty_query_rejected(self, theme_client):
        """Empty q parameter is rejected with 422."""
        response = theme_client.get("/api/v1/search/topics?q=")
        assert response.status_code == 422


# ===========================================================================
# Group 4: API Post Search (with populated FTS)
# ===========================================================================


class TestAPIPostSearch:
    """Test post search API endpoints using populated FTS data."""

    def test_api_search_posts_returns_results(self, populated_fts_client):
        """Post search results include topic_title and topic_slug context."""
        response = populated_fts_client.get("/api/v1/search/posts?q=theme")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0
        assert len(data["results"]) > 0

        result = data["results"][0]
        assert "topic_title" in result
        assert "topic_slug" in result

    def test_api_search_posts_body_truncation(self, populated_fts_client):
        """max_body_length truncates raw and cooked fields."""
        response = populated_fts_client.get(
            "/api/v1/search/posts?q=theme&max_body_length=50"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0

        for result in data["results"]:
            if result.get("raw"):
                # 50 chars + "..." = max 53
                assert len(result["raw"]) <= 53
            if result.get("cooked"):
                assert len(result["cooked"]) <= 53

    def test_api_search_posts_category_context(self, populated_fts_client):
        """Post search results include category_name and category_color."""
        response = populated_fts_client.get("/api/v1/search/posts?q=theme")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0

        # All posts in this archive are from the Theme category
        result = data["results"][0]
        assert result["category_name"] == "Theme"
        assert result["category_color"] == "E43D30"


# ===========================================================================
# Group 5: HTML Search Endpoint
# ===========================================================================


class TestHTMLSearchEndpoint:
    """Test server-rendered HTML search page."""

    def test_html_search_renders_results(self, theme_client):
        """GET /search?q=theme returns 200 with topic matches in HTML."""
        response = theme_client.get("/search?q=theme")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Should contain search results
        assert "theme" in response.text.lower()

    def test_html_search_shows_topic_matches(self, theme_client):
        """GET /search?q=dark returns HTML containing dark-related topics."""
        response = theme_client.get("/search?q=dark")
        assert response.status_code == 200
        text_lower = response.text.lower()
        assert "dark" in text_lower

    def test_html_search_empty_shows_form(self, theme_client):
        """GET /search (no query) returns 200 with search form, no results."""
        response = theme_client.get("/search")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Should contain a search form (input or form element)
        assert "search" in response.text.lower()
        # Should NOT contain result items (no topic/post results rendered)
        assert "result_type" not in response.text


# ===========================================================================
# Group 6: Search Quality
# ===========================================================================


class TestSearchQuality:
    """Validate search quality with known topic data."""

    def test_search_specific_theme_graceful(self, theme_archive_db):
        """'Graceful' returns exactly topic 93040."""
        results = theme_archive_db.search_topics("Graceful")
        assert len(results) == 1
        assert results[0].id == 93040
        assert "Graceful" in results[0].title

    def test_search_specific_theme_material_design(self, theme_archive_db):
        """'Material Design' returns topic 47142 in results."""
        results = theme_archive_db.search_topics('"Material Design"')
        topic_ids = {r.id for r in results}
        assert 47142 in topic_ids

    def test_search_no_results_for_unrelated(self, theme_archive_db):
        """'kubernetes' returns 0 results in a Theme-only archive."""
        results = theme_archive_db.search_topics("kubernetes")
        assert len(results) == 0
        count = theme_archive_db.search_topics_count("kubernetes")
        assert count == 0

    def test_search_results_include_category_context(self, theme_client):
        """API topic search results include category_name='Theme'."""
        response = theme_client.get("/api/v1/search/topics?q=dark")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0

        for result in data["results"]:
            assert result["category_name"] == "Theme"
            assert result["category_color"] == "E43D30"
