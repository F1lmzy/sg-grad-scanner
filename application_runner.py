#!/usr/bin/env python3
"""Shell-safe wrapper around the job application Playwright engines."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

import application_queue
import registry_cli
import safe_connect_proxy

SKILL_DIR = Path(os.path.expanduser("~/.hermes/skills/productivity/job-application-autofill"))
ENGINE_DIR = SKILL_DIR / "scripts"
DUMP_ENGINE = ENGINE_DIR / "jobform_dump.mjs"
FILL_ENGINE = ENGINE_DIR / "jobform_fill.mjs"
POLICY_PATH = Path("/home/kavin/jobscan/application_policy.json")
GOOGLE_SETUP = Path("/home/kavin/.hermes/skills/productivity/google-workspace/scripts/setup.py")
RESUME_PATH = Path("/home/kavin/Documents/Job_App/Sri_Rajkavin_Resume.pdf")
ALLOWED_ACTIONS = {
    "wait", "fill", "select", "check", "upload", "click", "textdump", "dump",
}
CLICK_LABEL = re.compile(r"apply|submit|verify|confirm|next|continue|save|agree|accept", re.I)
SUBMIT_LABEL = re.compile(r"submit|send application|apply(?: now)?", re.I)


def _load_job(job_file):
    payload = json.loads(Path(job_file).read_text())
    if not isinstance(payload, dict) or not isinstance(payload.get("url"), str):
        raise ValueError("job file must contain a url")
    if not payload["url"].lower().startswith("https://"):
        raise ValueError("application URLs must use HTTPS")
    registry_cli.validate_careers_url(payload["url"])
    return payload


def _atomic_write(path, content):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}-", dir=target.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _execute(command, timeout, extra_env=None):
    with safe_connect_proxy.safe_proxy() as proxy:
        environment = os.environ.copy()
        environment["JOBFORM_PROXY"] = proxy
        environment.update(extra_env or {})
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=environment,
        )
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "runner failed").strip()[-2000:]
        raise RuntimeError(message)
    return result.stdout


def validate_plan(plan, outdir, submit=False):
    if not isinstance(plan, dict) or not isinstance(plan.get("actions"), list):
        raise ValueError("plan must contain an actions list")
    if len(plan["actions"]) > 100:
        raise ValueError("plan has too many actions")
    submit_clicks = 0
    submit_index = -1
    for index, step in enumerate(plan["actions"]):
        if not isinstance(step, dict) or step.get("action") not in ALLOWED_ACTIONS:
            raise ValueError(f"unsupported action at index {index}")
        action = step["action"]
        target = str(step.get("target") or "")
        if "nth" in step:
            raise ValueError("nth selectors are not allowed")
        if len(target) > 500:
            raise ValueError("action target is too long")
        if target.startswith("@label|") and not re.fullmatch(
            r"@label\|[A-Za-z0-9 /'&,:.-]{2,160}", target
        ):
            raise ValueError("label targets must be literal and narrowly scoped")
        targeted = {"fill", "select", "check", "upload", "click"}
        if action in targeted and not target:
            raise ValueError(f"{action} requires a target")
        if action in {"fill", "select"} and not isinstance(
            step.get("value"), (str, int, float)
        ):
            raise ValueError(f"{action} requires a scalar value")
        if action == "upload" and Path(str(step.get("value") or "")).resolve() != RESUME_PATH:
            raise ValueError("upload path is not an approved profile artifact")
        if action == "check" and not target.startswith("@label|"):
            raise ValueError("check requires an exact literal label target")
        if action == "click":
            if not re.fullmatch(r"@button\|[A-Za-z0-9 /'&,:.-]{2,120}", target):
                raise ValueError("clicks require a literal @button target")
            if re.search(r"delete|remove|withdraw|cancel|purchase|pay|sign out", target, re.I):
                raise ValueError("destructive click target is forbidden")
            if not CLICK_LABEL.search(target[8:]):
                raise ValueError("click target is not an approved form control")
            if SUBMIT_LABEL.search(target[8:]):
                submit_clicks += 1
                submit_index = index
        if action == "wait" and not 0 <= int(step.get("ms") or 1000) <= 15000:
            raise ValueError("wait exceeds 15 seconds")

    if submit and submit_clicks != 1:
        raise ValueError("submit plan must contain exactly one explicit submit click")
    if submit and not any(
        step.get("action") == "textdump" for step in plan["actions"][submit_index + 1:]
    ):
        raise ValueError("submit plan must capture confirmation text after the click")
    return plan


def _target_matches(target, label):
    pattern = str(target or "")
    if pattern.startswith("@label|"):
        pattern = pattern[7:]
    return pattern.strip().casefold() == label.strip().casefold()


def _origin(url):
    parsed = urllib.parse.urlsplit(str(url))
    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), port


def _deterministic_preflight(job_file, plan):
    policy = json.loads(POLICY_PATH.read_text())
    if not policy.get("full_auto_submit"):
        raise ValueError("full-auto submission is disabled by policy")
    for step in plan["actions"]:
        target = str(step.get("target") or "")
        value = str(step.get("value") or "").strip()
        if re.search(r"\be-?mail\b", target, re.I) and step["action"] == "fill":
            if value.casefold() != str(policy["application_email"]).casefold():
                raise ValueError("application email differs from approved policy")
        if re.search(r"sponsor|work eligib|work author", target, re.I):
            if not re.search(r"needs? sponsorship|require sponsorship|^yes$", value, re.I):
                raise ValueError("work-authorization answer contradicts sponsorship policy")
        if re.search(r"salary|compensation", target, re.I) and value.casefold() not in {"", "open"}:
            raise ValueError("salary answer contradicts policy")

    with tempfile.TemporaryDirectory(prefix="application-preflight-") as temporary:
        dump = run_dump(job_file, Path(temporary) / "dump.json")
    required = []
    for field in dump.get("fields") or []:
        label = str(field.get("label") or "").strip().rstrip("*").strip()
        if field.get("req") and label and label.casefold() not in {"select...", "select"}:
            required.append(label)
    targets = [step.get("target") for step in plan["actions"] if step.get("target")]
    missing = [label for label in required if not any(_target_matches(target, label) for target in targets)]
    if missing:
        raise ValueError("required fields are not resolved: " + ", ".join(missing[:8]))

    if "greenhouse" in (dump.get("portal_fingerprints") or []):
        if not policy.get("greenhouse_code_access_confirmed"):
            raise ValueError("Greenhouse code mailbox access is not approved")
        auth = subprocess.run(
            [sys.executable, str(GOOGLE_SETUP), "--check"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        if auth.returncode != 0 or "AUTHENTICATED" not in auth.stdout:
            raise ValueError("Gmail OAuth is not authenticated for Greenhouse verification")
    return dump


def _json_objects(text):
    decoder = json.JSONDecoder()
    objects = []
    position = 0
    while position < len(text):
        start = text.find("{", position)
        if start < 0:
            break
        try:
            value, end = decoder.raw_decode(text, start)
            if isinstance(value, dict):
                objects.append(value)
            position = end
        except json.JSONDecodeError:
            position = start + 1
    return objects


def build_confirmation_evidence(job_file, output_file):
    job = json.loads(Path(job_file).read_text())
    objects = _json_objects(Path(output_file).read_text())
    final = next((item for item in reversed(objects) if item.get("status") in {"done", "failed"}), None)
    texts = [item for item in objects if item.get("event") == "text_after_submit"]
    final_text = texts[-1] if texts else {}
    confirmation_text = str(final_text.get("text") or "").strip()
    if not final or final.get("status") != "done" or final.get("submitted") is not True:
        raise ValueError("runner output does not prove a submission click")
    if final.get("errors"):
        raise ValueError("runner output contains validation errors")
    if not re.search(
        r"thank you.{0,100}application|(?:we have )?received your application|"
        r"your application (?:has been|was|is) (?:received|submitted)|"
        r"application successfully submitted",
        confirmation_text, re.I,
    ):
        raise ValueError("runner output lacks explicit confirmation text")
    screenshots = [entry.get("screenshot") for entry in final.get("log") or [] if entry.get("screenshot")]
    if not screenshots:
        raise ValueError("runner output lacks a confirmation artifact")
    artifact = Path(screenshots[-1]).resolve()
    if not artifact.is_relative_to(Path(output_file).resolve().parent) or not artifact.is_file():
        raise ValueError("confirmation artifact is outside RUN_DIR or missing")
    final_url = str(final.get("final_url") or "")
    if not final_url.startswith("https://"):
        raise ValueError("confirmation final URL is not HTTPS")
    if _origin(final_url) != _origin(str(job.get("url") or "")):
        raise ValueError("confirmation URL is not bound to the queued job origin")
    if _origin(str(final_text.get("url") or "")) != _origin(str(job.get("url") or "")):
        raise ValueError("confirmation text came from a cross-origin frame")
    return {
        "kind": "confirmation_page",
        "job_id": job.get("source_job_id"),
        "final_url": final_url,
        "confirmation_text": confirmation_text[:1000],
        "artifact_path": str(artifact),
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
    }


def run_dump(job_file, output_file, timeout=100):
    job = _load_job(job_file)
    stdout = _execute(["node", str(DUMP_ENGINE), job["url"], "90000"], timeout)
    parsed = json.loads(stdout)
    if not isinstance(parsed, dict):
        raise ValueError("dump engine output must be a JSON object")
    _atomic_write(output_file, stdout)
    return parsed


def run_fill(job_file, plan_file, outdir, submit=False, timeout=180, authorization=None):
    job = _load_job(job_file)
    plan = json.loads(Path(plan_file).read_text())
    validate_plan(plan, outdir, submit=submit)
    if submit:
        if not authorization:
            raise ValueError("submission authorization is required")
        application_queue.verify_submission_authorization(authorization, job["url"])
        _deterministic_preflight(job_file, plan)
        application_queue.verify_submission_authorization(authorization, job["url"])
    command = [
        "node", str(FILL_ENGINE), job["url"], str(plan_file),
        "--outdir", str(outdir),
    ]
    if submit:
        command.append("--submit")
    environment = {}
    if submit:
        environment = {
            "JOBFORM_AUTHORIZATION": str(Path(authorization).resolve()),
            "JOBFORM_QUEUE_CLI": str(Path(application_queue.__file__).resolve()),
        }
    return _execute(command, timeout, extra_env=environment)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    dump = sub.add_parser("dump")
    dump.add_argument("job_file")
    dump.add_argument("output_file")
    fill = sub.add_parser("fill")
    fill.add_argument("job_file")
    fill.add_argument("plan_file")
    fill.add_argument("outdir")
    fill.add_argument("--submit", action="store_true")
    fill.add_argument("--result")
    fill.add_argument("--authorization")
    evidence = sub.add_parser("evidence")
    evidence.add_argument("job_file")
    evidence.add_argument("output_file")
    evidence.add_argument("evidence_file")
    args = parser.parse_args(argv)
    if args.command == "dump":
        result = run_dump(args.job_file, args.output_file)
        print(json.dumps({
            "status": "dumped",
            "output": args.output_file,
            "fields": len(result.get("fields") or []),
            "portal_fingerprints": result.get("portal_fingerprints") or [],
        }, sort_keys=True))
    elif args.command == "fill":
        output = run_fill(
            args.job_file, args.plan_file, args.outdir, submit=args.submit,
            authorization=args.authorization,
        )
        if args.result:
            _atomic_write(args.result, output)
        sys.stdout.write(output)
    else:
        result = build_confirmation_evidence(args.job_file, args.output_file)
        _atomic_write(args.evidence_file, json.dumps(result, indent=2, sort_keys=True))
        print(json.dumps({"status": "evidence_verified", "output": args.evidence_file}))


if __name__ == "__main__":
    main(sys.argv[1:])
