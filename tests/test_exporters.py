# Test file for exporters
from datetime import datetime
from pathlib import Path

import pytest

from chronicon.exporters.html_static import HTMLStaticExporter
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

    # Create sample category
    category = Category(
        id=1,
        name="General Discussion",
        slug="general",
        color="FF0000",
        text_color="FFFFFF",
        description="General discussion topics",
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
        created_at=datetime(2024, 1, 1, 12, 5, 0),
        updated_at=datetime(2024, 1, 1, 12, 5, 0),
        cooked="<p>This is a reply</p>",
        raw="This is a reply",
        username="testuser",
    )
    db.insert_post(post2)

    return db


def test_html_export_creates_index(tmp_path, sample_db):
    """Test that HTML export creates an index page."""
    output_dir = tmp_path / "html_output"
    exporter = HTMLStaticExporter(sample_db, output_dir)
    exporter.generate_index()

    index_path = output_dir / "index.html"
    assert index_path.exists()

    content = index_path.read_text()
    assert "Forum Archive" in content
    assert "Statistics" in content
    assert "General Discussion" in content


def test_html_export_creates_category_pages(tmp_path, sample_db):
    """Test that HTML export creates category pages."""
    output_dir = tmp_path / "html_output"
    exporter = HTMLStaticExporter(sample_db, output_dir)
    exporter.generate_categories()

    # Check Discourse-compatible path structure: /c/{slug}/{id}/index.html
    category_path = output_dir / "c" / "general" / "1" / "index.html"
    assert category_path.exists()

    content = category_path.read_text()
    assert "General Discussion" in content
    assert "Test Topic" in content


def test_html_export_creates_topic_pages(tmp_path, sample_db):
    """Test that HTML export creates topic pages."""
    output_dir = tmp_path / "html_output"
    exporter = HTMLStaticExporter(sample_db, output_dir)
    exporter.generate_topics()

    # Check Discourse-compatible path structure: /t/{slug}/{id}.html
    topic_path = output_dir / "t" / "test-topic" / "1.html"
    assert topic_path.exists()

    content = topic_path.read_text()
    assert "Test Topic" in content
    assert "This is the first post" in content
    assert "This is a reply" in content
    assert "testuser" in content


def test_html_export_creates_search_index(tmp_path, sample_db):
    """Test that HTML export creates search index."""
    output_dir = tmp_path / "html_output"
    exporter = HTMLStaticExporter(sample_db, output_dir)
    exporter.generate_search_index()

    search_index_path = output_dir / "search_index.json"
    assert search_index_path.exists()

    import json

    content = json.loads(search_index_path.read_text())
    assert "version" in content
    assert "items" in content
    assert len(content["items"]) > 0

    # Verify URLs are relative paths (not absolute with leading /)
    for item in content["items"]:
        assert "url" in item
        assert not item["url"].startswith("/"), (
            f"URL should be relative, not absolute: {item['url']}"
        )

        # Verify URL structure matches expected format
        if item["type"] == "topic":
            # Topics should be: t/{slug}/{id}.html
            assert item["url"].startswith("t/"), (
                f"Topic URL should start with 't/': {item['url']}"
            )
            assert item["url"].endswith(".html"), (
                f"Topic URL should end with '.html': {item['url']}"
            )
        elif item["type"] == "post":
            # Posts should be: t/{slug}/{id}.html#post-{id}
            assert item["url"].startswith("t/"), (
                f"Post URL should start with 't/': {item['url']}"
            )
            assert "#post-" in item["url"], (
                f"Post URL should contain '#post-': {item['url']}"
            )


def test_html_export_copies_assets(tmp_path, sample_db):
    """Test that HTML export copies static assets."""
    output_dir = tmp_path / "html_output"
    # Use static search backend to test JS file copying
    exporter = HTMLStaticExporter(sample_db, output_dir, search_backend="static")
    exporter.copy_assets()

    assets_dir = output_dir / "assets"
    assert assets_dir.exists()
    assert (assets_dir / "css" / "archive.css").exists()
    assert (assets_dir / "js" / "search.js").exists()


