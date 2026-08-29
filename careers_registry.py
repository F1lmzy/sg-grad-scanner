#!/usr/bin/env python3
"""careers_registry.py — persistent registry of company career pages.

Each entry: {company: {url, domain, portal, added, last_verified, roles_seen}}
The sg-grad-scanner cron reads/writes this so future runs skip web-searching
for already-resolved companies.
"""
import json, os, time, re

PATH = os.path.expanduser('~/jobscan/careers_registry.json')

def load():
    try:
        return json.load(open(PATH))
    except Exception:
        return {}

def save(reg):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    json.dump(reg, open(PATH, 'w'), indent=1)

def add(company, url, portal=None, roles=None):
    """Add or update a company entry. Returns True if new."""
    reg = load()
    key = company.strip().lower()
    existing = reg.get(key)
    is_new = existing is None
    e = existing or {}
    if url:
        e['url'] = url
    if portal:
        e['portal'] = portal
    e['domain'] = _domain_of(url)
    e['last_verified'] = time.strftime('%Y-%m-%d')
    if roles:
        r = set(e.get('roles_seen') or [])
        r.update(roles)
        e['roles_seen'] = sorted(r)[-8:]  # keep last 8 distinct
    reg[key] = e
    save(reg)
    return is_new

def get(company):
    return load().get(company.strip().lower())

def all_entries():
    return load()

def stale(older_than_days=30):
    """Companies whose careers page hasn't been re-verified in N days."""
    cutoff = (time.time() - older_than_days * 86400)
    out = []
    for k, e in load().items():
        try:
            t = time.mktime(time.strptime(e.get('last_verified', '0'), '%Y-%m-%d'))
            if t < cutoff:
                out.append(k)
        except Exception:
            out.append(k)
    return out

def _domain_of(url):
    m = re.match(r'https?://([^/]+)', url or '')
    return m.group(1) if m else ''
