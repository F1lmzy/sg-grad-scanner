# SG Grad Job Scanner

Automated scanner for Singapore graduate/full-time SWE, ML/AI, Robotics, Embedded
and Quant roles. Runs as a Hermes cron job (every 4h).

## Lead engines
- Direct ATS APIs (Workday, Greenhouse, Lever, SmartRecruiters, etc.)
- MyCareersFuture (MCF) and LinkedIn guest-job feeds

All engines are LEAD ENGINES ONLY: they never emit MCF/LinkedIn/aggregate links.
Every result is resolved to the company's OWN career portal before reporting.

## Main entrypoint
`sg_ats_fetch.py` — recurring registered ATS scans + MCF/LinkedIn lead discovery,
deduped via `seen_ids.json`.

Every run:
1. Loads `careers_registry.json` and scans every registered Greenhouse, Lever,
   and Workable board once.
2. Searches MCF and LinkedIn as lead engines.
3. Reuses saved careers URLs for known lead companies and resolves unknown ones.
4. Emits up to 10 due non-API registry portals for browser/manual rechecking.

`careers_registry.py` stores company mappings and recurring check metadata.
The cron uses `registry_cli.py make-run-dir` for private mode-0700 payloads, then
records additions/checks through JSON-based CLI commands. Direct job IDs are
emitted as eligible acknowledgment candidates; only roles successfully persisted
or confirmed live and already tracked are committed to `seen_ids.json`. Source
outages and malformed HTTP-200 payloads are returned separately in
`direct_board_errors`, `mcf_errors`, and `linkedin_errors`. Singapore must be
explicit; APAC/Southeast Asia alone is insufficient. Internships,
contract/temporary, part-time, co-op/attachment, apprenticeship, and casual roles
are excluded before IDs become finalizable. Registry additions reject
aggregators, credentials, and non-public network destinations.

## Tests

```bash
uvx pytest -q tests/test_recurring_registry_scan.py
uvx pytest -q tests/test_application_queue.py tests/test_application_runner.py
```

## Autonomous application pipeline

Verified new scanner roles are persisted to `application_queue.sqlite3` only
after Obsidian reporting succeeds. `application_queue.py` provides an
idempotent SQLite state machine:

```text
pending -> claimed -> submitting -> submitted
                   -> retry -> claimed
                   -> blocked -> pending (after `requeue ID`)
```

`submitting` is a durable marker. A stale claim before that marker retries;
a stale or ambiguous claim after it blocks for receipt/account verification so
the worker cannot automatically submit the same application twice.

The `autonomous-job-applicator` Hermes cron claims at most one role hourly,
re-verifies eligibility and liveness, dumps/fills the form through the
shell-safe `application_runner.py`, and submits only with a current job-bound
authorization file. Browser traffic goes through a DNS-pinning CONNECT proxy
that blocks non-public destinations; Playwright Firefox runs with its content
sandbox enabled. Dump and dry-fill operations never auto-click Apply controls.
The runner validates the action schema, permits only the canonical resume,
enforces `application_policy.json`, checks required fields, and derives
role-bound confirmation evidence from explicit page text plus a screenshot
SHA-256. Submission authorization is rechecked by the engine immediately before
clicking the resolved, semantically verified submit control. Unknown mandatory
facts/documents, CAPTCHA/Singpass, unapproved or
expired Greenhouse mailbox access, and sponsorship incompatibility become
explicit blocked states. Retry limits are enforced in SQLite code, not only in
the agent prompt.

Browser contexts are ephemeral. Credentials, passwords, cookies, MFA secrets,
and security codes are never written to the repository, queue, Obsidian, or
cron output. A portal that requires account creation, an unavailable existing
session, MFA, CAPTCHA, or Singpass blocks for user action; the worker does not
invent credentials or bypass the challenge. Greenhouse code polling is enabled
only after `application_policy.json` records explicit mailbox-access approval
and the Google OAuth token passes a live check.

Useful commands:

```bash
python3 application_queue.py list
python3 application_queue.py list --status blocked
python3 application_queue.py requeue ID
```

## Operational rules
- User is a foreigner in SG: never report MCF/LinkedIn/aggregate links;
  always resolve to the company's own portal.
- Exit contract: script must indicate `found_via=mcf|linkedin` or a resolved
  company-portal result.
- An empty static response from a JS portal is not evidence of zero roles.