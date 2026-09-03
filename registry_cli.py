#!/usr/bin/env python3
"""Safe CLI for applying cron-produced registry check metadata from JSON."""
import ipaddress
import json
import socket
import sys
import tempfile
import urllib.parse

import careers_registry as cr

AGGREGATOR_DOMAINS = {
    'linkedin.com', 'mycareersfuture.gov.sg', 'jobsdb.com',
    'indeed.com', 'glassdoor.com', 'jobstreet.com', 'talent.com',
    'adzuna.com', 'adzuna.sg', 'foundit.sg', 'foundit.com',
    'jobscentral.com.sg', 'efinancialcareers.sg', 'efinancialcareers.com',
    'jobrapido.com', 'simplyhired.com', 'monster.com', 'ziprecruiter.com',
    'careerjet.sg', 'careerjet.com', 'jooble.org', 'grabjobs.co',
    'fastjobs.sg', 'internsg.com', 'glints.com', 'prosple.com',
    'gradconnection.com',
}


def make_run_dir(base_dir=None):
    """Create a private per-run payload directory outside shared fixed paths."""
    return tempfile.mkdtemp(prefix='sg-grad-scanner-', dir=base_dir)

def _load_object(payload_path):
    with open(payload_path) as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError('payload must be a JSON object')
    return payload

def _roles(payload):
    roles = payload.get('roles', [])
    if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
        raise ValueError('roles must be a list of strings')
    return roles


def _validate_public_destination(parsed):
    if parsed.username is not None or parsed.password is not None:
        raise ValueError('URL credentials are not allowed')
    host = parsed.hostname
    if not host or host.lower() == 'localhost' or host.lower().endswith('.localhost'):
        raise ValueError('URL must have a public hostname')
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            addresses = {
                ipaddress.ip_address(info[4][0])
                for info in socket.getaddrinfo(host, parsed.port or 443)
            }
        except (OSError, ValueError) as exc:
            raise ValueError('URL hostname must resolve publicly') from exc
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError('URL must resolve only to public network addresses')


def validate_careers_url(url):
    if not isinstance(url, str) or not url.startswith(('https://', 'http://')):
        raise ValueError('url must be an HTTP(S) URL')
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or '').lower()
    if any(host == domain or host.endswith('.' + domain) for domain in AGGREGATOR_DOMAINS):
        raise ValueError('aggregator URLs cannot be registered as company careers pages')
    _validate_public_destination(parsed)

def add_file(payload_path):
    payload = _load_object(payload_path)
    company = payload.get('company')
    url = payload.get('url')
    portal = payload.get('portal')
    if not isinstance(company, str) or not company.strip():
        raise ValueError('company must be a non-empty string')
    validate_careers_url(url)
    if not isinstance(portal, str) or ':' not in portal:
        raise ValueError('portal must be a prefix:identifier string')
    return cr.add(company, url, portal=portal, roles=_roles(payload))


def record_check_file(payload_path):
    payload = _load_object(payload_path)
    company = payload.get('company')
    success = payload.get('success')
    error = payload.get('error')
    if not isinstance(company, str) or not company.strip():
        raise ValueError('company must be a non-empty string')
    if not isinstance(success, bool):
        raise ValueError('success must be a boolean')
    if error is not None and not isinstance(error, str):
        raise ValueError('error must be a string or null')
    return cr.record_check(company, roles=_roles(payload), success=success, error=error)


def main(argv):
    if len(argv) == 2 and argv[1] == 'make-run-dir':
        print(make_run_dir())
        return
    if len(argv) != 3 or argv[1] not in {'add', 'record-check'}:
        raise SystemExit('usage: registry_cli.py make-run-dir | {add|record-check} PAYLOAD.json')
    result = add_file(argv[2]) if argv[1] == 'add' else record_check_file(argv[2])
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main(sys.argv)
