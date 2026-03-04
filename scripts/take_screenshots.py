#!/usr/bin/env python3
# ABOUTME: Script to capture screenshots of the example archive for documentation
# ABOUTME: Uses Playwright/Selenium or headless Chrome to capture HTML renders

import subprocess
import time
from pathlib import Path


def take_screenshot_chrome(url, output_path, width=1280, height=800, wait_time=2):
    """Take a screenshot using headless Chrome."""
    cmd = [
        "google-chrome",
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        f"--window-size={width},{height}",
        "--screenshot=" + str(output_path),
        url,
    ]

    print(f"Taking screenshot: {output_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"  ✓ Saved to {output_path}")
        return True
    else:
        print(f"  ✗ Failed: {result.stderr}")
        return False


def main():
    # Setup paths
    base_dir = Path(__file__).resolve().parent.parent
    html_dir = base_dir / "examples" / "meta-example" / "html"
    screenshots_dir = base_dir / "docs" / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    print("Taking screenshots of example archive...\n")

    # Screenshot 1: Homepage/Index
    take_screenshot_chrome(
        f"file://{html_dir}/index.html",
        screenshots_dir / "html-index.png",
        width=1280,
        height=900,
    )

    time.sleep(1)

    # Screenshot 2: A popular topic with good content
    # Discourse Mermaid topic
    take_screenshot_chrome(
        f"file://{html_dir}/t/discourse-mermaid/218242.html",
        screenshots_dir / "html-topic.png",
        width=1280,
        height=1200,
    )

    time.sleep(1)

    # Screenshot 3: Search page
    take_screenshot_chrome(
        f"file://{html_dir}/search.html",
        screenshots_dir / "html-search.png",
        width=1280,
        height=800,
    )

    time.sleep(1)

    # Screenshot 4: Topic with lots of replies (Formatting toolbar)
    take_screenshot_chrome(
        f"file://{html_dir}/t/formatting-toolbar/133823.html",
        screenshots_dir / "html-topic-replies.png",
        width=1280,
        height=1200,
    )

    time.sleep(1)

    # Screenshot 5: Mobile view (narrow width)
    take_screenshot_chrome(
        f"file://{html_dir}/index.html",
        screenshots_dir / "html-mobile.png",
        width=375,
        height=667,
    )

    print("\n✓ All screenshots captured!")
    print(f"Screenshots saved to: {screenshots_dir}")


if __name__ == "__main__":
    main()
