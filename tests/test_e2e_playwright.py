import os
import time
import subprocess
import pytest
from pathlib import Path
from playwright.sync_api import sync_playwright

root_dir = Path(__file__).resolve().parent.parent

@pytest.fixture(scope="module")
def servers():
    backend = subprocess.Popen(
        [str(root_dir / ".venv" / "Scripts" / "python.exe"), "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8765"],
        cwd=str(root_dir)
    )
    # Frontend dev server pointing to test backend
    frontend = subprocess.Popen(
        ["npm.cmd", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5175"],
        cwd=str(root_dir / "apps" / "web")
    )
    time.sleep(3)
    yield "http://127.0.0.1:5175"
    backend.terminate()
    frontend.terminate()
    backend.kill()
    frontend.kill()

def test_full_playwright_e2e(servers):
    import os
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(servers, wait_until="networkidle")

        # 1. Dashboard loads
        assert page.locator("h2:has-text('Operations Dashboard')").is_visible()

        # 2. Vault: Create Note
        page.locator("aside button:has-text('Knowledge Vault')").click()
        time.sleep(0.5)
        page.locator("button:has-text('New')").click()
        page.fill("input[placeholder='Note Title...']", "E2E Playwright Verification Note")
        page.fill("textarea[placeholder*='Write markdown here']", "Testing automated end-to-end flow with #e2e and [[SQLite FTS5]].")
        page.locator("button:has-text('Save Note')").click()
        time.sleep(0.8)
        assert page.locator("span:has-text('E2E Playwright Verification Note')").first.is_visible()

        # 3. Search: Find the note
        page.locator("aside button:has-text('Semantic Search')").click()
        time.sleep(0.5)
        page.fill("input[placeholder*='Search documents']", "E2E Playwright")
        page.get_by_role("button", name="Search", exact=True).click()
        time.sleep(0.8)
        assert page.locator("h4:has-text('E2E Playwright Verification Note')").first.is_visible()

        # 4. Graph: Check rendering
        page.locator("aside button:has-text('Knowledge Graph')").click()
        time.sleep(0.8)
        assert page.locator("canvas").is_visible()

        # 5. Assistant: Offline query synthesis
        page.locator("aside button:has-text('Knowledge Assistant')").click()
        time.sleep(0.5)
        page.fill("input[placeholder*='e.g. How to optimize']", "What is E2E Playwright Verification Note?")
        page.locator("button:has-text('Synthesize')").click()
        time.sleep(1.0)
        assert page.locator("span:has-text('Synthesized Answer')").is_visible()

        browser.close()
