#!/usr/bin/env python3
import sys
from playwright.sync_api import sync_playwright
CHROME = "/home/kavin/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell"
url = sys.argv[1]
maxpages = int(sys.argv[2]) if len(sys.argv) > 2 else 16
seen = {}
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, executable_path=CHROME)
    ctx = b.new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36", viewport={"width":1366,"height":1000})
    pg = ctx.new_page()
    try:
        pg.goto(url, wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(7000)
        for _ in range(maxpages):
            # collect visible job links+text
            items = pg.eval_on_selector_all("a[href]", "els => els.map(e => ({h: e.getAttribute('href'), t: (e.innerText||'').trim().replace(/\\s+/g,' ').slice(0,100)}))")
            added = 0
            for it in items:
                if it['t'] and '/' in it['h']:
                    k = it['t']
                    if k not in seen:
                        seen[k] = it['h']
                        added += 1
            # click next page
            nxt = pg.locator("a:has-text('Next'), button:has-text('Next'), [aria-label*='next' i]").first
            try:
                if nxt.is_visible(timeout=1500):
                    nxt.click(); pg.wait_for_timeout(4000)
                else:
                    break
            except Exception:
                break
    finally:
        b.close()
for t, h in seen.items():
    print(f"{t}\n    {h}")
print("=== count:", len(seen))