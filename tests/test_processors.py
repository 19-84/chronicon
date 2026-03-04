# ABOUTME: Test file for content processors
# ABOUTME: Tests for ThemeExtractor, HTMLProcessor, and URLRewriter

"""Tests for content processors."""

from pathlib import Path
from unittest.mock import Mock

from chronicon.processors.html_parser import HTMLProcessor
from chronicon.processors.url_rewriter import URLRewriter


class TestHTMLProcessor:
    """Tests for HTMLProcessor."""

    def test_extract_images_from_html(self):
        """Test extracting image URLs from HTML."""
        html = """
        <div class="post">
            <img src="/uploads/default/original/1X/abc.png" alt="Image 1">
            <p>Some text</p>
            <img src="https://example.com/image.jpg" alt="Image 2">
        </div>
        """

        processor = HTMLProcessor()
        images = processor.extract_images(html)

        assert len(images) == 2
        assert "/uploads/default/original/1X/abc.png" in images
        assert "https://example.com/image.jpg" in images

    def test_extract_images_with_srcset(self):
        """Test extracting images from srcset attributes."""
        html = """
        <picture>
            <source srcset="/uploads/image-800.jpg 800w, /uploads/image-1200.jpg 1200w">
            <img src="/uploads/image-400.jpg" alt="Responsive">
        </picture>
        """

        processor = HTMLProcessor()
        images = processor.extract_images(html)

        # Should extract all images from srcset and src
        assert "/uploads/image-400.jpg" in images
        assert any("image-800.jpg" in img for img in images)
        assert any("image-1200.jpg" in img for img in images)

    def test_extract_images_no_images(self):
        """Test extracting images from HTML without images."""
        html = "<p>Just text, no images</p>"

        processor = HTMLProcessor()
        images = processor.extract_images(html)

        assert images == []

    def test_rewrite_urls_with_mapping(self):
        """Test URL rewriting using a mapping dictionary."""
        html = """
        <img src="https://example.com/uploads/image.png" alt="Test">
        <a href="https://example.com/t/topic/123">Link</a>
        """

        url_map = {
            "https://example.com/uploads/image.png": "../assets/images/1/image.png",
            "https://example.com/t/topic/123": "../topics/topic-123.html",
        }

        processor = HTMLProcessor()
        rewritten = processor.rewrite_urls(html, url_map)

        assert "../assets/images/1/image.png" in rewritten
        assert "../topics/topic-123.html" in rewritten
        assert "https://example.com" not in rewritten

    def test_download_and_rewrite(self):
        """Test download and rewrite in one operation."""
        html = '<img src="https://example.com/image.png" alt="Test">'

        # Mock asset downloader
        mock_downloader = Mock()
        mock_downloader.download_image.return_value = Path(
            "/output/assets/images/1/image.png"
        )
        mock_downloader.output_dir = Path("/output/assets")

        processor = HTMLProcessor(mock_downloader)
        result = processor.download_and_rewrite(html, topic_id=1)

        # Should have downloaded the image
        mock_downloader.download_image.assert_called_once()
        # Result should have local path
        assert "assets/images" in result or "image.png" in result

    def test_enhance_emoji_with_unicode(self):
        """Test enhancing emoji images with Unicode fallbacks."""
        html = """
        <p>I like this <img class="emoji" title=":+1:" alt=":+1:"
            src="/images/emoji/+1.png"> feature!</p>
        <p>Here's a smile: <img class="emoji" title="slight_smile"
            src="/images/emoji/slight_smile.png"></p>
        <p>And a heart <img class="emoji" title=":heart:"
            src="/images/emoji/heart.png"></p>
        """

        processor = HTMLProcessor()
        enhanced = processor.enhance_emoji_with_unicode(html)

        # Should have Unicode emoji in alt text
        assert "👍" in enhanced  # :+1: -> thumbs up
        assert "🙂" in enhanced  # :slight_smile: -> slightly smiling face
        assert "❤️" in enhanced or "❤" in enhanced  # :heart: -> red heart

        # Should have data-emoji attributes
        assert 'data-emoji="👍"' in enhanced
        assert 'data-emoji="🙂"' in enhanced

    def test_enhance_emoji_no_mapping(self):
        """Test enhancing emoji with no Unicode mapping."""
        html = (
            '<img class="emoji" title=":unknown_emoji:" '
            'src="/images/emoji/unknown.png">'
        )

        processor = HTMLProcessor()
        enhanced = processor.enhance_emoji_with_unicode(html)

        # Should return original HTML if no mapping exists
        assert enhanced
        assert "emoji" in enhanced

    def test_emoji_size_normalization(self):
        """Test that emoji images are normalized to consistent 20x20 size."""
        html = """
        <p>Mixed sizes:
        <img class="emoji" title=":+1:" alt=":+1:" src="/emoji/+1.png">
        <img class="emoji" title=":heart:" src="/emoji/heart.png"
            width="16" height="16">
        <img class="emoji" title=":smile:" src="/emoji/smile.png"
            width="24" height="24">
        </p>
        """

        processor = HTMLProcessor()
        enhanced = processor.enhance_emoji_with_unicode(html)

        # All emojis should have width="20" and height="20"
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(enhanced, "html.parser")

        emoji_imgs = soup.find_all("img", class_="emoji")
        assert len(emoji_imgs) == 3

        for img in emoji_imgs:
            assert img.get("width") == "20", (
                f"Expected width='20', got width='{img.get('width')}'"
            )
            assert img.get("height") == "20", (
                f"Expected height='20', got height='{img.get('height')}'"
            )

    def test_enhance_lightbox_image_with_filename_and_info(self):
        """Test enhancing lightbox image with filename and dimensions."""
        html = """
        <div class="lightbox-wrapper">
            <a class="lightbox" href="image.jpg" title="1">
                <img src="image_small.jpg" alt="1" width="281" height="500">
                <div class="meta">
                    <span class="filename">1</span>
                    <span class="informations">720×1280 149 KB</span>
                </div>
            </a>
        </div>
        """

        processor = HTMLProcessor()
        enhanced = processor.enhance_all_image_alt_text(html)

        # Should have enhanced alt text
        assert 'alt="Image: 1 (720×1280 149 KB)"' in enhanced
        # Should have title attribute for hover
        assert 'title="Image: 1 (720×1280 149 KB)"' in enhanced
        # Should have removed the visual meta div
        assert '<div class="meta">' not in enhanced

    def test_enhance_lightbox_image_with_empty_filename(self):
        """Test enhancing lightbox image with empty filename."""
        html = """
        <div class="lightbox-wrapper">
            <a class="lightbox" href="image.png">
                <img src="image_small.png" alt="" role="presentation"
                    width="461" height="500">
                <div class="meta">
                    <span class="filename"></span>
                    <span class="informations">603×653 432 KB</span>
                </div>
            </a>
        </div>
        """

        processor = HTMLProcessor()
        enhanced = processor.enhance_all_image_alt_text(html)

        # Should have enhanced alt text without filename
        assert 'alt="Image (603×653 432 KB)"' in enhanced
        # Should have title attribute
        assert 'title="Image (603×653 432 KB)"' in enhanced
        # Should have removed meta div
        assert '<div class="meta">' not in enhanced

    def test_enhance_lightbox_image_chinese_filename(self):
        """Test enhancing lightbox image with Chinese filename."""
        html = """
        <div class="lightbox-wrapper">
            <a class="lightbox" href="image.jpeg" title="10的副本2">
                <img src="image_small.jpeg" alt="10的副本2" width="690" height="387">
                <div class="meta">
                    <span class="filename">10的副本2</span>
                    <span class="informations">800×449 153 KB</span>
                </div>
            </a>
        </div>
        """

        processor = HTMLProcessor()
        enhanced = processor.enhance_all_image_alt_text(html)

        # Should handle Chinese characters properly
        assert 'alt="Image: 10的副本2 (800×449 153 KB)"' in enhanced

    def test_enhance_inline_gallery_image(self):
        """Test enhancing inline gallery image with dimensions."""
        html = """
        <div data-masonry-gallery="">
            <p><img src="image1.webp" alt="" role="presentation"
                width="602" height="451"></p>
            <p><img src="image2.webp" alt="" role="presentation"
                width="197" height="197"></p>
        </div>
        """

        processor = HTMLProcessor()
        enhanced = processor.enhance_all_image_alt_text(html)

        # Should have dimensions in alt text
        assert 'alt="Image (602×451)"' in enhanced
        assert 'alt="Image (197×197)"' in enhanced
        # Should have title attributes for hover
        assert 'title="Image (602×451)"' in enhanced
        assert 'title="Image (197×197)"' in enhanced

    def test_enhance_onebox_site_icon(self):
        """Test enhancing onebox site icon with domain context."""
        html = """
        <aside class="onebox" data-onebox-src="https://www.facebook.com/lifechanyuan">
            <header class="source">
                <img src="fb_icon.png" class="site-icon" width="32" height="32">
                <a href="https://www.facebook.com/lifechanyuan">facebook.com</a>
            </header>
        </aside>
        """

        processor = HTMLProcessor()
        enhanced = processor.enhance_all_image_alt_text(html)

        # Should have contextual alt text
        assert 'alt="Site icon for facebook.com"' in enhanced

    def test_enhance_onebox_thumbnail(self):
        """Test enhancing onebox thumbnail with domain context."""
        html = """
        <aside class="onebox" data-onebox-src="http://newoasisforlife.org/forum/">
            <article class="onebox-body">
                <img src="thumb.png" class="thumbnail onebox-avatar"
                    width="477" height="477">
            </article>
        </aside>
        """

        processor = HTMLProcessor()
        enhanced = processor.enhance_all_image_alt_text(html)

        # Should have contextual alt text
        assert 'alt="Preview thumbnail for newoasisforlife.org"' in enhanced

    def test_skip_emoji_images(self):
        """Test that emoji images are not modified."""
        html = '<img class="emoji" alt="😀" src="emoji.png" title=":grinning:">'

        processor = HTMLProcessor()
        enhanced = processor.enhance_all_image_alt_text(html)

        # Should keep original emoji alt text
        assert 'alt="😀"' in enhanced

    def test_skip_avatar_images(self):
        """Test that avatar images are not modified."""
        html = (
            '<img src="avatar.png" alt="username\'s avatar" class="avatar avatar-post">'
        )

        processor = HTMLProcessor()
        enhanced = processor.enhance_all_image_alt_text(html)

        # Should keep original avatar alt text
        assert (
            'alt="username\'s avatar"' in enhanced
            or 'alt="username\'s avatar"' in enhanced
        )

    def test_skip_logo_images(self):
        """Test that logo images are not modified."""
        html = '<img src="logo.png" alt="FIC Forum logo" class="header-logo">'

        processor = HTMLProcessor()
        enhanced = processor.enhance_all_image_alt_text(html)

        # Should keep original logo alt text
        assert 'alt="FIC Forum logo"' in enhanced

    def test_enhance_inline_image_without_dimensions(self):
        """Test enhancing inline image without width/height attributes."""
        html = '<p><img src="image.jpg" alt="" role="presentation"></p>'

        processor = HTMLProcessor()
        enhanced = processor.enhance_all_image_alt_text(html)

        # Should have generic alt text
        assert 'alt="Image"' in enhanced

    def test_skip_inline_image_with_meaningful_alt(self):
        """Test that inline images with meaningful alt text are not modified."""
        html = (
            '<p><img src="image.jpg" alt="Beautiful sunset photo" '
            'role="presentation" width="600" height="400"></p>'
        )

        processor = HTMLProcessor()
        enhanced = processor.enhance_all_image_alt_text(html)

        # Should keep original meaningful alt text
        assert 'alt="Beautiful sunset photo"' in enhanced
        assert "Image (600×400)" not in enhanced

    def test_enhance_mixed_content(self):
        """Test enhancing HTML with mixed image types."""
        html = """
        <div class="post">
            <p>Here's a photo:</p>
            <div class="lightbox-wrapper">
                <a class="lightbox" href="photo.jpg">
                    <img src="photo_thumb.jpg" alt="photo1" width="500" height="300">
                    <div class="meta">
                        <span class="filename">photo1</span>
                        <span class="informations">1920×1080 2 MB</span>
                    </div>
                </a>
            </div>
            <p>And here's an emoji: <img class="emoji" alt="😊" src="smile.png"></p>
            <p>Gallery:</p>
            <div data-masonry-gallery="">
                <p><img src="gallery1.webp" alt="" role="presentation"
                    width="300" height="300"></p>
            </div>
        </div>
        """

        processor = HTMLProcessor()
        enhanced = processor.enhance_all_image_alt_text(html)

        # Lightbox should be enhanced
        assert 'alt="Image: photo1 (1920×1080 2 MB)"' in enhanced
        # Emoji should be unchanged
        assert 'alt="😊"' in enhanced
        # Gallery image should be enhanced
        assert 'alt="Image (300×300)"' in enhanced


