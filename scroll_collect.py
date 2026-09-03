#!/usr/bin/env python3
import sys, re
from playwright.sync_api import sync_playwright

url = sys.argv[1]
n_scrolls = int(sys.argv[2]) if len(sys.argv) > 2 else 12
key = sys.argv[3] if len(sys.argv) > 3 else None
CHROME = "/home/kavin/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell"

titles = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, executable_path=CHROME)
    ctx = b.new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36", viewport={"width": 1366, "height": 900})
    pg = ctx.new_page()
    try:
        pg.goto(url, wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(7000)
        for i in range(n_scrolls):
            pg.mouse.wheel(0, 2500)
            pg.wait_for_timeout(1200)
        txt = pg.inner_text("body")
        for line in txt.splitlines():
            l = line.strip()
            if key and key.lower() in l.lower():
                titles.append(l)
    finally:
        b.close()
seen = []
for t in titles:
    if t not in seen:
        seen.append(t)
for t in seen:
    print(t)
print("=== TOTAL full text lines:", len(txt.splitlines()))