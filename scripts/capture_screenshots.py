import time
import subprocess
import os
import signal
from pathlib import Path
from playwright.sync_api import sync_playwright

root_dir = Path(__file__).resolve().parent.parent
screenshots_dir = root_dir / "docs" / "screenshots"
screenshots_dir.mkdir(parents=True, exist_ok=True)

# 1. Start backend process
backend_proc = subprocess.Popen(
    [str(root_dir / ".venv" / "Scripts" / "python.exe"), "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8765"],
    cwd=str(root_dir)
)

# 2. Start frontend process
frontend_proc = subprocess.Popen(
    ["npm.cmd", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
    cwd=str(root_dir / "apps" / "web")
)

print("Started backend (PID:", backend_proc.pid, ") and frontend (PID:", frontend_proc.pid, ")")
time.sleep(4)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        # 1. Dashboard Overview
        page.goto("http://127.0.0.1:5173", wait_until="networkidle")
        time.sleep(1.5)
        page.screenshot(path=str(screenshots_dir / "overview.png"))
        print("Captured overview.png")

        # 2. Knowledge Vault (Notes)
        page.locator("aside button:has-text('Knowledge Vault')").click()
        time.sleep(0.8)
        # Click on first note to display details
        page.locator(".cursor-pointer").first.click()
        time.sleep(0.5)
        page.screenshot(path=str(screenshots_dir / "vault.png"))
        print("Captured vault.png")

        # 3. Documents
        page.locator("aside button:has-text('Documents')").click()
        time.sleep(0.8)
        # Inspect first document
        inspect_btn = page.locator("button:has-text('Inspect')").first
        if inspect_btn.is_visible():
            inspect_btn.click()
            time.sleep(0.5)
        page.screenshot(path=str(screenshots_dir / "documents.png"))
        print("Captured documents.png")

        # 4. Semantic Search
        page.locator("aside button:has-text('Semantic Search')").click()
        time.sleep(0.8)
        page.fill("input[placeholder*='Search documents']", "SQLite FTS5 performance")
        page.get_by_role("button", name="Search", exact=True).click()
        time.sleep(1.0)
        page.screenshot(path=str(screenshots_dir / "search.png"))
        print("Captured search.png")

        # 5. Knowledge Graph
        page.locator("aside button:has-text('Knowledge Graph')").click()
        time.sleep(1.5)
        page.screenshot(path=str(screenshots_dir / "graph.png"))
        print("Captured graph.png")

        # 6. Entities & Relations
        page.locator("aside button:has-text('Entities & Relations')").click()
        time.sleep(0.8)
        page.screenshot(path=str(screenshots_dir / "entities.png"))
        print("Captured entities.png")

        # 7. Knowledge Assistant
        page.locator("aside button:has-text('Knowledge Assistant')").click()
        time.sleep(0.8)
        page.fill("input[placeholder*='e.g. How to optimize']", "How does SQLite WAL mode optimize writes?")
        page.locator("button:has-text('Synthesize')").click()
        time.sleep(1.5)
        page.screenshot(path=str(screenshots_dir / "assistant.png"))
        print("Captured assistant.png")

        # 8. System & Export
        page.locator("aside button:has-text('System & Export')").click()
        time.sleep(0.8)
        page.screenshot(path=str(screenshots_dir / "settings.png"))
        print("Captured settings.png")

        browser.close()

finally:
    print("Terminating test servers...")
    backend_proc.terminate()
    frontend_proc.terminate()
    try:
        backend_proc.wait(timeout=3)
        frontend_proc.wait(timeout=3)
    except Exception:
        backend_proc.kill()
        frontend_proc.kill()
    print("Done capturing screenshots.")