class TestResolveAssetRelativePath:
    """Tests for HTMLProcessor._resolve_asset_relative_path helper."""

    def test_same_topic_image_path(self):
        """Test resolving an asset stored under the same topic."""
        processor = HTMLProcessor()
        local_path = "archives/assets/images/42/smile.png"
        result = processor._resolve_asset_relative_path(local_path, "../../")
        assert result == "../../assets/images/42/smile.png"

    def test_cross_topic_image_path(self):
        """Test resolving an asset stored under a different topic."""
        processor = HTMLProcessor()
        # Emoji downloaded under topic 10 but referenced in topic 42
        local_path = "archives/assets/images/10/emoji_smile.png"
        result = processor._resolve_asset_relative_path(local_path, "../../")
        assert result == "../../assets/images/10/emoji_smile.png"

    def test_avatar_subdirectory_path(self):
        """Test resolving an avatar asset path."""
        processor = HTMLProcessor()
        local_path = "archives/assets/avatars/codinghorror_288.png"
        result = processor._resolve_asset_relative_path(local_path, "../../")
        assert result == "../../assets/avatars/codinghorror_288.png"

    def test_emoji_subdirectory_path(self):
        """Test resolving an emoji asset path."""
        processor = HTMLProcessor()
        local_path = "archives/assets/emoji/heart.png"
        result = processor._resolve_asset_relative_path(local_path, "../../")
        assert result == "../../assets/emoji/heart.png"

    def test_site_subdirectory_path(self):
        """Test resolving a site asset path."""
        processor = HTMLProcessor()
        local_path = "archives/assets/site/logo.png"
        result = processor._resolve_asset_relative_path(local_path, "../../")
        assert result == "../../assets/site/logo.png"

    def test_absolute_path(self):
        """Test resolving an absolute local_path."""
        processor = HTMLProcessor()
        local_path = "/tmp/test-archives/assets/images/42/photo.jpg"
        result = processor._resolve_asset_relative_path(local_path, "../../")
        assert result == "../../assets/images/42/photo.jpg"

    def test_zero_depth_prefix(self):
        """Test resolving with empty rel_prefix (index page at root)."""
        processor = HTMLProcessor()
        local_path = "archives/assets/images/10/emoji.png"
        result = processor._resolve_asset_relative_path(local_path, "")
        assert result == "assets/images/10/emoji.png"

    def test_no_assets_prefix_fallback(self):
        """Test fallback when 'assets/' is not in the path."""
        processor = HTMLProcessor()
        local_path = "some/random/path/image.png"
        result = processor._resolve_asset_relative_path(local_path, "../../")
        # Should return None when assets/ prefix cannot be found
        assert result is None


