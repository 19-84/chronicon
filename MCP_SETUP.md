# Chronicon MCP Server Setup

The Chronicon MCP (Model Context Protocol) server is now configured for this repository!

## What's Available

The MCP server provides **8 tools** to interact with the archived Discourse forum:

### Tools
- `get_topics` - List topics with pagination
- `get_topic` - Get detailed information about a specific topic
- `get_topic_posts` - Get posts in a topic with pagination
- `get_post` - Get detailed information about a specific post
- `search_topics` - Full-text search through topics
- `search_posts` - Full-text search through posts
- `get_users` - List users with post counts
- `get_categories` - List all categories

### Resources
- `archive://stats` - Archive statistics
- `archive://categories` - All categories
- `archive://timeline` - Activity timeline

### Prompts
- `token-safety-guide` - How to use field selection and body truncation
- `search-query-guide` - How to construct effective search queries

## How to Use

The MCP server is configured in `opencode.json` and will automatically load when you start OpenCode in this repository.

**Important:** OpenCode must be started from within this directory to load the config:

```bash
cd /path/to/chronicon
opencode
```

Then check that the MCP server is loaded by running:
```
/mcp list
```

You should see `chronicon-archive` in the list.

**Note:** The config file is named `opencode.json` (without a leading dot). Do NOT name it `.opencode.json` as that won't be recognized by OpenCode.

### Example Prompts

```
Show me the latest topics in the archive. use chronicon-archive

Search for topics about themes. use chronicon-archive

Get user statistics from the archive. use chronicon-archive

Show me posts from topic 23552. use chronicon-archive
```

### Manual Testing

You can also test the MCP server directly:

```bash
# Test that it starts
export DATABASE_URL="sqlite:///./path/to/your/archive.db"
.venv/bin/python -m chronicon.cli mcp

# Or use the MCP test script we created earlier
export DATABASE_URL="sqlite:///./path/to/your/archive.db"
.venv/bin/python << 'EOF'
import sys
sys.path.insert(0, 'src')
import asyncio
from chronicon.mcp.server import call_tool

async def test():
    result = await call_tool("get_statistics", {})
    print(result)

asyncio.run(test())
EOF
```

## Configuration

To set up the MCP server for your own use:

1. Copy the example config:
   ```bash
   cp opencode.json.example opencode.json
   ```

2. Update the paths in `opencode.json`:
   - Change `/path/to/your/.venv/bin/python` to your actual venv Python path
   - Change `/absolute/path/to/your/archive.db` to your actual archive database path

The MCP server configuration in `opencode.json` looks like:

```json
{
  "mcp": {
    "chronicon-archive": {
      "type": "local",
      "command": [
        "/path/to/chronicon/.venv/bin/python",
        "-m",
        "chronicon.cli",
        "mcp"
      ],
      "environment": {
        "DATABASE_URL": "sqlite:////path/to/your/archive.db"
      },
      "enabled": true
    }
  }
}
```

**Note:** The `opencode.json` file is in `.gitignore` to avoid committing local paths. Use `opencode.json.example` as a reference.

**Important:** The file must be named `opencode.json` (without a leading dot) for OpenCode to recognize it.

To use a different database, update the `DATABASE_URL` environment variable.

## Demo Archive

A live demo archive from meta.discourse.org is available at:
- **Live site:** https://online-archives.github.io/chronicon-archive-example/
- **Source repo:** https://github.com/online-archives/chronicon-archive-example