def test_html_export_full_pipeline(tmp_path, sample_db):
    """Test complete HTML export pipeline."""
    output_dir = tmp_path / "html_output"
    # Use static search backend to test all static files generated
    exporter = HTMLStaticExporter(sample_db, output_dir, search_backend="static")
    exporter.export()

    # Check all expected files exist
    assert (output_dir / "index.html").exists()
    assert (output_dir / "search.html").exists()
    # Check Discourse-compatible paths
    assert (output_dir / "c" / "general" / "1" / "index.html").exists()
    assert (output_dir / "t" / "test-topic" / "1.html").exists()
    assert (output_dir / "search_index.json").exists()
    assert (output_dir / "assets" / "css" / "archive.css").exists()


def test_html_export_fts_mode_skips_search_files(tmp_path, sample_db):
    """Test FTS mode doesn't generate search.html or search_index.json."""
    output_dir = tmp_path / "html_output"
    # Default is fts mode
    exporter = HTMLStaticExporter(sample_db, output_dir)
    exporter.export()

    # Check core files exist
    assert (output_dir / "index.html").exists()
    assert (output_dir / "c" / "general" / "1" / "index.html").exists()
    assert (output_dir / "t" / "test-topic" / "1.html").exists()

    # Check that static search files are NOT generated in FTS mode
    assert not (output_dir / "search.html").exists()
    assert not (output_dir / "search_index.json").exists()
    assert not (output_dir / "assets" / "js" / "search.js").exists()

    # CSS should still be copied
    assert (output_dir / "assets" / "css" / "archive.css").exists()


def test_html_export_with_users(tmp_path, sample_db):
    """Test HTML export with user pages enabled."""
    output_dir = tmp_path / "html_output"
    exporter = HTMLStaticExporter(sample_db, output_dir, include_users=True)
    exporter.generate_users()

    user_path = output_dir / "users" / "testuser.html"
    assert user_path.exists()

    content = user_path.read_text()
    assert "testuser" in content


def test_html_export_renders_avatars_in_posts(tmp_path, sample_db):
    """Test that avatars are rendered in post headers."""
    output_dir = tmp_path / "html_output"
    exporter = HTMLStaticExporter(sample_db, output_dir)
    exporter.generate_topics()

    # Check Discourse-compatible path structure: /t/{slug}/{id}.html
    topic_path = output_dir / "t" / "test-topic" / "1.html"
    assert topic_path.exists()

    content = topic_path.read_text()

    # Should have avatar-related CSS classes
    assert "post-author-section" in content
    assert "avatar" in content
    assert "avatar-post" in content


def test_html_export_renders_avatar_placeholder(tmp_path, sample_db):
    """Test that avatar placeholder is rendered when no avatar is downloaded."""
    output_dir = tmp_path / "html_output"
    exporter = HTMLStaticExporter(sample_db, output_dir)
    exporter.generate_topics()

    topic_path = output_dir / "t" / "test-topic" / "1.html"
    content = topic_path.read_text()

    # Should have avatar placeholder with first letter of username
    # Since no avatars are downloaded in test, it should fallback to placeholder
    assert "avatar-placeholder" in content
    # Should have first letter of username (T from testuser)
    assert ">T<" in content


def test_html_export_handles_null_user_id(tmp_path, sample_db):
    """Test that posts with null user_id show system placeholder."""
    # Add a post with null user_id (system post)
    system_post = Post(
        id=3,
        topic_id=1,
        user_id=None,  # System post
        post_number=3,
        created_at=datetime(2024, 1, 1, 12, 10, 0),
        updated_at=datetime(2024, 1, 1, 12, 10, 0),
        cooked="<p>System message</p>",
        raw="System message",
        username="system",
    )
    sample_db.insert_post(system_post)

    output_dir = tmp_path / "html_output"
    exporter = HTMLStaticExporter(sample_db, output_dir)
    exporter.generate_topics()

    topic_path = output_dir / "t" / "test-topic" / "1.html"
    content = topic_path.read_text()

    # Should have question mark for system posts
    assert ">?<" in content
    # Should still have avatar-placeholder class
    assert "avatar-placeholder" in content


def test_database_statistics(tmp_path, sample_db):
    """Test database statistics query."""
    stats = sample_db.get_statistics()

    assert stats["total_topics"] == 1
    assert stats["total_posts"] == 2
    assert stats["total_users"] == 1
    assert stats["total_categories"] == 1