class TestGlobalAssetFallback:
    """Tests for global asset fallback in rewrite_with_full_resolution_links."""

    def _make_mock_db(self, topic_assets, global_assets=None):
        """Create a mock DB with topic-scoped and global asset lookups."""
        mock_db = Mock()
        mock_db.get_assets_for_topic.return_value = topic_assets
        if global_assets is None:
            global_assets = {}
        mock_db.get_asset_path.side_effect = lambda url: global_assets.get(url)
        return mock_db

    def test_emoji_from_different_topic_rewritten(self):
        """Test that emoji downloaded under topic 10 is
        rewritten when used in topic 42."""
        processor = HTMLProcessor()
        html = (
            '<img src="https://emoji.discourse-cdn.com/twitter/heart.png"'
            ' class="emoji" alt=":heart:">'
        )

        # Topic 42 has no assets (emoji was saved under topic 10's path)
        topic_assets = []
        global_assets = {
            "https://emoji.discourse-cdn.com/twitter/heart.png": (
                "archives/assets/images/10/heart.png"
            )
        }
        mock_db = self._make_mock_db(topic_assets, global_assets)

        result = processor.rewrite_with_full_resolution_links(
            html, topic_id=42, db=mock_db, page_depth=2
        )

        assert "../../assets/images/10/heart.png" in result
        assert "emoji.discourse-cdn.com" not in result

    def test_quote_avatar_from_global_rewritten(self):
        """Test that a quote avatar is resolved via global lookup."""
        processor = HTMLProcessor()
        html = (
            '<img src="https://d3bpeqsaub0i6y.cloudfront.net/user/avatar/288.png"'
            ' alt="avatar">'
        )

        topic_assets = []
        global_assets = {
            "https://d3bpeqsaub0i6y.cloudfront.net/user/avatar/288.png": (
                "archives/assets/avatars/user_288.png"
            )
        }
        mock_db = self._make_mock_db(topic_assets, global_assets)

        result = processor.rewrite_with_full_resolution_links(
            html, topic_id=42, db=mock_db, page_depth=2
        )

        assert "../../assets/avatars/user_288.png" in result
        assert "cloudfront.net" not in result

    def test_topic_local_asset_preferred_over_global(self):
        """Test that topic-local asset map is checked first, global is not called."""
        processor = HTMLProcessor()
        html = '<img src="https://example.com/image.png" alt="test">'

        topic_assets = [
            {
                "url": "https://example.com/image.png",
                "local_path": "archives/assets/images/42/image.png",
            }
        ]
        mock_db = self._make_mock_db(topic_assets)

        result = processor.rewrite_with_full_resolution_links(
            html, topic_id=42, db=mock_db, page_depth=2
        )

        assert "../../assets/images/42/image.png" in result
        # Global lookup should NOT have been called for this URL
        mock_db.get_asset_path.assert_not_called()

    def test_keep_external_url_when_not_downloaded(self):
        """Test that external URLs are kept when asset is not downloaded anywhere."""
        processor = HTMLProcessor()
        html = '<img src="https://thirdparty.com/random.png" alt="external">'

        topic_assets = []
        global_assets = {}  # Not downloaded
        mock_db = self._make_mock_db(topic_assets, global_assets)

        result = processor.rewrite_with_full_resolution_links(
            html, topic_id=42, db=mock_db, page_depth=2
        )

        assert "https://thirdparty.com/random.png" in result

    def test_mixed_local_and_global_assets(self):
        """Test a post with both topic-local and global assets."""
        processor = HTMLProcessor()
        html = """
        <img src="https://example.com/topic-image.png" alt="local">
        <img src="https://emoji.discourse-cdn.com/twitter/smile.png"
            class="emoji" alt=":smile:">
        <img src="https://thirdparty.com/external.jpg" alt="external">
        """

        topic_assets = [
            {
                "url": "https://example.com/topic-image.png",
                "local_path": "archives/assets/images/42/topic-image.png",
            }
        ]
        global_assets = {
            "https://emoji.discourse-cdn.com/twitter/smile.png": (
                "archives/assets/images/5/smile.png"
            )
        }
        mock_db = self._make_mock_db(topic_assets, global_assets)

        result = processor.rewrite_with_full_resolution_links(
            html, topic_id=42, db=mock_db, page_depth=2
        )

        # Topic-local should be rewritten
        assert "../../assets/images/42/topic-image.png" in result
        # Global emoji should be rewritten
        assert "../../assets/images/5/smile.png" in result
        # External should stay
        assert "https://thirdparty.com/external.jpg" in result

    def test_global_fallback_with_zero_depth(self):
        """Test global fallback works with zero page depth (index page)."""
        processor = HTMLProcessor()
        html = (
            '<img src="https://emoji.discourse-cdn.com/twitter/wave.png" class="emoji">'
        )

        topic_assets = []
        global_assets = {
            "https://emoji.discourse-cdn.com/twitter/wave.png": (
                "archives/assets/images/3/wave.png"
            )
        }
        mock_db = self._make_mock_db(topic_assets, global_assets)

        result = processor.rewrite_with_full_resolution_links(
            html, topic_id=42, db=mock_db, page_depth=0
        )

        assert "assets/images/3/wave.png" in result
        assert not result.startswith("../../")


