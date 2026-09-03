#!/usr/bin/env python3
"""Idempotent queue and state machine for autonomous job applications."""

import argparse
import hashlib
import json
import os
import re
import secrets
import sqlite3
import sys
import tempfile
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import registry_cli
import sg_ats_fetch as scanner

DB_PATH = Path(os.path.expanduser("~/jobscan/application_queue.sqlite3"))
SENIOR = re.compile(r"\b(senior|principal|staff|director|head of|vice president|vp|manager)\b", re.I)
TARGET_DOMAIN = re.compile(scanner.DOMAINS.pattern + r"|data analyst|data engineer", re.I)
TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {"trk", "trackingid", "ref", "source"}
MAX_ATTEMPTS = 3


def _utc_now(now=None):
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value):
    return _utc_now(value).isoformat(timespec="seconds")


def normalize_url(url):
    parsed = urllib.parse.urlsplit(url)
    query = [
        (key, value)
        for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_KEYS
        and not key.lower().startswith(TRACKING_QUERY_PREFIXES)
    ]
    return urllib.parse.urlunsplit((
        parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/") or "/",
        urllib.parse.urlencode(sorted(query)), "",
    ))


def _eligible(job):
    title = str(job.get("title") or "").strip()
    location = str(job.get("location") or "").strip()
    if not scanner.is_full_time_grad(title):
        return False, "not a full-time graduate/entry-level title"
    if not TARGET_DOMAIN.search(title):
        return False, "outside target technical domains"
    if SENIOR.search(title) and not re.search(r"\b(junior|graduate|entry|associate)\b", title, re.I):
        return False, "senior role"
    if not scanner.SG_HINT.search(location) and not scanner.SG_HINT.search(title):
        return False, "location is not explicitly Singapore"
    return True, None


def _connect(db_path=None):
    path = Path(db_path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=30000")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dedup_key TEXT NOT NULL UNIQUE,
            source_job_id TEXT,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            location TEXT NOT NULL,
            url TEXT NOT NULL,
            normalized_url TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending','claimed','retry','submitted','blocked')),
            attempts INTEGER NOT NULL DEFAULT 0,
            discovered_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            next_attempt_at TEXT,
            claimed_at TEXT,
            claim_token TEXT,
            submission_started_at TEXT,
            last_error TEXT,
            confirmation TEXT,
            submitted_at TEXT
        )
        """
    )
    columns = {row[1] for row in connection.execute("PRAGMA table_info(applications)")}
    if "normalized_url" not in columns:
        connection.execute("ALTER TABLE applications ADD COLUMN normalized_url TEXT")
        for row in connection.execute("SELECT id, url FROM applications"):
            connection.execute(
                "UPDATE applications SET normalized_url=? WHERE id=?",
                (normalize_url(row[1]), row[0]),
            )
    if "submission_started_at" not in columns:
        connection.execute("ALTER TABLE applications ADD COLUMN submission_started_at TEXT")
    duplicates = connection.execute(
        """SELECT normalized_url FROM applications
           WHERE normalized_url IS NOT NULL
           GROUP BY normalized_url HAVING COUNT(*) > 1"""
    ).fetchall()
    if duplicates:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS application_migration_audit (
               normalized_url TEXT NOT NULL, kept_id INTEGER NOT NULL,
               removed_rows_json TEXT NOT NULL, migrated_at TEXT NOT NULL)"""
        )
    for duplicate in duplicates:
        rows = connection.execute(
            "SELECT * FROM applications WHERE normalized_url=? ORDER BY id",
            (duplicate[0],),
        ).fetchall()
        submitted = [row for row in rows if row["status"] == "submitted"]
        active = [row for row in rows if row["status"] == "claimed"]
        keeper = (submitted or active or rows)[0]
        removed = [dict(row) for row in rows if row["id"] != keeper["id"]]
        status = keeper["status"]
        error = keeper["last_error"]
        token = keeper["claim_token"]
        claimed_at = keeper["claimed_at"]
        if active and not submitted:
            status = "blocked"
            error = "legacy duplicate active claims merged; verify application status before requeue"
            token = claimed_at = None
        connection.execute(
            """UPDATE applications SET status=?, attempts=?, last_error=?,
               claim_token=?, claimed_at=? WHERE id=?""",
            (status, max(row["attempts"] for row in rows), error, token, claimed_at, keeper["id"]),
        )
        connection.executemany(
            "DELETE FROM applications WHERE id=?",
            [(row["id"],) for row in rows if row["id"] != keeper["id"]],
        )
        connection.execute(
            "INSERT INTO application_migration_audit VALUES (?,?,?,?)",
            (duplicate[0], keeper["id"], json.dumps(removed, sort_keys=True), _iso(None)),
        )
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS applications_normalized_url_uq "
        "ON applications(normalized_url)"
    )
    connection.commit()
    return connection


