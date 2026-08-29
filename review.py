import json, re

cands = json.load(open('/home/kavin/jobscan/candidates.json'))
det = json.load(open('/home/kavin/jobscan/details.json'))

# Only consider candidates fetched this run that have fresh details (id in candidates.json)
ids = [k for k in cands]
ids.sort(key=lambda x: int(x))

ENTRY = re.compile(r'\b(graduate|entry[- ]level|junior|associate|assistant|trainee|fresh|apprentice|early[- ]career)\b', re.I)
SENIOR = re.compile(r'\b(senior|staff|lead|principal|director|vp\b|head of|experienced)\b', re.I)

rows = []
for jid in ids:
    info = det.get(jid, {})
    t = info.get('title','')
    org = info.get('org','')
    desc = info.get('desc','')
    loc = info.get('loc','')
    date = info.get('date','')
    if not t:
        # fetch may have failed -> mark for skip
        rows.append(('NO-DETAIL', jid, org, t, loc, date))
        continue
    entry_t = bool(ENTRY.search(t))
    senior_t = bool(SENIOR.search(t))
    desc_nyr = re.findall(r'(\d{1,2})\s*\+\s*years', desc) or re.findall(r'(\d{1,2})\s*(?:years|yrs)\s*(?:of)?\s*(?:experience|exp)', desc)
    maxy = max([int(x) for x in desc_nyr]) if desc_nyr else 0
    rows.append((jid, org, t, loc, date, entry_t, senior_t, maxy))

# Print new candidates with entry title flag
print("=== NEW CANDIDATES (this run) ===")
for r in sorted(rows, key=lambda x: (x[0]=='NO-DETAIL', int(x[0]) if x[0]!='NO-DETAIL' else 0)):
    if r[0]=='NO-DETAIL':
        print(f"[{r[0]}] {r[1]} | {r[3]}")
        continue
    jid, org, t, loc, date, entry_t, senior_t, maxy = r
    flag = 'E' if entry_t else ' '
    flag2 = 'S' if senior_t else ' '
    yrs = f"{maxy}y" if maxy else "  "
    print(f"[{flag}{flag2}{yrs}] {jid} | {org[:30]} | {t[:90]} | {loc[:20]} | {date[:25]}")
