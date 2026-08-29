#!/usr/bin/env python3
"""Render a JS-heavy page with Playwright and dump visible text (+ optional links).

Usage: python3 render.py <url> [wait_ms] [--links]
"""
import sys, re
from playwright.sync_api import sync_playwright

url = sys.argv[1]
wait_ms = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 6000
show_links = "--links" in sys.argv

CHROME = "/home/kavin/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, executable_path=CHROME)
    ctx = b.new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36", viewport={"width": 1366, "height": 900})
    pg = ctx.new_page()
    try:
        pg.goto(url, wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(wait_ms)
        # try to dismiss cookie banners
        for sel in ["text=Accept", "text=Accept all", "text=I Accept", "#onetrust-accept-btn-handler", "button:has-text('Agree')"]:
            try:
                el = pg.locator(sel).first
                if el.is_visible(timeout=800):
                    el.click()
                    pg.wait_for_timeout(1000)
                    break
            except Exception:
                pass
        txt = pg.inner_text("body")
        txt = re.sub(r"\n{3,}", "\n\n", txt)
        print(txt[:12000])
        if show_links:
            print("\n===== LINKS =====")
            hrefs = pg.eval_on_selector_all("a[href]", "els => els.map(e => e.getAttribute('href') + ' :: ' + (e.innerText||'').trim().replace(/\\s+/g,' ').slice(0,110))")
            seen = set()
            for h in hrefs:
                if h not in seen:
                    seen.add(h)
                    print(h)
    finally:
        b.close()