class TestSrcsetRewriting:
    """Tests for srcset attribute rewriting in rewrite_with_full_resolution_links."""

    def _make_mock_db(self, topic_assets, global_assets=None):
        """Create a mock DB with topic-scoped and global asset lookups."""
        mock_db = Mock()
        mock_db.get_assets_for_topic.return_value = topic_assets
        if global_assets is None:
            global_assets = {}
        mock_db.get_asset_path.side_effect = lambda url: global_assets.get(url)
        return mock_db

    def test_source_srcset_topic_local(self):
        """Test rewriting srcset in <source> tags with topic-local assets."""
        processor = HTMLProcessor()
        html = """
        <picture>
            <source srcset="https://d11a6trkgmumsb.cloudfront.net/img_800.webp 800w,
                https://d11a6trkgmumsb.cloudfront.net/img_1200.webp 1200w">
            <img src="https://d11a6trkgmumsb.cloudfront.net/img_400.webp" alt="photo">
        </picture>
        """

        topic_assets = [
            {
                "url": "https://d11a6trkgmumsb.cloudfront.net/img_400.webp",
                "local_path": "archives/assets/images/42/img_400.webp",
            },
            {
                "url": "https://d11a6trkgmumsb.cloudfront.net/img_800.webp",
                "local_path": "archives/assets/images/42/img_800.webp",
            },
            {
                "url": "https://d11a6trkgmumsb.cloudfront.net/img_1200.webp",
                "local_path": "archives/assets/images/42/img_1200.webp",
            },
        ]
        mock_db = self._make_mock_db(topic_assets)

        result = processor.rewrite_with_full_resolution_links(
            html, topic_id=42, db=mock_db, page_depth=2
        )

        # img src should be rewritten
        assert "../../assets/images/42/img_400.webp" in result
        # srcset entries should be rewritten
        assert "../../assets/images/42/img_800.webp" in result
        assert "../../assets/images/42/img_1200.webp" in result
        # No external URLs should remain
        assert "cloudfront.net" not in result

    def test_source_srcset_global_fallback(self):
        """Test rewriting srcset in <source> tags with global asset fallback."""
        processor = HTMLProcessor()
        html = """
        <picture>
            <source srcset="https://cdn.example.com/photo_800.webp 800w,
                https://cdn.example.com/photo_1200.webp 1200w">
            <img src="https://cdn.example.com/photo_400.webp" alt="photo">
        </picture>
        """

        topic_assets = []
        global_assets = {
            "https://cdn.example.com/photo_400.webp": (
                "archives/assets/images/10/photo_400.webp"
            ),
            "https://cdn.example.com/photo_800.webp": (
                "archives/assets/images/10/photo_800.webp"
            ),
            "https://cdn.example.com/photo_1200.webp": (
                "archives/assets/images/10/photo_1200.webp"
            ),
        }
        mock_db = self._make_mock_db(topic_assets, global_assets)

        result = processor.rewrite_with_full_resolution_links(
            html, topic_id=42, db=mock_db, page_depth=2
        )

        # All URLs should be rewritten via global fallback
        assert "../../assets/images/10/photo_800.webp" in result
        assert "../../assets/images/10/photo_1200.webp" in result
        assert "cdn.example.com" not in result

    def test_source_srcset_partial_resolution(self):
        """Test that srcset entries are rewritten using nearest-variant
        fallback when only some assets exist."""
        processor = HTMLProcessor()
        html = """
        <picture>
            <source srcset="https://cdn.example.com/a_800.webp 800w,
                https://cdn.example.com/a_1200.webp 1200w">
            <img src="https://cdn.example.com/a_400.webp" alt="photo">
        </picture>
        """

        topic_assets = [
            {
                "url": "https://cdn.example.com/a_400.webp",
                "local_path": "archives/assets/images/42/a_400.webp",
            },
            {
                "url": "https://cdn.example.com/a_800.webp",
                "local_path": "archives/assets/images/42/a_800.webp",
            },
        ]
        # a_1200 not downloaded at all
        mock_db = self._make_mock_db(topic_assets)

        result = processor.rewrite_with_full_resolution_links(
            html, topic_id=42, db=mock_db, page_depth=2
        )

        # Downloaded asset should be rewritten
        assert "../../assets/images/42/a_800.webp 800w" in result
        # Unresolved 1200w should map to nearest resolved variant (800w)
        assert "cdn.example.com" not in result
        assert "../../assets/images/42/a_800.webp 1200w" in result

    def test_img_srcset_rewriting(self):
        """Test rewriting srcset on <img> tags (not just <source>)."""
        processor = HTMLProcessor()
        html = (
            '<img src="https://cdn.example.com/photo.webp"'
            ' srcset="https://cdn.example.com/photo_2x.webp 2x"'
            ' alt="photo">'
        )

        topic_assets = [
            {
                "url": "https://cdn.example.com/photo.webp",
                "local_path": "archives/assets/images/42/photo.webp",
            },
            {
                "url": "https://cdn.example.com/photo_2x.webp",
                "local_path": "archives/assets/images/42/photo_2x.webp",
            },
        ]
        mock_db = self._make_mock_db(topic_assets)

        result = processor.rewrite_with_full_resolution_links(
            html, topic_id=42, db=mock_db, page_depth=2
        )

        # Both src and srcset should be rewritten
        assert "../../assets/images/42/photo.webp" in result
        assert "../../assets/images/42/photo_2x.webp" in result
        assert "cdn.example.com" not in result

    def test_srcset_no_external_urls(self):
        """Test that non-http srcset entries are left alone."""
        processor = HTMLProcessor()
        html = """
        <picture>
            <source srcset="local/image_800.webp 800w">
            <img src="https://cdn.example.com/photo.webp" alt="photo">
        </picture>
        """

        topic_assets = [
            {
                "url": "https://cdn.example.com/photo.webp",
                "local_path": "archives/assets/images/42/photo.webp",
            },
        ]
        mock_db = self._make_mock_db(topic_assets)

        result = processor.rewrite_with_full_resolution_links(
            html, topic_id=42, db=mock_db, page_depth=2
        )

        # img src should be rewritten
        assert "../../assets/images/42/photo.webp" in result
        # Local srcset entry should be untouched
        assert "local/image_800.webp" in result


