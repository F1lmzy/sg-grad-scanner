#!/usr/bin/env python3
"""DuckDuckGo HTML fallback search. Usage: python3 ddg.py "<query>" [n]"""
import urllib.request, urllib.parse, re, sys
q = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
u = 'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(q)
req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36'})
h = urllib.request.urlopen(req, timeout=25).read().decode('utf-8', 'ignore')
count = 0
for r in re.findall(r'result__a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', h):
    t = re.sub(r'<[^>]+>', '', r[1])
    src = r[0].split('uddg=')[-1] if 'uddg=' in r[0] else r[0]
    print(src, '::', t)
    count += 1
    if count >= n:
        break
if count == 0:
    print('(no organic results parsed)')