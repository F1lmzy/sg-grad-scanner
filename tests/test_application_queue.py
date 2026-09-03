import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone

import application_queue as aq

NOW = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)


def _job(**overrides):
    job = {
        "company": "GovTech Singapore",
        "title": "Technology Associate Programme - Software Engineering",
        "url": "https://jobs.careers.gov.sg/jobs/greenhouse/4005356201?gh_jid=4005356201",
        "job_id": "greenhouse:govtech:4005356201",
        "source": "scanner",
        "location": "Singapore",
        "priority": 100,
    }
    job.update(overrides)
    return job


def _public(_url):
    return None


def test_enqueue_is_idempotent_by_source_job_id(tmp_path):
    db = tmp_path / "queue.sqlite3"

    first = aq.enqueue_jobs([_job()], db_path=db, validate_url=_public, now=NOW)
    second = aq.enqueue_jobs([_job(title="Technology Associate Programme - Software Engineering, rediscovered")], db_path=db, validate_url=_public, now=NOW)

    assert first == {"inserted": 1, "duplicates": 0, "rejected": []}
    assert second == {"inserted": 0, "duplicates": 1, "rejected": []}
    jobs = aq.list_jobs(db_path=db)
    assert len(jobs) == 1
    assert jobs[0]["status"] == "pending"


def test_same_canonical_url_with_different_source_ids_is_duplicate(tmp_path):
    db = tmp_path / "queue.sqlite3"
    first = _job(job_id="linkedin:123")
    second = _job(job_id="greenhouse:4005356201")

    aq.enqueue_jobs([first], db_path=db, validate_url=_public, now=NOW)
    result = aq.enqueue_jobs([second], db_path=db, validate_url=_public, now=NOW)

    assert result["inserted"] == 0
    assert result["duplicates"] == 1
    assert len(aq.list_jobs(db_path=db)) == 1


def test_legacy_duplicate_urls_are_migrated_without_bricking_queue(tmp_path):
    db = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(db)
    connection.execute("""
        CREATE TABLE applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT, dedup_key TEXT NOT NULL UNIQUE,
            source_job_id TEXT, company TEXT NOT NULL, title TEXT NOT NULL,
            location TEXT NOT NULL, url TEXT NOT NULL, source TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0, discovered_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, next_attempt_at TEXT, claimed_at TEXT,
            claim_token TEXT, last_error TEXT, confirmation TEXT, submitted_at TEXT
        )
    """)
    base = ("GovTech", "Graduate Software Engineer", "Singapore", "scanner", NOW.isoformat(), NOW.isoformat())
    connection.execute("INSERT INTO applications (dedup_key,company,title,location,url,source,discovered_at,updated_at) VALUES (?,?,?,?,?,?,?,?)", ("id:1", *base[:3], "https://careers.example.com/jobs/1?utm_source=x", *base[3:]))
    connection.execute("INSERT INTO applications (dedup_key,company,title,location,url,source,discovered_at,updated_at) VALUES (?,?,?,?,?,?,?,?)", ("id:2", *base[:3], "https://careers.example.com/jobs/1", *base[3:]))
    connection.commit()
    connection.close()

    rows = aq.list_jobs(db_path=db)

    assert len(rows) == 1
    assert rows[0]["normalized_url"] == "https://careers.example.com/jobs/1"


def test_enqueue_rejects_ineligible_or_non_singapore_roles(tmp_path):
    db = tmp_path / "queue.sqlite3"
    jobs = [
        _job(job_id="intern", title="Junior Software Engineer Internship"),
        _job(job_id="apac", location="APAC"),
        _job(job_id="senior", title="Senior Software Engineer"),
    ]

    result = aq.enqueue_jobs(jobs, db_path=db, validate_url=_public, now=NOW)

    assert result["inserted"] == 0
    assert result["duplicates"] == 0
    assert len(result["rejected"]) == 3
    assert aq.list_jobs(db_path=db) == []


def test_data_analyst_graduate_programme_is_eligible(tmp_path):
    db = tmp_path / "queue.sqlite3"
    job = _job(
        job_id="data-analyst",
        title="Data Analyst (HealthTech Associate Programme)",
    )

    result = aq.enqueue_jobs([job], db_path=db, validate_url=_public, now=NOW)

    assert result["inserted"] == 1
    assert result["rejected"] == []


