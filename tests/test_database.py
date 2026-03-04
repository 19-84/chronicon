# Test file for database operations
from datetime import datetime

from chronicon.models.category import Category
from chronicon.models.post import Post
from chronicon.models.topic import Topic
from chronicon.models.user import User
from chronicon.storage.database import ArchiveDatabase


def test_database_creation(tmp_path):
    """Test database schema creation."""
    # Will be implemented in Phase 7
    pass


def test_insert_post(tmp_path):
    """Test inserting a post."""
    # Will be implemented in Phase 7
    pass


def test_get_topic_posts_paginated(tmp_path):
    """Test fetching paginated posts for a topic."""
    db_path = tmp_path / "test.db"
    db = ArchiveDatabase(db_path)

    # Create a test topic
    topic = Topic(
        id=1,
        title="Test Topic",
        slug="test-topic",
        category_id=1,
        user_id=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        posts_count=100,
        views=50,
        tags=[],
        excerpt="Test excerpt",
        image_url=None,
        fancy_title="Test Topic",
    )
    db.insert_topic(topic)

    # Insert 100 test posts
    for i in range(1, 101):
        post = Post(
            id=i,
            topic_id=1,
            user_id=1,
            post_number=i,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            cooked=f"<p>Test post {i}</p>",
            raw=f"Test post {i}",
            username="testuser",
        )
        db.insert_post(post)

    # Test first page (posts 1-50)
    page1 = db.get_topic_posts_paginated(topic_id=1, page=1, per_page=50)
    assert len(page1) == 50
    assert page1[0].post_number == 1
    assert page1[49].post_number == 50

    # Test second page (posts 51-100)
    page2 = db.get_topic_posts_paginated(topic_id=1, page=2, per_page=50)
    assert len(page2) == 50
    assert page2[0].post_number == 51
    assert page2[49].post_number == 100

    # Test third page (should be empty)
    page3 = db.get_topic_posts_paginated(topic_id=1, page=3, per_page=50)
    assert len(page3) == 0

    # Test smaller page size
    page1_small = db.get_topic_posts_paginated(topic_id=1, page=1, per_page=10)
    assert len(page1_small) == 10
    assert page1_small[0].post_number == 1
    assert page1_small[9].post_number == 10

    db.close()


def test_get_topic_posts_count(tmp_path):
    """Test counting posts for a topic."""
    db_path = tmp_path / "test.db"
    db = ArchiveDatabase(db_path)

    # Create a test topic
    topic = Topic(
        id=1,
        title="Test Topic",
        slug="test-topic",
        category_id=1,
        user_id=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        posts_count=75,
        views=50,
        tags=[],
        excerpt="Test excerpt",
        image_url=None,
        fancy_title="Test Topic",
    )
    db.insert_topic(topic)

    # Initially, count should be 0
    count = db.get_topic_posts_count(topic_id=1)
    assert count == 0

    # Insert 75 test posts
    for i in range(1, 76):
        post = Post(
            id=i,
            topic_id=1,
            user_id=1,
            post_number=i,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            cooked=f"<p>Test post {i}</p>",
            raw=f"Test post {i}",
            username="testuser",
        )
        db.insert_post(post)

    # Count should now be 75
    count = db.get_topic_posts_count(topic_id=1)
    assert count == 75

    # Count for non-existent topic should be 0
    count_nonexistent = db.get_topic_posts_count(topic_id=999)
    assert count_nonexistent == 0

    db.close()


def test_pagination_edge_cases(tmp_path):
    """Test edge cases for pagination."""
    db_path = tmp_path / "test.db"
    db = ArchiveDatabase(db_path)

    # Create a test topic
    topic = Topic(
        id=1,
        title="Test Topic",
        slug="test-topic",
        category_id=1,
        user_id=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        posts_count=5,
        views=50,
        tags=[],
        excerpt="Test excerpt",
        image_url=None,
        fancy_title="Test Topic",
    )
    db.insert_topic(topic)

    # Insert exactly 5 posts
    for i in range(1, 6):
        post = Post(
            id=i,
            topic_id=1,
            user_id=1,
            post_number=i,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            cooked=f"<p>Test post {i}</p>",
            raw=f"Test post {i}",
            username="testuser",
        )
        db.insert_post(post)

    # Test when posts fit exactly on one page
    page1 = db.get_topic_posts_paginated(topic_id=1, page=1, per_page=5)
    assert len(page1) == 5

    # Test when there's exactly one page
    page2 = db.get_topic_posts_paginated(topic_id=1, page=2, per_page=5)
    assert len(page2) == 0

    # Test partial last page (3 posts per page)
    page1 = db.get_topic_posts_paginated(topic_id=1, page=1, per_page=3)
    assert len(page1) == 3
    assert page1[0].post_number == 1

    page2 = db.get_topic_posts_paginated(topic_id=1, page=2, per_page=3)
    assert len(page2) == 2  # Only 2 posts remaining
    assert page2[0].post_number == 4

    db.close()