def test_github_markdown_export_creates_files(tmp_path, sample_db):
    """Test that GitHub markdown export creates expected files."""
    from chronicon.exporters.markdown import MarkdownGitHubExporter

    output_dir = tmp_path / "github_output"
    exporter = MarkdownGitHubExporter(sample_db, output_dir)
    exporter.export()

    # Check expected files exist
    assert (output_dir / "README.md").exists()
    assert (output_dir / "t").exists()

    # Check topic file was created using Discourse-style URL structure
    topic_path = output_dir / "t" / "test-topic" / "1.md"
    assert topic_path.exists()

    # Verify content
    content = topic_path.read_text()
    assert "# Test Topic" in content
    assert "testuser" in content


def test_github_markdown_export_readme(tmp_path, sample_db):
    """Test README generation with table of contents."""
    from chronicon.exporters.markdown import MarkdownGitHubExporter

    output_dir = tmp_path / "github_output"
    exporter = MarkdownGitHubExporter(sample_db, output_dir)
    exporter.generate_readme()

    readme_path = output_dir / "README.md"
    assert readme_path.exists()

    content = readme_path.read_text()

    # Should have title
    assert "Archived Forum" in content or "Archive" in content

    # Should have landing page sections
    assert "Getting Started" in content or "About This Archive" in content

    # Should NOT have table of contents (that's in index.md now)
    assert "Table of Contents" not in content

    # Should have navigation links
    assert "Latest Topics" in content

    # Should NOT mention categories/topics (those are in index.md)
    # README is now a landing page, not a content listing


def test_github_markdown_convert_html_to_gfm(tmp_path, sample_db):
    """Test HTML to GitHub-flavored markdown conversion."""
    from chronicon.exporters.markdown import MarkdownGitHubExporter

    output_dir = tmp_path / "github_output"
    exporter = MarkdownGitHubExporter(sample_db, output_dir)

    # Test simple HTML
    html = "<p>Hello <strong>world</strong>!</p>"
    md = exporter.convert_html_to_gfm(html, 1)
    assert "Hello" in md
    assert "world" in md

    # Test with images
    html = '<p>Check this <img src="https://example.com/image.png" alt="test"></p>'
    md = exporter.convert_html_to_gfm(html, 1)
    assert "!" in md  # Markdown image syntax
    assert "image" in md.lower()


def test_github_markdown_export_topic(tmp_path, sample_db):
    """Test exporting a single topic to GitHub markdown."""
    from chronicon.exporters.markdown import MarkdownGitHubExporter

    output_dir = tmp_path / "github_output"
    exporter = MarkdownGitHubExporter(sample_db, output_dir)

    # Get a topic from the database
    topics = sample_db.get_all_topics()
    topic = topics[0]

    # Export it
    result_path = exporter.export_topic(topic)

    # Check return value is a Path
    assert result_path is not None
    assert isinstance(result_path, Path)

    # Check file was created
    assert result_path.exists()

    # Verify content structure
    content = result_path.read_text()
    assert "# Test Topic" in content  # Title
    assert (
        "> **Category:**" in content or "**Category:**" in content
    )  # Metadata in blockquote
    assert "testuser" in content  # Author
    assert "### Post #1" in content  # Post header with H3
    assert "### Post #2" in content  # Second post


def test_github_markdown_full_pipeline(tmp_path, sample_db):
    """Test complete GitHub markdown export pipeline."""
    from chronicon.exporters.markdown import MarkdownGitHubExporter

    output_dir = tmp_path / "github_output"
    exporter = MarkdownGitHubExporter(sample_db, output_dir)
    exporter.export()

    # Verify all expected files exist
    assert (output_dir / "README.md").exists()
    assert (output_dir / "t" / "test-topic" / "1.md").exists()

    # Verify README content - should be landing page format
    readme = (output_dir / "README.md").read_text()
    assert "Getting Started" in readme
    assert "Browse the Archive" in readme
    # README should NOT have topic listings (those are in index.md)
    assert "Test Topic" not in readme

    # Verify topic content
    topic_content = (output_dir / "t" / "test-topic" / "1.md").read_text()
    assert "# Test Topic" in topic_content
    assert "first post" in topic_content
    assert "reply" in topic_content


