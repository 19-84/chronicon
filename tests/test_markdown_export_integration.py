# ABOUTME: Integration tests for GitHub-flavored markdown exporter
# ABOUTME: Tests end-to-end markdown export with multiple topics and categories
from datetime import datetime

import pytest

from chronicon.exporters.markdown import MarkdownGitHubExporter
from chronicon.models.category import Category
from chronicon.models.post import Post
from chronicon.models.topic import Topic
from chronicon.models.user import User
from chronicon.storage.database import ArchiveDatabase


@pytest.fixture
def comprehensive_db(tmp_path):
    """Create a database with multiple topics and categories."""
    db_path = tmp_path / "test.db"
    db = ArchiveDatabase(db_path)

    # Create multiple categories
    categories = [
        Category(
            id=1,
            name="General Discussion",
            slug="general",
            color="FF0000",
            text_color="FFFFFF",
            description="General discussion topics",
            parent_category_id=None,
            topic_count=2,
        ),
        Category(
            id=2,
            name="Technical Support",
            slug="support",
            color="0000FF",
            text_color="FFFFFF",
            description="Get help with technical issues",
            parent_category_id=None,
            topic_count=1,
        ),
    ]
    for category in categories:
        db.insert_category(category)

    # Create multiple users
    users = [
        User(
            id=1,
            username="alice",
            name="Alice Smith",
            avatar_template="/avatars/{size}/1.png",
            trust_level=2,
            created_at=datetime(2024, 1, 1, 10, 0, 0),
        ),
        User(
            id=2,
            username="bob",
            name="Bob Jones",
            avatar_template="/avatars/{size}/2.png",
            trust_level=1,
            created_at=datetime(2024, 1, 2, 10, 0, 0),
        ),
    ]
    for user in users:
        db.insert_user(user)

    # Create multiple topics across different categories
    topics = [
        Topic(
            id=1,
            title="Welcome to the Forum",
            slug="welcome",
            category_id=1,
            user_id=1,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 2, 12, 0, 0),
            posts_count=3,
            views=100,
        ),
        Topic(
            id=2,
            title="How to Install Software",
            slug="install-software",
            category_id=2,
            user_id=2,
            created_at=datetime(2024, 2, 15, 14, 0, 0),
            updated_at=datetime(2024, 2, 15, 14, 0, 0),
            posts_count=2,
            views=50,
        ),
        Topic(
            id=3,
            title="Feature Requests",
            slug="feature-requests",
            category_id=1,
            user_id=1,
            created_at=datetime(2024, 3, 10, 16, 0, 0),
            updated_at=datetime(2024, 3, 10, 16, 0, 0),
            posts_count=1,
            views=25,
        ),
    ]
    for topic in topics:
        db.insert_topic(topic)

    # Create posts for each topic
    posts = [
        # Topic 1 posts
        Post(
            id=1,
            topic_id=1,
            user_id=1,
            post_number=1,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 0, 0),
            cooked="<p>Welcome to our <strong>community forum</strong>!</p>",
            raw="Welcome to our **community forum**!",
            username="alice",
        ),
        Post(
            id=2,
            topic_id=1,
            user_id=2,
            post_number=2,
            created_at=datetime(2024, 1, 2, 10, 0, 0),
            updated_at=datetime(2024, 1, 2, 10, 0, 0),
            cooked="<p>Thanks for the <em>warm welcome</em>!</p>",
            raw="Thanks for the *warm welcome*!",
            username="bob",
        ),
        Post(
            id=3,
            topic_id=1,
            user_id=1,
            post_number=3,
            created_at=datetime(2024, 1, 2, 12, 0, 0),
            updated_at=datetime(2024, 1, 2, 12, 0, 0),
            cooked="<p>Feel free to ask questions!</p>",
            raw="Feel free to ask questions!",
            username="alice",
        ),
        # Topic 2 posts
        Post(
            id=4,
            topic_id=2,
            user_id=2,
            post_number=1,
            created_at=datetime(2024, 2, 15, 14, 0, 0),
            updated_at=datetime(2024, 2, 15, 14, 0, 0),
            cooked="<p>Run <code>install.sh</code> to install.</p>",
            raw="Run `install.sh` to install.",
            username="bob",
        ),
        Post(
            id=5,
            topic_id=2,
            user_id=1,
            post_number=2,
            created_at=datetime(2024, 2, 15, 14, 30, 0),
            updated_at=datetime(2024, 2, 15, 14, 30, 0),
            cooked="<p>Thanks, it worked!</p>",
            raw="Thanks, it worked!",
            username="alice",
        ),
        # Topic 3 posts
        Post(
            id=6,
            topic_id=3,
            user_id=1,
            post_number=1,
            created_at=datetime(2024, 3, 10, 16, 0, 0),
            updated_at=datetime(2024, 3, 10, 16, 0, 0),
            cooked=(
                "<p>I'd like to request a "
                "<a href='https://example.com'>new feature</a>.</p>"
            ),
            raw="I'd like to request a [new feature](https://example.com).",
            username="alice",
        ),
    ]
    for post in posts:
        db.insert_post(post)

    return db


