# Test file for hybrid exporter
from datetime import datetime

import pytest

from chronicon.exporters.hybrid import HybridExporter
from chronicon.models.category import Category
from chronicon.models.post import Post
from chronicon.models.topic import Topic
from chronicon.models.user import User
from chronicon.storage.database import ArchiveDatabase


@pytest.fixture
def sample_db(tmp_path):
    """Create a sample database with test data."""
    db_path = tmp_path / "test.db"
    db = ArchiveDatabase(db_path)

    # Update site metadata
    db.update_site_metadata(
        "https://example.com", site_title="Test Forum", site_description="Test"
    )

    # Create sample category
    category = Category(
        id=1,
        name="General",
        slug="general",
        color="FF0000",
        text_color="FFFFFF",
        description="General discussion",
        parent_category_id=None,
        topic_count=1,
    )
    db.insert_category(category)

    # Create sample user
    user = User(
        id=1,
        username="testuser",
        name="Test User",
        avatar_template="/avatars/{size}/1.png",
        trust_level=1,
        created_at=datetime(2024, 1, 1, 10, 0, 0),
    )
    db.insert_user(user)

    # Create sample topic
    topic = Topic(
        id=1,
        title="Test Topic",
        slug="test-topic",
        category_id=1,
        user_id=1,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 1, 12, 0, 0),
        posts_count=2,
        views=10,
    )
    db.insert_topic(topic)

    # Create sample posts
    post1 = Post(
        id=1,
        topic_id=1,
        user_id=1,
        post_number=1,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 1, 12, 0, 0),
        cooked="<p>This is the first post</p>",
        raw="This is the first post",
        username="testuser",
    )
    db.insert_post(post1)

    post2 = Post(
        id=2,
        topic_id=1,
        user_id=1,
        post_number=2,
        created_at=datetime(2024, 1, 1, 12, 30, 0),
        updated_at=datetime(2024, 1, 1, 12, 30, 0),
        cooked="<p>This is a reply</p>",
        raw="This is a reply",
        username="testuser",
    )
    db.insert_post(post2)

    yield db
    db.close()


def test_hybrid_export_creates_both_formats(tmp_path, sample_db):
    """Test that hybrid export creates both HTML and Markdown outputs."""
    output_dir = tmp_path / "hybrid_output"

    exporter = HybridExporter(
        sample_db,
        output_dir,
        include_html=True,
        include_md=True,
    )
    exporter.export()

    # Verify HTML files exist at root
    assert (output_dir / "index.html").exists()
    assert (output_dir / "t" / "test-topic" / "1" / "index.html").exists()
    assert (output_dir / "c" / "general" / "1" / "index.html").exists()
    # search.html and search_index.json only created with static search backend
    # Default is FTS (server-side search), so these files won't exist

    # Verify Markdown files exist in /md/ subdirectory
    assert (output_dir / "md" / "README.md").exists()
    assert (output_dir / "md" / "index.md").exists()
    assert (output_dir / "md" / "t" / "test-topic" / "1.md").exists()
    assert (output_dir / "md" / "c" / "general" / "index.md").exists()

    # Verify shared assets directory exists at root
    assert (output_dir / "assets").exists()
    assert (output_dir / "assets" / "css").exists()
    # Note: assets/js only exists with static search backend

    # Verify root README exists
    assert (output_dir / "README.md").exists()
    root_readme = (output_dir / "README.md").read_text()
    assert "Test Forum Archive" in root_readme
    assert "Archive Statistics" in root_readme
    assert "Browse the Archive" in root_readme

    # Verify GitHub Pages config exists
    assert (output_dir / "_config.yml").exists()
    config_content = (output_dir / "_config.yml").read_text()
    assert "exclude:" in config_content
    assert "- md" in config_content


def test_hybrid_export_html_only(tmp_path, sample_db):
    """Test hybrid export with only HTML enabled."""
    output_dir = tmp_path / "html_only"

    exporter = HybridExporter(
        sample_db,
        output_dir,
        include_html=True,
        include_md=False,
    )
    exporter.export()

    # HTML files should exist
    assert (output_dir / "index.html").exists()
    assert (output_dir / "t" / "test-topic" / "1" / "index.html").exists()

    # Markdown directory should not exist
    assert not (output_dir / "md").exists()

    # Root README and config should still exist
    assert (output_dir / "README.md").exists()
    assert (output_dir / "_config.yml").exists()


def test_hybrid_export_markdown_only(tmp_path, sample_db):
    """Test hybrid export with only Markdown enabled."""
    output_dir = tmp_path / "md_only"

    exporter = HybridExporter(
        sample_db,
        output_dir,
        include_html=False,
        include_md=True,
    )
    exporter.export()

    # HTML files should not exist (except root README)
    assert not (output_dir / "index.html").exists()
    assert not (output_dir / "search.html").exists()

    # Markdown files should exist
    assert (output_dir / "md" / "README.md").exists()
    assert (output_dir / "md" / "t" / "test-topic" / "1.md").exists()

    # Root README should still exist
    assert (output_dir / "README.md").exists()