def _row(row):
    return dict(row) if row is not None else None


def enqueue_jobs(jobs, db_path=None, validate_url=None, now=None):
    if not isinstance(jobs, list):
        raise ValueError("enqueue payload must be a JSON list")
    validator = validate_url or registry_cli.validate_careers_url
    timestamp = _iso(now)
    inserted = duplicates = 0
    rejected = []
    connection = _connect(db_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        for raw in jobs:
            try:
                if not isinstance(raw, dict):
                    raise ValueError("job must be a JSON object")
                company = str(raw.get("company") or "").strip()
                title = str(raw.get("title") or "").strip()
                location = str(raw.get("location") or "").strip()
                url = str(raw.get("url") or "").strip()
                if not company or not title or not url:
                    raise ValueError("company, title, and url are required")
                eligible, reason = _eligible(raw)
                if not eligible:
                    raise ValueError(reason)
                validator(url)
                source_job_id = str(raw.get("job_id") or raw.get("id") or "").strip() or None
                dedup_key = f"id:{source_job_id}" if source_job_id else f"url:{normalize_url(url)}"
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO applications
                    (dedup_key, source_job_id, company, title, location, url,
                     normalized_url, source,
                     priority, discovered_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dedup_key, source_job_id, company, title, location, url,
                        normalize_url(url),
                        str(raw.get("source") or "scanner"), int(raw.get("priority") or 0),
                        timestamp, timestamp,
                    ),
                )
                if cursor.rowcount:
                    inserted += 1
                else:
                    duplicates += 1
            except (TypeError, ValueError, OSError) as exc:
                rejected.append({
                    "company": str(raw.get("company") or "") if isinstance(raw, dict) else "",
                    "title": str(raw.get("title") or "") if isinstance(raw, dict) else "",
                    "reason": str(exc),
                })
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return {"inserted": inserted, "duplicates": duplicates, "rejected": rejected}


def _recover_stale(connection, now, stale_minutes):
    cutoff = _iso(_utc_now(now) - timedelta(minutes=stale_minutes))
    timestamp = _iso(now)
    connection.execute(
        """
        UPDATE applications
        SET status='blocked', claim_token=NULL, claimed_at=NULL,
            last_error='submission outcome uncertain after stale worker; verify receipt before requeue',
            updated_at=?
        WHERE status='claimed' AND submission_started_at IS NOT NULL
          AND submission_started_at < ?
        """,
        (timestamp, cutoff),
    )
    connection.execute(
        """
        UPDATE applications
        SET status='blocked', claim_token=NULL, claimed_at=NULL,
            last_error='maximum application attempts exhausted', updated_at=?
        WHERE status='claimed' AND submission_started_at IS NULL
          AND attempts >= ? AND claimed_at < ?
        """,
        (timestamp, MAX_ATTEMPTS, cutoff),
    )
    connection.execute(
        """
        UPDATE applications
        SET status='retry', claim_token=NULL, claimed_at=NULL,
            next_attempt_at=?, last_error='stale claim recovered', updated_at=?
        WHERE status='claimed' AND submission_started_at IS NULL
          AND attempts < ? AND claimed_at < ?
        """,
        (timestamp, timestamp, MAX_ATTEMPTS, cutoff),
    )


