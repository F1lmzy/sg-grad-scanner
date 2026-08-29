#!/usr/bin/env python3
"""Fetch job details for candidate IDs via LinkedIn guest jobPosting API."""
import json, re, subprocess, sys, time

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

def fetch(jid):
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{jid}"
    r = subprocess.run(["curl", "-s", "-L", "-A", UA, url], capture_output=True, text=True, timeout=45)
    return r.stdout

def clean(s):
    return re.sub(r'\s+', ' ', s or '').strip()

def parse(html, jid):
    title = clean(re.search(r'<h2 class="top-card-layout__title[^"]*"[^>]*>(.*?)</h2>', html, re.S).group(1)) if re.search(r'<h2 class="top-card-layout__title[^"]*"[^>]*>(.*?)</h2>', html, re.S) else ""
    org = clean(re.search(r'class="topcard__org-name-link[^"]*"[^>]*>(.*?)</a>', html, re.S).group(1)) if re.search(r'class="topcard__org-name-link[^"]*"[^>]*>(.*?)</a>', html, re.S) else ""
    loc = clean(re.search(r'class="topcard__flavor--bullet[^"]*"[^>]*>(.*?)</span>', html, re.S).group(1)) if re.search(r'class="topcard__flavor--bullet[^"]*"[^>]*>(.*?)</span>', html, re.S) else ""
    # posted date
    date = clean(re.search(r'class="posted-time-ago__text[^"]*"[^>]*>(.*?)</span>', html, re.S).group(1)) if re.search(r'class="posted-time-ago__text[^"]*"[^>]*>(.*?)</span>', html, re.S) else ""
    desc = clean(re.search(r'<div class="show-more-less-html__markup[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</section>', html, re.S).group(1)) if re.search(r'<div class="show-more-less-html__markup[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</section>', html, re.S) else ""
    if not desc:
        m = re.search(r'<div class="show-more-less-html__markup[^"]*"[^>]*>(.*?)</div>', html, re.S)
        desc = clean(m.group(1)) if m else ""
    desc = re.sub(r'<[^>]+>', ' ', desc)
    desc = clean(desc)
    return {"id": jid, "title": title, "org": org, "loc": loc, "date": date, "desc": desc[:1500]}

cands = json.load(open("/home/kavin/jobscan/candidates.json"))
tracked = {l.strip() for l in open("/home/kavin/jobscan/tracked_ids.txt") if l.strip()}
cands = {k: v for k, v in cands.items() if k not in tracked}
print(f"After improved dedup: {len(cands)} candidates", file=sys.stderr)

out = {}
if __import__("os").path.exists("/home/kavin/jobscan/details.json"):
    out = json.load(open("/home/kavin/jobscan/details.json"))
for i, jid in enumerate(sorted(cands, key=lambda x: int(x))):
    if jid in out:
        continue
    try:
        html = fetch(jid)
    except Exception as e:
        print(f"ERR {jid}: {e}", file=sys.stderr)
        continue
    info = parse(html, jid)
    out[jid] = info
    if i % 25 == 0:
        print(f"progress {i}/{len(cands)}", file=sys.stderr)
    time.sleep(0.5)

json.dump(out, open("/home/kavin/jobscan/details.json", "w"), indent=1)
print(f"Fetched details for {len(out)} jobs", file=sys.stderr)
