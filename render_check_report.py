from pathlib import Path
from playwright.sync_api import sync_playwright

path = Path("output/hw6_report.html").resolve()
with sync_playwright() as p:
    browser = p.chromium.launch()

    # Desktop width
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(path.as_uri())
    page.screenshot(path="output/hw6_report_desktop.png", full_page=True)
    print("desktop screenshot saved")
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.close()

    # Mobile width
    page2 = browser.new_page(viewport={"width": 390, "height": 844})
    page2.goto(path.as_uri())
    page2.screenshot(path="output/hw6_report_mobile.png", full_page=True)
    print("mobile screenshot saved")
    page2.close()

    browser.close()
print("console errors:", errors)