def claim_next(db_path=None, now=None, stale_minutes=45):
    moment = _utc_now(now)
    timestamp = _iso(moment)
    connection = _connect(db_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        _recover_stale(connection, moment, stale_minutes)
        connection.execute(
            """UPDATE applications SET status='blocked',
               last_error='maximum application attempts exhausted', updated_at=?
               WHERE status IN ('pending','retry') AND attempts >= ?""",
            (timestamp, MAX_ATTEMPTS),
        )
        row = connection.execute(
            """
            SELECT * FROM applications
            WHERE status IN ('pending','retry')
              AND attempts < ?
              AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
            ORDER BY priority DESC, discovered_at ASC, id ASC
            LIMIT 1
            """,
            (MAX_ATTEMPTS, timestamp),
        ).fetchone()
        if row is None:
            connection.commit()
            return None
        token = secrets.token_urlsafe(24)
        connection.execute(
            """
            UPDATE applications
            SET status='claimed', attempts=attempts+1, claimed_at=?, claim_token=?,
                next_attempt_at=NULL, updated_at=?
            WHERE id=?
            """,
            (timestamp, token, timestamp, row["id"]),
        )
        claimed = connection.execute("SELECT * FROM applications WHERE id=?", (row["id"],)).fetchone()
        connection.commit()
        return _row(claimed)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _claimed_update(job_id, token, assignments, values, db_path=None, condition=""):
    connection = _connect(db_path)
    try:
        cursor = connection.execute(
            f"UPDATE applications SET {assignments} "
            f"WHERE id=? AND claim_token=? AND status='claimed' {condition}",
            (*values, int(job_id), token),
        )
        if cursor.rowcount != 1:
            connection.rollback()
            raise ValueError("job is not claimed with this token")
        connection.commit()
    finally:
        connection.close()


def _validate_confirmation(row, evidence):
    if not isinstance(evidence, dict):
        raise ValueError("confirmation evidence must be a JSON object")
    if evidence.get("job_id") != row["source_job_id"]:
        raise ValueError("confirmation evidence is not bound to this job ID")
    kind = evidence.get("kind")
    if kind == "confirmation_page":
        final_url = str(evidence.get("final_url") or "")
        text = str(evidence.get("confirmation_text") or "")
        digest = str(evidence.get("artifact_sha256") or "")
        artifact = Path(str(evidence.get("artifact_path") or "")).resolve()
        if not final_url.startswith("https://"):
            raise ValueError("confirmation page requires an HTTPS final URL")
        if not re.search(
            r"thank you.{0,100}application|(?:we have )?received your application|"
            r"your application (?:has been|was|is) (?:received|submitted)|"
            r"application successfully submitted",
            text, re.I,
        ):
            raise ValueError("confirmation page text is not explicit")
        final_parts = urllib.parse.urlsplit(final_url)
        job_parts = urllib.parse.urlsplit(row["url"])
        final_origin = (
            final_parts.scheme.lower(), (final_parts.hostname or "").lower(), final_parts.port or 443,
        )
        job_origin = (
            job_parts.scheme.lower(), (job_parts.hostname or "").lower(), job_parts.port or 443,
        )
        if final_origin != job_origin:
            raise ValueError("confirmation URL is not bound to the queued job origin")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("confirmation artifact SHA-256 is required")
        if not artifact.is_file() or not artifact.is_relative_to(Path("/tmp").resolve()):
            raise ValueError("confirmation artifact must exist in a private run directory")
        if not any(part.startswith("sg-grad-scanner-") for part in artifact.parts):
            raise ValueError("confirmation artifact is not in a scanner run directory")
        if hashlib.sha256(artifact.read_bytes()).hexdigest() != digest:
            raise ValueError("confirmation artifact hash mismatch")
        registry_cli.validate_careers_url(final_url)
    else:
        raise ValueError("unsupported confirmation evidence kind")
    return json.dumps(evidence, sort_keys=True)


def mark_submitted(job_id, token, confirmation, db_path=None, now=None):
    connection = _connect(db_path)
    try:
        row = connection.execute(
            "SELECT * FROM applications WHERE id=? AND claim_token=? AND status='claimed' "
            "AND submission_started_at IS NOT NULL",
            (int(job_id), token),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise ValueError("job has no authorized durable submission boundary")
    confirmation_json = _validate_confirmation(row, confirmation)
    timestamp = _iso(now)
    _claimed_update(
        job_id, token,
        "status='submitted', confirmation=?, submitted_at=?, updated_at=?, claim_token=NULL, claimed_at=NULL",
        (confirmation_json, timestamp, timestamp), db_path,
        condition="AND submission_started_at IS NOT NULL",
    )


def mark_submitting(job_id, token, db_path=None, now=None):
    timestamp = _iso(now)
    _claimed_update(
        job_id, token,
        "submission_started_at=?, updated_at=?",
        (timestamp, timestamp), db_path,
    )


def write_submission_authorization(job_id, token, output_path, db_path=None, now=None):
    mark_submitting(job_id, token, db_path=db_path, now=now)
    connection = _connect(db_path)
    try:
        row = connection.execute(
            "SELECT * FROM applications WHERE id=? AND claim_token=? AND status='claimed'",
            (int(job_id), token),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise ValueError("submission authorization could not be created")
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".submit-auth-", dir=target.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as handle:
            json.dump({
                "id": row["id"], "claim_token": token,
                "normalized_url": row["normalized_url"],
                "submission_started_at": row["submission_started_at"],
                "db_path": str(db_path or DB_PATH),
            }, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def verify_submission_authorization(path, url):
    authorization = json.loads(Path(path).read_text())
    connection = _connect(authorization.get("db_path"))
    try:
        row = connection.execute(
            """SELECT * FROM applications WHERE id=? AND claim_token=?
               AND status='claimed' AND submission_started_at IS NOT NULL""",
            (authorization.get("id"), authorization.get("claim_token")),
        ).fetchone()
    finally:
        connection.close()
    if row is None or row["normalized_url"] != normalize_url(url):
        raise ValueError("submission authorization is stale or belongs to another job")
    return dict(row)


def mark_retry(job_id, token, reason, db_path=None, now=None):
    reason = str(reason or "").strip()
    if not reason:
        raise ValueError("retry reason is required")
    connection = _connect(db_path)
    try:
        row = connection.execute(
            """SELECT attempts FROM applications
               WHERE id=? AND claim_token=? AND status='claimed'
                 AND submission_started_at IS NULL""",
            (int(job_id), token),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise ValueError("job is not claimed with this token")
    timestamp = _iso(now)
    if row["attempts"] >= MAX_ATTEMPTS:
        _claimed_update(
            job_id, token,
            "status='blocked', last_error=?, updated_at=?, claim_token=NULL, claimed_at=NULL",
            ("maximum application attempts exhausted: " + reason, timestamp), db_path,
            "AND submission_started_at IS NULL",
        )
        return "blocked"
    delay = min(30 * (2 ** max(row["attempts"] - 1, 0)), 24 * 60)
    next_attempt = _iso(_utc_now(now) + timedelta(minutes=delay))
    _claimed_update(
        job_id, token,
        "status='retry', last_error=?, next_attempt_at=?, updated_at=?, claim_token=NULL, claimed_at=NULL",
        (reason, next_attempt, timestamp), db_path,
        "AND submission_started_at IS NULL",
    )
    return "retry"


def mark_blocked(job_id, token, reason, db_path=None, now=None):
    reason = str(reason or "").strip()
    if not reason:
        raise ValueError("block reason is required")
    _claimed_update(
        job_id, token,
        "status='blocked', last_error=?, updated_at=?, claim_token=NULL, claimed_at=NULL",
        (reason, _iso(now)), db_path,
    )


def requeue_blocked(job_id, db_path=None, now=None):
    connection = _connect(db_path)
    try:
        cursor = connection.execute(
            """
            UPDATE applications
            SET status='pending', last_error=NULL, next_attempt_at=NULL,
                claim_token=NULL, claimed_at=NULL, submission_started_at=NULL,
                updated_at=?
            WHERE id=? AND status='blocked'
            """,
            (_iso(now), int(job_id)),
        )
        if cursor.rowcount != 1:
            connection.rollback()
            raise ValueError('job is not blocked')
        connection.commit()
    finally:
        connection.close()


def list_jobs(db_path=None, status=None):
    connection = _connect(db_path)
    try:
        if status:
            rows = connection.execute(
                "SELECT * FROM applications WHERE status=? ORDER BY id", (status,)
            ).fetchall()
        else:
            rows = connection.execute("SELECT * FROM applications ORDER BY id").fetchall()
        return [_row(row) for row in rows]
    finally:
        connection.close()


def _read_text(path):
    return Path(path).read_text().strip()


def _read_json(path):
    return json.loads(Path(path).read_text())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DB_PATH))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    enqueue = sub.add_parser("enqueue")
    enqueue.add_argument("payload")
    sub.add_parser("claim")
    listing = sub.add_parser("list")
    listing.add_argument("--status")
    requeue = sub.add_parser("requeue")
    requeue.add_argument("job_id", type=int)
    submitting = sub.add_parser("submitting")
    submitting.add_argument("job_id", type=int)
    submitting.add_argument("token")
    submitting.add_argument("authorization_file")
    verify_auth = sub.add_parser("verify-authorization")
    verify_auth.add_argument("authorization_file")
    verify_auth.add_argument("url")
    for name in ("submitted", "retry", "blocked"):
        command = sub.add_parser(name)
        command.add_argument("job_id", type=int)
        command.add_argument("token")
        command.add_argument("payload")
    args = parser.parse_args(argv)
    if args.command == "init":
        connection = _connect(args.db)
        connection.close()
        result = {"initialized": args.db}
    elif args.command == "enqueue":
        result = enqueue_jobs(json.loads(Path(args.payload).read_text()), db_path=args.db)
    elif args.command == "claim":
        result = claim_next(db_path=args.db)
    elif args.command == "list":
        result = list_jobs(db_path=args.db, status=args.status)
    elif args.command == "requeue":
        requeue_blocked(args.job_id, db_path=args.db)
        result = {"status": "pending", "id": args.job_id}
    elif args.command == "submitting":
        write_submission_authorization(
            args.job_id, args.token, args.authorization_file, db_path=args.db,
        )
        result = {"status": "submitting", "id": args.job_id}
    elif args.command == "verify-authorization":
        row = verify_submission_authorization(args.authorization_file, args.url)
        result = {"status": "authorized", "id": row["id"]}
    elif args.command == "submitted":
        mark_submitted(args.job_id, args.token, _read_json(args.payload), db_path=args.db)
        result = {"status": "submitted", "id": args.job_id}
    elif args.command == "retry":
        status = mark_retry(args.job_id, args.token, _read_text(args.payload), db_path=args.db)
        result = {"status": status, "id": args.job_id}
    else:
        mark_blocked(args.job_id, args.token, _read_text(args.payload), db_path=args.db)
        result = {"status": "blocked", "id": args.job_id}
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1:])