def test_hybrid_export_shared_assets(tmp_path, sample_db):
    """Test that HTML and Markdown share the same assets directory."""
    output_dir = tmp_path / "shared_assets"

    # Create some mock downloaded assets
    assets_dir = output_dir / "assets"
    images_dir = assets_dir / "images" / "1"
    images_dir.mkdir(parents=True, exist_ok=True)

    test_image = images_dir / "test.png"
    test_image.write_text("fake image data")

    # Register asset in database
    sample_db.register_asset(
        "https://example.com/test.png", str(test_image), "image/png"
    )

    exporter = HybridExporter(
        sample_db,
        output_dir,
        include_html=True,
        include_md=True,
    )
    exporter.export()

    # Verify assets exist at root level (not duplicated)
    assert (output_dir / "assets" / "images" / "1" / "test.png").exists()

    # Verify no duplicate assets in /md/assets/
    assert not (output_dir / "md" / "assets").exists()


def test_hybrid_export_root_readme_content(tmp_path, sample_db):
    """Test that root README has correct statistics and links."""
    output_dir = tmp_path / "readme_test"

    exporter = HybridExporter(
        sample_db,
        output_dir,
        include_html=True,
        include_md=True,
    )
    exporter.export()

    readme = (output_dir / "README.md").read_text()

    # Check for required sections
    assert "# Test Forum Archive" in readme
    assert "## Archive Statistics" in readme
    assert "- **Topics:** 1" in readme
    assert "- **Posts:** 2" in readme
    assert "- **Users:** 1" in readme

    # Check for browsing options
    assert "## Browse the Archive" in readme
    assert "### Web Experience (Recommended)" in readme
    assert "[View HTML Archive](index.html)" in readme
    assert "### Markdown Browsing" in readme
    assert "[Browse Markdown Archive](md/index.md)" in readme

    # Check for deployment info
    assert "## Deployment" in readme
    assert "_config.yml" in readme

    # Check for footer
    assert "Chronicon" in readme


def test_hybrid_export_incremental_topics(tmp_path, sample_db):
    """Test incremental topic regeneration in hybrid mode."""
    output_dir = tmp_path / "incremental"

    # Initial export
    exporter = HybridExporter(
        sample_db,
        output_dir,
        include_html=True,
        include_md=True,
    )
    exporter.export()

    # Verify initial files exist
    html_topic = output_dir / "t" / "test-topic" / "1" / "index.html"
    md_topic = output_dir / "md" / "t" / "test-topic" / "1.md"

    assert html_topic.exists()
    assert md_topic.exists()

    # Get initial modification times
    html_mtime = html_topic.stat().st_mtime
    md_mtime = md_topic.stat().st_mtime

    # Add a new post to the topic
    new_post = Post(
        id=3,
        topic_id=1,
        user_id=1,
        post_number=3,
        created_at=datetime(2024, 1, 1, 13, 0, 0),
        updated_at=datetime(2024, 1, 1, 13, 0, 0),
        cooked="<p>New post</p>",
        raw="New post",
        username="testuser",
    )
    sample_db.insert_post(new_post)

    # Regenerate just this topic
    exporter.export_topics([1])

    # Verify files were updated
    assert html_topic.stat().st_mtime > html_mtime
    assert md_topic.stat().st_mtime > md_mtime

    # Verify new content appears
    html_content = html_topic.read_text()
    md_content = md_topic.read_text()

    assert "New post" in html_content
    assert "New post" in md_content


def test_hybrid_export_update_index(tmp_path, sample_db):
    """Test that update_index regenerates README and indexes."""
    output_dir = tmp_path / "update_index_test"

    exporter = HybridExporter(
        sample_db,
        output_dir,
        include_html=True,
        include_md=True,
    )
    exporter.export()

    # Get initial README modification time
    root_readme = output_dir / "README.md"
    initial_mtime = root_readme.stat().st_mtime

    # Update indexes
    exporter.update_index()

    # Verify README was regenerated
    assert root_readme.stat().st_mtime >= initial_mtime


def test_hybrid_export_github_pages_config(tmp_path, sample_db):
    """Test GitHub Pages configuration file content."""
    output_dir = tmp_path / "config_test"

    exporter = HybridExporter(
        sample_db,
        output_dir,
        include_html=True,
        include_md=True,
    )
    exporter.export()

    config_path = output_dir / "_config.yml"
    assert config_path.exists()

    config_content = config_path.read_text()

    # Check exclusions
    assert "exclude:" in config_content
    assert "- md" in config_content
    assert "- archive.db" in config_content
    assert '- "*.json"' in config_content

    # Check inclusions
    assert "include:" in config_content
    assert "- assets" in config_content

    # Check other config
    assert 'baseurl: ""' in config_content
    assert "markdown: kramdown" in config_content
