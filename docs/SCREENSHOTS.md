# Screenshot Documentation

This document describes the screenshots captured for the Chronicon project documentation.

## Screenshot Files

All screenshots are located in `docs/screenshots/` and are referenced in the main README.

### HTML Export Screenshots

1. **01-html-index.png** (270 KB, 1280x900)
   - Homepage/index page showing topic listing
   - Displays forum title, navigation, and topic cards
   - Shows overall layout and design

2. **02-html-topic.png** (332 KB, 1280x1000)
   - Individual topic page (Discourse Mermaid)
   - Shows post content with rich formatting
   - Demonstrates image embedding and layout

3. **03-html-topic-replies.png** (265 KB, 1280x1000)
   - Topic with multiple replies (Formatting toolbar - 184 posts)
   - Shows conversation threading
   - Demonstrates pagination and navigation

4. **04-html-search.png** (320 KB, 1280x800)
   - Search functionality page
   - Shows client-side search interface
   - Demonstrates offline search capabilities

5. **05-html-latest.png** (205 KB, 1280x900)
   - Latest topics listing page
   - Shows chronological topic organization
   - Demonstrates alternate view formats

6. **06-html-mobile.png** (94 KB, 375x667)
   - Mobile-responsive view of homepage
   - iPhone SE dimensions (375x667)
   - Shows responsive design adaptation

## Source Archive

Screenshots were captured from the demo archive of meta.discourse.org:
- **Live site:** https://online-archives.github.io/chronicon-archive-example/
- **Source repo:** https://github.com/online-archives/chronicon-archive-example

## Capture Method

Screenshots were captured using Playwright with headless Chromium:
- Script: `scripts/capture_screenshots.py`
- Browser: Chromium (Playwright build v1200)
- Format: PNG
- Total Size: ~1.5 MB

## Usage in Documentation

Screenshots are embedded in:
1. **Main README.md** - Features section with screenshot gallery

## Updating Screenshots

To regenerate screenshots:

```bash
# Ensure Playwright is installed
export TMPDIR=$HOME/tmp
export PLAYWRIGHT_BROWSERS_PATH=$HOME/.playwright
.venv/bin/python -m playwright install chromium

# Run screenshot script
.venv/bin/python scripts/capture_screenshots.py
```

## Design Considerations

### Desktop Screenshots (1280x900/1000)
- Standard desktop resolution
- Shows full interface without scrolling
- Captures typical user experience

### Mobile Screenshot (375x667)
- iPhone SE / standard small phone size
- Demonstrates responsive design
- Shows mobile navigation patterns

### Content Selection
- **Index pages:** Show overall organization and navigation
- **Topic pages:** Display content formatting and images
- **Search page:** Demonstrate key functionality
- **Mobile view:** Prove responsive design works

## File Naming Convention

Screenshots use zero-padded numbering for consistent ordering:
- Format: `##-description.png`
- Example: `01-html-index.png`

This ensures:
1. Alphabetical sorting matches intended display order
2. Easy reference in documentation
3. Clear description of content

## Technical Details

### Image Properties
- Format: PNG (non-interlaced)
- Color: 8-bit RGB
- Compression: Optimized for web display
- No alpha channel (opaque backgrounds)

### Viewport Sizes
- Desktop: 1280x900 (index, latest, search)
- Desktop tall: 1280x1000 (topic pages with more content)
- Mobile: 375x667 (iPhone SE size)

### Browser Configuration
- Headless: Yes
- JavaScript: Enabled
- CSS: Enabled
- Images: Enabled
- Wait time: 1 second per page for rendering

## Screenshot Content

### What's Visible

Each screenshot captures:
- **Navigation:** Header, menus, breadcrumbs
- **Content:** Topics, posts, metadata
- **Styling:** Colors, fonts, spacing
- **Layout:** Responsive grid, columns
- **Interactive elements:** Buttons, search, pagination

### What's NOT Captured

- Hover states
- Animations
- Video content
- Dynamic JavaScript interactions
- Print styles

## Future Screenshot Ideas

Consider adding:
1. **Markdown export** - File listing in code editor
2. **GitHub render** - Markdown as displayed on GitHub
3. **Search in action** - With results visible
4. **Category pages** - Category-specific views
5. **User profiles** - If `--include-users` is used
6. **Dark mode** - If theme supports it
7. **Comparison view** - Side-by-side export formats

## License

Screenshots contain content from meta.discourse.org which is publicly available. The screenshots are provided as documentation examples for the Chronicon project.