class TestAssetRewritingIntegration:
    """Integration tests for asset URL rewriting with a real SQLite database."""

    def test_all_three_asset_types_rewritten(self, tmp_path):
        """End-to-end: emoji, quote avatar, and srcset images are all rewritten."""
        from chronicon.storage.database import ArchiveDatabase

        db_path = tmp_path / "test.db"
        db = ArchiveDatabase(db_path)
        # DB auto-initializes on construction

        # Register assets as they would be downloaded:
        # Emoji - registered under topic 10's path
        db.register_asset(
            "https://emoji.discourse-cdn.com/twitter/heart.png",
            "archives/assets/images/10/heart.png",
            "image/png",
        )
        # Quote avatar - registered under avatars directory
        db.register_asset(
            "https://d3bpeqsaub0i6y.cloudfront.net/user/avatar/288.png",
            "archives/assets/avatars/user_288.png",
            "image/png",
        )
        # Srcset images - registered under topic 42's path
        db.register_asset(
            "https://d11a6trkgmumsb.cloudfront.net/img_400.webp",
            "archives/assets/images/42/img_400.webp",
            "image/webp",
        )
        db.register_asset(
            "https://d11a6trkgmumsb.cloudfront.net/img_800.webp",
            "archives/assets/images/42/img_800.webp",
            "image/webp",
        )
        db.register_asset(
            "https://d11a6trkgmumsb.cloudfront.net/img_1200.webp",
            "archives/assets/images/42/img_1200.webp",
            "image/webp",
        )
        # Topic-local image for topic 42
        db.register_asset(
            "https://example.com/uploads/photo.jpg",
            "archives/assets/images/42/photo.jpg",
            "image/jpeg",
        )

        # HTML from topic 42 referencing all three types
        html = """
        <div class="post">
            <p>Great post <img src="https://emoji.discourse-cdn.com/twitter/heart.png"
                class="emoji" alt=":heart:"></p>
            <blockquote>
                <img src="https://d3bpeqsaub0i6y.cloudfront.net/user/avatar/288.png"
                    alt="avatar" class="avatar">
            </blockquote>
            <picture>
                <source srcset="https://d11a6trkgmumsb.cloudfront.net/img_800.webp 800w,
                https://d11a6trkgmumsb.cloudfront.net/img_1200.webp 1200w">
                <img src="https://d11a6trkgmumsb.cloudfront.net/img_400.webp"
                    alt="photo">
            </picture>
            <img src="https://example.com/uploads/photo.jpg"
                alt="local photo">
            <img src="https://thirdparty.com/undownloaded.jpg" alt="external">
        </div>
        """

        processor = HTMLProcessor()
        result = processor.rewrite_with_full_resolution_links(
            html, topic_id=42, db=db, page_depth=2
        )

        # Emoji (cross-topic): rewritten via global fallback
        assert "../../assets/images/10/heart.png" in result
        assert "emoji.discourse-cdn.com" not in result

        # Quote avatar (cross-topic): rewritten via global fallback
        assert "../../assets/avatars/user_288.png" in result
        assert "d3bpeqsaub0i6y.cloudfront.net" not in result

        # Srcset (topic-local): all entries rewritten
        assert "../../assets/images/42/img_400.webp" in result
        assert "../../assets/images/42/img_800.webp" in result
        assert "../../assets/images/42/img_1200.webp" in result
        assert "d11a6trkgmumsb.cloudfront.net" not in result

        # Topic-local image: rewritten normally
        assert "../../assets/images/42/photo.jpg" in result

        # External undownloaded image: kept as-is
        assert "https://thirdparty.com/undownloaded.jpg" in result

        db.close()

    def test_global_fallback_does_not_pollute_topic_local(self, tmp_path):
        """Verify global fallback only applies when topic lookup fails."""
        from chronicon.storage.database import ArchiveDatabase

        db_path = tmp_path / "test.db"
        db = ArchiveDatabase(db_path)
        # DB auto-initializes on construction

        # Same image registered under topic 10
        db.register_asset(
            "https://example.com/shared.png",
            "archives/assets/images/10/shared.png",
            "image/png",
        )

        html = '<img src="https://example.com/shared.png" alt="shared">'

        processor = HTMLProcessor()

        # From topic 10 (topic-local lookup should find it)
        result_10 = processor.rewrite_with_full_resolution_links(
            html, topic_id=10, db=db, page_depth=2
        )
        assert "../../assets/images/10/shared.png" in result_10

        # From topic 42 (should fall back to global)
        result_42 = processor.rewrite_with_full_resolution_links(
            html, topic_id=42, db=db, page_depth=2
        )
        assert "../../assets/images/10/shared.png" in result_42

        db.close()


