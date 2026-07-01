"""One-off script to capture a real Swagger UI screenshot of api.py.
Not part of the shipped project - run manually, then delete/ignore.

Usage: python scripts/capture_api_screenshot.py
(requires uvicorn api:app already running on port 8503, and playwright installed)
"""

import time

from playwright.sync_api import sync_playwright

URL = "http://localhost:8503/docs"
OUT_DIR = "demo"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 1000})
        page.goto(URL)
        page.wait_for_selector("text=POST", timeout=15000)
        time.sleep(1)

        # Expand the /chat endpoint
        page.locator("text=/chat").first.click()
        time.sleep(0.5)

        # Click "Try it out"
        page.locator("text=Try it out").first.click()
        time.sleep(0.3)

        # Fill in the request body with a real example
        body_editor = page.locator(".body-param__text").first
        body_editor.click()
        page.keyboard.press("Control+A")
        page.keyboard.type('{\n  "message": "where is order 1001?"\n}')
        time.sleep(0.3)

        # Execute the real request
        page.locator("text=Execute").first.click()
        page.wait_for_selector("text=Response body", timeout=15000)
        time.sleep(1)

        # Shot 1: top of the expanded endpoint (path, summary, schema)
        page.locator("text=Chat").first.scroll_into_view_if_needed()
        time.sleep(0.3)
        page.screenshot(path=f"{OUT_DIR}/04_api_docs_endpoint.png")

        # Shot 2: request + real response together
        page.locator("text=Server response").first.scroll_into_view_if_needed()
        time.sleep(0.5)
        page.screenshot(path=f"{OUT_DIR}/04b_api_docs_response.png")

        browser.close()
        print("Saved demo/04_api_docs.png")


if __name__ == "__main__":
    main()
