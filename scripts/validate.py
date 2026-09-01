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

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

PRIVATE_PATHS = ("config/bio.json", "data/resume.pdf", "data/jobs.json")
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
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        errors.append(f"{path.relative_to(ROOT)}: invalid JSON — {exc}")
        return None


def check_shipped_json() -> None:
    for rel in ("config/bio.template.json", "config/search.template.json",
                "data/jobs.example.json"):
        path = ROOT / rel
        if not path.exists():
            errors.append(f"{rel}: missing (should be committed)")
        else:
            load(path)


def check_bio() -> None:
    bio = load(ROOT / "config" / "bio.json")
    if bio is None:
        warnings.append("config/bio.json not found — copy config/bio.template.json to create it")
        return

    for section in REQUIRED_BIO_SECTIONS:
        if section not in bio:
            errors.append(f"config/bio.json: missing required section '{section}'")

    blob = json.dumps(bio)
    hits = [m for m in TEMPLATE_MARKERS if m in blob]
    if hits:
        warnings.append(
            "config/bio.json still contains template values "
            f"({', '.join(hits)}) — replace them with your own before a real run"
        )

    ask_me = [k for k, v in _walk(bio) if v == "ASK_ME"]
    if ask_me:
        warnings.append(
            f"{len(ask_me)} field(s) set to ASK_ME — the agent will pause and ask: "
            + ", ".join(ask_me[:5]) + ("…" if len(ask_me) > 5 else "")
        )

    documents = bio.get("documents") or {}
    resume_rel = documents.get("resume_path") or "data/resume.pdf"
    if not (ROOT / resume_rel).exists():
        errors.append(f"{resume_rel}: resume not found (referenced by documents.resume_path)")

    policy = bio.get("agent_policy") or {}

    level = policy.get("autonomy_level")
    if level not in VALID_AUTONOMY:
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
    if esc.get("mode") not in VALID_ESCALATION:
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
    conv = (support.get("conversational_apply") or {})
    if conv.get("attempt") is True:
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
        warnings.append(
            f"tier-2 adapters enabled: {sorted(tier2)}. These need a session you sign "
            "into yourself; rows quarantine when you are not signed in."
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


def check_jobs() -> None:
    jobs_doc = load(ROOT / "data" / "jobs.json")
    if jobs_doc is None:
        warnings.append("data/jobs.json not found — run prompts/01_job_grabber.md first")
        return

    jobs = jobs_doc.get("jobs")
    if not isinstance(jobs, list):
        errors.append("data/jobs.json: 'jobs' must be a list")
        return

    seen: set[str] = set()
    for i, job in enumerate(jobs):
        where = f"data/jobs.json: jobs[{i}]"
        for field in ("id", "status", "company", "title", "apply_url"):
            if not job.get(field):
                errors.append(f"{where}: missing '{field}'")
        status = job.get("status")
        if status and status not in VALID_STATUSES:
            errors.append(f"{where}: unknown status '{status}'")
        if status == "quarantined" and not job.get("quarantine_reason"):
            errors.append(f"{where}: quarantined without a quarantine_reason")
        shape = job.get("apply_shape")
        if shape is not None and shape not in VALID_APPLY_SHAPES:
            errors.append(f"{where}: unknown apply_shape {shape!r}")
        if shape == "conversational" and status not in {"skipped", "needs_review"}:
            errors.append(
                f"{where}: apply_shape is conversational but status is {status!r}. "
                "Chat-based applications are never attempted."
            )
        if job.get("white_label") and job.get("ats") and not job.get("resolution_hops"):
            warnings.append(
                f"{where}: white_label with a resolved vendor but no resolution_hops "
                "— the resolution path should be recorded"
            )
        if job.get("requires_account") and status not in {"skipped", "needs_review"}:
            errors.append(f"{where}: requires_account is true but status is '{status}'")
        key = job.get("apply_url_normalized") or job.get("apply_url")
        if key in seen:
            warnings.append(f"{where}: duplicate apply URL — {key}")
        seen.add(key)

    counts: dict[str, int] = {}
    shapes: dict[str, int] = {}
    vendors: dict[str, int] = {}
    for job in jobs:
        counts[job.get("status", "?")] = counts.get(job.get("status", "?"), 0) + 1
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
GENERIC_VALUES = {
    "united states", "computer science", "bachelor of science", "no preference",
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
    try:
        bio = json.loads(bio_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return

    needles: list[tuple[str, str]] = []
    for field, value in _walk(bio):
        if not isinstance(value, str):
            continue
        if not any(re.match(pat, field) for pat in PII_FIELD_PATTERNS):
            continue
        v = value.strip()
        if len(v) < 5 or v.lower() in GENERIC_VALUES:
            continue
        if v.startswith(("http://", "https://")):
            v = v.split("//", 1)[1]
        needles.append((field, v.lower().rstrip("/")))

    if not needles:
        return
    result = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        return

    for rel in result.stdout.split():
        if rel.endswith(".template.json"):
            continue
        try:
            body = (ROOT / rel).read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        for field, needle in needles:
            if needle in body:
                errors.append(
                    f"PRIVACY: the value of bio.json '{field}' appears in the tracked "
                    f"file {rel}. Public files carry vendor behaviour, never your own "
                    f"data (CLAUDE.md 5.4)."
                )


def main() -> int:
    print("linkedin-claude-connector — validate")
    for step in (check_shipped_json, check_bio, check_jobs, check_gitignore,
                 check_no_pii_in_tracked_files):
        step()

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
