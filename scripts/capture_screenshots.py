#!/usr/bin/env python3
# ABOUTME: Script to capture screenshots of the example archive using Playwright
# ABOUTME: Takes screenshots of HTML exports for documentation purposes

import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright


def take_screenshots():
    """Take screenshots of the HTML export."""

    # Set up paths
    base_dir = Path(__file__).resolve().parent.parent
    html_dir = base_dir / "archives" / "html"
    screenshots_dir = base_dir / "docs" / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    # Set PLAYWRIGHT_BROWSERS_PATH
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(Path.home() / ".playwright")

    print("Starting browser and taking screenshots...\n")

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch()

        # Screenshot 1: Homepage/Index (desktop)
        print("📸 Taking screenshot 1/6: HTML index page...")
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"file://{html_dir}/index.html")
        page.wait_for_timeout(1000)
        page.screenshot(path=screenshots_dir / "01-html-index.png", full_page=False)
        page.close()
        print("   ✓ Saved: 01-html-index.png")

        # Screenshot 2: Topic with rich content (Discourse Mermaid)
        print("📸 Taking screenshot 2/6: Topic page with content...")
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(f"file://{html_dir}/t/discourse-mermaid/218242.html")
        page.wait_for_timeout(1000)
        page.screenshot(path=screenshots_dir / "02-html-topic.png", full_page=False)
        page.close()
        print("   ✓ Saved: 02-html-topic.png")

        # Screenshot 3: Topic with many replies (Formatting toolbar)
        print("📸 Taking screenshot 3/6: Topic with multiple replies...")
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(f"file://{html_dir}/t/formatting-toolbar/40649.html")
        page.wait_for_timeout(1000)
        page.screenshot(
            path=screenshots_dir / "03-html-topic-replies.png", full_page=False
        )
        page.close()
        print("   ✓ Saved: 03-html-topic-replies.png")

        # Screenshot 4: Search page
        print("📸 Taking screenshot 4/6: Search functionality...")
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"file://{html_dir}/search.html")
        page.wait_for_timeout(1000)
        page.screenshot(path=screenshots_dir / "04-html-search.png", full_page=False)
        page.close()
        print("   ✓ Saved: 04-html-search.png")

        # Screenshot 5: Latest topics page
        print("📸 Taking screenshot 5/6: Latest topics listing...")
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"file://{html_dir}/latest/index.html")
        page.wait_for_timeout(1000)
        page.screenshot(path=screenshots_dir / "05-html-latest.png", full_page=False)
        page.close()
        print("   ✓ Saved: 05-html-latest.png")

        # Screenshot 6: Mobile view
        print("📸 Taking screenshot 6/6: Mobile responsive view...")
        page = browser.new_page(viewport={"width": 375, "height": 667})
        page.goto(f"file://{html_dir}/index.html")
        page.wait_for_timeout(1000)
        page.screenshot(path=screenshots_dir / "06-html-mobile.png", full_page=False)
        page.close()
        print("   ✓ Saved: 06-html-mobile.png")

        browser.close()

    print(f"\n✅ All screenshots captured successfully!")
    print(f"📁 Location: {screenshots_dir}")
    print(f"\nScreenshots:")
    for img in sorted(screenshots_dir.glob("*.png")):
        size_kb = img.stat().st_size / 1024
        print(f"   - {img.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    take_screenshots()
