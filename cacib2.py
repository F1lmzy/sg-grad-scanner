#!/usr/bin/env python3
import re
from playwright.sync_api import sync_playwright
CHROME = "/home/kavin/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell"
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, executable_path=CHROME)
    ctx = b.new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36", viewport={"width":1366,"height":1000})
    pg = ctx.new_page()
    try:
        pg.goto("https://jobs.ca-cib.com/Pages/Offre/ListeOffre.aspx?mode=list&lcid=2057", wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(9000)
        # try country facet -> Singapore via URL param
        pg.goto("https://jobs.ca-cib.com/Pages/Offre/ListeOffre.aspx?mode=list&lcid=2057&facet_Country=169", wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(9000)
        txt = pg.inner_text("body")
        txt = re.sub(r"\n{3,}", "\n\n", txt)
        print(txt[:14000])
    finally:
        b.close()