#!/usr/bin/env python3
import re
from playwright.sync_api import sync_playwright
CHROME = "/home/kavin/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell"
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, executable_path=CHROME)
    ctx = b.new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36", viewport={"width":1366,"height":900})
    pg = ctx.new_page()
    try:
        pg.goto("https://careers.ey.com/ey-global/en/", wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(6000)
        for sel in ["text=Accept All Cookies", "#cookie_accept_all_btn", "button:has-text('Accept All')"]:
            try:
                el = pg.locator(sel).first
                if el.is_visible(timeout=1500):
                    el.click(); pg.wait_for_timeout(3000); break
            except Exception:
                pass
        # click Job search
        try:
            pg.locator("a:has-text('Job search')").first.click(); pg.wait_for_timeout(8000)
        except Exception as e:
            print("nav err", e)
        # fill search
        try:
            inp = pg.locator("input[placeholder*='Search' i], #search-field, input[name='q']").first
            inp.fill("AI Solutions"); pg.wait_for_timeout(4000)
        except Exception:
            pass
        txt = pg.inner_text("body")
        txt = re.sub(r"\n{3,}", "\n\n", txt)
        print(txt[:14000])
    finally:
        b.close()