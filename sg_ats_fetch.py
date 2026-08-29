#!/usr/bin/env python3
"""sg-ats-fetch.py — SG graduate-job fetcher via DIRECT company portals.

Strategy (user is a foreigner — cannot apply via MyCareersFuture):
  1. CURATED ATS BOARDS: query Greenhouse/Lever/Workable APIs directly for
     companies known to hire in SG (quant/trading/tech/robotics).
  2. MCF AS LEAD ENGINE ONLY: search MyCareersFuture for fresh grad-level
     postings, but use them purely to DISCOVER which companies are hiring.
     Never surface MCF apply links.
  3. PORTAL RESOLUTION: for every discovered company, probe its own careers
     infrastructure (gh/lv/wb/ashby/smartrecruiters APIs) so output links point
     at the COMPANY'S OWN portal, not an aggregator.

Output JSON: {curated_new, curated_all, mcf_leads, resolved, errors}
Dedup state: ~/jobscan/seen_ids.json
"""
import json, re, os, time, html as html_mod, urllib.request, urllib.parse, concurrent.futures as cf

STATE = os.path.expanduser('~/jobscan/seen_ids.json')
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}

# --- curated direct boards (verified live 2026-08-24) ---
GREENHOUSE_BOARDS = [
    'abnormalsecurity', 'point72', 'optiver', 'jumptrading', 'flowtraders',
    'akunacapital', 'schonfeld', 'exoduspoint', 'winton', 'coinbase', 'stripe', 'shein',
]
LEVER_COMPANIES = ['ninjavan']
WORKABLE_ACCOUNTS = ['qcp-group', 'genesis']

KEYWORDS = re.compile(r'graduate|entry.level|junior|associate|fresh|trainee|analyst program|academy|intern\b|internship', re.I)
# LinkedIn search terms (guest API discovery) - distinct from the filter regex
LI_QUERIES = [
    'graduate software engineer', 'graduate engineer', 'graduate program',
    'fresh graduate', 'entry level software engineer', 'junior software engineer',
    'junior machine learning engineer', 'machine learning engineer',
    'graduate data scientist', 'data analyst', 'quantitative analyst',
    'quantitative developer', 'graduate trader', 'junior trader',
    'robotics engineer', 'embedded engineer', 'firmware engineer',
    'electrical engineer', 'mechatronics engineer', 'automation engineer',
    'software engineer trainee', 'associate engineer', 'graduate developer',
    'cloud engineer', 'backend engineer', 'AI engineer', 'research engineer',
]
DOMAINS = re.compile(r'software|engineer|developer|machine learning|\bml\b|\bai\b|data scien|quant|robotic|electrical|embedded|firmware|full.stack|backend|platform|infrastructure|devops|reliability|analytics', re.I)
SG_HINT = re.compile(r'singapore|\bsg\b|\(sg\)|southeast asia|apac', re.I)

def get_json(url, data=None, extra=None):
    headers = dict(UA)
    headers.update(extra or {})
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())

def norm(s):
    return re.sub(r'\s+', ' ', s or '').strip()

def load_seen():
    try:
        return set(json.load(open(STATE)))
    except Exception:
        return set()

def save_seen(seen):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(sorted(seen), open(STATE, 'w'))

def slugify(name):
    s = re.sub(r'[^a-z0-9]+', '', name.lower())
    return s

# ---------- curated board fetchers ----------
def j_common(source, slug, jid, company, title, loc, url, updated):
    return {
        'id': f'{source}:{slug}:{jid}',
        'company': company, 'title': title, 'location': loc, 'url': url,
        'updated': updated,
        'sg': bool(SG_HINT.search(loc)) or bool(SG_HINT.search(title)),
        'grad': bool(KEYWORDS.search(title)),
        'domain': bool(DOMAINS.search(title)),
        'source': source,
    }

def fetch_greenhouse(slug):
    d = get_json(f'https://boards-api.greenhouse.io/v1/boards/{slug}/jobs')
    return [j_common('greenhouse', slug, j['id'], norm(slug).title(), j.get('title',''),
                     j.get('location',{}).get('name',''), j.get('absolute_url',''), (j.get('updated_at') or '')[:10])
            for j in d.get('jobs', [])]

def fetch_lever(slug):
    d = get_json(f'https://api.lever.co/v0/postings/{slug}?mode=json')
    return [j_common('lever', slug, j['id'], norm(slug).title(), j.get('text',''),
                     (j.get('categories') or {}).get('location',''), j.get('hostedUrl',''),
                     time.strftime('%Y-%m-%d', time.gmtime(j.get('createdAt',0)/1000)))
            for j in d]

def fetch_workable(slug):
    d = get_json(f'https://apply.workable.com/api/v1/widget/accounts/{slug}')
    return [j_common('workable', slug, j.get('shortcode') or j.get('id'),
                     (j.get('company') or {}).get('name', slug.title()), j.get('title',''),
                     f"{j.get('location',{}).get('city','')} {j.get('country','')}".strip(),
                     j.get('url','') or j.get('shortlink',''), (j.get('published') or '')[:10])
            for j in d.get('jobs', [])]

