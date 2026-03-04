# ABOUTME: HTML content processor for Chronicon
# ABOUTME: Parses and processes post HTML content for archiving

"""Process post HTML content."""

import urllib.parse
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    # BeautifulSoup4 is required but make it graceful for testing
    BeautifulSoup = None

from .emoji_mapper import get_unicode_emoji, has_unicode_emoji


class HTMLProcessor:
    """Process post HTML content."""

    def __init__(self, asset_downloader=None):
        """
        Initialize HTML processor.

        Args:
            asset_downloader: AssetDownloader instance for downloading embedded assets
        """
        self.asset_downloader = asset_downloader

    def process_post_html(self, html: str, topic_id: int, output_base: Path) -> str:
        """
        Process HTML content from a post.

        Args:
            html: HTML content to process
            topic_id: Topic ID for asset organization
            output_base: Base output directory

        Returns:
            Processed HTML with rewritten URLs
        """
        # Extract images
        images = self.extract_images(html)

        # Download images if asset downloader available
        url_map = {}
        if self.asset_downloader:
            for img_url in images:
                local_path = self.asset_downloader.download_image(img_url, topic_id)
                if local_path:
                    # Convert to relative path
                    relative_path = (
                        str(local_path.relative_to(output_base))
                        if output_base
                        else str(local_path)
                    )
                    url_map[img_url] = relative_path

        # Rewrite URLs
        return self.rewrite_urls(html, url_map)

    def extract_images(self, html: str) -> list[str]:
        """
        Extract image URLs from HTML content.

        Args:
            html: HTML content

        Returns:
            List of image URLs
        """
        if not html:
            return []

        if BeautifulSoup is None:
            raise ImportError(
                "BeautifulSoup4 is required. Install with: uv add beautifulsoup4"
            )

        images = []
        soup = BeautifulSoup(html, "html.parser")

        # Extract from img tags
        for img in soup.find_all("img"):
            src = img.get("src")
            if src:
                images.append(src)

        # Extract from picture/source tags with srcset
        for source in soup.find_all("source"):
            srcset = source.get("srcset")
            if srcset:
                # Parse srcset: "url1 width1, url2 width2, ..."
                for entry in srcset.split(","):
                    parts = entry.strip().split()
                    if parts:
                        images.append(parts[0])

        return images

    def parse_srcset(self, srcset: str) -> list[tuple]:
        """
        Parse srcset attribute into list of (url, width) tuples.

        Args:
            srcset: srcset attribute value like "img-800.jpg 800w, img-1200.jpg 1200w"

        Returns:
            List of (url, width_in_pixels) tuples, sorted by width ascending
        """
        if not srcset:
            return []

        results = []
        for entry in srcset.split(","):
            parts = entry.strip().split()
            if not parts:
                continue

            url = parts[0]

            # Extract width if specified (e.g., "800w")
            width = 0
            if len(parts) > 1 and parts[1].endswith("w"):
                try:
                    width = int(parts[1][:-1])  # Remove 'w' suffix
                except ValueError:
                    width = 0

            results.append((url, width))

        # Sort by width for easier selection
        results.sort(key=lambda x: x[1])
        return results

    def select_image_resolutions(self, resolutions: list[tuple]) -> tuple:
        """
        Select medium (600-800px) and highest resolution from available options.

        Args:
            resolutions: List of (url, width) tuples sorted by width

        Returns:
            (medium_url, highest_url) tuple. Either can be None if no
            resolutions available. If only one resolution exists, both will be
            the same URL.
        """
        if not resolutions:
            return (None, None)

        # Highest is always the last (largest width)
        highest_url = resolutions[-1][0]

        # For medium, target 600-800px width
        target_width = 700

        # Find closest to target
        medium_url = min(
            resolutions,
            key=lambda x: abs(x[1] - target_width) if x[1] > 0 else float("inf"),
        )[0]

        return (medium_url, highest_url)

    def extract_image_sets(self, html: str) -> dict:
        """
        Extract images with resolution information from HTML.

        This parses both regular img tags and srcset attributes to identify
        all available resolutions for each image.

        Args:
            html: HTML content

        Returns:
            Dictionary mapping base image identifier to dict with:
            {
                "all_urls": [url1, url2, ...],
                "medium": url or None,
                "highest": url or None
            }
        """
        if not html:
            return {}

        if BeautifulSoup is None:
            raise ImportError(
                "BeautifulSoup4 is required. Install with: uv add beautifulsoup4"
            )

        image_sets = {}
        soup = BeautifulSoup(html, "html.parser")

        # Process img tags
        for img in soup.find_all("img"):
            src = img.get("src")
            srcset = img.get("srcset")

            if src:
                # Use src as base identifier
                base_id = src

                if base_id not in image_sets:
                    image_sets[base_id] = {
                        "all_urls": [],
                        "medium": None,
                        "highest": None,
                    }

                # Add src URL
                if src not in image_sets[base_id]["all_urls"]:
                    image_sets[base_id]["all_urls"].append(src)

                # Parse srcset if available
                if srcset:
                    resolutions = self.parse_srcset(srcset)
                    for url, _width in resolutions:
                        if url not in image_sets[base_id]["all_urls"]:
                            image_sets[base_id]["all_urls"].append(url)

                    # Select medium and highest from srcset
                    if resolutions:
                        medium, highest = self.select_image_resolutions(resolutions)
                        image_sets[base_id]["medium"] = medium
                        image_sets[base_id]["highest"] = highest
                else:
                    # No srcset, use src as both medium and highest
                    image_sets[base_id]["medium"] = src
                    image_sets[base_id]["highest"] = src

        # Process source tags with srcset (inside picture elements)
        for source in soup.find_all("source"):
            srcset = source.get("srcset")
            if srcset:
                resolutions = self.parse_srcset(srcset)
                if resolutions:
                    # Use highest resolution URL as base identifier
                    base_id = resolutions[-1][0]

                    if base_id not in image_sets:
                        image_sets[base_id] = {
                            "all_urls": [],
                            "medium": None,
                            "highest": None,
                        }

                    # Add all URLs from srcset
                    for url, _width in resolutions:
                        if url not in image_sets[base_id]["all_urls"]:
                            image_sets[base_id]["all_urls"].append(url)

                    # Select resolutions
                    medium, highest = self.select_image_resolutions(resolutions)
                    image_sets[base_id]["medium"] = medium
                    image_sets[base_id]["highest"] = highest

        return image_sets

    def rewrite_urls(self, html: str, url_map: dict) -> str:
        """
        Rewrite URLs in HTML using a mapping.

        Args:
            html: HTML content
            url_map: Dictionary mapping original URLs to local paths

        Returns:
            HTML with rewritten URLs
        """
        if not html or not url_map:
            return html

        if BeautifulSoup is None:
            raise ImportError(
                "BeautifulSoup4 is required. Install with: uv add beautifulsoup4"
            )

        soup = BeautifulSoup(html, "html.parser")

        # Rewrite img src attributes
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and src in url_map:
                img["src"] = url_map[src]

        # Rewrite a href attributes
        for link in soup.find_all("a"):
            href = link.get("href")
            if href and href in url_map:
                link["href"] = url_map[href]

        # Rewrite source srcset attributes
        for source in soup.find_all("source"):
            srcset = source.get("srcset")
            if srcset:
                new_srcset = srcset
                for original, local in url_map.items():
                    new_srcset = new_srcset.replace(original, local)
                source["srcset"] = new_srcset

        return str(soup)

    def download_and_rewrite(self, html: str, topic_id: int) -> str:
        """
        Download assets and rewrite URLs in HTML.

        Args:
            html: HTML content
            topic_id: Topic ID

        Returns:
            HTML with local URLs
        """
        if not self.asset_downloader:
            return html

        # Extract all images
        images = self.extract_images(html)

        # Download each image and build URL map
        url_map = {}
        for img_url in images:
            local_path = self.asset_downloader.download_image(img_url, topic_id)
            if local_path and self.asset_downloader.output_dir:
                # Calculate relative path from asset output dir
                try:
                    relative = str(
                        local_path.relative_to(self.asset_downloader.output_dir)
                    )
                    url_map[img_url] = f"assets/{relative}"
                except ValueError:
                    # If relative_to fails, use absolute path
                    url_map[img_url] = str(local_path)

        # Rewrite URLs with the mapping
        return self.rewrite_urls(html, url_map)

    def rewrite_to_relative_assets(
        self, html: str, topic_id: int, page_depth: int = 2
    ) -> str:
        """
        Rewrite external image URLs to relative asset paths.

        This assumes assets are already downloaded to assets/images/{topic_id}/

        Args:
            html: HTML content
            topic_id: Topic ID
            page_depth: Depth of the page (2 for topics, 0 for index)

        Returns:
            HTML with relative asset paths
        """
        if not html:
            return html

        if BeautifulSoup is None:
            raise ImportError(
                "BeautifulSoup4 is required. Install with: uv add beautifulsoup4"
            )

        soup = BeautifulSoup(html, "html.parser")

        # Calculate relative path prefix based on depth
        rel_prefix = "../" * page_depth if page_depth > 0 else ""

        # Rewrite img src attributes
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and src.startswith("http"):
                # Extract filename from URL
                filename = src.split("/")[-1].split("?")[0]
                # Rewrite to relative asset path
                img["src"] = f"{rel_prefix}assets/images/{topic_id}/{filename}"

        return str(soup)

    def enhance_emoji_with_unicode(self, html: str) -> str:
        """
        Enhance emoji images with Unicode character fallbacks.

        Adds Unicode emoji to alt text for better offline viewing when images
        fail to load.

        Args:
            html: HTML content

        Returns:
            HTML with enhanced emoji
        """
        if not html:
            return html

        if BeautifulSoup is None:
            raise ImportError(
                "BeautifulSoup4 is required. Install with: uv add beautifulsoup4"
            )

        soup = BeautifulSoup(html, "html.parser")

        # Find all emoji images
        for img in soup.find_all("img", class_="emoji"):
            # Normalize emoji sizing to ensure consistent display
            # All emojis should be 20x20 pixels
            img["width"] = "20"
            img["height"] = "20"

            # Get shortcode from title or alt attribute
            shortcode = img.get("title") or img.get("alt") or ""

            # Ensure shortcode has colons
            if shortcode and not shortcode.startswith(":"):
                shortcode = f":{shortcode}:"

            # Check if we have a Unicode mapping for this emoji
            if shortcode and has_unicode_emoji(shortcode):
                unicode_emoji = get_unicode_emoji(shortcode)

                # Update alt text to include Unicode emoji
                img["alt"] = unicode_emoji

                # Add Unicode emoji as data attribute for accessibility
                img["data-emoji"] = unicode_emoji

        return str(soup)

    def enhance_all_image_alt_text(self, html: str) -> str:
        """
        Enhance alt text for all images using available metadata and context.

        This improves accessibility by:
        1. Adding filename + dimensions + size to lightbox images
        2. Adding dimensions to inline gallery images
        3. Adding context to onebox images (site icons, thumbnails)
        4. Skipping already well-described images (emoji, avatars, logos)

        Args:
            html: HTML content

        Returns:
            HTML with enhanced image alt text
        """
        if not html:
            return html

        if BeautifulSoup is None:
            raise ImportError(
                "BeautifulSoup4 is required. Install with: uv add beautifulsoup4"
            )

        soup = BeautifulSoup(html, "html.parser")

        # Handle lightbox-wrapped images with metadata
        for lightbox in soup.find_all("div", class_="lightbox-wrapper"):
            img = lightbox.find("img")
            meta_div = lightbox.find("div", class_="meta")

            if img and meta_div:
                # Extract metadata
                filename_span = meta_div.find("span", class_="filename")
                info_span = meta_div.find("span", class_="informations")

                filename = filename_span.get_text(strip=True) if filename_span else ""
                info = info_span.get_text(strip=True) if info_span else ""

                # Build descriptive text for both alt and title
                if filename and info:
                    desc_text = f"Image: {filename} ({info})"
                elif info:
                    desc_text = f"Image ({info})"
                elif filename:
                    desc_text = f"Image: {filename}"
                else:
                    desc_text = None

                # Apply to both alt (screen readers) and title (hover tooltip)
                if desc_text:
                    img["alt"] = desc_text
                    img["title"] = desc_text

                # Remove the visual metadata div (keep info in alt/title only)
                meta_div.decompose()

        # Handle inline images (not in lightbox) with role="presentation"
        for img in soup.find_all("img", role="presentation"):
            # Skip if already in a lightbox (handled above)
            if img.find_parent("div", class_="lightbox-wrapper"):
                continue

            # Only enhance if alt is empty or minimal
            current_alt = img.get("alt", "").strip()
            if current_alt and len(current_alt) > 3:
                continue  # Already has meaningful alt text

            # Extract dimensions from attributes
            width = img.get("width", "")
            height = img.get("height", "")

            if width and height:
                desc_text = f"Image ({width}×{height})"
                img["alt"] = desc_text
                img["title"] = desc_text
            else:
                img["alt"] = "Image"
                img["title"] = "Image"

        # Handle onebox images (social media previews)
        for onebox in soup.find_all("aside", class_="onebox"):
            # Get the source URL/domain
            onebox_src = onebox.get("data-onebox-src", "")
            domain = ""

            if onebox_src:
                # Extract domain from URL
                try:
                    from urllib.parse import urlparse

                    parsed = urlparse(onebox_src)
                    domain = parsed.netloc.replace("www.", "")
                except Exception:
                    domain = onebox_src

            # Handle site icon
            site_icon = onebox.find("img", class_="site-icon")
            if site_icon and not site_icon.get("alt"):
                if domain:
                    desc_text = f"Site icon for {domain}"
                    site_icon["alt"] = desc_text
                    site_icon["title"] = desc_text
                else:
                    site_icon["alt"] = "Site icon"
                    site_icon["title"] = "Site icon"

            # Handle thumbnail/avatar images in onebox
            for thumb_class in ["thumbnail", "onebox-avatar"]:
                thumbnail = onebox.find("img", class_=thumb_class)
                if thumbnail and not thumbnail.get("alt"):
                    if domain:
                        desc_text = f"Preview thumbnail for {domain}"
                        thumbnail["alt"] = desc_text
                        thumbnail["title"] = desc_text
                    else:
                        thumbnail["alt"] = "Preview thumbnail"
                        thumbnail["title"] = "Preview thumbnail"

        return str(soup)

    def _resolve_asset_relative_path(
        self, local_path: str, rel_prefix: str
    ) -> str | None:
        """
        Convert a database local_path to a relative path for HTML output.

        Finds the 'assets/' substring in local_path and prepends rel_prefix
        to produce a path like '../../assets/images/10/smile.png'.

        Args:
            local_path: Path from database (e.g., 'archives/assets/images/10/smile.png')
            rel_prefix: Relative prefix based on page depth (e.g., '../../')

        Returns:
            Relative path string, or None if 'assets/' not found in local_path
        """
        assets_marker = "assets/"
        idx = local_path.find(assets_marker)
        if idx == -1:
            return None
        return f"{rel_prefix}{local_path[idx:]}"

    def _rewrite_srcset_value(
        self, srcset: str, asset_map: dict, db, rel_prefix: str
    ) -> str:
        """
        Rewrite URLs in a srcset attribute value using asset lookups.

        Uses a two-pass approach:
        - Pass 1: Resolve each entry via topic-scoped and global lookups,
          tracking resolved entries with their width descriptors.
        - Pass 2: For unresolved entries with width descriptors (e.g., 100w),
          map to the nearest resolved variant by width proximity.

        Args:
            srcset: srcset attribute value
                (e.g., "img_800.webp 800w, img_1200.webp 1200w")
            asset_map: Topic-scoped URL-to-local-path mapping
            db: ArchiveDatabase instance for global lookups
            rel_prefix: Relative prefix based on page depth

        Returns:
            Rewritten srcset string
        """
        # Parse all entries first
        parsed_entries = []
        for entry in srcset.split(","):
            entry = entry.strip()
            if not entry:
                continue

            parts = entry.split()
            if not parts:
                parsed_entries.append(
                    {"original": entry, "url": "", "descriptor": "", "is_http": False}
                )
                continue

            url = parts[0]
            descriptor = " ".join(parts[1:]) if len(parts) > 1 else ""
            parsed_entries.append(
                {
                    "original": entry,
                    "url": url,
                    "descriptor": descriptor,
                    "is_http": url.startswith("http"),
                }
            )

        # Pass 1: Try to resolve each entry, track resolved widths
        resolved_variants = []  # [(width_int, relative_path), ...]
        results = []  # parallel list: resolved relative_path or None

        for pe in parsed_entries:
            if not pe["is_http"]:
                results.append(pe["original"])
                continue

            url = pe["url"]
            descriptor = pe["descriptor"]
            relative_path = None

            # Try topic-scoped lookup first
            local_path = asset_map.get(url)
            if local_path:
                relative_path = self._resolve_asset_relative_path(
                    local_path, rel_prefix
                )

            # Try global lookup
            if not relative_path:
                global_path = db.get_asset_path(url)

                # Query-param fallback: strip ?v=X and try prefix match
                if not global_path:
                    parsed = urllib.parse.urlparse(url)
                    if parsed.query:
                        base_url = urllib.parse.urlunparse(parsed._replace(query=""))
                        global_path = db.find_asset_by_url_prefix(base_url)

                if global_path:
                    relative_path = self._resolve_asset_relative_path(
                        global_path, rel_prefix
                    )

            if relative_path:
                rewritten = (
                    f"{relative_path} {descriptor}" if descriptor else relative_path
                )
                results.append(rewritten)
                # Track width for pass 2 nearest-variant matching
                if descriptor.endswith("w"):
                    try:
                        width = int(descriptor[:-1])
                        resolved_variants.append((width, relative_path))
                    except ValueError:
                        pass
            else:
                # Mark as unresolved for pass 2
                results.append(None)

        # Pass 2: Map unresolved width-descriptor entries to nearest resolved
        if resolved_variants:
            for i, pe in enumerate(parsed_entries):
                if results[i] is not None:
                    continue
                descriptor = pe["descriptor"]
                # Only apply nearest-variant logic to width descriptors
                if not descriptor.endswith("w"):
                    results[i] = pe["original"]
                    continue
                try:
                    target_width = int(descriptor[:-1])
                except ValueError:
                    results[i] = pe["original"]
                    continue
                # Find nearest resolved variant by width proximity
                nearest_path = min(
                    resolved_variants, key=lambda r: abs(r[0] - target_width)
                )[1]
                results[i] = f"{nearest_path} {descriptor}"

        # Fill any remaining unresolved entries with originals
        for i, pe in enumerate(parsed_entries):
            if results[i] is None:
                results[i] = pe["original"]

        return ", ".join(results)

    def rewrite_with_full_resolution_links(
        self, html: str, topic_id: int, db, page_depth: int = 2
    ) -> str:
        """
        Rewrite HTML to use downloaded assets with anchor links to full resolution.

        This method:
        1. Queries the asset registry to find actually downloaded images
        2. Wraps medium-resolution images in <a> tags linking to full resolution
        3. Falls back to original URLs for assets that failed to download

        Args:
            html: HTML content
            topic_id: Topic ID
            db: ArchiveDatabase instance
            page_depth: Depth of current page (2 for topics, 0 for index)

        Returns:
            HTML with local asset references and clickable full-resolution links
        """
        if not html:
            return html

        if BeautifulSoup is None:
            raise ImportError(
                "BeautifulSoup4 is required. Install with: uv add beautifulsoup4"
            )

        soup = BeautifulSoup(html, "html.parser")
        rel_prefix = "../" * page_depth if page_depth > 0 else ""

        # Get all assets for this topic from database
        topic_assets = db.get_assets_for_topic(topic_id)

        # Build lookup dict: url -> local_path
        asset_map = {asset["url"]: asset["local_path"] for asset in topic_assets}

        # Process each image
        for img in soup.find_all("img"):
            src = img.get("src")
            if not src or not src.startswith("http"):
                continue  # Skip relative URLs or empty src

            # Try to find this exact URL in topic-scoped assets
            if src in asset_map:
                local_path_str = asset_map[src]
                relative_path = self._resolve_asset_relative_path(
                    local_path_str, rel_prefix
                )
                if not relative_path:
                    local_path = Path(local_path_str)
                    relative_path = (
                        f"{rel_prefix}assets/images/{topic_id}/{local_path.name}"
                    )

                # Check if there's a higher resolution version
                # Look for other assets with similar filenames
                local_path = Path(local_path_str)
                filename = local_path.name
                base_filename = filename.split("_")[0]  # Remove resolution suffix
                higher_res_asset = None

                for _url, path in asset_map.items():
                    path_obj = Path(path)

                    # Check if this might be a higher resolution version
                    is_similar = (
                        base_filename in path_obj.name and path_obj.name != filename
                    )
                    if not is_similar:
                        continue

                    # Prefer files with 'original' in name or larger file size
                    try:
                        is_higher_res = "original" in path_obj.name.lower() or (
                            local_path.exists()
                            and path_obj.exists()
                            and path_obj.stat().st_size > local_path.stat().st_size
                        )
                        if is_higher_res:
                            higher_res_asset = path_obj
                            break
                    except (OSError, FileNotFoundError):
                        continue

                if higher_res_asset:
                    # Wrap in anchor tag to full resolution
                    higher_res_path = self._resolve_asset_relative_path(
                        str(higher_res_asset), rel_prefix
                    )
                    if not higher_res_path:
                        higher_res_path = (
                            f"{rel_prefix}assets/images/{topic_id}/"
                            f"{higher_res_asset.name}"
                        )

                    anchor = soup.new_tag(
                        "a",
                        href=higher_res_path,
                        **{"class": "discourse-image-link", "target": "_blank"},
                    )
                    img["src"] = relative_path
                    img.wrap(anchor)
                else:
                    # Just rewrite the src, no anchor needed
                    img["src"] = relative_path

            else:
                # Asset not in topic-scoped map - try global lookup
                global_path = db.get_asset_path(src)

                # Query-param fallback: strip ?v=X and try prefix match
                if not global_path:
                    parsed = urllib.parse.urlparse(src)
                    if parsed.query:
                        base_url = urllib.parse.urlunparse(parsed._replace(query=""))
                        global_path = db.find_asset_by_url_prefix(base_url)

                if global_path:
                    relative_path = self._resolve_asset_relative_path(
                        global_path, rel_prefix
                    )
                    if relative_path:
                        img["src"] = relative_path
                        continue

                # Fall back to pattern matching within topic assets
                original_filename = src.split("/")[-1].split("?")[0]

                # Find any asset with matching filename
                matching_asset = None
                for _url, path in asset_map.items():
                    if original_filename in Path(path).name:
                        matching_asset = Path(path)
                        break

                if matching_asset:
                    relative_path = self._resolve_asset_relative_path(
                        str(matching_asset), rel_prefix
                    )
                    if not relative_path:
                        relative_path = (
                            f"{rel_prefix}assets/images/{topic_id}/"
                            f"{matching_asset.name}"
                        )
                    img["src"] = relative_path
                # else: keep original URL (will load remotely if online)

        # Rewrite srcset attributes on <source> and <img> tags
        for tag in soup.find_all(["source", "img"]):
            srcset = tag.get("srcset")
            if not srcset:
                continue
            # Only process if srcset contains http URLs
            if "http" not in srcset:
                continue
            tag["srcset"] = self._rewrite_srcset_value(
                srcset, asset_map, db, rel_prefix
            )

        return str(soup)

    def add_image_dimensions(self, html: str, base_path: Path = None) -> str:  # type: ignore[arg-type]
        """
        Add explicit width and height attributes to images.

        This prevents Cumulative Layout Shift (CLS) by specifying image dimensions
        before the images load. Reads actual dimensions from image files if available.

        Args:
            html: HTML content
            base_path: Base path for resolving relative image paths

        Returns:
            HTML with width/height attributes added to images
        """
        if not html:
            return html

        if BeautifulSoup is None:
            raise ImportError(
                "BeautifulSoup4 is required. Install with: uv add beautifulsoup4"
            )

        soup = BeautifulSoup(html, "html.parser")

        for img in soup.find_all("img"):
            # Skip if already has both width and height
            if img.get("width") and img.get("height"):
                continue

            src = img.get("src")
            if not src:
                continue

            # Try to resolve path and read image dimensions
            if base_path and not src.startswith("http"):
                # Relative path - try to resolve it
                image_path = base_path / src.lstrip("/")

                if image_path.exists():
                    try:
                        from PIL import Image  # type: ignore[import-not-found]

                        with Image.open(image_path) as pil_img:
                            width, height = pil_img.size
                            img["width"] = str(width)
                            img["height"] = str(height)
                    except Exception:
                        # If PIL fails or image is corrupted, skip
                        pass

        return str(soup)
