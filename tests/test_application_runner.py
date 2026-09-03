import json
from types import SimpleNamespace

import application_runner as runner


def _job_file(tmp_path, url="https://careers.example.com/jobs/1?x=a&y=b"):
    path = tmp_path / "job.json"
    path.write_text(json.dumps({"url": url}))
    return path


def test_dump_passes_url_as_single_subprocess_argument(tmp_path, monkeypatch):
    job = _job_file(tmp_path, "https://careers.example.com/jobs/1?x=$(unsafe)&y='quoted'")
    output = tmp_path / "dump.json"
    calls = []
    monkeypatch.setattr(runner.registry_cli, "validate_careers_url", lambda url: None)
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda command, **kwargs: calls.append((command, kwargs)) or SimpleNamespace(returncode=0, stdout='{"fields":[]}', stderr=""),
    )

    runner.run_dump(job, output)

    command, kwargs = calls[0]
    assert command[2] == "https://careers.example.com/jobs/1?x=$(unsafe)&y='quoted'"
    assert kwargs.get("shell") is not True
    assert json.loads(output.read_text()) == {"fields": []}


def test_fill_uses_submit_flag_only_when_requested(tmp_path, monkeypatch):
    job = _job_file(tmp_path)
    plan = tmp_path / "plan.json"
    plan.write_text('{"actions":[{"action":"click","target":"@button|Submit application"},{"action":"textdump"}]}')
    outdir = tmp_path / "out"
    calls = []
    monkeypatch.setattr(runner.registry_cli, "validate_careers_url", lambda url: None)
    monkeypatch.setattr(runner, "_deterministic_preflight", lambda job_file, payload: {})
    monkeypatch.setattr(
        runner.application_queue, "verify_submission_authorization", lambda path, url: {},
    )
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda command, **kwargs: calls.append(command)
        or SimpleNamespace(returncode=0, stdout='{"clickedSubmit":false}', stderr=""),
    )

    runner.run_fill(job, plan, outdir, submit=False)
    runner.run_fill(job, plan, outdir, submit=True, authorization=tmp_path / "auth.json")

    assert "--submit" not in calls[0]
    assert "--submit" in calls[1]


def test_runner_rejects_job_file_without_url(tmp_path):
    job = tmp_path / "job.json"
    job.write_text("{}")

    try:
        runner.run_dump(job, tmp_path / "dump.json")
    except ValueError as error:
        assert "url" in str(error)
    else:
        raise AssertionError("job URL is required")


def test_plan_rejects_unknown_actions_and_arbitrary_uploads(tmp_path):
    outdir = tmp_path / "run" / "artifacts"
    for plan in (
        {"actions": [{"action": "evaluate", "value": "steal()"}]},
        {"actions": [{"action": "upload", "target": "Resume", "value": "/etc/passwd"}]},
    ):
        try:
            runner.validate_plan(plan, outdir, submit=False)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe plan was accepted")


def test_security_code_actions_are_not_supported(tmp_path):
    outdir = tmp_path / "run" / "artifacts"
    plan = {"actions": [{
        "action": "await_security_code",
        "poll": "/tmp/shared-code.txt",
        "timeout_ms": 600000,
    }]}

    try:
        runner.validate_plan(plan, outdir, submit=True)
    except ValueError as error:
        assert "unsupported" in str(error)
    else:
        raise AssertionError("unsafe poll path was accepted")


def test_submit_plan_requires_exactly_one_explicit_submit_click(tmp_path):
    outdir = tmp_path / "run" / "artifacts"
    without_submit = {"actions": [{"action": "fill", "target": "Email", "value": "a@b.com"}]}
    with_submit = {"actions": [
        {"action": "fill", "target": "Email", "value": "a@b.com"},
        {"action": "click", "target": "@button|Submit application"},
        {"action": "textdump"},
    ]}

    try:
        runner.validate_plan(without_submit, outdir, submit=True)
    except ValueError:
        pass
    else:
        raise AssertionError("submit run without explicit submit click was accepted")
    runner.validate_plan(with_submit, outdir, submit=True)


