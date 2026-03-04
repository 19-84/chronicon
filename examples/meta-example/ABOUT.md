# Example Archive - meta.discourse.org Theme Category

This is a demonstration archive showcasing Chronicon's **hybrid export format** - a unified output with both HTML and Markdown.

## Archive Contents

- **Source**: meta.discourse.org, Category: Theme (ID 61)
- **Topics**: 65 topics about Discourse themes
- **Posts**: 2,505 posts
- **Users**: 594 user profiles (1 unavailable from API)
- **Categories**: 1 (Theme only)
- **Date Range**: 2014-12-31 to 2025-11-08
- **Export Format**: Hybrid (HTML + Markdown with shared assets)

## Hybrid Format Architecture

The hybrid format creates a unified archive suitable for:
- **GitHub Pages deployment** (HTML at root)
- **GitHub/Forgejo markdown browsing** (`/md/` directory)
- **Offline viewing** (both formats work without internet)

### Directory Structure

```
examples/meta-example/
├── index.html              # HTML homepage (recommended)
├── search.html             # Full-text search interface
├── search_index.json       # Search index data
├── _config.yml             # GitHub Pages configuration
├── README.md               # Root landing page with stats
├── archive.db              # SQLite database (4.6 MB)
│
├── t/                      # HTML topic pages (65 themes)
│   └── {slug}/{id}.html
├── c/                      # HTML category index
│   └── theme/61/
├── users/                  # HTML user profiles (594 users)
│   └── {username}.html
├── latest/                 # Latest topics index
├── top/                    # Top topics indexes (by replies/views)
│
├── assets/                 # Shared assets (CSS, JS)
│   ├── css/                # Stylesheets
│   └── js/                 # JavaScript (search)
│
└── md/                     # Markdown export subdirectory
    ├── README.md           # Markdown landing page
    ├── index.md            # Markdown browsing interface
    ├── t/                  # Markdown topic files (65 themes)
    │   └── {slug}/{id}.md
    ├── c/                  # Category index
    │   └── theme/
    ├── users/              # Markdown user profiles
    ├── latest/             # Latest topics
    └── top/                # Top topics
```

## Bug Fixed: URL Encoding for Usernames

This archive demonstrates a bug fix in Chronicon v1.0.1 where usernames with special characters (like `Alex_王`, `Cécile_Savoie`) were not being URL-encoded properly, causing API fetch failures.

**Fixed in:** `src/chronicon/fetchers/users.py` - Added `urllib.parse.quote()` to encode usernames before making API requests.

**Result:** 594 out of 595 users successfully fetched (99.8% success rate). The one missing user (codinghorror) appears to be unavailable from the API.

## How to Use

### Option 1: View HTML (Recommended)

**Open in browser:**
```bash
open examples/meta-example/index.html
# or
firefox examples/meta-example/index.html
```

**Features:**
- Full-featured web interface
- Client-side search
- Clean, responsive design
- Works entirely offline

### Option 2: Browse Markdown

**On GitHub/Forgejo:**
Navigate to `examples/meta-example/md/README.md` and click through topics.

**Locally:**
```bash
cd examples/meta-example/md
# Use any markdown viewer
cat README.md
```

### Option 3: Deploy to GitHub Pages

1. Push this directory to a GitHub repository
2. Enable GitHub Pages in repository settings
3. Set source to "root" or "main branch"
4. Access at `https://username.github.io/repo-name/`

## Note About Images

This example archive was created **without downloading images** to keep repository size small. Image links point to original meta.discourse.org URLs and require internet to view.

To create an archive with downloaded assets:
```bash
chronicon archive --urls https://meta.discourse.org \
  --categories 61 \
  --formats hybrid \
  --download-images \
  --output-dir my-archive
```

## Generated With

Chronicon v1.0.1 - https://github.com/19-84/chronicon

**Command used:**
```bash
chronicon archive \
  --urls https://meta.discourse.org \
  --categories 61 \
  --formats hybrid \
  --output-dir examples/meta-example \
  --include-users
```

## Theme Topics Included

All 65 topics are Discourse theme discussions including:
- Air Theme
- Alien Night Theme (dark theme)
- Atlas (blog-styled theme with sidebar)
- Battle Axe (Tappara.co hockey community theme)
- Blackout (OLED display theme)
- Canvas Theme Template
- Dracula (dark theme)
- FKB Pro Social Theme
- Graceful Theme
- Grogu (Mandalorian-inspired theme)
- Minima Theme
- Mint Theme
- Sam's Simple Theme
- And 52 more...

## Exploring the Archive

### HTML Path (Recommended)
1. Open `index.html` in browser
2. Use search bar to find specific themes
3. Browse by latest/top/category
4. Click any topic to view discussion
5. View user profiles from topic pages

### Markdown Path
1. Start with `md/README.md` for overview
2. Open `md/index.md` to browse topics
3. Click topic links to read discussions
4. Check `md/users/index.md` for contributors

All links work offline in both formats!
