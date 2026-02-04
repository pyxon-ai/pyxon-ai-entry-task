"""Automated demo runner and screen recording using Playwright.

This script will:
1) Start the demo server on a non-conflicting port (default 8001)
2) Wait for /api/health to be ready
3) Open the demo UI
4) Upload sample English and Arabic documents
5) Ask an English and Arabic question
6) Run the benchmark suite from the UI
7) Save a browser-recorded video to recordings/demo.webm
"""

import os
import sys
import time
import subprocess
from pathlib import Path

import httpx

# Ensure project root on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))


def wait_for_health(base_url: str, timeout: float = 60.0) -> None:
    start = time.time()
    last_err = None
    while time.time() - start < timeout:
        try:
            r = httpx.get(f"{base_url}/api/health", timeout=5.0)
            if r.status_code == 200:
                return
        except Exception as e:
            last_err = e
        time.sleep(1.0)
    raise RuntimeError(f"Server not ready at {base_url}/api/health: {last_err}")


def main():
    project_root = Path(__file__).parent.parent
    demo_port = int(os.environ.get("DEMO_PORT", "8001"))
    base_url = f"http://localhost:{demo_port}"

    # Install Playwright browser if needed
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)
    except Exception:
        pass

    # Start the demo server
    env = os.environ.copy()
    env["DEMO_PORT"] = str(demo_port)
    server_proc = subprocess.Popen([sys.executable, "scripts/run_demo.py"], cwd=str(project_root), env=env)

    try:
        # Wait for health
        wait_for_health(base_url, timeout=90.0)

        # Playwright automation
        from playwright.sync_api import sync_playwright

        recordings_dir = project_root / "recordings"
        recordings_dir.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(record_video_dir=str(recordings_dir))
            page = context.new_page()

            # Go to demo UI
            page.goto(f"{base_url}/demo")
            page.wait_for_selector("text=System Statistics", timeout=20000)

            # Upload English document
            english = project_root / "sample_documents" / "english_sample.txt"
            if english.exists():
                page.set_input_files("#fileInput", str(english))
                page.click("#uploadBtn")
                page.wait_for_selector("#uploadResult .success", timeout=60000)

            # Upload Arabic document
            arabic = project_root / "sample_documents" / "arabic_with_diacritics.txt"
            if arabic.exists():
                page.set_input_files("#fileInput", str(arabic))
                page.click("#uploadBtn")
                page.wait_for_selector("#uploadResult .success", timeout=60000)

            # Ask an English question
            page.fill("#queryInput", "What is the main topic of the document?")
            page.click("#queryBtn")
            page.wait_for_selector("#queryResult .success", timeout=60000)

            # Ask an Arabic question
            page.fill("#queryInput", "ما هو المحتوى الرئيسي في هذا المستند؟")
            page.click("#queryBtn")
            page.wait_for_selector("#queryResult .success", timeout=60000)

            # Run Benchmarks
            page.click("#benchmarkBtn")
            page.wait_for_selector("text=Benchmark Results", timeout=600000)

            # Close and save video
            page.close()
            context.close()
            browser.close()

        # Find the most recent video file and rename it to demo.webm
        video_files = sorted(recordings_dir.glob("**/*.webm"), key=lambda p: p.stat().st_mtime, reverse=True)
        if video_files:
            (recordings_dir / "demo.webm").write_bytes(video_files[0].read_bytes())
            print(f"Demo video saved to {recordings_dir / 'demo.webm'}")
        else:
            print("Warning: no video file recorded.")

    finally:
        # Terminate the server
        try:
            server_proc.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    main()
