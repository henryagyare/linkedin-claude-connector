#!/usr/bin/env python3
"""Offline sanity checks for linkedin-claude-connector.

Standard library only. No network. No writes. Exits 0 on success, 1 on failure.

Checks:
  1. Every shipped JSON file parses.
  2. config/bio.json (if present) has the required sections, a valid autonomy
     level, intact fact-integrity rules, and no leftover template values.
  3. The resume referenced by bio.json exists.
  4. data/jobs.json (if present) matches the documented schema.
  5. The three private paths are actually ignored by git.
  6. No value from your own bio.json appears in any tracked (public) file.

Usage:
    python3 scripts/validate.py
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

SCHEMA_VERSION = "2.0.0"
PRIVATE_PATHS = ("config/bio.json", "config/search.json", "data/resume.pdf", "data/jobs.json",
                 "data/jobs.json.tmp", "data/review/check.md", "data/quarantine/check.md")
REQUIRED_BIO_SECTIONS = (
    "identity",
    "location",
    "social_links",
    "education",
    "documents",
    "work_authorization",
    "compensation",
    "availability",
    "screening_questions",
    "voluntary_disclosures",
    "agent_policy",
)
TEMPLATE_MARKERS = ("example.com", "Jordan", "Rivera", "555 013 4477", "example-user")
TIER_1_KNOWN = {"greenhouse", "ashby", "lever", "bamboohr"}
REQUIRED_BOUNDARIES = (
    "agent_enters_credentials",
    "agent_creates_accounts",
    "agent_solves_or_bypasses_captcha",
    "agent_supplies_ssn_government_id_or_payment_info",
    "agent_evades_rate_limits",
    "agent_fabricates_facts",
)
VALID_STATUSES = {"pending", "applied", "skipped", "quarantined",
                  "needs_review", "failed"}
VALID_AUTONOMY = {"SUPERVISED", "BATCH_REVIEW", "TRUSTED_BATCH", "AUTOPILOT"}
VALID_ESCALATION = {"BLOCK_AND_ASK", "QUARANTINE_AND_CONTINUE"}
VALID_APPLY_SHAPES = {"form", "conversational", "unknown"}

errors: list[str] = []
warnings: list[str] = []


def load(path: Path) -> Any | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(doc, dict):
            errors.append(f"{path.relative_to(ROOT)}: expected a JSON object")
            return None
        return doc
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, UnicodeError, OSError):
        errors.append(f"{path.relative_to(ROOT)}: cannot read valid UTF-8 JSON")
        return None


def check_version(doc: dict, where: str) -> None:
    if doc.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{where}: expected schema_version {SCHEMA_VERSION}; "
                      "follow docs/UPGRADING.md before running an agent")


def check_shipped_json() -> None:
    for rel in ("config/bio.template.json", "config/search.template.json",
                "data/jobs.example.json"):
        path = ROOT / rel
        if not path.exists():
            errors.append(f"{rel}: missing (should be committed)")
        else:
            doc = load(path)
            if doc is None:
                errors.append(f"{rel}: expected a JSON object")
            elif rel.endswith("bio.template.json"):
                check_bio(doc, template=True)
            elif rel.endswith("jobs.example.json"):
                check_jobs(doc)
            else:
                check_search(doc)


def check_search(doc: Any = None) -> None:
    if doc is None:
        doc = load(ROOT / "config/search.json")
        if doc is None:
            warnings.append("config/search.json not found — copy the search template before discovery")
            return
    if not isinstance(doc, dict):
        errors.append("search: must be a JSON object")
        return
    check_version(doc, "search")
    for key in ("queries", "locations"):
        value = doc.get(key)
        if not isinstance(value, list) or not value or any(not isinstance(v, str) or not v for v in value):
            errors.append(f"search.{key}: must be a nonempty list of strings")
    pagination = doc.get("pagination")
    if not isinstance(pagination, dict):
        errors.append("search.pagination: must be an object")
    else:
        for key in ("max_pages_per_query", "max_jobs_per_query"):
            if type(pagination.get(key)) is not int or pagination[key] <= 0:
                errors.append(f"search.pagination.{key}: must be a positive integer")
    capture = doc.get("ats_capture")
    if not isinstance(capture, dict):
        errors.append("search.ats_capture: must be an object")
    else:
        for key in ("capture_tier_1", "capture_tier_2", "capture_unknown_hosts"):
            if type(capture.get(key)) is not bool:
                errors.append(f"search.ats_capture.{key}: must be boolean")
    output = doc.get("output")
    if not isinstance(output, dict) or output.get("jobs_file") != "data/jobs.json":
        errors.append("search.output.jobs_file: must be data/jobs.json")


def check_bio(bio: Any = None, *, template: bool = False) -> None:
    if bio is None:
        bio = load(ROOT / "config" / "bio.json")
    if bio is None:
        warnings.append("config/bio.json not found — copy config/bio.template.json to create it")
        return

    if not isinstance(bio, dict):
        errors.append("bio: must be a JSON object")
        return
    check_version(bio, "bio")

    for section in REQUIRED_BIO_SECTIONS:
        if section not in bio:
            errors.append(f"config/bio.json: missing required section '{section}'")
        elif not isinstance(bio[section], list if section == "education" else dict):
            errors.append(f"bio.{section}: invalid section type")
    if any(not isinstance(bio.get(s), list if s == "education" else dict)
           for s in REQUIRED_BIO_SECTIONS):
        return
    policy = bio["agent_policy"]
    for section in ("fact_integrity", "escalation", "post_run_audit", "hard_boundaries",
                    "batch", "ats_support", "scope"):
        if not isinstance(policy.get(section), dict):
            errors.append(f"bio.agent_policy.{section}: must be an object")
            return
    for key in ("tier_1_no_login", "tier_2_session_based"):
        value = policy["ats_support"].get(key)
        if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
            errors.append(f"bio.ats_support.{key}: must be a list of strings")
            return
    for key in ("max_applications_per_run", "min_seconds_between_applications"):
        if type(policy.get(key)) is not int or policy[key] <= 0:
            errors.append(f"bio.agent_policy.{key}: must be a positive integer")
            return
    if type(policy.get("dry_run")) is not bool:
        errors.append("bio.agent_policy.dry_run: must be boolean")
    if type(policy["batch"].get("batch_size")) is not int or policy["batch"]["batch_size"] <= 0:
        errors.append("bio.batch.batch_size: must be a positive integer")
    if policy["scope"].get("apply_via_linkedin_easy_apply") is not False:
        errors.append("bio.scope.apply_via_linkedin_easy_apply: must be false")
    audit = policy["post_run_audit"]
    if audit.get("record_full_readback_for_every_submission") is not True:
        errors.append("Every autonomy level requires record_full_readback_for_every_submission = true")
    if not isinstance(audit.get("audit_sheet_path"), str) or not audit["audit_sheet_path"]:
        errors.append("bio.post_run_audit.audit_sheet_path: required")

    blob = json.dumps(bio)
    hits = [m for m in TEMPLATE_MARKERS if m in blob]
    if hits and not template:
        warnings.append(
            "config/bio.json still contains template values "
            f"({', '.join(hits)}) — replace them with your own before a real run"
        )

    ask_me = [k for k, v in _walk(bio) if v == "ASK_ME"]
    if ask_me and not template:
        warnings.append(
            f"{len(ask_me)} field(s) set to ASK_ME — follow escalation.mode when required: "
            + ", ".join(ask_me[:5]) + ("…" if len(ask_me) > 5 else "")
        )

    documents = bio.get("documents") or {}
    if documents.get("cover_letter_mode") not in ("SKIP_UNLESS_REQUIRED", "DRAFT_IF_REQUIRED"):
        errors.append("documents.cover_letter_mode: expected SKIP_UNLESS_REQUIRED or DRAFT_IF_REQUIRED")
    resume_rel = documents.get("resume_path") or "data/resume.pdf"
    if not isinstance(resume_rel, str):
        errors.append("documents.resume_path: must be a path string")
    elif not template and not (ROOT / resume_rel).is_file():
        errors.append(f"{resume_rel}: resume not found (referenced by documents.resume_path)")

    policy = bio.get("agent_policy") or {}

    level = policy.get("autonomy_level")
    if not isinstance(level, str) or level not in VALID_AUTONOMY:
        errors.append(
            f"config/bio.json: agent_policy.autonomy_level is {level!r}; "
            f"expected one of {sorted(VALID_AUTONOMY)}"
        )
    elif level == "TRUSTED_BATCH":
        warnings.append(
            "autonomy_level is TRUSTED_BATCH — clean rows are auto-approved. "
            "Run once at BATCH_REVIEW on any ATS you have not watched it handle."
        )

    facts = policy.get("fact_integrity") or {}
    for key in ("never_fabricate_a_fact",
                "quarantine_row_if_required_fact_missing",
                "quarantine_row_on_legal_attestation_not_in_config",
                "voluntary_disclosures_never_substituted"):
        if facts.get(key) is not True:
            errors.append(
                f"config/bio.json: agent_policy.fact_integrity.{key} must be true. "
                "Fact integrity holds at every autonomy level."
            )

    esc = policy.get("escalation") or {}
    if type(esc.get("max_quarantined_before_abort")) is not int or esc["max_quarantined_before_abort"] <= 0:
        errors.append("escalation.max_quarantined_before_abort: must be a positive integer")
    if not isinstance(esc.get("mode"), str) or esc.get("mode") not in VALID_ESCALATION:
        errors.append(
            f"config/bio.json: agent_policy.escalation.mode is {esc.get('mode')!r}; "
            f"expected one of {sorted(VALID_ESCALATION)}"
        )
    if level == "AUTOPILOT":
        warnings.append(
            "autonomy_level is AUTOPILOT — applications submit unattended. "
            "Read data/review/<run-id>.md after each run; quarantined rows are in "
            "data/quarantine/."
        )
        if not (policy.get("post_run_audit") or {}).get(
            "record_full_readback_for_every_submission"
        ):
            errors.append(
                "AUTOPILOT requires post_run_audit."
                "record_full_readback_for_every_submission = true. "
                "Unattended submission without an audit trail is not supported."
            )
        if facts.get("autosubmit_agent_drafted_prose") is True:
            warnings.append(
                "AUTOPILOT + autosubmit_agent_drafted_prose — drafted cover letters "
                "will submit unread. Set it false to quarantine those rows instead."
            )

    boundaries = policy.get("hard_boundaries") or {}
    for key in REQUIRED_BOUNDARIES:
        if boundaries.get(key) is not False:
            errors.append(
                f"config/bio.json: agent_policy.hard_boundaries.{key} must be false. "
                "These constrain the agent, not which platforms are supported — "
                "widen ats_support instead."
            )
    for key, value in boundaries.items():
        if key.startswith("_") or key in REQUIRED_BOUNDARIES:
            continue
        if value is not False:
            errors.append(f"config/bio.json: hard_boundaries.{key} must be false.")

    batch = policy.get("batch") or {}
    size = batch.get("batch_size")
    if isinstance(size, int) and size > policy.get("max_applications_per_run", 25):
        warnings.append("batch.batch_size exceeds max_applications_per_run")

    support = policy.get("ats_support") or {}
    tier1 = set(support.get("tier_1_no_login") or [])
    tier2 = set(support.get("tier_2_session_based") or [])
    if not tier1 and not tier2:
        errors.append("config/bio.json: ats_support enables no platforms at all")
    if tier1 - TIER_1_KNOWN:
        warnings.append(
            f"tier_1_no_login lists platforms with no adapter in prompts/: "
            f"{sorted(tier1 - TIER_1_KNOWN)}"
        )
    if overlap := tier1 & tier2:
        errors.append(f"ats_support: {sorted(overlap)} listed in both tiers")
    conv = support.get("conversational_apply")
    if not isinstance(conv, dict) or conv.get("attempt") is not False:
        errors.append(
            "config/bio.json: ats_support.conversational_apply.attempt must be false. "
            "A chatbot dialogue has no field readback and no pre-submit gate, so none "
            "of the review safeguards apply to it."
        )
    if support.get("route_on_vendor_not_host") is False:
        warnings.append(
            "route_on_vendor_not_host is false — white-label domains wrapping a "
            "supported vendor will be skipped unnecessarily"
        )
    if tier2:
        errors.append(
            "No tier-2 adapters ship yet; leave tier_2_session_based empty. "
            "Enabling a vendor name alone does not install an adapter."
        )


def _walk(node: Any, prefix: str = "") -> list[tuple[str, Any]]:
    out: list[tuple[str, Any]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            out += _walk(value, f"{prefix}.{key}" if prefix else key)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            out += _walk(value, f"{prefix}[{i}]")
    else:
        out.append((prefix, node))
    return out


def check_jobs(jobs_doc: Any = None) -> None:
    if jobs_doc is None:
        jobs_doc = load(ROOT / "data" / "jobs.json")
    if jobs_doc is None:
        warnings.append("data/jobs.json not found — run prompts/01_job_grabber.md first")
        return

    if not isinstance(jobs_doc, dict):
        errors.append("jobs: must be a JSON object")
        return
    check_version(jobs_doc, "jobs")

    jobs = jobs_doc.get("jobs")
    if not isinstance(jobs, list):
        errors.append("data/jobs.json: 'jobs' must be a list")
        return

    seen: set[str] = set()
    for i, job in enumerate(jobs):
        where = f"data/jobs.json: jobs[{i}]"
        if not isinstance(job, dict):
            errors.append(f"{where}: must be an object")
            continue
        if any(job.get(k) is not None and not isinstance(job[k], str)
               for k in ("id", "status", "company", "title", "apply_url", "apply_url_normalized",
                         "ats", "apply_shape")):
            errors.append(f"{where}: invalid string field type")
            continue
        for field in ("id", "status", "company", "title", "apply_url"):
            if not job.get(field):
                errors.append(f"{where}: missing '{field}'")
        status = job.get("status")
        if status and status not in VALID_STATUSES:
            errors.append(f"{where}: unknown status '{status}'")
        if status == "quarantined" and not job.get("quarantine_reason"):
            errors.append(f"{where}: quarantined without a quarantine_reason")
        shape = job.get("apply_shape")
        if shape not in VALID_APPLY_SHAPES:
            errors.append(f"{where}: unknown apply_shape {shape!r}")
        if shape == "conversational" and status not in {"skipped", "needs_review", "quarantined"}:
            errors.append(
                f"{where}: apply_shape is conversational but status is {status!r}. "
                "Chat-based applications are never attempted."
            )
        if job.get("white_label") and job.get("ats") and not job.get("resolution_hops"):
            warnings.append(
                f"{where}: white_label with a resolved vendor but no resolution_hops "
                "— the resolution path should be recorded"
            )
        tier = job.get("ats_tier")
        account = job.get("requires_account")
        if tier is not None and (type(tier) is not int or tier not in (1, 2)):
            errors.append(f"{where}: ats_tier must be 1, 2, or null")
        if type(account) is not bool:
            errors.append(f"{where}: requires_account must be boolean")
        elif (tier == 1 and account) or (tier == 2 and not account):
            errors.append(f"{where}: ats_tier contradicts requires_account")
        if status == "pending" and (shape != "form" or tier not in (1, 2) or not job.get("ats")):
            errors.append(f"{where}: pending rows need an observed form, tier, and vendor")
        if status == "skipped" and not job.get("skip_reason"):
            errors.append(f"{where}: skipped without a skip_reason")
        key = job.get("apply_url_normalized") or job.get("apply_url")
        if key in seen:
            warnings.append(f"{where}: duplicate apply URL — {key}")
        seen.add(key)

    counts: dict[str, int] = {}
    shapes: dict[str, int] = {}
    vendors: dict[str, int] = {}
    for job in jobs:
        if not isinstance(job, dict) or any(job.get(k) is not None and not isinstance(job[k], str)
                                          for k in ("status", "apply_shape", "ats")):
            continue
        counts[job.get("status") or "?"] = counts.get(job.get("status") or "?", 0) + 1
        shapes[job.get("apply_shape") or "?"] = shapes.get(job.get("apply_shape") or "?", 0) + 1
        key = job.get("ats") or ("white-label/unresolved" if job.get("white_label") else "unknown")
        vendors[key] = vendors.get(key, 0) + 1
    print("  queue :", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "empty")
    print("  shapes:", ", ".join(f"{k}={v}" for k, v in sorted(shapes.items())))
    print("  vendor:", ", ".join(f"{k}={v}" for k, v in sorted(vendors.items())))


def check_gitignore() -> None:
    if not (ROOT / ".git").exists():
        warnings.append("not a git repository — skipping gitignore verification")
        return
    for rel in PRIVATE_PATHS:
        result = subprocess.run(
            ["git", "check-ignore", "-q", rel],
            cwd=ROOT, capture_output=True,
        )
        if result.returncode != 0:
            errors.append(
                f"PRIVACY: {rel} is NOT ignored by git. Fix .gitignore before committing."
            )


PII_FIELD_PATTERNS = (
    r"^identity\.(first_name|last_name|preferred_name|email|phone|date_of_birth|headline)$",
    r"^location\.(street_address|city|postal_code)$",
    r"^social_links\.",
    r"^education\[\d+\]\.institution$",
    r"^experience\[\d+\]\.company$",
)
# Frozen fixture values: never derive exemptions from an editable template.
SYNTHETIC_VALUES = {
    "identity.first_name": "Jordan", "identity.last_name": "Rivera",
    "identity.preferred_name": "Jordan", "identity.email": "jordan.rivera.example@gmail.com",
    "identity.phone": "+1 555 013 4477", "identity.date_of_birth": "ASK_ME",
    "identity.headline": "Computer Science student | Backend & distributed systems",
    "location.street_address": "1200 Example Ave, Apt 4B", "location.city": "Austin",
    "location.postal_code": "78701",
    "social_links.linkedin": "https://www.linkedin.com/in/example-profile",
    "social_links.github": "https://github.com/example-user",
    "social_links.portfolio": "https://example-portfolio.vercel.app",
    "social_links.personal_website": "https://example.dev",
    "education[0].institution": "Example State University",
    "experience[0].company": "Example Technologies",
}


def check_no_pii_in_tracked_files() -> None:
    """Cross-check: no identifying value from bio.json may appear in a tracked file.

    This guards the class of leak a .gitignore cannot catch — the file is public and
    the leak is something typed into it. Only genuinely identifying fields are scanned
    (name, contact, address, social links, school, employers); config machinery shares
    vocabulary with the docs by design and is skipped. Values are never printed.
    """
    bio_path = ROOT / "config" / "bio.json"
    if not bio_path.exists() or not (ROOT / ".git").exists():
        return
    bio = load(bio_path)
    if not isinstance(bio, dict):
        errors.append("PRIVACY: private bio unreadable; identifying-value scan incomplete")
        return

    fields = dict(_walk(bio))
    synthetic = all(fields.get(key) == SYNTHETIC_VALUES[key] for key in
                    ("identity.first_name", "identity.last_name", "identity.email", "identity.phone"))
    needles: list[tuple[str, str]] = []
    for field, value in _walk(bio):
        if not isinstance(value, str):
            continue
        if not any(re.match(pat, field) for pat in PII_FIELD_PATTERNS):
            continue
        v = value.strip()
        if not v or v == "ASK_ME" or (synthetic and SYNTHETIC_VALUES.get(field) == value):
            continue
        if v.startswith(("http://", "https://")):
            v = v.split("//", 1)[1]
        needles.append((field, v.lower().rstrip("/")))

    if not needles:
        return
    result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True)
    if result.returncode != 0:
        errors.append("PRIVACY: cannot enumerate tracked files; scan incomplete")
        return

    for encoded in dict.fromkeys(result.stdout.split(b"\0")):
        if not encoded:
            continue
        rel = encoded.decode("utf-8", errors="surrogateescape")
        staged = subprocess.run(["git", "show", f":{rel}"], cwd=ROOT, capture_output=True)
        if staged.returncode != 0:
            errors.append(f"PRIVACY: cannot read indexed file {rel}; scan incomplete")
            continue
        bodies = [staged.stdout.decode("utf-8", errors="replace").lower()]
        try:
            bodies.append((ROOT / rel).read_text(encoding="utf-8", errors="replace").lower())
        except FileNotFoundError:
            pass  # A locally deleted file is still scanned from the index.
        except OSError:
            errors.append(f"PRIVACY: cannot read working file {rel}; scan incomplete")
        for field, needle in needles:
            pattern = (r"(?<!\w)" + re.escape(needle) + r"(?!\w)"
                       if len(needle) < 5 else re.escape(needle))
            if any(re.search(pattern, body) for body in bodies):
                errors.append(
                    f"PRIVACY: the value of bio.json '{field}' appears in the tracked "
                    f"file {rel}. Public files carry vendor behaviour, never your own "
                    f"data (CLAUDE.md 5.4)."
                )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-only", action="store_true",
                        help="Validate shipped files and Git privacy; omit private schema/resume checks")
    args = parser.parse_args(argv)
    errors.clear()
    warnings.clear()
    print("linkedin-claude-connector — validate")
    steps = [check_shipped_json]
    if not args.repository_only:
        steps.extend((check_bio, check_search, check_jobs))
    steps.extend((check_gitignore, check_no_pii_in_tracked_files))
    for step in steps:
        try:
            step()
        except OSError:
            errors.append(f"{step.__name__}: filesystem or Git access failed")

    for w in warnings:
        print(f"  ! {w}")
    for e in errors:
        print(f"  ✗ {e}")

    if errors:
        print(f"\nFAILED — {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"\nOK — {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
