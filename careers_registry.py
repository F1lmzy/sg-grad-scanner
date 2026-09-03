#!/usr/bin/env python3
"""careers_registry.py — persistent registry of company career pages.

Each entry: {company: {url, domain, portal, added, last_verified, roles_seen}}
The sg-grad-scanner cron reads/writes this so future runs skip web-searching
for already-resolved companies.
"""
import fcntl
import json
import os
import re
import tempfile
import time
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone

PATH = os.path.expanduser('~/jobscan/careers_registry.json')

@contextmanager
def _registry_lock(exclusive):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH + '.lock', 'a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield

def _load_unlocked():
    try:
        with open(PATH) as handle:
            return json.load(handle)
    except FileNotFoundError:
        return {}

def _save_unlocked(reg):
    directory = os.path.dirname(PATH)
    os.makedirs(directory, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.careers-registry-', suffix='.json', dir=directory)
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(reg, handle, indent=1)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, PATH)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def load():
    with _registry_lock(exclusive=False):
        return _load_unlocked()

def save(reg):
    with _registry_lock(exclusive=True):
        _save_unlocked(reg)

def _update(mutator):
    with _registry_lock(exclusive=True):
        reg = _load_unlocked()
        result = mutator(reg)
        _save_unlocked(reg)
        return result

def add(company, url, portal=None, roles=None):
    """Add or update a company entry. Returns True if new."""
    def mutate(reg):
        key = company.strip().lower()
        existing = reg.get(key)
        is_new = existing is None
        e = existing or {}
        if url:
            e['url'] = url
            e['domain'] = _domain_of(url)
        if portal:
            e['portal'] = portal
        e['last_verified'] = time.strftime('%Y-%m-%d')
        if roles:
            r = set(e.get('roles_seen') or [])
            r.update(roles)
            e['roles_seen'] = sorted(r)[-8:]
        reg[key] = e
        return is_new
    return _update(mutate)

def get(company):
    return load().get(company.strip().lower())

def company_key(company):
    """Normalize company names from lead engines for registry matching."""
    text = unicodedata.normalize('NFKD', (company or '').casefold())
    text = ''.join(char for char in text if not unicodedata.combining(char))
    key = re.sub(r'[^a-z0-9]+', ' ', text).strip()
    suffixes = (
        'private limited', 'pte limited', 'pte ltd', 'limited', 'ltd',
        'llc', 'incorporated', 'inc', 'singapore',
    )
    changed = True
    while changed:
        changed = False
        for suffix in suffixes:
            if key == suffix:
                key = ''
                changed = True
                break
            if key.endswith(' ' + suffix):
                key = key[:-(len(suffix) + 1)].strip()
                changed = True
                break
    aliases = {
        'credit agricole corporate and investment bank': 'credit agricole cib',
        'credit agricole corporate investment bank': 'credit agricole cib',
    }
    return aliases.get(key, key)

def find_company(company, registry=None):
    """Return ``(registry_key, entry)`` for a lead-engine company name."""
    reg = registry if registry is not None else load()
    wanted = company_key(company)
    for key, entry in reg.items():
        if company_key(key) == wanted:
            return key, entry
    return None, None

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

def _checked_at(entry):
    raw = entry.get('last_attempted') or entry.get('last_checked') or entry.get('last_verified')
    if not raw:
        return None
    try:
        if len(raw) == 10:
            raw += 'T00:00:00+00:00'
        return datetime.fromisoformat(raw.replace('Z', '+00:00')).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None

def due_for_check(registry=None, limit=10, interval_hours=24, now=None,
                  excluded_portals=None):
    """Return oldest registered portals due for browser/manual verification."""
    reg = registry if registry is not None else load()
    now = now or datetime.now(timezone.utc)
    excluded = set(excluded_portals or ())
    due = []
    for key, entry in reg.items():
        prefix = (entry.get('portal') or '').split(':', 1)[0]
        if prefix in excluded:
            continue
        checked = _checked_at(entry)
        age_hours = float('inf') if checked is None else (now - checked).total_seconds() / 3600
        if age_hours >= interval_hours:
            due.append((checked or datetime.min.replace(tzinfo=timezone.utc), key, entry))
    due.sort(key=lambda row: (row[0], row[1]))
    return [(key, entry) for _, key, entry in due[:limit]]

def record_check(company, roles=None, success=True, error=None, checked_at=None):
    """Persist a recurring portal-check attempt and its verified roles."""
    def mutate(reg):
        key, entry = find_company(company, registry=reg)
        if entry is None:
            raise KeyError(f'company is not registered: {company}')
        stamp = checked_at or datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        entry['last_attempted'] = stamp
        if success:
            entry['last_checked'] = stamp
            entry['last_verified'] = stamp[:10]
            entry.pop('check_error', None)
            if roles:
                known = set(entry.get('roles_seen') or [])
                known.update(roles)
                entry['roles_seen'] = sorted(known)[-8:]
        elif error:
            entry['check_error'] = str(error)[:300]
        reg[key] = entry
        return entry
    return _update(mutate)

def _domain_of(url):
    m = re.match(r'https?://([^/]+)', url or '')
    return m.group(1) if m else ''
