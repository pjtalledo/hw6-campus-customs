"""Problem 5 follow-up: render suspicious HTML documents in a real headless
Chromium (via Playwright) to verify what a human would actually SEE, and
compare that against what tools.py's read_document() extracts.

Safety: file:// load of static local HTML only. No scripts are executed
beyond what Chromium's own page load does for this static content (the one
analytics <script> tag in p11 just pushes to a local array; nothing is
clicked, no links are followed, no external network calls are made).
"""

import sys
from pathlib import Path

sys.path.insert(0, ".")
from playwright.sync_api import sync_playwright
import tools

DOCS = [
    "p02_elmcity_quote.html",
    "p03_ivyprint_catalog.html",
    "p04_harborstitch_quote.html",
    "p11_yorkst_quote.html",
]

SRC_DIR = Path("data/practice_docs")
OUT_DIR = Path("output/render_evidence")
OUT_DIR.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 900, "height": 1000})
    for doc in DOCS:
        path = (SRC_DIR / doc).resolve()
        page.goto(path.as_uri())
        visible_text = page.inner_text("body")
        screenshot_path = OUT_DIR / f"{doc}.png"
        page.screenshot(path=str(screenshot_path), full_page=True)

        extracted_text = tools.read_document(str(path))

        print(f"=== {doc} ===")
        print("--- BROWSER-VISIBLE TEXT (page.inner_text) ---")
        print(visible_text)
        print("--- AGENT-EXTRACTED TEXT (tools.read_document) ---")
        print(extracted_text)
        print(f"--- screenshot saved: {screenshot_path} ---")
        print()
    browser.close()
