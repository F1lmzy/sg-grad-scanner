#!/usr/bin/env python3
"""Minimal Bing SERP scraper fallback (web_search backend is intermittent).

Usage: python3 bing_search.py "<query>" [num_results]
"""
import re, sys, urllib.parse, urllib.request

query = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
url = "https://www.bing.com/search?q=" + urllib.parse.quote(query) + "&count=15"
req = urllib.request.Request(url, headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
})
html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
items = re.findall(r'<h2[^>]*><a href="([^"]+)"[^>]*>(.*?)</a></h2>', html)
seen = set()
count = 0
for u, t in items:
    t = re.sub(r"<[^>]+>", "", t)
    if u.startswith("http") and "bing.com" not in u and u not in seen:
        seen.add(u)
        print(f"{u} :: {t}")
        count += 1
        if count >= n:
            break
if count == 0:
    print("(no organic results parsed)")
