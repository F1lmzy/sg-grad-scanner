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

Output JSON includes recurring direct-board results, LinkedIn/MCF company leads,
registered lead verification targets, unresolved companies, and due registered
portals for browser checks.
Dedup state: ~/jobscan/seen_ids.json
"""
import concurrent.futures as cf
import fcntl
import html as html_mod
import json
import os
import re
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from contextlib import contextmanager

import careers_registry as cr

STATE = os.path.expanduser('~/jobscan/seen_ids.json')
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}

# --- curated direct boards (verified live 2026-08-24) ---
GREENHOUSE_BOARDS = [
    'abnormalsecurity', 'point72', 'optiver', 'jumptrading', 'flowtraders',
    'akunacapital', 'schonfeld', 'exoduspoint', 'winton', 'coinbase', 'stripe', 'shein',
]
LEVER_COMPANIES = ['ninjavan']
WORKABLE_ACCOUNTS = ['qcp-group', 'genesis']

KEYWORDS = re.compile(r'graduate|entry.level|junior|associate|fresh|trainee|analyst program|academy', re.I)
NON_FULL_TIME = re.compile(
    r'\bintern(?:ship)?\b|\bco[- ]?op\b|\battachment\b|\bpart[- ]?time\b|'
    r'\bcontract(?:or)?\b|\btemporary\b|\btemp\b|\bapprentice(?:ship)?\b|\bcasual\b',
    re.I,
)
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
SG_HINT = re.compile(r'singapore|\bsg\b|\(sg\)', re.I)

def is_full_time_grad(title):
    return bool(KEYWORDS.search(title or '')) and not bool(NON_FULL_TIME.search(title or ''))

def get_json(url, data=None, extra=None):
    headers = dict(UA)
    headers.update(extra or {})
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())

def norm(s):
    return re.sub(r'\s+', ' ', s or '').strip()

@contextmanager
def _seen_lock(exclusive):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE + '.lock', 'a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield

def _load_seen_unlocked():
    try:
        with open(STATE) as handle:
            return set(json.load(handle))
    except FileNotFoundError:
        return set()

def load_seen():
    with _seen_lock(exclusive=False):
        return _load_seen_unlocked()

def _save_seen_unlocked(seen):
    directory = os.path.dirname(STATE)
    fd, temporary = tempfile.mkstemp(prefix='.seen-ids-', suffix='.json', dir=directory)
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(sorted(seen), handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, STATE)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def save_seen(seen):
    with _seen_lock(exclusive=True):
        _save_seen_unlocked(seen)

def commit_seen_file(payload_path):
    """Atomically merge acknowledged direct-job IDs from a JSON file."""
    with open(payload_path) as handle:
        ids = json.load(handle)
    if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
        raise ValueError('seen-ID payload must be a JSON list of strings')
    with _seen_lock(exclusive=True):
        merged = _load_seen_unlocked() | set(ids)
        _save_seen_unlocked(merged)
    return len(merged)

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
        'grad': is_full_time_grad(title),
        'domain': bool(DOMAINS.search(title)),
        'source': source,
    }

def _require_jobs(payload, source):
    if not isinstance(payload, dict) or not isinstance(payload.get('jobs'), list):
        raise ValueError(f'{source} response is missing a jobs list')
    return payload['jobs']

def fetch_greenhouse(slug):
    d = get_json(f'https://boards-api.greenhouse.io/v1/boards/{slug}/jobs')
    return [j_common('greenhouse', slug, j['id'], norm(slug).title(), j.get('title',''),
                     j.get('location',{}).get('name',''), j.get('absolute_url',''), (j.get('updated_at') or '')[:10])
            for j in _require_jobs(d, 'Greenhouse')]

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
            for j in _require_jobs(d, 'Workable')]

DIRECT_PORTALS = {'greenhouse', 'lever', 'workable'}
DIRECT_FETCHERS = {
    'greenhouse': fetch_greenhouse,
    'lever': fetch_lever,
    'workable': fetch_workable,
}

def direct_boards_from_registry(registry):
    """Return unique direct-API boards from the persistent registry."""
    boards = {}
    for company, entry in registry.items():
        portal = entry.get('portal') or ''
        if ':' not in portal:
            continue
        source, slug = portal.split(':', 1)
        if source in DIRECT_PORTALS and slug:
            boards.setdefault((source, slug), company)
    return [(source, slug, boards[(source, slug)]) for source, slug in sorted(boards)]

def configured_direct_boards(registry):
    """Registry boards plus bootstrap boards not registered yet, deduplicated."""
    boards = {(source, slug): company for source, slug, company
              in direct_boards_from_registry(registry)}
    for slug in GREENHOUSE_BOARDS:
        boards.setdefault(('greenhouse', slug), norm(slug).title())
    for slug in LEVER_COMPANIES:
        boards.setdefault(('lever', slug), norm(slug).title())
    for slug in WORKABLE_ACCOUNTS:
        boards.setdefault(('workable', slug), norm(slug).title())
    return [(source, slug, boards[(source, slug)]) for source, slug in sorted(boards)]

def target_jobs(jobs):
    """Return Singapore, full-time graduate, target-domain jobs only."""
    return [job for job in jobs if job['sg'] and job['grad'] and job['domain']]

def scan_direct_boards(boards, seen, fetchers=None):
    """Scan every registered direct ATS board once and identify new matches."""
    fetchers = fetchers or DIRECT_FETCHERS
    jobs, errors = [], []
    with cf.ThreadPoolExecutor(10) as ex:
        futures = {
            ex.submit(fetchers[source], slug): (source, slug, company)
            for source, slug, company in boards
        }
        for future in cf.as_completed(futures):
            source, slug, company = futures[future]
            try:
                fetched = future.result()
                for job in fetched:
                    job['company'] = company
                jobs.extend(fetched)
            except Exception as exc:
                errors.append(f'{source}/{slug}: {type(exc).__name__}')
    hits = target_jobs(jobs)
    new = [job for job in hits if job['id'] not in seen]
    new.sort(key=lambda job: job['id'])
    return {
        'new': new,
        'all_open_matching': len(hits),
        'scanned': len(boards),
        'errors': sorted(errors),
    }

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

def validate_li_html(body, cards, start):
    """Reject HTTP-200 auth walls and malformed guest-search responses."""
    if not isinstance(body, str):
        raise ValueError('LinkedIn response is not text')
    lowered = body.lower()
    blocked = ('authwall', 'sign in | linkedin', '/checkpoint/', 'captcha', 'challenge-page')
    if any(marker in lowered for marker in blocked):
        raise ValueError('LinkedIn returned a block/login page')
    if not body.strip() and start == 0:
        raise ValueError('LinkedIn returned an empty first page')
    if body.strip() and not cards:
        raise ValueError('LinkedIn returned malformed guest-search HTML')


def fetch_linkedin_leads():
    """Discover LinkedIn lead companies and return source errors explicitly."""
    leads = {}
    role_count = 0
    errors = []
    seen = set()
    for kw in LI_QUERIES:
        for start in (0, 25):
            try:
                html = li_fetch(kw, start)
                cards = parse_li_cards(html)
                validate_li_html(html, cards, start)
            except Exception as exc:
                errors.append(f'{kw}@{start}: {type(exc).__name__}')
                continue
            for jid, title, company, _location, _url in cards:
                if jid in seen:
                    continue
                seen.add(jid)
                if not title or not company:
                    continue
                if not is_full_time_grad(title) or not DOMAINS.search(title):
                    continue
                if re.search(r'\b(senior|principal|staff|director|head of|vp|manager)\b', title, re.I) \
                        and not re.search(r'junior|graduate|entry|associate', title, re.I):
                    continue
                posted = time.strftime('%Y-%m-%d', time.gmtime())
                _add_lead(leads, company, title, posted, source='linkedin')
                role_count += 1
            time.sleep(0.6)  # be gentle to LinkedIn
    return leads, role_count, errors


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
    d = get_json('https://api.mycareersfuture.gov.sg/v2/search?limit=100&page=%d' % page,
                 data={'search': q, 'sortBy': []}, extra=MCF_HDRS)
    if not isinstance(d, dict) or not isinstance(d.get('results'), list):
        raise ValueError('MCF response is missing a results list')
    return d['results']

def fetch_mcf_leads():
    """Return {(company): {roles:set, sample_title, posted}} from MCF matches."""
    queries = [
        'graduate engineer', 'graduate software engineer', 'graduate analyst',
        'junior software engineer', 'junior electrical engineer',
        'machine learning engineer junior', 'quantitative analyst graduate',
        'robotics engineer junior', 'embedded engineer junior',
        'data analyst graduate', 'firmware engineer junior',
    ]
    leads, errors = {}, []
    seen_uuids = set()
    with cf.ThreadPoolExecutor(6) as ex:
        futures = {ex.submit(mcf_search, query, 0): query for query in queries}
        results = []
        for future in cf.as_completed(futures):
            query = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                errors.append(f'{query}: {type(exc).__name__}')
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
            if not is_full_time_grad(title) or not DOMAINS.search(hay):
                continue
            if re.search(r'\b(senior|principal|staff|director|head of|vp|manager)\b', title, re.I) and not re.search(r'junior|graduate|entry', title, re.I):
                continue
            company = norm((j.get('postedCompany') or {}).get('name') or '')
            if not company or len(company) < 2:
                continue
            posted = ((j.get('metadata') or {}).get('originalPostingDate') or '')[:10]
            _add_lead(leads, company, title, posted, source='mcf')
    return leads, sorted(errors)

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

def _lead_source(info):
    return ','.join(sorted(info['sources'])) if info.get('sources') else 'unknown'

def partition_registered_leads(leads, registry):
    """Separate known-company leads so their saved careers pages are reused."""
    registered, unregistered = [], {}
    for company, info in leads.items():
        registry_company, entry = cr.find_company(company, registry=registry)
        if entry is None:
            unregistered[company] = info
            continue
        registered.append({
            'company': company,
            'registry_company': registry_company,
            'portal': entry.get('portal', ''),
            'careers_url': entry.get('url', ''),
            'roles': sorted(info['roles'])[:4],
            'posted': info['posted_max'],
            'count': info['count'],
            'found_via': _lead_source(info),
            '_last_attempted': (entry.get('last_attempted') or
                                entry.get('last_checked') or
                                entry.get('last_verified') or ''),
        })
    registered.sort(key=lambda row: (row['_last_attempted'], -row['count'], row['company']))
    for row in registered:
        row.pop('_last_attempted')
    return registered, unregistered

def collect_verified_ids(direct_new, resolved):
    """Collect stable direct-portal IDs that should enter dedup state."""
    ids = {job['id'] for job in direct_new if job.get('id')}
    for company in resolved:
        ids.update(job['id'] for job in company.get('own_portal_roles', [])
                   if job.get('id'))
    return ids

def main():
    seen = load_seen()

    # 1. scan every direct-API company in the persistent registry. The legacy
    # lists are only bootstrap fallbacks for boards not registered yet.
    registry = cr.load()
    direct_boards = configured_direct_boards(registry)
    direct_scan = scan_direct_boards(direct_boards, seen)
    cur_new = direct_scan['new']

    # 2. MCF + LinkedIn lead engines -> merged leads
    try:
        mcf_leads, mcf_errors = fetch_mcf_leads()
    except Exception as exc:
        mcf_leads, mcf_errors = {}, [f'fetch_mcf_leads: {type(exc).__name__}']
    try:
        li_leads, li_role_count, linkedin_errors = fetch_linkedin_leads()
    except Exception as exc:
        li_leads, li_role_count, linkedin_errors = {}, 0, [f'fetch_linkedin_leads: {type(exc).__name__}']
    leads = {}
    for src_leads in (mcf_leads, li_leads):
        for co, e in src_leads.items():
            t = leads.setdefault(co, {'roles': set(), 'posted_max': '', 'count': 0, 'sources': set()})
            t['roles'] |= e.get('roles', set())
            t['sources'] |= e.get('sources', set())
            t['count'] += e.get('count', 0)
            if e.get('posted_max', '') > t['posted_max']:
                t['posted_max'] = e['posted_max']

    # 3. Known lead companies reuse their registered careers pages. Only new
    # companies incur generic ATS-slug probes and manual careers lookup.
    registered_leads, unregistered_leads = partition_registered_leads(leads, registry)
    resolved, unresolved = [], []
    top = sorted(unregistered_leads.items(), key=lambda kv: (-kv[1]['count'], kv[0]))[:25]
    with cf.ThreadPoolExecutor(6) as ex:
        futs = {ex.submit(probe_ats, co): co for co, _ in top}
        for f in cf.as_completed(futs):
            co = futs[f]
            info = unregistered_leads[co]
            r = f.result()
            if r:
                src, slug, jobs = r
                match = target_jobs(jobs)
                if match:
                    resolved.append({'company': co, 'portal': f'{src}:{slug}',
                                     'roles': sorted(info['roles'])[:4], 'found_via': _lead_source(info),
                                     'own_portal_roles': [{'title': j['title'], 'url': j['url'], 'id': j['id']} for j in match[:6]]})
                    continue
            unresolved.append({'company': co, 'roles': sorted(info['roles'])[:4],
                               'posted': info['posted_max'], 'count': info['count'],
                               'found_via': _lead_source(info)})

    dedup_ids_to_commit = sorted(collect_verified_ids(cur_new, resolved))

    # 4. Rotate through non-API registered portals. The cron agent renders and
    # verifies these company pages, then calls careers_registry.record_check().
    recurring_due = cr.due_for_check(
        registry=registry, limit=10, interval_hours=24,
        excluded_portals=DIRECT_PORTALS,
    )
    recurring_checks = [{
        'company': company,
        'portal': entry.get('portal', ''),
        'careers_url': entry.get('url', ''),
        'last_checked': entry.get('last_checked') or entry.get('last_verified'),
        'roles_seen': entry.get('roles_seen') or [],
    } for company, entry in recurring_due]

    print(json.dumps({
        'generated': time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime()),
        'curated': {
            'new': [{k: j[k] for k in ('id','company','title','location','url','updated','source')} for j in sorted(cur_new, key=lambda x: x['id'])],
            'all_open_matching': direct_scan['all_open_matching'],
            'registered_boards_scanned': direct_scan['scanned'],
        },
        'mcf_leads_found': len(mcf_leads),
        'linkedin_roles_seen': li_role_count,
        'linkedin_lead_companies': len(li_leads),
        'total_lead_companies': len(leads),
        'registered_leads_to_verify': registered_leads,
        'resolved_to_own_portal': resolved,
        'needs_manual_careers_lookup': sorted(unresolved, key=lambda x: -x['count'])[:15],
        'registered_portals_due_for_recurring_check': recurring_checks,
        'dedup_ids_to_commit_after_persist': dedup_ids_to_commit,
        'direct_board_errors': direct_scan['errors'],
        'mcf_errors': mcf_errors,
        'linkedin_errors': linkedin_errors,
        'errors': direct_scan['errors'] + mcf_errors + linkedin_errors,
    }, indent=1))

if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--commit-seen':
        print(commit_seen_file(sys.argv[2]))
    else:
        main()