def test_github_markdown_image_download(tmp_path, sample_db):
    """Test that images are downloaded and URLs rewritten correctly."""
    from unittest.mock import Mock

    from chronicon.exporters.markdown import MarkdownGitHubExporter
    from chronicon.fetchers.api_client import DiscourseAPIClient
    from chronicon.fetchers.assets import AssetDownloader

    # Create a post with an image
    post_with_image = Post(
        id=3,
        topic_id=1,
        user_id=1,
        post_number=3,
        created_at=datetime(2024, 1, 1, 13, 0, 0),
        updated_at=datetime(2024, 1, 1, 13, 0, 0),
        cooked=(
            '<p>Check this image: <img src="https://example.com/'
            'test-image.png" alt="test"></p>'
        ),
        raw="Check this image: ![test](https://example.com/test-image.png)",
        username="testuser",
    )
    sample_db.insert_post(post_with_image)

    # Create asset downloader with mock client
    output_dir = tmp_path / "github_output"
    assets_dir = tmp_path / "assets"

    # Mock the API client
    mock_client = Mock(spec=DiscourseAPIClient)
    mock_client.base_url = "https://example.com"

    # Create asset downloader
    asset_downloader = AssetDownloader(mock_client, sample_db, assets_dir)

    # Mock the actual download to avoid network calls
    def mock_download_image(url, topic_id):
        # Simulate successful download
        topic_dir = assets_dir / "images" / str(topic_id)
        topic_dir.mkdir(parents=True, exist_ok=True)

        # Create a dummy image file
        filename = Path(url).name
        local_path = topic_dir / filename
        local_path.write_text("fake image data")

        # Register in database
        sample_db.register_asset(url, str(local_path), "image/png")

        return local_path

    asset_downloader.download_image = mock_download_image  # type: ignore[attr-defined]

    # Create exporter with asset downloader
    exporter = MarkdownGitHubExporter(
        sample_db, output_dir, asset_downloader=asset_downloader
    )

    # Export topics
    exporter.export()

    # Verify image was downloaded
    image_path = assets_dir / "images" / "1" / "test-image.png"
    assert image_path.exists(), f"Image should be downloaded to {image_path}"

    # Verify image URL was rewritten in markdown
    topic_path = output_dir / "t" / "test-topic" / "1.md"
    content = topic_path.read_text()

    # Should have relative path to image
    assert "../../assets/images/1/test-image.png" in content, (
        "Image URL should be rewritten to relative path"
    )

    # Should NOT have original absolute URL
    assert "https://example.com/test-image.png" not in content, (
        "Original URL should be replaced"
    )


def test_github_markdown_image_download_failure(tmp_path, sample_db):
    """Test that original URLs are kept when image download fails."""
    from unittest.mock import Mock

    from chronicon.exporters.markdown import MarkdownGitHubExporter
    from chronicon.fetchers.api_client import DiscourseAPIClient
    from chronicon.fetchers.assets import AssetDownloader

    # Create a post with an image
    post_with_image = Post(
        id=3,
        topic_id=1,
        user_id=1,
        post_number=3,
        created_at=datetime(2024, 1, 1, 13, 0, 0),
        updated_at=datetime(2024, 1, 1, 13, 0, 0),
        cooked=(
            '<p>Check this image: <img src="https://example.com/'
            'test-image.png" alt="test"></p>'
        ),
        raw="Check this image: ![test](https://example.com/test-image.png)",
        username="testuser",
    )
    sample_db.insert_post(post_with_image)

    # Create asset downloader with mock client
    output_dir = tmp_path / "github_output"
    assets_dir = tmp_path / "assets"

    # Mock the API client
    mock_client = Mock(spec=DiscourseAPIClient)
    mock_client.base_url = "https://example.com"

    # Create asset downloader
    asset_downloader = AssetDownloader(mock_client, sample_db, assets_dir)

    # Mock download_image to simulate failure
    def mock_download_image_fails(url, topic_id):
        return None  # Simulate download failure

    asset_downloader.download_image = mock_download_image_fails  # type: ignore[attr-defined]

    # Create exporter with asset downloader
    exporter = MarkdownGitHubExporter(
        sample_db, output_dir, asset_downloader=asset_downloader
    )

    # Export topics
    exporter.export()

    # Verify topic was exported
    topic_path = output_dir / "t" / "test-topic" / "1.md"
    content = topic_path.read_text()

    # Should keep original URL when download fails
    assert "https://example.com/test-image.png" in content, (
        "Original URL should be kept when download fails"
    )


