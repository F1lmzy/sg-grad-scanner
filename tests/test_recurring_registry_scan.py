import json
import os
from datetime import datetime, timezone

import careers_registry as cr
import registry_cli
import sg_ats_fetch as scanner


def _job(source, slug, jid, company, title="Graduate Software Engineer", location="Singapore"):
    return scanner.j_common(
        source, slug, jid, company, title, location,
        f"https://careers.example/{jid}", "2026-09-01",
    )


def test_find_company_matches_legal_suffix_and_punctuation():
    registry = {
        "ninja van": {"url": "https://careers.ninjavan.co", "portal": "lever:ninjavan"}
    }

    key, entry = cr.find_company("Ninja Van Pte. Ltd.", registry=registry)

    assert key == "ninja van"
    assert entry["portal"] == "lever:ninjavan"


def test_find_company_matches_unicode_and_known_aliases():
    registry = {
        "tüv süd": {"portal": "phenom:tuv"},
        "ey": {"portal": "sf:ey"},
        "credit agricole cib": {"portal": "cacib:jobs"},
    }

    assert cr.find_company("TUV SUD", registry=registry)[0] == "tüv süd"
    assert cr.find_company("EY Singapore", registry=registry)[0] == "ey"
    assert cr.find_company(
        "Credit Agricole Corporate and Investment Bank", registry=registry,
    )[0] == "credit agricole cib"


def test_direct_boards_are_derived_from_registry_without_duplicates():
    registry = {
        "point72": {"portal": "greenhouse:point72", "url": "https://point72.com/careers"},
        "point72 duplicate": {"portal": "greenhouse:point72", "url": "https://point72.com/jobs"},
        "ninja van": {"portal": "lever:ninjavan", "url": "https://careers.ninjavan.co"},
        "hcltech": {"portal": "phenom:careers.hcltech.com", "url": "https://careers.hcltech.com"},
    }

    boards = scanner.direct_boards_from_registry(registry)

    assert boards == [
        ("greenhouse", "point72", "point72"),
        ("lever", "ninjavan", "ninja van"),
    ]


def test_scan_direct_boards_returns_only_new_matching_roles():
    boards = [
        ("greenhouse", "point72", "Point72"),
        ("lever", "ninjavan", "Ninja Van"),
    ]
    fetchers = {
        "greenhouse": lambda slug: [
            _job("greenhouse", slug, "1", "Point72"),
            _job("greenhouse", slug, "2", "Point72", title="Senior Counsel"),
        ],
        "lever": lambda slug: [_job("lever", slug, "3", "Ninja Van")],
    }

    result = scanner.scan_direct_boards(boards, seen={"greenhouse:point72:1"}, fetchers=fetchers)

    assert result["all_open_matching"] == 2
    assert [job["id"] for job in result["new"]] == ["lever:ninjavan:3"]
    assert result["scanned"] == 2
    assert result["errors"] == []


def test_target_jobs_excludes_senior_domain_only_roles():
    senior = _job(
        "lever", "acme", "senior-1", "Acme",
        title="Senior Software Engineer", location="Singapore",
    )

    assert scanner.target_jobs([senior]) == []


def test_apac_location_without_singapore_is_not_a_singapore_role():
    apac = _job(
        "lever", "acme", "apac-1", "Acme",
        title="Graduate Software Engineer", location="APAC",
    )

    assert apac["sg"] is False


def test_direct_fetchers_reject_malformed_http_200_payloads(monkeypatch):
    monkeypatch.setattr(scanner, "get_json", lambda *args, **kwargs: {})

    for fetcher in (scanner.fetch_greenhouse, scanner.fetch_workable):
        try:
            fetcher("acme")
        except ValueError as error:
            assert "jobs" in str(error)
        else:
            raise AssertionError(f"{fetcher.__name__} must reject malformed schema")


def test_internship_is_not_a_full_time_graduate_candidate():
    job = _job(
        "greenhouse", "acme", "intern-1", "Acme",
        title="Junior Software Engineer Internship", location="Singapore",
    )

    assert job["grad"] is False


def test_contract_part_time_and_temporary_roles_are_not_full_time_candidates():
    for suffix in ("Contract", "Part Time", "Temporary", "Apprenticeship"):
        job = _job(
            "greenhouse", "acme", suffix, "Acme",
            title=f"Junior Software Engineer - {suffix}", location="Singapore",
        )
        assert job["grad"] is False, suffix


def test_mcf_outage_is_reported_per_query(monkeypatch):
    monkeypatch.setattr(scanner, "mcf_search", lambda query, page=0: (_ for _ in ()).throw(OSError("down")))

    leads, errors = scanner.fetch_mcf_leads()

    assert leads == {}
    assert len(errors) == 11
    assert all("OSError" in error for error in errors)


def test_linkedin_outage_is_reported(monkeypatch):
    monkeypatch.setattr(scanner, "li_fetch", lambda keyword, start=0: (_ for _ in ()).throw(OSError("down")))

    leads, role_count, errors = scanner.fetch_linkedin_leads()

    assert leads == {}
    assert role_count == 0
    assert len(errors) == len(scanner.LI_QUERIES) * 2


