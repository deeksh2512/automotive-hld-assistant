"""Capture screenshots of each page for visual review.

Development tool, not part of the application. Requires playwright and a running
UI: python scripts/screenshot.py [base_url] [output_dir]
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8501"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "screenshots")

PAGES = [
    ("home", ""),
    ("documents", "Documents"),
    ("analysis", "HLD_Analysis"),
    ("review", "Review_Queue"),
    ("audit", "Audit_Trail"),
]


def settle(page, timeout_ms: int = 120_000) -> None:
    """Streamlit streams its render over a websocket, so poll until it is idle."""
    page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=60_000)
    waited = 0
    idle = 0
    while waited < timeout_ms:
        running = page.query_selector("[data-testid='stStatusWidget']") is not None
        idle = 0 if running else idle + 1
        if idle >= 4:
            break
        page.wait_for_timeout(500)
        waited += 500
    page.wait_for_timeout(2000)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1100},
                                device_scale_factor=2)
        for name, slug in PAGES:
            page.goto(f"{BASE}/{slug}", wait_until="load")
            settle(page)
            target = OUT / f"{name}.png"
            page.screenshot(path=str(target), full_page=True)
            print(f"captured {target}")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