@pytest.fixture
def multi_user_db(tmp_path):
    """Create a sample database with multiple users for user regeneration tests."""
    db_path = tmp_path / "multi_user_test.db"
    db = ArchiveDatabase(db_path)

    category = Category(
        id=1,
        name="General",
        slug="general",
        color="FF0000",
        text_color="FFFFFF",
        description="General topics",
        parent_category_id=None,
        topic_count=2,
    )
    db.insert_category(category)

    user_alice = User(
        id=1,
        username="alice",
        name="Alice A",
        avatar_template="/avatars/{size}/1.png",
        trust_level=2,
        created_at=datetime(2024, 1, 1, 10, 0, 0),
    )
    user_bob = User(
        id=2,
        username="bob",
        name="Bob B",
        avatar_template="/avatars/{size}/2.png",
        trust_level=1,
        created_at=datetime(2024, 1, 2, 10, 0, 0),
    )
    user_charlie = User(
        id=3,
        username="charlie",
        name="Charlie C",
        avatar_template="/avatars/{size}/3.png",
        trust_level=1,
        created_at=datetime(2024, 1, 3, 10, 0, 0),
    )
    db.insert_user(user_alice)
    db.insert_user(user_bob)
    db.insert_user(user_charlie)

    topic1 = Topic(
        id=1,
        title="Topic One",
        slug="topic-one",
        category_id=1,
        user_id=1,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 1, 12, 0, 0),
        posts_count=2,
        views=10,
    )
    topic2 = Topic(
        id=2,
        title="Topic Two",
        slug="topic-two",
        category_id=1,
        user_id=2,
        created_at=datetime(2024, 1, 2, 12, 0, 0),
        updated_at=datetime(2024, 1, 2, 12, 0, 0),
        posts_count=1,
        views=5,
    )
    db.insert_topic(topic1)
    db.insert_topic(topic2)

    post1 = Post(
        id=1,
        topic_id=1,
        user_id=1,
        post_number=1,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 1, 12, 0, 0),
        cooked="<p>Alice's first post</p>",
        raw="Alice's first post",
        username="alice",
    )
    post2 = Post(
        id=2,
        topic_id=1,
        user_id=2,
        post_number=2,
        created_at=datetime(2024, 1, 1, 12, 5, 0),
        updated_at=datetime(2024, 1, 1, 12, 5, 0),
        cooked="<p>Bob's reply</p>",
        raw="Bob's reply",
        username="bob",
    )
    post3 = Post(
        id=3,
        topic_id=2,
        user_id=2,
        post_number=1,
        created_at=datetime(2024, 1, 2, 12, 0, 0),
        updated_at=datetime(2024, 1, 2, 12, 0, 0),
        cooked="<p>Bob's topic</p>",
        raw="Bob's topic",
        username="bob",
    )
    post4 = Post(
        id=4,
        topic_id=2,
        user_id=3,
        post_number=2,
        created_at=datetime(2024, 1, 2, 12, 5, 0),
        updated_at=datetime(2024, 1, 2, 12, 5, 0),
        cooked="<p>Charlie's reply</p>",
        raw="Charlie's reply",
        username="charlie",
    )
    db.insert_post(post1)
    db.insert_post(post2)
    db.insert_post(post3)
    db.insert_post(post4)

    return db


def test_html_export_users_by_username(tmp_path, multi_user_db):
    """Test export_users_by_username regenerates specified users."""
    output_dir = tmp_path / "html_output"
    exporter = HTMLStaticExporter(multi_user_db, output_dir, include_users=True)

    # First do a full user export so pages exist
    exporter.generate_users_index()
    exporter.generate_users()

    # Verify all three user pages exist
    assert (output_dir / "users" / "alice.html").exists()
    assert (output_dir / "users" / "bob.html").exists()
    assert (output_dir / "users" / "charlie.html").exists()

    # Record modification times
    alice_mtime = (output_dir / "users" / "alice.html").stat().st_mtime
    charlie_mtime = (output_dir / "users" / "charlie.html").stat().st_mtime

    import time

    time.sleep(0.05)  # Ensure mtime difference

    # Regenerate only bob's page
    exporter.export_users_by_username({"bob"})

    # Bob's page should be regenerated (newer mtime)
    bob_new_mtime = (output_dir / "users" / "bob.html").stat().st_mtime

    # Alice and Charlie should NOT be regenerated
    alice_new_mtime = (output_dir / "users" / "alice.html").stat().st_mtime
    charlie_new_mtime = (output_dir / "users" / "charlie.html").stat().st_mtime

    assert bob_new_mtime > alice_mtime  # Bob was regenerated
    assert alice_new_mtime == alice_mtime  # Alice was NOT regenerated
    assert charlie_new_mtime == charlie_mtime  # Charlie was NOT regenerated