def test_linkedin_block_page_with_http_200_is_reported(monkeypatch):
    monkeypatch.setattr(scanner, "li_fetch", lambda keyword, start=0: "<html><title>Sign In | LinkedIn</title><div class='authwall'></div></html>")

    leads, role_count, errors = scanner.fetch_linkedin_leads()

    assert leads == {}
    assert role_count == 0
    assert len(errors) == len(scanner.LI_QUERIES) * 2


def test_linkedin_placeholder_cards_are_reported_as_malformed(monkeypatch):
    monkeypatch.setattr(scanner, "li_fetch", lambda keyword, start=0: "<li class='base-search-card'>broken placeholder</li>")

    leads, role_count, errors = scanner.fetch_linkedin_leads()

    assert leads == {}
    assert role_count == 0
    assert len(errors) == len(scanner.LI_QUERIES) * 2


def test_mcf_malformed_success_payload_is_reported(monkeypatch):
    monkeypatch.setattr(scanner, "get_json", lambda *args, **kwargs: {"unexpected": []})

    leads, errors = scanner.fetch_mcf_leads()

    assert leads == {}
    assert len(errors) == 11


def test_registered_leads_are_separated_from_unregistered_leads():
    registry = {
        "ninja van": {"portal": "lever:ninjavan", "url": "https://careers.ninjavan.co"}
    }
    leads = {
        "Ninja Van Pte Ltd": {
            "roles": {"Graduate Software Engineer"}, "posted_max": "2026-09-01",
            "count": 2, "sources": {"linkedin"},
        },
        "New Robotics Co": {
            "roles": {"Junior Robotics Engineer"}, "posted_max": "2026-09-01",
            "count": 1, "sources": {"mcf"},
        },
    }

    registered, unresolved = scanner.partition_registered_leads(leads, registry)

    assert registered == [{
        "company": "Ninja Van Pte Ltd",
        "registry_company": "ninja van",
        "portal": "lever:ninjavan",
        "careers_url": "https://careers.ninjavan.co",
        "roles": ["Graduate Software Engineer"],
        "posted": "2026-09-01",
        "count": 2,
        "found_via": "linkedin",
    }]
    assert list(unresolved) == ["New Robotics Co"]


def test_registered_leads_prioritize_never_checked_then_oldest_attempt():
    registry = {
        "fresh": {"portal": "web:fresh", "url": "https://fresh", "last_attempted": "2026-09-01T03:00:00Z"},
        "never": {"portal": "web:never", "url": "https://never"},
        "old": {"portal": "web:old", "url": "https://old", "last_attempted": "2026-08-01T00:00:00Z"},
    }
    leads = {
        name: {"roles": {"Graduate Engineer"}, "posted_max": "2026-09-01", "count": 1, "sources": {"linkedin"}}
        for name in ("fresh", "never", "old")
    }

    registered, _ = scanner.partition_registered_leads(leads, registry)

    assert [row["registry_company"] for row in registered] == ["never", "old", "fresh"]


def test_due_for_check_rotates_oldest_non_direct_portals():
    registry = {
        "fresh": {"portal": "phenom:fresh.example", "last_attempted": "2026-09-01T01:00:00Z"},
        "never": {"portal": "workday:never.example"},
        "old": {"portal": "web:old.example", "last_checked": "2026-08-01T00:00:00Z"},
        "direct": {"portal": "greenhouse:direct", "last_checked": "2026-01-01T00:00:00Z"},
    }

    due = cr.due_for_check(
        registry=registry,
        limit=2,
        interval_hours=24,
        now=datetime(2026, 9, 1, 4, 0, tzinfo=timezone.utc),
        excluded_portals={"greenhouse", "lever", "workable"},
    )

    assert [key for key, _ in due] == ["never", "old"]


def test_collect_verified_ids_includes_direct_and_resolved_portal_jobs():
    direct = [{"id": "greenhouse:point72:1"}]
    resolved = [{
        "company": "Acme",
        "own_portal_roles": [
            {"id": "lever:acme:2", "title": "Graduate Engineer"},
            {"title": "Role without a stable ID"},
        ],
    }]

    assert scanner.collect_verified_ids(direct, resolved) == {
        "greenhouse:point72:1", "lever:acme:2",
    }


def test_record_check_persists_attempt_and_success_metadata(tmp_path, monkeypatch):
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"acme": {"url": "https://acme.example", "portal": "web:acme"}}))
    monkeypatch.setattr(cr, "PATH", str(path))

    cr.record_check(
        "Acme", roles=["Graduate Engineer"], success=True,
        checked_at="2026-09-01T04:00:00Z",
    )

    entry = json.loads(path.read_text())["acme"]
    assert entry["last_attempted"] == "2026-09-01T04:00:00Z"
    assert entry["last_checked"] == "2026-09-01T04:00:00Z"
    assert entry["last_verified"] == "2026-09-01"
    assert entry["roles_seen"] == ["Graduate Engineer"]
    assert "check_error" not in entry