class TestURLRewriter:
    """Tests for URLRewriter."""

    def test_rewrite_image_url_relative_path(self):
        """Test rewriting image URL to relative path."""
        rewriter = URLRewriter("https://meta.discourse.org")

        # Context: /topics/2024-10/my-topic.html
        # Image:   /assets/images/123/pic.png
        context_path = Path("/output/topics/2024-10/my-topic.html")
        local_path = Path("/output/assets/images/123/pic.png")

        relative = rewriter.rewrite_image_url(
            "https://meta.discourse.org/uploads/pic.png", local_path, context_path
        )

        # Should be relative path from context to image
        assert relative.startswith("../")
        assert "pic.png" in relative

    def test_rewrite_user_link(self):
        """Test rewriting user profile link."""
        rewriter = URLRewriter("https://meta.discourse.org")

        user_link = rewriter.rewrite_user_link("codinghorror")

        assert user_link == "/users/codinghorror.html"

    def test_rewrite_topic_link(self):
        """Test rewriting topic link."""
        rewriter = URLRewriter("https://meta.discourse.org")

        topic_link = rewriter.rewrite_topic_link(123, "how-to-install")

        # Should match PLAN.md structure
        assert "how-to-install" in topic_link
        assert "123" in topic_link
        assert ".html" in topic_link

    def test_rewrite_category_link(self):
        """Test rewriting category link."""
        rewriter = URLRewriter("https://meta.discourse.org")

        category_link = rewriter.rewrite_category_link(5, "meta")

        assert "meta" in category_link
        assert "categories" in category_link
        assert "index.html" in category_link