def test_html_export_users_by_username_skips_when_not_included(tmp_path, multi_user_db):
    """Test that export_users_by_username does nothing when include_users is False."""
    output_dir = tmp_path / "html_output"
    exporter = HTMLStaticExporter(multi_user_db, output_dir, include_users=False)

    # Should not create any user files
    exporter.export_users_by_username({"alice", "bob"})

    users_dir = output_dir / "users"
    assert not users_dir.exists() or not list(users_dir.glob("*.html"))


def test_html_export_users_by_username_regenerates_index(tmp_path, multi_user_db):
    """Test that export_users_by_username also regenerates the users index."""
    output_dir = tmp_path / "html_output"
    exporter = HTMLStaticExporter(multi_user_db, output_dir, include_users=True)

    # Full export first
    exporter.generate_users_index()
    exporter.generate_users()

    index_mtime = (output_dir / "users" / "index.html").stat().st_mtime

    import time

    time.sleep(0.05)

    # Regenerate a specific user
    exporter.export_users_by_username({"alice"})

    # Users index should be regenerated (post counts may have changed)
    index_new_mtime = (output_dir / "users" / "index.html").stat().st_mtime
    assert index_new_mtime > index_mtime


def test_html_export_users_by_username_empty_set(tmp_path, multi_user_db):
    """Test that export_users_by_username handles empty set gracefully."""
    output_dir = tmp_path / "html_output"
    exporter = HTMLStaticExporter(multi_user_db, output_dir, include_users=True)

    # Should not raise
    exporter.export_users_by_username(set())


def test_html_export_users_by_username_unknown_user(tmp_path, multi_user_db):
    """Test that export_users_by_username handles unknown usernames gracefully."""
    output_dir = tmp_path / "html_output"
    exporter = HTMLStaticExporter(multi_user_db, output_dir, include_users=True)

    # Should not raise for unknown usernames
    exporter.export_users_by_username({"nonexistent_user"})


def test_markdown_export_users_by_username(tmp_path, multi_user_db):
    """Test that Markdown export_users_by_username regenerates only specified users."""
    from chronicon.exporters.markdown import MarkdownGitHubExporter

    output_dir = tmp_path / "md_output"
    exporter = MarkdownGitHubExporter(multi_user_db, output_dir, include_users=True)

    # Full export first
    exporter.generate_users_index()
    exporter.export_users()

    assert (output_dir / "users" / "alice.md").exists()
    assert (output_dir / "users" / "bob.md").exists()

    alice_mtime = (output_dir / "users" / "alice.md").stat().st_mtime

    import time

    time.sleep(0.05)

    exporter.export_users_by_username({"bob"})

    bob_new_mtime = (output_dir / "users" / "bob.md").stat().st_mtime
    alice_new_mtime = (output_dir / "users" / "alice.md").stat().st_mtime

    assert bob_new_mtime > alice_mtime  # Bob was regenerated
    assert alice_new_mtime == alice_mtime  # Alice was NOT regenerated


def test_markdown_export_users_by_username_skips_when_not_included(
    tmp_path, multi_user_db
):
    """Test MD export_users_by_username skips when not included."""
    from chronicon.exporters.markdown import MarkdownGitHubExporter

    output_dir = tmp_path / "md_output"
    exporter = MarkdownGitHubExporter(multi_user_db, output_dir, include_users=False)

    exporter.export_users_by_username({"alice"})

    users_dir = output_dir / "users"
    assert not users_dir.exists() or not list(users_dir.glob("*.md"))


def test_hybrid_export_users_by_username(tmp_path, multi_user_db):
    """Test HybridExporter delegates export_users_by_username."""
    from unittest.mock import patch

    from chronicon.exporters.hybrid import HybridExporter
    from chronicon.exporters.markdown import MarkdownGitHubExporter

    output_dir = tmp_path / "hybrid_output"
    exporter = HybridExporter(
        multi_user_db,
        output_dir,
        include_html=True,
        include_md=True,
        include_users=True,
    )

    # Patch the sub-exporter classes to track calls
    with (
        patch.object(HTMLStaticExporter, "export_users_by_username") as mock_html,
        patch.object(MarkdownGitHubExporter, "export_users_by_username") as mock_md,
    ):
        exporter.export_users_by_username({"alice", "bob"})

        mock_html.assert_called_once_with({"alice", "bob"})
        mock_md.assert_called_once_with({"alice", "bob"})