# ---------- LinkedIn lead extraction (guest API, discovery only) ----------
# LinkedIn is a LEAD ENGINE like MCF: never surface linkedin.com/jobs apply
# links (user is a foreigner who can't apply via aggregators). Roles must be
# resolved to the company's OWN careers domain by probe_ats / LLM phase.
LI_BASE = ('https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search'
           '?keywords={kw}&location=Singapore&f_TPR=r604800&start={start}')
LI_UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
         'Chrome/125.0.0.0 Safari/537.36')
LI_HDRS = {'User-Agent': LI_UA, 'Accept-Language': 'en-US,en;q=0.9',
           'Accept': 'text/html,application/xhtml+xml'}


def _clean_html(s):
    s = re.sub(r'<[^>]+>', ' ', s or '')
    return re.sub(r'^[>:·\s]+|[>\s]+$', '', html_mod.unescape(s)).strip()


def parse_li_cards(html):
    """Parse LinkedIn guest search fragment -> (jid, title, company, location, url)."""
    cards = []
    for m in re.finditer(r'base-search-card[^>]*data-entity-urn="urn:li:jobPosting:(\d+)"(.*?)</li>', html, re.S):
        jid, block = m.group(1), m.group(2)
        t = re.search(r'<h3[^>]*class="base-search-card__title"(.*?)</h3>', block, re.S)
        c = re.search(r'class="base-search-card__subtitle"(.*?)</a>', block, re.S)
        loc = re.search(r'job-search-card__location"(.*?)<', block, re.S)
        u = re.search(r'<a class="base-card__full-link"[^>]*href="([^"]+)"', block)
        cards.append((
            jid,
            _clean_html(t.group(1)) if t else None,
            _clean_html(c.group(1)) if c else None,
            _clean_html(loc.group(1)) if loc else None,
            html_mod.unescape(u.group(1)) if u else None,
        ))
    return cards


def li_fetch(keyword, start=0):
    req = urllib.request.Request(LI_BASE.format(kw=urllib.parse.quote_plus(keyword), start=start),
                                 headers=LI_HDRS)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode('utf-8', 'ignore')


def fetch_linkedin_leads():
    """Discover companies hiring from LinkedIn guest jobs. Returns (leads, raw_roles)."""
    leads = {}
    roles = []
    seen = set()
    for kw in LI_QUERIES:
        for start in (0, 25):
            try:
                html = li_fetch(kw, start)
            except Exception:
                continue
            for jid, title, company, location, url in parse_li_cards(html):
                if jid in seen:
                    continue
                seen.add(jid)
                if not title or not company:
                    continue
                if not KEYWORDS.search(title) or not DOMAINS.search(title):
                    continue
                if re.search(r'\b(senior|principal|staff|director|head of|vp|manager)\b', title, re.I) \
                        and not re.search(r'junior|graduate|entry|associate', title, re.I):
                    continue
                posted = time.strftime('%Y-%m-%d', time.gmtime())
                _add_lead(leads, company, title, posted, source='linkedin')
                roles.append({'id': f'linkedin:{jid}', 'source': 'linkedin', 'company': company,
                              'title': title, 'location': location, 'url': url})
            time.sleep(0.6)  # be gentle to LinkedIn
    return leads, roles


# ---------- MCF lead extraction ----------
MCF_HDRS = {'Content-Type': 'application/json',
            'Origin': 'https://www.mycareersfuture.gov.sg',
            'Referer': 'https://www.mycareersfuture.gov.sg/'}


def _add_lead(leads, company, title, posted, source):
    e = leads.setdefault(company, {'roles': set(), 'posted_max': '', 'count': 0, 'sources': set()})
    e['roles'].add(_clean_html(title))
    e['count'] += 1
    e['sources'].add(source)
    if posted > e['posted_max']:
        e['posted_max'] = posted

def mcf_search(q, page=0):
    try:
        d = get_json('https://api.mycareersfuture.gov.sg/v2/search?limit=100&page=%d' % page,
                     data={'search': q, 'sortBy': []}, extra=MCF_HDRS)
        return d.get('results', [])
    except Exception:
        return []

def fetch_mcf_leads():
    """Return {(company): {roles:set, sample_title, posted}} from MCF matches."""
    queries = [
        'graduate engineer', 'graduate software engineer', 'graduate analyst',
        'junior software engineer', 'junior electrical engineer',
        'machine learning engineer junior', 'quantitative analyst graduate',
        'robotics engineer junior', 'embedded engineer junior',
        'data analyst graduate', 'firmware engineer junior',
    ]
    leads = {}
    seen_uuids = set()
    with cf.ThreadPoolExecutor(6) as ex:
        results = list(ex.map(lambda q: mcf_search(q, 0), queries))
    for res in results:
        for j in res:
            uid = j.get('uuid')
            if not uid or uid in seen_uuids:
                continue
            seen_uuids.add(uid)
            title = norm(j.get('title'))
            desc = norm(j.get('description'))[:800]
            hay = title + ' ' + desc
            # must look entry-level AND in-domain; skip if it screams senior
            if not KEYWORDS.search(title) or not DOMAINS.search(hay):
                continue
            if re.search(r'\b(senior|principal|staff|director|head of|vp|manager)\b', title, re.I) and not re.search(r'junior|graduate|entry', title, re.I):
                continue
            company = norm((j.get('postedCompany') or {}).get('name') or '')
            if not company or len(company) < 2:
                continue
            posted = ((j.get('metadata') or {}).get('originalPostingDate') or '')[:10]
            _add_lead(leads, company, title, posted, source='mcf')
    return leads