def test_click_selector_unions_broad_labels_and_nth_are_rejected(tmp_path):
    outdir = tmp_path / "run" / "artifacts"
    plans = [
        {"actions": [{"action": "click", "target": "button.delete, @button|Submit"}]},
        {"actions": [{"action": "fill", "target": "@label|.*", "value": "x"}]},
        {"actions": [{"action": "fill", "target": "@label|Email", "value": "x", "nth": 1}]},
        {"actions": [{"action": "check", "target": "button[type=submit]"}]},
    ]
    for plan in plans:
        try:
            runner.validate_plan(plan, outdir, submit=False)
        except ValueError:
            pass
        else:
            raise AssertionError("broad or positional selector was accepted")


def test_greenhouse_submit_is_blocked_without_approved_code_mailbox(tmp_path, monkeypatch):
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({
        "full_auto_submit": True,
        "application_email": "srirajkavin@u.nus.edu",
        "greenhouse_code_access_confirmed": False,
    }))
    monkeypatch.setattr(runner, "POLICY_PATH", policy)
    monkeypatch.setattr(runner, "run_dump", lambda *args, **kwargs: {
        "fields": [], "portal_fingerprints": ["greenhouse"],
    })
    plan = {"actions": [
        {"action": "fill", "target": "Email", "value": "srirajkavin@u.nus.edu"},
        {"action": "click", "target": "@button|Submit application"},
    ]}

    try:
        runner._deterministic_preflight(tmp_path / "job.json", plan)
    except ValueError as error:
        assert "mailbox" in str(error)
    else:
        raise AssertionError("Greenhouse submission bypassed mailbox policy")


def test_confirmation_evidence_is_derived_from_runner_output_and_artifact(tmp_path):
    artifact = tmp_path / "final.png"
    artifact.write_bytes(b"screenshot")
    job = tmp_path / "job.json"
    job.write_text(json.dumps({"source_job_id": "job-123", "url": "https://careers.example.com/jobs/1"}))
    output = tmp_path / "submit-output.txt"
    output.write_text(
        json.dumps({
            "event": "text_after_submit",
            "url": "https://careers.example.com/confirmation",
            "text": "Thank you. Your application was received.",
        })
        + "\n"
        + json.dumps({
            "status": "done", "submitted": True, "errors": [],
            "final_url": "https://careers.example.com/jobs/1/confirmation",
            "log": [{"screenshot": str(artifact)}],
        })
    )

    evidence = runner.build_confirmation_evidence(job, output)

    assert evidence["job_id"] == "job-123"
    assert evidence["kind"] == "confirmation_page"
    assert len(evidence["artifact_sha256"]) == 64


def test_confirmation_rejects_cross_origin_and_uses_only_last_textdump(tmp_path):
    artifact = tmp_path / "final.png"
    artifact.write_bytes(b"screenshot")
    job = tmp_path / "job.json"
    job.write_text(json.dumps({"source_job_id": "job-123", "url": "https://careers.example.com/jobs/1"}))
    cases = [
        [
            {"event": "text_after_submit", "url": "https://evil.example/frame", "text": "We received your application"},
            {"status": "done", "submitted": True, "errors": [],
             "final_url": "https://careers.example.com/received", "log": [{"screenshot": str(artifact)}]},
        ],
        [
            {"event": "text_after_submit", "url": "https://careers.example.com/old", "text": "We received your application"},
            {"event": "text_after_submit", "url": "https://careers.example.com/current", "text": "Welcome to an unrelated page"},
            {"status": "done", "submitted": True, "errors": [],
             "final_url": "https://careers.example.com/current", "log": [{"screenshot": str(artifact)}]},
        ],
    ]
    for index, events in enumerate(cases):
        output = tmp_path / f"submit-output-{index}.txt"
        output.write_text("\n".join(json.dumps(event) for event in events))
        try:
            runner.build_confirmation_evidence(job, output)
        except ValueError:
            pass
        else:
            raise AssertionError("cross-origin/pre-submit text produced false confirmation")
