#!/usr/bin/env python3
"""LinkedIn guest job search scraper for Singapore grad/entry-level FT roles."""
import json, re, subprocess, sys, time, urllib.parse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
BASE = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

KEYWORDS = [
    "graduate engineer", "graduate software engineer", "graduate program",
    "entry level engineer", "entry level software", "fresh graduate engineer",
    "fresh graduate software", "junior software engineer", "junior engineer",
    "associate engineer", "graduate analyst", "new graduate",
    "graduate developer", "junior developer", "assistant engineer",
    "graduate data scientist", "junior data scientist", "machine learning engineer",
    "data engineer", "embedded engineer", "firmware engineer", "robotics engineer",
    "automation engineer", "mechatronics engineer", "test engineer", "process engineer",
    "product engineer", "quality engineer", "equipment engineer", "graduate trainee",
    "quantitative researcher", "quantitative analyst", "quantitative developer",
    "junior trader", "graduate trader", "trading analyst", "risk analyst",
    "software engineer trainee", "engineer trainee", "site reliability engineer",
    "cloud engineer", "backend engineer", "frontend engineer", "full stack",
    "AI engineer", "research engineer", "research assistant", "data analyst",
    "design engineer", "systems engineer", "control engineer", "network engineer",
    "cybersecurity analyst", "electrical engineer", "electronics engineer",
    "IoT engineer", "DevOps engineer", "QA engineer", "SDET",
]

def fetch(keyword, start):
    qs = urllib.parse.urlencode({
        "keywords": keyword, "location": "Singapore",
        "f_TPR": "r604800", "start": start,
    })
    url = f"{BASE}?{qs}"
    r = subprocess.run(["curl", "-s", "-L", "-A", UA, url], capture_output=True, text=True, timeout=60)
    return r.stdout

def parse_ids(html):
    ids = set(re.findall(r'urn:li:jobPosting:(\d+)', html))
    return ids

seen = {}  # job_id -> (keyword, start)
for kw in KEYWORDS:
    for start in (0, 25):
        try:
            html = fetch(kw, start)
        except Exception as e:
            print(f"ERR {kw}@{start}: {e}", file=sys.stderr)
            continue
        ids = parse_ids(html)
        for jid in ids:
            if jid not in seen:
                seen[jid] = (kw, start)
        time.sleep(0.7)

tracked = set()
with open("/home/kavin/jobscan/tracked_ids.txt") as f:
    tracked = {l.strip() for l in f if l.strip()}

new_ids = [jid for jid in seen if jid not in tracked]
print(f"Total unique postings seen: {len(seen)}")
print(f"New (not in tracked {len(tracked)}): {len(new_ids)}")
with open("/home/kavin/jobscan/candidates.json", "w") as f:
    json.dump({jid: seen[jid] for jid in new_ids}, f, indent=1)
for jid in sorted(new_ids, key=lambda x: int(x)):
    print(jid, seen[jid])
