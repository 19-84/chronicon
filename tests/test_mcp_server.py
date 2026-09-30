# ABOUTME: Tests for MCP server functionality
# ABOUTME: Tests tools, resources, and prompts

from datetime import datetime

import pytest

# Skip all tests if mcp or pytest-asyncio is not installed
pytest.importorskip("mcp")
pytest.importorskip("pytest_asyncio")

from chronicon.models.category import Category
from chronicon.models.post import Post
from chronicon.models.topic import Topic
from chronicon.models.user import User


@pytest.fixture
def test_db(tmp_path):
    """Create a test database with sample data."""
    from chronicon.storage.database import ArchiveDatabase

    db_path = tmp_path / "test.db"
    db = ArchiveDatabase(db_path)

    # Insert test data
    category = Category(
        id=1,
        name="General",
        slug="general",
        color="0088CC",
        text_color="FFFFFF",
        description="General discussion",
        parent_category_id=None,
        topic_count=1,
    )
    db.insert_category(category)

    user = User(
        id=1,
        username="alice",
        name="Alice Smith",
        trust_level=3,
        avatar_template="/avatar/{size}/1.png",
        created_at=datetime(2024, 1, 1),
    )
    db.insert_user(user)

    topic = Topic(
        id=1,
        title="Python Programming",
        slug="python-programming",
        posts_count=2,
        views=100,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 2),
        last_posted_at=datetime(2024, 1, 2),
        user_id=1,
        category_id=1,
        closed=False,
        archived=False,
        pinned=False,
        visible=True,
        excerpt="Learn Python basics",
    )
    db.insert_topic(topic)

    post1 = Post(
        id=1,
        topic_id=1,
        post_number=1,
        user_id=1,
        username="alice",
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
        raw="This is a post about Python programming",
        cooked="<p>This is a post about Python programming</p>",
    )
    post2 = Post(
        id=2,
        topic_id=1,
        post_number=2,
        user_id=1,
        username="alice",
        created_at=datetime(2024, 1, 2),
        updated_at=datetime(2024, 1, 2),
        raw="More details about Python",
        cooked="<p>More details about Python</p>",
    )
    db.insert_post(post1)
    db.insert_post(post2)

    return db_path


@pytest.fixture(autouse=True)
def set_database_url(test_db, monkeypatch):
    """Set DATABASE_URL for all MCP tests."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{test_db}")


@pytest.mark.asyncio
async def test_list_tools():
    """Test that MCP server lists all tools."""
    from chronicon.mcp.server import list_tools

    tools = await list_tools()

    assert len(tools) > 0

    # Check for expected tools
    tool_names = [tool.name for tool in tools]
    assert "get_topics" in tool_names
    assert "get_topic" in tool_names
    assert "search_topics" in tool_names
    assert "search_posts" in tool_names
    assert "get_users" in tool_names
    assert "get_categories" in tool_names
    assert "get_statistics" in tool_names


@pytest.mark.asyncio
async def test_call_get_topics():
    """Test calling get_topics tool."""
    from mcp.types import TextContent

    from chronicon.mcp.server import call_tool

    result = await call_tool("get_topics", {"page": 1, "per_page": 20})

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "Python Programming" in result[0].text
    assert "page 1" in result[0].text


@pytest.mark.asyncio
async def test_call_get_topic():
    """Test calling get_topic tool."""
    from mcp.types import TextContent

    from chronicon.mcp.server import call_tool

    result = await call_tool("get_topic", {"topic_id": 1})

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "Python Programming" in result[0].text
    assert "Posts:" in result[0].text


@pytest.mark.asyncio
async def test_call_get_topic_not_found():
    """Test calling get_topic with non-existent ID."""
    from mcp.types import TextContent

    from chronicon.mcp.server import call_tool

    result = await call_tool("get_topic", {"topic_id": 999})

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "not found" in result[0].text.lower()


@pytest.mark.asyncio
async def test_call_search_topics():
    """Test calling search_topics tool."""
    from mcp.types import TextContent

    from chronicon.mcp.server import call_tool

    result = await call_tool("search_topics", {"query": "python", "page": 1})

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "python" in result[0].text.lower()


@pytest.mark.asyncio
async def test_call_get_users():
    """Test calling get_users tool."""
    from mcp.types import TextContent

    from chronicon.mcp.server import call_tool

    result = await call_tool("get_users", {"page": 1, "per_page": 20})

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "alice" in result[0].text


@pytest.mark.asyncio
async def test_call_get_categories():
    """Test calling get_categories tool."""
    from mcp.types import TextContent

    from chronicon.mcp.server import call_tool

    result = await call_tool("get_categories", {})

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "General" in result[0].text


@pytest.mark.asyncio
async def test_call_get_statistics():
    """Test calling get_statistics tool."""
    from mcp.types import TextContent

    from chronicon.mcp.server import call_tool

    result = await call_tool("get_statistics", {})

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "Total Topics:" in result[0].text
    assert "Total Posts:" in result[0].text


@pytest.mark.asyncio
async def test_call_unknown_tool():
    """Test calling a non-existent tool."""
    from chronicon.mcp.server import call_tool

    with pytest.raises(ValueError) as exc_info:
        await call_tool("nonexistent_tool", {})

    assert "Unknown tool" in str(exc_info.value)


@pytest.mark.asyncio
async def test_list_resources():
    """Test that MCP server lists all resources."""
    from chronicon.mcp.server import list_resources

    resources = await list_resources()

    assert len(resources) > 0

    # Check for expected resources
    resource_uris = [str(r.uri) for r in resources]
    assert "archive://stats" in resource_uris
    assert "archive://categories" in resource_uris
    assert "archive://timeline" in resource_uris


@pytest.mark.asyncio
async def test_read_resource_stats():
    """Test reading archive://stats resource."""
    from chronicon.mcp.server import read_resource

    result = await read_resource("archive://stats")

    assert isinstance(result, str)
    assert "Total Topics:" in result
    assert "Total Posts:" in result