def test_claims_are_atomic_and_do_not_claim_same_job_twice(tmp_path):
    db = tmp_path / "queue.sqlite3"
    aq.enqueue_jobs([_job(), _job(job_id="second", url="https://careers.example.com/jobs/2")], db_path=db, validate_url=_public, now=NOW)

    first = aq.claim_next(db_path=db, now=NOW)
    second = aq.claim_next(db_path=db, now=NOW)

    assert first["id"] != second["id"]
    assert first["claim_token"] != second["claim_token"]
    assert aq.claim_next(db_path=db, now=NOW) is None


def test_submission_requires_matching_claim_token_and_confirmation(tmp_path, monkeypatch):
    monkeypatch.setattr(aq.registry_cli, "validate_careers_url", lambda url: None)
    db = tmp_path / "queue.sqlite3"
    aq.enqueue_jobs([_job()], db_path=db, validate_url=_public, now=NOW)
    claimed = aq.claim_next(db_path=db, now=NOW)

    for token, confirmation in (("wrong", "received"), (claimed["claim_token"], "")):
        try:
            aq.mark_submitted(claimed["id"], token, confirmation, db_path=db, now=NOW)
        except ValueError:
            pass
        else:
            raise AssertionError("submission must require token and confirmation")

    artifact = tmp_path / "sg-grad-scanner-test" / "final.png"
    artifact.parent.mkdir()
    artifact.write_bytes(b"receipt")
    evidence = {
        "kind": "confirmation_page",
        "job_id": claimed["source_job_id"],
        "final_url": "https://jobs.careers.gov.sg/confirmation",
        "confirmation_text": "Your application has been received",
        "artifact_path": str(artifact),
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
    }
    try:
        aq.mark_submitted(
            claimed["id"], claimed["claim_token"], evidence,
            db_path=db, now=NOW,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("submission completed without a durable submission boundary")
    aq.mark_submitting(claimed["id"], claimed["claim_token"], db_path=db, now=NOW)
    aq.mark_submitted(
        claimed["id"], claimed["claim_token"], evidence,
        db_path=db, now=NOW,
    )
    row = aq.list_jobs(db_path=db)[0]
    assert row["status"] == "submitted"
    assert row["submitted_at"].startswith("2026-09-01")


def test_retry_is_delayed_and_reclaimable_after_backoff(tmp_path):
    db = tmp_path / "queue.sqlite3"
    aq.enqueue_jobs([_job()], db_path=db, validate_url=_public, now=NOW)
    claimed = aq.claim_next(db_path=db, now=NOW)

    aq.mark_retry(claimed["id"], claimed["claim_token"], "portal timeout", db_path=db, now=NOW)

    assert aq.claim_next(db_path=db, now=NOW + timedelta(minutes=29)) is None
    retried = aq.claim_next(db_path=db, now=NOW + timedelta(minutes=31))
    assert retried["id"] == claimed["id"]
    assert retried["attempts"] == 2


def test_stale_submitting_job_blocks_instead_of_risking_duplicate_submission(tmp_path):
    db = tmp_path / "queue.sqlite3"
    aq.enqueue_jobs(
        [_job(), _job(job_id="second", url="https://jobs.careers.gov.sg/jobs/greenhouse/2")],
        db_path=db,
        validate_url=_public,
        now=NOW,
    )
    first = aq.claim_next(db_path=db, now=NOW)
    aq.mark_submitting(first["id"], first["claim_token"], db_path=db, now=NOW)

    next_job = aq.claim_next(db_path=db, now=NOW + timedelta(hours=1), stale_minutes=45)

    blocked = aq.list_jobs(db_path=db, status="blocked")
    assert next_job["source_job_id"] == "second"
    assert blocked[0]["id"] == first["id"]
    assert "uncertain" in blocked[0]["last_error"]


def test_submitting_job_can_be_marked_submitted(tmp_path, monkeypatch):
    monkeypatch.setattr(aq.registry_cli, "validate_careers_url", lambda url: None)
    db = tmp_path / "queue.sqlite3"
    aq.enqueue_jobs([_job()], db_path=db, validate_url=_public, now=NOW)
    claimed = aq.claim_next(db_path=db, now=NOW)
    aq.mark_submitting(claimed["id"], claimed["claim_token"], db_path=db, now=NOW)

    artifact = tmp_path / "sg-grad-scanner-test" / "final.png"
    artifact.parent.mkdir()
    artifact.write_bytes(b"receipt")
    evidence = {
        "kind": "confirmation_page",
        "job_id": claimed["source_job_id"],
        "final_url": claimed["url"],
        "confirmation_text": "Thank you, your application was received",
        "artifact_path": str(artifact),
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
    }
    aq.mark_submitted(claimed["id"], claimed["claim_token"], evidence, db_path=db, now=NOW)

    assert aq.list_jobs(db_path=db)[0]["status"] == "submitted"


def test_submission_authorization_is_job_bound_and_revoked_by_state_change(tmp_path):
    db = tmp_path / "queue.sqlite3"
    auth = tmp_path / "private-run" / "submit-auth.json"
    aq.enqueue_jobs([_job()], db_path=db, validate_url=_public, now=NOW)
    claimed = aq.claim_next(db_path=db, now=NOW)
    aq.write_submission_authorization(
        claimed["id"], claimed["claim_token"], auth, db_path=db, now=NOW
    )

    assert aq.verify_submission_authorization(auth, claimed["url"])["id"] == claimed["id"]
    assert auth.stat().st_mode & 0o777 == 0o600
    aq.mark_blocked(claimed["id"], claimed["claim_token"], "stop", db_path=db, now=NOW)
    try:
        aq.verify_submission_authorization(auth, claimed["url"])
    except ValueError:
        pass
    else:
        raise AssertionError("authorization remained valid after state change")


def test_submission_confirmation_must_be_structured_and_role_bound(tmp_path):
    db = tmp_path / "queue.sqlite3"
    aq.enqueue_jobs([_job()], db_path=db, validate_url=_public, now=NOW)
    claimed = aq.claim_next(db_path=db, now=NOW)
    for invalid in ("receipt", {"kind": "confirmation_page", "job_id": "other"}):
        try:
            aq.mark_submitted(claimed["id"], claimed["claim_token"], invalid, db_path=db, now=NOW)
        except ValueError:
            pass
        else:
            raise AssertionError("unstructured or unbound evidence must fail")


def test_third_failed_attempt_blocks_in_code(tmp_path):
    db = tmp_path / "queue.sqlite3"
    aq.enqueue_jobs([_job()], db_path=db, validate_url=_public, now=NOW)
    moment = NOW
    for attempt in range(3):
        claimed = aq.claim_next(db_path=db, now=moment)
        status = aq.mark_retry(
            claimed["id"], claimed["claim_token"], "transient", db_path=db, now=moment
        )
        moment += timedelta(days=2)
    assert status == "blocked"
    assert aq.claim_next(db_path=db, now=moment) is None


def test_submitting_job_cannot_be_automatically_retried(tmp_path):
    db = tmp_path / "queue.sqlite3"
    aq.enqueue_jobs([_job()], db_path=db, validate_url=_public, now=NOW)
    claimed = aq.claim_next(db_path=db, now=NOW)
    aq.mark_submitting(claimed["id"], claimed["claim_token"], db_path=db, now=NOW)

    try:
        aq.mark_retry(
            claimed["id"], claimed["claim_token"], "timeout", db_path=db, now=NOW
        )
    except ValueError:
        pass
    else:
        raise AssertionError("uncertain submission must not be auto-retried")


def test_stale_claim_is_recovered(tmp_path):
    db = tmp_path / "queue.sqlite3"
    aq.enqueue_jobs([_job()], db_path=db, validate_url=_public, now=NOW)
    first = aq.claim_next(db_path=db, now=NOW)

    recovered = aq.claim_next(db_path=db, now=NOW + timedelta(minutes=46), stale_minutes=45)

    assert recovered["id"] == first["id"]
    assert recovered["claim_token"] != first["claim_token"]


def test_blocked_job_can_be_requeued_after_manual_prerequisite_is_fixed(tmp_path):
    db = tmp_path / "queue.sqlite3"
    aq.enqueue_jobs([_job()], db_path=db, validate_url=_public, now=NOW)
    claimed = aq.claim_next(db_path=db, now=NOW)
    aq.mark_blocked(claimed["id"], claimed["claim_token"], "Gmail OAuth expired", db_path=db, now=NOW)

    aq.requeue_blocked(claimed["id"], db_path=db, now=NOW + timedelta(hours=1))

    reclaimed = aq.claim_next(db_path=db, now=NOW + timedelta(hours=1))
    assert reclaimed["id"] == claimed["id"]


def test_blocked_job_is_not_reclaimed(tmp_path):
    db = tmp_path / "queue.sqlite3"
    aq.enqueue_jobs([_job()], db_path=db, validate_url=_public, now=NOW)
    claimed = aq.claim_next(db_path=db, now=NOW)

    aq.mark_blocked(claimed["id"], claimed["claim_token"], "mandatory transcript missing", db_path=db, now=NOW)

    assert aq.claim_next(db_path=db, now=NOW + timedelta(days=10)) is None
    assert aq.list_jobs(db_path=db)[0]["status"] == "blocked"
