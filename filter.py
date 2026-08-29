import json, re

d = json.load(open("/home/kavin/jobscan/details.json"))

SENIOR = re.compile(r'\b(senior|staff|lead|principal|director|vp\b|vice president|head of|manager|architect|experienced|expert)\b', re.I)
ENTRY = re.compile(r'\b(graduate|entry[- ]level|junior|associate|assistant|trainee|fresh|apprentice|early[- ]career)\b', re.I)
DESC_ENTRY = re.compile(r'(fresh graduate|fresh grad|entry level|entry-level|no experience|without experience|0[- ]?\+? years|1[- ]?\+? years|recent graduate|new graduate|early[- ]career|newly graduated|welcome to apply|are welcome to apply|internship experience|no prior)', re.I)
SENIOR_DESC = re.compile(r'(\d{1,2}\s*\+?\s*years?(?!.*(?:internship|coursework|relevant experience (?:is )?a plus|welcome))|senior level|minimum \d+ years)', re.I)

rows = []
for jid, info in sorted(d.items(), key=lambda x: int(x[0])):
    t = info.get("title", "")
    org = info.get("org", "")
    desc = info.get("desc", "")
    loc = info.get("loc", "")
    if not t:
        continue
    # skip non-SG locations
    if loc and not re.search(r'Singapore|SG', loc, re.I):
        continue
    score = 0
    reasons = []
    if SENIOR.search(t):
        score -= 2
        reasons.append("senior-title")
    if ENTRY.search(t):
        score += 2
        reasons.append("entry-title")
    if DESC_ENTRY.search(desc):
        score += 1
        reasons.append("entry-desc")
    # years-of-exp signals in description
    yrs = re.findall(r'(\d+)\s*\+?\s*(?:years|yrs)\s*(?:of)?\s*(?:experience|exp)', desc)
    if yrs:
        maxy = max(int(y) for y in yrs)
        if maxy >= 3:
            score -= 2
            reasons.append(f"desc-{maxy}yrs")
        elif maxy == 2:
            score -= 1
            reasons.append(f"desc-{maxy}yrs")
        else:
            reasons.append(f"desc-{maxy}yrs")
    if re.search(r'\b(manager|director|head|principal|staff|lead)\b', desc, re.I):
        score -= 0
    rows.append((score, jid, org, t, loc, reasons, desc[:300]))

rows.sort(key=lambda r: -r[0])
print("=== TOP CANDIDATES (score >= 1) ===")
for score, jid, org, t, loc, reasons, desc in rows:
    if score >= 1:
        print(f"[{score}] {jid} | {org[:30]} | {t[:75]} | {loc[:25]} | {','.join(reasons)}")
print()
print("=== BORDERLINE (score 0) ===")
for score, jid, org, t, loc, reasons, desc in rows:
    if score == 0:
        print(f"[{score}] {jid} | {org[:30]} | {t[:75]} | {loc[:25]} | {','.join(reasons)}")