@pytest.mark.asyncio
async def test_read_resource_categories():
    """Test reading archive://categories resource."""
    from chronicon.mcp.server import read_resource

    result = await read_resource("archive://categories")

    assert isinstance(result, str)
    assert "General" in result
    assert "topics" in result


@pytest.mark.asyncio
async def test_read_resource_timeline():
    """Test reading archive://timeline resource."""
    from chronicon.mcp.server import read_resource

    result = await read_resource("archive://timeline")

    assert isinstance(result, str)
    assert "Activity Timeline" in result


@pytest.mark.asyncio
async def test_read_unknown_resource():
    """Test reading a non-existent resource."""
    from chronicon.mcp.server import read_resource

    with pytest.raises(ValueError) as exc_info:
        await read_resource("archive://nonexistent")

    assert "Unknown resource URI" in str(exc_info.value)


@pytest.mark.asyncio
async def test_list_prompts():
    """Test that MCP server lists all prompts."""
    from chronicon.mcp.server import list_prompts

    prompts = await list_prompts()

    assert len(prompts) > 0

    # Check for expected prompts
    prompt_names = [p.name for p in prompts]
    assert "token-safety-guide" in prompt_names
    assert "search-query-guide" in prompt_names


@pytest.mark.asyncio
async def test_get_prompt_token_safety():
    """Test getting token-safety-guide prompt."""
    from chronicon.mcp.server import get_prompt

    result = await get_prompt("token-safety-guide", None)

    assert isinstance(result, str)
    assert "Token Safety Guide" in result
    assert "?fields=" in result
    assert "?max_body_length=" in result


@pytest.mark.asyncio
async def test_get_prompt_search_query():
    """Test getting search-query-guide prompt."""
    from chronicon.mcp.server import get_prompt

    result = await get_prompt("search-query-guide", None)

    assert isinstance(result, str)
    assert "Search Query Guide" in result
    assert "FTS5" in result or "tsvector" in result


@pytest.mark.asyncio
async def test_get_unknown_prompt():
    """Test getting a non-existent prompt."""
    from chronicon.mcp.server import get_prompt

    with pytest.raises(ValueError) as exc_info:
        await get_prompt("nonexistent_prompt", None)

    assert "Unknown prompt" in str(exc_info.value)


@pytest.mark.asyncio
async def test_tool_pagination():
    """Test that tools support pagination."""
    from mcp.types import TextContent

    from chronicon.mcp.server import call_tool

    # Get first page
    result1 = await call_tool("get_topics", {"page": 1, "per_page": 1})
    assert isinstance(result1, list)
    assert isinstance(result1[0], TextContent)
    assert "page 1" in result1[0].text

    # Get second page (even if empty)
    result2 = await call_tool("get_topics", {"page": 2, "per_page": 1})
    assert isinstance(result2, list)
    assert isinstance(result2[0], TextContent)
    assert "page 2" in result2[0].text


def test_mcp_server_requires_database_url(monkeypatch):
    """Test that MCP server raises error without DATABASE_URL."""
    # Remove DATABASE_URL
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Clear the global database instance
    import chronicon.mcp.server as mcp_server_module

    mcp_server_module._db_instance = None

    from chronicon.mcp.server import get_db

    with pytest.raises(ValueError) as exc_info:
        get_db()

    assert "DATABASE_URL" in str(exc_info.value)