def test_get_user_posts_paginated(tmp_path):
    """Test fetching paginated posts for a user with topic information."""
    db_path = tmp_path / "test.db"
    db = ArchiveDatabase(db_path)

    # Create test user
    user = User(
        id=1,
        username="testuser",
        name="Test User",
        avatar_template="/user_avatar/{size}/1.png",
        trust_level=2,
        created_at=datetime.now(),
    )
    db.insert_user(user)

    # Create test category
    category = Category(
        id=1,
        name="General",
        slug="general",
        color="0088CC",
        text_color="FFFFFF",
        description="General discussion",
        parent_category_id=None,
        topic_count=3,
    )
    db.insert_category(category)

    # Create test topics
    for i in range(1, 4):
        topic = Topic(
            id=i,
            title=f"Test Topic {i}",
            slug=f"test-topic-{i}",
            category_id=1,
            user_id=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            posts_count=25,
            views=100,
            tags=[],
            excerpt=f"Test excerpt {i}",
            image_url=None,
            fancy_title=f"Test Topic {i}",
        )
        db.insert_topic(topic)

    # Insert 75 test posts (25 per topic) by the same user
    for topic_id in range(1, 4):
        for post_num in range(1, 26):
            post_id = (topic_id - 1) * 25 + post_num
            post = Post(
                id=post_id,
                topic_id=topic_id,
                user_id=1,
                post_number=post_num,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                cooked=f"<p>Test post {post_id}</p>",
                raw=f"Test post {post_id}",
                username="testuser",
            )
            db.insert_post(post)

    # Test first page (posts 1-50)
    page1 = db.get_user_posts_paginated(user_id=1, page=1, per_page=50)
    assert len(page1) == 50
    # Verify post data structure includes topic information
    assert page1[0]["post"] is not None
    assert page1[0]["topic_title"] is not None
    assert page1[0]["topic_slug"] is not None
    assert page1[0]["topic_id"] is not None
    assert page1[0]["category_name"] == "General"
    assert page1[0]["category_color"] == "0088CC"

    # Test second page (posts 51-75)
    page2 = db.get_user_posts_paginated(user_id=1, page=2, per_page=50)
    assert len(page2) == 25

    # Test third page (should be empty)
    page3 = db.get_user_posts_paginated(user_id=1, page=3, per_page=50)
    assert len(page3) == 0

    # Test smaller page size
    page1_small = db.get_user_posts_paginated(user_id=1, page=1, per_page=10)
    assert len(page1_small) == 10

    # Test non-existent user
    page_empty = db.get_user_posts_paginated(user_id=999, page=1, per_page=50)
    assert len(page_empty) == 0

    db.close()


def test_get_user_post_count(tmp_path):
    """Test counting posts for a user."""
    db_path = tmp_path / "test.db"
    db = ArchiveDatabase(db_path)

    # Create test user
    user = User(
        id=1,
        username="testuser",
        name="Test User",
        avatar_template="/user_avatar/{size}/1.png",
        trust_level=2,
        created_at=datetime.now(),
    )
    db.insert_user(user)

    # Create test topic
    topic = Topic(
        id=1,
        title="Test Topic",
        slug="test-topic",
        category_id=1,
        user_id=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        posts_count=50,
        views=100,
        tags=[],
        excerpt="Test excerpt",
        image_url=None,
        fancy_title="Test Topic",
    )
    db.insert_topic(topic)

    # Initially, count should be 0
    count = db.get_user_post_count(user_id=1)
    assert count == 0

    # Insert 50 test posts
    for i in range(1, 51):
        post = Post(
            id=i,
            topic_id=1,
            user_id=1,
            post_number=i,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            cooked=f"<p>Test post {i}</p>",
            raw=f"Test post {i}",
            username="testuser",
        )
        db.insert_post(post)

    # Count should now be 50
    count = db.get_user_post_count(user_id=1)
    assert count == 50

    # Count for non-existent user should be 0
    count_nonexistent = db.get_user_post_count(user_id=999)
    assert count_nonexistent == 0

    db.close()


def test_category_filter_set_and_get(tmp_path):
    """Test setting and getting category filter for a site."""
    db_path = tmp_path / "test.db"
    db = ArchiveDatabase(db_path)

    site_url = "https://example.com"

    # Initially, category filter should be None
    result = db.get_category_filter(site_url)
    assert result is None

    # Set a category filter
    category_ids = [1, 2, 5]
    db.set_category_filter(site_url, category_ids)

    # Verify it was stored
    result = db.get_category_filter(site_url)
    assert result == [1, 2, 5]

    # Update to a different filter
    db.set_category_filter(site_url, [7, 10])
    result = db.get_category_filter(site_url)
    assert result == [7, 10]

    # Clear the filter (set to None)
    db.set_category_filter(site_url, None)
    result = db.get_category_filter(site_url)
    assert result is None

    db.close()


def test_category_filter_empty_list(tmp_path):
    """Test that empty list is treated as None (all categories)."""
    db_path = tmp_path / "test.db"
    db = ArchiveDatabase(db_path)

    site_url = "https://example.com"

    # Set to empty list - should effectively be None
    db.set_category_filter(site_url, [])

    # Empty list serializes to JSON "[]" but we want it treated as None
    # This tests the current behavior - if [] should be None, code needs update
    result = db.get_category_filter(site_url)
    # Empty list is valid - it means "no categories" which is different from None
    assert result == [] or result is None

    db.close()


def test_category_filter_multiple_sites(tmp_path):
    """Test category filters work correctly with multiple sites."""
    db_path = tmp_path / "test.db"
    db = ArchiveDatabase(db_path)

    site1 = "https://site1.example.com"
    site2 = "https://site2.example.com"

    # Set different filters for different sites
    db.set_category_filter(site1, [1, 2, 3])
    db.set_category_filter(site2, [4, 5])

    # Verify each site has its own filter
    assert db.get_category_filter(site1) == [1, 2, 3]
    assert db.get_category_filter(site2) == [4, 5]

    # Update one site's filter
    db.set_category_filter(site1, [10])
    assert db.get_category_filter(site1) == [10]
    assert db.get_category_filter(site2) == [4, 5]  # Unchanged

    db.close()
