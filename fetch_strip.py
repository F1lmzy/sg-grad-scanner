#!/usr/bin/env python3
"""Fetch a URL with browser UA and print stripped text (first N chars)."""
import re, sys, html, urllib.request

url = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Accept-Language': 'en-SG,en;q=0.9',
})
try:
    raw = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', errors='ignore')
except Exception as e:
    print(f'FETCH-ERROR: {e}')
    sys.exit(1)
txt = re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>|<noscript[\s\S]*?</noscript>', ' ', raw)
txt = re.sub(r'<[^>]+>', ' ', txt)
txt = html.unescape(re.sub(r'\s+', ' ', txt))
print(f'BYTES={len(raw)}')
print(txt[:limit])