@pytest.mark.asyncio
async def test_call_get_topic_posts():
    """Test calling get_topic_posts tool."""
    from mcp.types import TextContent

    from chronicon.mcp.server import call_tool

    result = await call_tool(
        "get_topic_posts", {"topic_id": 1, "page": 1, "per_page": 20}
    )

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "alice" in result[0].text
    assert "python" in result[0].text.lower()


@pytest.mark.asyncio
async def test_search_when_unavailable(tmp_path, monkeypatch):
    """Test search tools when search is not available."""
    from mcp.types import TextContent

    from chronicon.storage.database import ArchiveDatabase

    # Create a database - search will actually be available in SQLite
    db_path = tmp_path / "nosearch.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    # Create empty database (side effect: initializes schema)
    ArchiveDatabase(db_path)

    from chronicon.mcp.server import call_tool

    result = await call_tool("search_topics", {"query": "test"})

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    # Search IS available in SQLite, so we'll get an empty result set
    assert "search results" in result[0].text.lower()


# Protocol-level tests: drive the server through a real MCP client session so
# request/result types are validated the way an MCP client would see them.


@pytest.fixture
def mcp_server(monkeypatch):
    """The MCP server with a fresh database connection for this test's archive.

    Tests open the client in the test body: an async generator fixture would
    exit the client's cancel scope in a different task than it entered it.
    """
    import chronicon.mcp.server as mcp_server_module

    monkeypatch.setattr(mcp_server_module, "_db_instance", None)
    return mcp_server_module.mcp_server


@pytest.mark.asyncio
async def test_protocol_list_and_call_tool(mcp_server):
    """Tools are listed and callable over the MCP protocol."""
    from mcp import Client
    from mcp.types import TextContent

    async with Client(mcp_server) as client:
        tools = await client.list_tools()
        assert "get_statistics" in [tool.name for tool in tools.tools]

        result = await client.call_tool("get_topics", {"page": 1, "per_page": 20})

    assert not result.is_error
    assert isinstance(result.content[0], TextContent)
    assert "Python Programming" in result.content[0].text


@pytest.mark.asyncio
async def test_protocol_call_tool_missing_argument(mcp_server):
    """A missing required argument comes back as a tool error, not a crash."""
    from mcp import Client
    from mcp.types import TextContent

    async with Client(mcp_server) as client:
        result = await client.call_tool("get_topic", {})

    assert result.is_error
    assert isinstance(result.content[0], TextContent)
    assert "topic_id" in result.content[0].text


@pytest.mark.asyncio
async def test_protocol_read_resource(mcp_server):
    """Every listed resource can be read back by URI."""
    from mcp import Client
    from mcp.types import TextResourceContents

    async with Client(mcp_server) as client:
        resources = await client.list_resources()
        uris = [str(r.uri) for r in resources.resources]
        assert uris == ["archive://stats", "archive://categories", "archive://timeline"]

        results = {uri: await client.read_resource(uri) for uri in uris}

    for uri, result in results.items():
        contents = result.contents[0]
        assert isinstance(contents, TextResourceContents)
        assert str(contents.uri) == uri
        assert contents.text

    stats = results["archive://stats"].contents[0]
    assert isinstance(stats, TextResourceContents)
    assert "Total Topics:" in stats.text


@pytest.mark.asyncio
async def test_protocol_get_prompt(mcp_server):
    """Every listed prompt can be fetched as prompt messages."""
    from mcp import Client
    from mcp.types import TextContent

    async with Client(mcp_server) as client:
        prompts = await client.list_prompts()
        names = [p.name for p in prompts.prompts]
        assert names == ["token-safety-guide", "search-query-guide"]

        results = {name: await client.get_prompt(name) for name in names}

    for result in results.values():
        content = result.messages[0].content
        assert isinstance(content, TextContent)
        assert content.text

    guide = results["token-safety-guide"].messages[0].content
    assert isinstance(guide, TextContent)
    assert "Token Safety Guide" in guide.text


@pytest.mark.asyncio
async def test_protocol_unknown_names_are_errors(mcp_server):
    """Unknown resources and prompts surface as MCP errors to the client."""
    from mcp import Client
    from mcp.shared.exceptions import MCPError

    async with Client(mcp_server) as client:
        with pytest.raises(MCPError):
            await client.read_resource("archive://nonexistent")
        with pytest.raises(MCPError):
            await client.get_prompt("nonexistent_prompt")