def test_github_markdown_export_multiple_topics(tmp_path, comprehensive_db):
    """Test GitHub markdown export with multiple topics and categories."""
    output_dir = tmp_path / "github_output"
    exporter = MarkdownGitHubExporter(comprehensive_db, output_dir)
    exporter.export()

    # Verify all topics were exported
    topics_dir = output_dir / "t"
    assert topics_dir.exists()

    # Check topics exist using Discourse-style URLs: /t/{slug}/{id}.md
    assert (topics_dir / "welcome" / "1.md").exists()
    assert (topics_dir / "install-software" / "2.md").exists()
    assert (topics_dir / "feature-requests" / "3.md").exists()

    # Verify README exists
    readme_path = output_dir / "README.md"
    assert readme_path.exists()

    readme_content = readme_path.read_text()

    # Check README is a landing page (not a content listing)
    assert "Getting Started" in readme_content
    assert "Browse the Archive" in readme_content
    assert "About This Archive" in readme_content
    assert "How to Browse" in readme_content

    # README should NOT contain topic listings (those are in index.md)
    assert "Welcome to the Forum" not in readme_content

    # Check README has navigation links
    assert "Latest Topics" in readme_content
    assert "Top Topics" in readme_content


def test_markdown_conversion_preserves_formatting(tmp_path, comprehensive_db):
    """Test that HTML to markdown conversion preserves formatting."""
    output_dir = tmp_path / "github_output"
    exporter = MarkdownGitHubExporter(comprehensive_db, output_dir)
    exporter.export()

    # Read a topic with formatting using Discourse-style path
    topic_content = (output_dir / "t" / "welcome" / "1.md").read_text()

    # Should have bold text
    assert "community forum" in topic_content or "**community forum**" in topic_content

    # Should have italic text from second post
    assert "warm welcome" in topic_content

    # Read topic with code
    support_topic = (output_dir / "t" / "install-software" / "2.md").read_text()

    # Should have code formatting
    assert "install.sh" in support_topic


def test_github_markdown_readme_organization(tmp_path, comprehensive_db):
    """Test that README is a landing page, not a content listing."""
    output_dir = tmp_path / "github_output"
    exporter = MarkdownGitHubExporter(comprehensive_db, output_dir)
    exporter.export()

    readme_content = (output_dir / "README.md").read_text()

    # README should be a landing page, not a content listing
    assert "Getting Started" in readme_content
    assert "About This Archive" in readme_content
    assert "How to Browse" in readme_content
    assert "About Chronicon" in readme_content

    # Should have navigation links but NOT topic/category listings
    assert "Latest Topics" in readme_content
    assert "Top Topics" in readme_content

    # Should NOT have category sections (those are in index.md)
    assert "### Category: General Discussion" not in readme_content
    assert "### Category: Technical Support" not in readme_content

    # Should NOT have topic titles (those are in index.md)
    assert "Welcome to the Forum" not in readme_content
    assert "How to Install Software" not in readme_content


def test_empty_database_export(tmp_path):
    """Test that exporters handle empty databases gracefully."""
    db_path = tmp_path / "empty.db"
    db = ArchiveDatabase(db_path)

    # Test markdown export with empty database
    md_dir = tmp_path / "md"
    md_exporter = MarkdownGitHubExporter(db, md_dir)
    md_exporter.export()

    # Should create directory structure
    assert md_dir.exists()
    # No topics means no t directory or empty t directory
    assert not (md_dir / "t").exists() or len(list((md_dir / "t").iterdir())) == 0

    # Should create README even with no topics
    assert (md_dir / "README.md").exists()
    readme = (md_dir / "README.md").read_text()
    # Check the new format uses "Content:" instead of "**Topics:**"
    assert "0 topics, 0 posts" in readme