# ---------- portal resolution ----------
def probe_ats(company):
    """Try to find this company's own ATS board; return (source, slug, jobs) or None."""
    cands = {slugify(company)}
    # also try with common suffixes stripped
    base = re.sub(r'(pte ltd|ltd|llc|inc|singapore|asia|group|technologies|technology|holdings|international)$', '', company.lower()).strip()
    if base:
        cands.add(slugify(base))
    probes = []
    for c in filter(None, cands):
        probes += [('greenhouse', c), ('lever', c), ('workable', c)]
    def one(args):
        src, c = args
        try:
            fn = {'greenhouse': fetch_greenhouse, 'lever': fetch_lever, 'workable': fetch_workable}[src]
            jobs = fn(c)
            return (src, c, jobs) if jobs else None
        except Exception:
            return None
    with cf.ThreadPoolExecutor(8) as ex:
        for r in ex.map(one, probes):
            if r:
                return r
    return None

def main():
    seen = load_seen()
    errors = []

    def run(fn, *a):
        try:
            return fn(*a)
        except Exception as e:
            errors.append(f'{fn.__name__}/{a[0] if a else ""}: {type(e).__name__}')
            return []

    # 1. curated boards
    curated = []
    with cf.ThreadPoolExecutor(10) as ex:
        futs = {}
        for s in GREENHOUSE_BOARDS:
            futs[ex.submit(run, fetch_greenhouse, s)] = s
        for s in LEVER_COMPANIES:
            futs[ex.submit(run, fetch_lever, s)] = s
        for s in WORKABLE_ACCOUNTS:
            futs[ex.submit(run, fetch_workable, s)] = s
        for f in cf.as_completed(futs):
            curated.extend(f.result())

    cur_hits = [j for j in curated if j['sg'] and j['grad'] and j['domain']]
    cur_new = [j for j in cur_hits if j['id'] not in seen]
    save_seen(seen | {j['id'] for j in cur_new})

    # 2. MCF + LinkedIn lead engines -> merged leads
    mcf_leads = run(fetch_mcf_leads) or {}
    li_leads, li_roles = (run(fetch_linkedin_leads) or ({}, []))
    if not isinstance(li_leads, dict):
        li_leads, li_roles = {}, []
    leads = {}
    for src_leads in (mcf_leads, li_leads):
        for co, e in src_leads.items():
            t = leads.setdefault(co, {'roles': set(), 'posted_max': '', 'count': 0, 'sources': set()})
            t['roles'] |= e.get('roles', set())
            t['sources'] |= e.get('sources', set())
            t['count'] += e.get('count', 0)
            if e.get('posted_max', '') > t['posted_max']:
                t['posted_max'] = e['posted_max']

    def src_str(info):
        return ','.join(sorted(info['sources'])) if info.get('sources') else 'mcf'

    # 3. resolve top leads to their own portals (cap for runtime)
    resolved, unresolved = [], []
    top = sorted(leads.items(), key=lambda kv: (-kv[1]['count'], kv[0]))[:25]
    with cf.ThreadPoolExecutor(6) as ex:
        futs = {ex.submit(probe_ats, co): co for co, _ in top}
        for f in cf.as_completed(futs):
            co = futs[f]
            info = leads[co]
            r = f.result()
            if r:
                src, slug, jobs = r
                match = [j for j in jobs if j['sg'] and (j['grad'] or j['domain'])]
                if match:
                    resolved.append({'company': co, 'portal': f'{src}:{slug}',
                                     'roles': sorted(info['roles'])[:4], 'found_via': src_str(info),
                                     'own_portal_roles': [{'title': j['title'], 'url': j['url'], 'id': j['id']} for j in match[:6]]})
                    continue
            unresolved.append({'company': co, 'roles': sorted(info['roles'])[:4],
                               'posted': info['posted_max'], 'count': info['count'],
                               'found_via': src_str(info)})

    print(json.dumps({
        'generated': time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime()),
        'curated': {
            'new': [{k: j[k] for k in ('id','company','title','location','url','updated','source')} for j in sorted(cur_new, key=lambda x: x['id'])],
            'all_open_matching': len(cur_hits),
        },
        'mcf_leads_found': len(mcf_leads),
        'linkedin_roles_seen': len(li_roles),
        'linkedin_lead_companies': len(li_leads),
        'total_lead_companies': len(leads),
        'resolved_to_own_portal': resolved,
        'needs_manual_careers_lookup': sorted(unresolved, key=lambda x: -x['count'])[:15],
        'errors': errors[:8],
    }, indent=1))

if __name__ == '__main__':
    main()