class TestQueryParamNormalization:
    """Tests for query-param normalization (emoji ?v= mismatch fix)."""

    def test_find_asset_by_url_prefix_exact_match(self, tmp_path):
        """Test find_asset_by_url_prefix returns path for URL with query params."""
        from chronicon.storage.database import ArchiveDatabase

        db = ArchiveDatabase(tmp_path / "test.db")

        # Register asset with ?v=15 query param
        db.register_asset(
            "https://emoji.discourse-cdn.com/twitter/heart.png?v=15",
            "archives/assets/emoji/heart.png",
            "image/png",
        )

        # Look up by base URL (no query param)
        result = db.find_asset_by_url_prefix(
            "https://emoji.discourse-cdn.com/twitter/heart.png"
        )
        assert result == "archives/assets/emoji/heart.png"

        db.close()

    def test_find_asset_by_url_prefix_no_match(self, tmp_path):
        """Test find_asset_by_url_prefix returns None for unknown URL."""
        from chronicon.storage.database import ArchiveDatabase

        db = ArchiveDatabase(tmp_path / "test.db")

        # Register an unrelated asset
        db.register_asset(
            "https://example.com/other.png?v=1",
            "archives/assets/images/other.png",
            "image/png",
        )

        # Look up a different base URL
        result = db.find_asset_by_url_prefix(
            "https://emoji.discourse-cdn.com/twitter/heart.png"
        )
        assert result is None

        db.close()

    def test_find_asset_by_url_prefix_no_false_positives(self, tmp_path):
        """Test that prefix matching doesn't produce false positives."""
        from chronicon.storage.database import ArchiveDatabase

        db = ArchiveDatabase(tmp_path / "test.db")

        # Register asset with similar but different base path
        db.register_asset(
            "https://cdn.example.com/heart_extra.png?v=5",
            "archives/assets/images/heart_extra.png",
            "image/png",
        )

        # Query with a prefix that should NOT match
        result = db.find_asset_by_url_prefix("https://cdn.example.com/heart.png")
        assert result is None

        db.close()

    def test_rewriter_falls_back_to_query_stripped_url(self, tmp_path):
        """Test rewrite_with_full_resolution_links falls back to query-stripped URL."""
        from chronicon.storage.database import ArchiveDatabase

        db = ArchiveDatabase(tmp_path / "test.db")

        # Asset registered with ?v=15
        db.register_asset(
            "https://emoji.discourse-cdn.com/twitter/smile.png?v=15",
            "archives/assets/emoji/smile.png",
            "image/png",
        )

        # HTML references the same emoji with ?v=9
        html = (
            '<img src="https://emoji.discourse-cdn.com/twitter/smile.png?v=9"'
            ' class="emoji" alt=":smile:">'
        )

        processor = HTMLProcessor()
        result = processor.rewrite_with_full_resolution_links(
            html, topic_id=42, db=db, page_depth=2
        )

        # Should be rewritten to local path despite ?v= mismatch
        assert "../../assets/emoji/smile.png" in result
        assert "emoji.discourse-cdn.com" not in result

        db.close()

    def test_srcset_rewriter_falls_back_to_query_stripped_url(self, tmp_path):
        """Test _rewrite_srcset_value falls back to query-stripped URL."""
        from chronicon.storage.database import ArchiveDatabase

        db = ArchiveDatabase(tmp_path / "test.db")

        # Asset registered with ?v=15
        db.register_asset(
            "https://emoji.discourse-cdn.com/twitter/heart.png?v=15",
            "archives/assets/emoji/heart.png",
            "image/png",
        )

        processor = HTMLProcessor()
        # srcset entry references the same asset with ?v=9
        srcset = "https://emoji.discourse-cdn.com/twitter/heart.png?v=9 20w"

        result = processor._rewrite_srcset_value(srcset, {}, db, "../../")

        assert "../../assets/emoji/heart.png" in result
        assert "emoji.discourse-cdn.com" not in result

        db.close()

    def test_rewriter_integration_with_query_param_mismatch(self, tmp_path):
        """Integration test: full HTML with emoji query-param mismatch."""
        from chronicon.storage.database import ArchiveDatabase

        db = ArchiveDatabase(tmp_path / "test.db")

        # Register several emoji with ?v=15
        db.register_asset(
            "https://emoji.discourse-cdn.com/twitter/+1.png?v=15",
            "archives/assets/emoji/plus1.png",
            "image/png",
        )
        db.register_asset(
            "https://emoji.discourse-cdn.com/twitter/heart.png?v=15",
            "archives/assets/emoji/heart.png",
            "image/png",
        )
        # Also register a normal image (no query param issue)
        db.register_asset(
            "https://example.com/photo.jpg",
            "archives/assets/images/42/photo.jpg",
            "image/jpeg",
        )

        html = """
        <div class="post">
            <p>Great <img src="https://emoji.discourse-cdn.com/twitter/+1.png?v=9"
                class="emoji" alt=":+1:"></p>
            <p>Love <img src="https://emoji.discourse-cdn.com/twitter/heart.png?v=9"
                class="emoji" alt=":heart:"></p>
            <img src="https://example.com/photo.jpg" alt="photo">
        </div>
        """

        processor = HTMLProcessor()
        result = processor.rewrite_with_full_resolution_links(
            html, topic_id=42, db=db, page_depth=2
        )

        # Both emoji should be rewritten despite ?v= mismatch
        assert "../../assets/emoji/plus1.png" in result
        assert "../../assets/emoji/heart.png" in result
        # Normal image should also be rewritten
        assert "../../assets/images/42/photo.jpg" in result
        # No external URLs should remain
        assert "emoji.discourse-cdn.com" not in result
        assert "example.com" not in result

        db.close()