def test_record_check_failure_persists_retry_metadata(tmp_path, monkeypatch):
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"acme": {"url": "https://acme.example", "portal": "web:acme"}}))
    monkeypatch.setattr(cr, "PATH", str(path))

    cr.record_check(
        "Acme", success=False, error="HTTP 503",
        checked_at="2026-09-01T04:00:00Z",
    )

    entry = json.loads(path.read_text())["acme"]
    assert entry["last_attempted"] == "2026-09-01T04:00:00Z"
    assert entry["check_error"] == "HTTP 503"
    assert "last_checked" not in entry


def test_malformed_registry_is_not_silently_treated_as_empty(tmp_path, monkeypatch):
    path = tmp_path / "registry.json"
    path.write_text("{broken")
    monkeypatch.setattr(cr, "PATH", str(path))

    try:
        cr.load()
    except json.JSONDecodeError:
        pass
    else:
        raise AssertionError("malformed registry must raise JSONDecodeError")


def test_commit_seen_file_merges_ids_without_losing_existing_state(tmp_path, monkeypatch):
    state = tmp_path / "seen.json"
    state.write_text(json.dumps(["greenhouse:old:1"]))
    payload = tmp_path / "payload.json"
    payload.write_text(json.dumps(["lever:new:2", "greenhouse:old:1"]))
    monkeypatch.setattr(scanner, "STATE", str(state))

    scanner.commit_seen_file(str(payload))

    assert json.loads(state.read_text()) == ["greenhouse:old:1", "lever:new:2"]


def test_registry_cli_rejects_aggregator_urls(tmp_path, monkeypatch):
    monkeypatch.setattr(cr, "PATH", str(tmp_path / "registry.json"))
    payload = tmp_path / "add.json"
    payload.write_text(json.dumps({
        "company": "Acme",
        "url": "https://www.linkedin.com/jobs/view/123",
        "portal": "web:linkedin",
        "roles": [],
    }))

    try:
        registry_cli.add_file(str(payload))
    except ValueError as error:
        assert "aggregator" in str(error)
    else:
        raise AssertionError("aggregator URL must be rejected")


def test_registry_cli_rejects_additional_aggregator_domains(tmp_path, monkeypatch):
    monkeypatch.setattr(cr, "PATH", str(tmp_path / "registry.json"))
    for host in ("talent.com", "jobscentral.com.sg", "efinancialcareers.sg"):
        payload = tmp_path / "add.json"
        payload.write_text(json.dumps({
            "company": "Acme",
            "url": f"https://{host}/job/123",
            "portal": "web:aggregator",
            "roles": [],
        }))
        try:
            registry_cli.add_file(str(payload))
        except ValueError as error:
            assert "aggregator" in str(error)
        else:
            raise AssertionError(f"aggregator URL must be rejected: {host}")


def test_registry_cli_rejects_private_and_credential_bearing_urls(tmp_path, monkeypatch):
    monkeypatch.setattr(cr, "PATH", str(tmp_path / "registry.json"))
    urls = (
        "http://127.0.0.1/admin",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.1/careers",
        "https://user:secret@careers.example.com/jobs",
    )
    for url in urls:
        payload = tmp_path / "add.json"
        payload.write_text(json.dumps({
            "company": "Acme", "url": url,
            "portal": "web:acme", "roles": [],
        }))
        try:
            registry_cli.add_file(str(payload))
        except ValueError as error:
            assert "public" in str(error) or "credentials" in str(error)
        else:
            raise AssertionError(f"unsafe URL must be rejected: {url}")


def test_registry_cli_add_file_validates_and_adds_company(tmp_path, monkeypatch):
    monkeypatch.setattr(
        registry_cli.socket, "getaddrinfo",
        lambda *args, **kwargs: [(registry_cli.socket.AF_INET, 0, 0, "", ("8.8.8.8", 0))],
    )
    registry = tmp_path / "registry.json"
    payload = tmp_path / "add.json"
    payload.write_text(json.dumps({
        "company": "Acme Robotics Pte Ltd",
        "url": "https://careers.acme.example/jobs",
        "portal": "web:acme",
        "roles": ["Graduate Robotics Engineer"],
    }))
    monkeypatch.setattr(cr, "PATH", str(registry))

    assert registry_cli.add_file(str(payload)) is True

    entry = json.loads(registry.read_text())["acme robotics pte ltd"]
    assert entry["portal"] == "web:acme"
    assert entry["roles_seen"] == ["Graduate Robotics Engineer"]


def test_runtime_payload_directory_is_unique_and_private(tmp_path):
    first = registry_cli.make_run_dir(str(tmp_path))
    second = registry_cli.make_run_dir(str(tmp_path))

    assert first != second
    assert os.stat(first).st_mode & 0o777 == 0o700
    assert os.stat(second).st_mode & 0o777 == 0o700
