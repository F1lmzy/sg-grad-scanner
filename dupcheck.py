import json, re, glob

cands = json.load(open('/home/kavin/jobscan/candidates.json'))
det = json.load(open('/home/kavin/jobscan/details.json'))

# Load master list + scan text
master = ''
for f in ['/home/kavin/obsidian-vault/Master_List.md'] + glob.glob('/home/kavin/obsidian-vault/Scans/*.md'):
    master += open(f, encoding='utf-8', errors='ignore').read()

def norm(s):
    s = s.replace('&amp;','&')
    return s.strip().lower()

# Extract org->title pairs from master tables (rows in the graduate FT table: | Company | Role ...)
# Grab all "Company | Role" pairs in graduate table lines
known = set()
for line in master.splitlines():
    if line.strip().startswith('|'):
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) >= 3:
            known.add((norm(cells[0]), norm(cells[1])))

full_known_text = master.lower()

# For each candidate, mark duplicate if same org+title in known, or title text present
dup_org_title = []
for jid in cands:
    info = det.get(jid, {})
    org = norm(info.get('org',''))
    t = norm(info.get('title',''))
    if not t:
        continue
    hit = (org, t) in known
    # also check title+org subset
    if not hit and org:
        # substring match: same org and title token overlap significant
        pass
    if hit:
        dup_org_title.append((jid, info.get('org'), info.get('title')))

print("=== DUPLICATES (same org+title in master/scans) ===")
for jid, org, t in sorted(dup_org_title, key=lambda x:int(x[0])):
    print(f"{jid} | {org} | {t}")
print("count:", len(dup_org_title))
