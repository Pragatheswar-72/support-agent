"""One-off script to capture real README screenshots of the running app.
Not part of the shipped project - run manually, then delete/ignore.

Usage: python scripts/capture_screenshots.py
(requires the Streamlit app already running at http://localhost:8501,
 and `pip install playwright && playwright install chromium`)
"""

import time

from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"
OUT_DIR = "demo"


def send_message(page, text: str) -> None:
    textarea = page.locator("textarea").first
    textarea.click()
    textarea.fill(text)
    textarea.press("Enter")


def wait_for_reply(page, timeout_s: int = 30) -> None:
    page.wait_for_selector("text=Thinking...", state="visible", timeout=timeout_s * 1000)
    page.wait_for_selector("text=Thinking...", state="detached", timeout=timeout_s * 1000)
    time.sleep(0.5)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1100, "height": 900})
        page.goto(URL)
        page.wait_for_selector("textarea", timeout=20000)
        time.sleep(1)

        # 1. Order lookup
        send_message(page, "Hi, where is my order 1004?")
        wait_for_reply(page)
        page.screenshot(path=f"{OUT_DIR}/01_order_lookup.png")

        # 2. Guardrail refusal (order 1002 is shipped, not delivered)
        send_message(page, "I'd like a refund for order 1002, it's the wrong item")
        wait_for_reply(page)
        page.screenshot(path=f"{OUT_DIR}/02_guardrail_refusal.png")

        # expand the newest agent trace, scroll it into view, then screenshot
        trace_toggle = page.locator("summary", has_text="Agent trace").last
        trace_toggle.click()
        time.sleep(0.3)
        trace_toggle.scroll_into_view_if_needed()
        time.sleep(0.3)
        page.screenshot(path=f"{OUT_DIR}/02b_guardrail_trace_expanded.png")

        # 3. FAQ + sidebar stats
        send_message(page, "What is your return policy?")
        wait_for_reply(page)
        time.sleep(2)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.5)
        page.screenshot(path=f"{OUT_DIR}/03_faq_and_sidebar.png")

        browser.close()
        print("Saved screenshots to demo/")


if __name__ == "__main__":
    main()
