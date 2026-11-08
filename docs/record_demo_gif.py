"""Record docs/demo.gif from a running demo (python app.py first).

    python docs/record_demo_gif.py --url http://localhost:7860
"""
from __future__ import annotations

import argparse
import io
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "demo.gif"


def main(url: str) -> None:
    frames: list[tuple[Image.Image, int]] = []

    def snap(page, ms: int) -> None:
        img = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
        img.thumbnail((960, 960))
        frames.append((img, ms))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 860})
        page.goto(url)
        page.get_by_text("Loaded 4 sample documents").wait_for(timeout=60000)
        snap(page, 1800)

        # 1. parse the vocalized Arabic sample
        page.get_by_role("tab", name="1 · Parse documents").click()
        page.get_by_text("water_ar.txt").first.click()
        page.wait_for_timeout(800)
        page.get_by_role("button", name="Parse & index").click()
        page.get_by_text("Chunking strategy", exact=False).first.wait_for(timeout=60000)
        page.wait_for_timeout(800)
        snap(page, 3200)
        page.mouse.wheel(0, 650)
        page.wait_for_timeout(500)
        snap(page, 2600)
        page.mouse.wheel(0, -2000)

        # 2. search, diacritic-insensitive
        page.get_by_role("tab", name="2 · Search").click()
        box = page.get_by_label("Query")
        box.fill("الجفاف")
        box.press("Enter")
        page.locator(".chunk:visible").first.wait_for(timeout=30000)
        page.wait_for_timeout(600)
        snap(page, 2600)

        # 3. ask in Arabic, then English, then a metadata question routed to SQL
        page.get_by_role("tab", name="3 · Ask (RAG)").click()
        for q in ["من أين يأتي المطر؟", "Which forklift failed inspection?", "Which documents are Arabic?"]:
            qb = page.get_by_label("Question")
            qb.fill(q)
            snap(page, 900)
            page.get_by_role("button", name="Ask").click()
            page.wait_for_timeout(2500)
            snap(page, 3000)
        browser.close()

    imgs = [f.quantize(colors=128, method=Image.Quantize.MEDIANCUT) for f, _ in frames]
    imgs[0].save(OUT, save_all=True, append_images=imgs[1:], duration=[d for _, d in frames], loop=0, optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB, {len(imgs)} frames)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:7860")
    main(ap.parse_args().url)