class TestNearestVariantSrcset:
    """Tests for nearest-variant srcset rewriting (zero additional downloads)."""

    def _make_mock_db(self, topic_assets, global_assets=None):
        """Create a mock DB with topic-scoped and global asset lookups."""
        mock_db = Mock()
        mock_db.get_assets_for_topic.return_value = topic_assets
        if global_assets is None:
            global_assets = {}
        mock_db.get_asset_path.side_effect = lambda url: global_assets.get(url)
        mock_db.find_asset_by_url_prefix.return_value = None
        return mock_db

    def test_unresolved_entries_map_to_nearest_resolved(self):
        """Test that unresolved srcset entries map to the nearest resolved variant."""
        processor = HTMLProcessor()

        # Only 690w and 1380w are downloaded
        asset_map = {
            "https://cdn.example.com/img_690w.webp": (
                "archives/assets/images/42/img_690w.webp"
            ),
            "https://cdn.example.com/img_1380w.webp": (
                "archives/assets/images/42/img_1380w.webp"
            ),
        }
        mock_db = self._make_mock_db([])

        srcset = (
            "https://cdn.example.com/img_100w.webp 100w, "
            "https://cdn.example.com/img_200w.webp 200w, "
            "https://cdn.example.com/img_690w.webp 690w, "
            "https://cdn.example.com/img_1380w.webp 1380w"
        )

        result = processor._rewrite_srcset_value(srcset, asset_map, mock_db, "../../")

        # 690w and 1380w should be rewritten to local paths
        assert "../../assets/images/42/img_690w.webp 690w" in result
        assert "../../assets/images/42/img_1380w.webp 1380w" in result
        # 100w and 200w should map to nearest (690w), not remain external
        assert "cdn.example.com" not in result
        # All entries should have local paths
        entries = [e.strip() for e in result.split(",")]
        for entry in entries:
            assert entry.startswith("../../assets/"), f"Entry still external: {entry}"

    def test_all_unresolved_keeps_originals(self):
        """Test that when no variants are resolved, originals are kept."""
        processor = HTMLProcessor()

        mock_db = self._make_mock_db([])

        srcset = (
            "https://cdn.example.com/img_100w.webp 100w, "
            "https://cdn.example.com/img_200w.webp 200w"
        )

        result = processor._rewrite_srcset_value(srcset, {}, mock_db, "../../")

        # All entries should remain as external URLs
        assert "https://cdn.example.com/img_100w.webp 100w" in result
        assert "https://cdn.example.com/img_200w.webp 200w" in result

    def test_mixed_resolved_unresolved(self):
        """Test mixed resolved/unresolved with correct nearest mapping."""
        processor = HTMLProcessor()

        asset_map = {
            "https://cdn.example.com/img_500w.webp": (
                "archives/assets/images/42/img_500w.webp"
            ),
            "https://cdn.example.com/img_2000w.webp": (
                "archives/assets/images/42/img_2000w.webp"
            ),
        }
        mock_db = self._make_mock_db([])

        srcset = (
            "https://cdn.example.com/img_100w.webp 100w, "
            "https://cdn.example.com/img_500w.webp 500w, "
            "https://cdn.example.com/img_1024w.webp 1024w, "
            "https://cdn.example.com/img_2000w.webp 2000w"
        )

        result = processor._rewrite_srcset_value(srcset, asset_map, mock_db, "../../")

        # All entries should be local
        assert "cdn.example.com" not in result
        entries = [e.strip() for e in result.split(",")]
        for entry in entries:
            assert entry.startswith("../../assets/"), f"Entry still external: {entry}"

    def test_width_based_proximity_selection(self):
        """Test that width proximity correctly selects the nearest variant."""
        processor = HTMLProcessor()

        asset_map = {
            "https://cdn.example.com/img_400w.webp": (
                "archives/assets/images/42/img_400w.webp"
            ),
            "https://cdn.example.com/img_1200w.webp": (
                "archives/assets/images/42/img_1200w.webp"
            ),
        }
        mock_db = self._make_mock_db([])

        # 800w is exactly between 400w and 1200w (|800-400|=400, |800-1200|=400)
        # Either is acceptable; test that it picks one of them
        srcset = (
            "https://cdn.example.com/img_800w.webp 800w, "
            "https://cdn.example.com/img_400w.webp 400w, "
            "https://cdn.example.com/img_1200w.webp 1200w"
        )

        result = processor._rewrite_srcset_value(srcset, asset_map, mock_db, "../../")

        # No external URLs should remain
        assert "cdn.example.com" not in result
        # The 800w entry should map to either 400w or 1200w local path
        entries = [e.strip() for e in result.split(",")]
        entry_800w = [e for e in entries if "800w" in e][0]
        assert (
            "../../assets/images/42/img_400w.webp" in entry_800w
            or "../../assets/images/42/img_1200w.webp" in entry_800w
        )

    def test_nearest_variant_in_full_html(self):
        """Integration: nearest-variant srcset with full HTML rewriting."""
        processor = HTMLProcessor()

        topic_assets = [
            {
                "url": "https://cdn.example.com/img_690w.webp",
                "local_path": "archives/assets/images/42/img_690w.webp",
            },
            {
                "url": "https://cdn.example.com/img_1380w.webp",
                "local_path": "archives/assets/images/42/img_1380w.webp",
            },
        ]
        mock_db = self._make_mock_db(topic_assets)

        html = """
        <picture>
            <source srcset="https://cdn.example.com/img_100w.webp 100w,
                https://cdn.example.com/img_200w.webp 200w,
                https://cdn.example.com/img_690w.webp 690w,
                https://cdn.example.com/img_1380w.webp 1380w">
            <img src="https://cdn.example.com/img_690w.webp" alt="photo">
        </picture>
        """

        result = processor.rewrite_with_full_resolution_links(
            html, topic_id=42, db=mock_db, page_depth=2
        )

        # No external URLs should remain in srcset
        assert "cdn.example.com" not in result

    def test_no_width_descriptor_entries_kept(self):
        """Test that entries without width descriptors (e.g., 2x) are not
        affected by nearest-variant logic."""
        processor = HTMLProcessor()

        asset_map = {
            "https://cdn.example.com/img.webp": ("archives/assets/images/42/img.webp"),
        }
        mock_db = self._make_mock_db([])

        # 2x descriptor, not a width descriptor
        srcset = (
            "https://cdn.example.com/img.webp 1x, "
            "https://cdn.example.com/img_2x.webp 2x"
        )

        result = processor._rewrite_srcset_value(srcset, asset_map, mock_db, "../../")

        # 1x entry should be rewritten (exact match)
        assert "../../assets/images/42/img.webp" in result
        # 2x entry should remain external (no width, can't do nearest)
        assert "https://cdn.example.com/img_2x.webp 2x" in result
