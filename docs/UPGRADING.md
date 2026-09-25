# Upgrading private files to schema 2.0.0

Version 2 changes ATS settings, boundary names, and queue classification. The validator
rejects older versions with a link here. It never rewrites your files. Do not replace a
populated private bio or queue with a template: that would lose answers and history.

## Before editing

Copy your private `config/bio.json`, `config/search.json`, and `data/jobs.json` into
`local/upgrade-backup/` (gitignored). Only back up files that exist. Do not commit backups.
Record your current autonomy, escalation, dry-run, application cap, spacing, and ATS choices.
Preserve them throughout the upgrade; do not adopt a higher autonomy level from a template.

## Bio configuration

Keep identity, documents, answers, experience, disclosures, and all unrelated settings.
Use `config/bio.template.json` as a structural reference, not as replacement personal data.

1. Move `agent_policy.allowed_ats` to `agent_policy.ats_support.tier_1_no_login`.
   Preserve the exact existing list. Leave `tier_2_session_based` empty: this release
   has no tier-2 adapters. If `ats_support` already exists, preserve it and compare any
   legacy list manually; do not overwrite a narrower enabled list.
2. Rename the boundary keys according to the table. Only a legacy `false` maps to the
   required `false`; a true, missing, or conflicting value needs explicit resolution.
   Do not silently weaken a restriction or treat an unknown value as consent.

| Old `hard_boundaries` key | New destination under `agent_policy` |
|---|---|
| `solve_or_bypass_captcha` | `hard_boundaries.agent_solves_or_bypasses_captcha` |
| `enter_credentials_or_create_accounts` | Both `hard_boundaries.agent_enters_credentials` and `hard_boundaries.agent_creates_accounts` |
| `supply_ssn_government_id_or_payment_info` | `hard_boundaries.agent_supplies_ssn_government_id_or_payment_info` |
| `evade_rate_limits` | `hard_boundaries.agent_evades_rate_limits` |
| `apply_via_linkedin_easy_apply` | `scope.apply_via_linkedin_easy_apply` (must remain false) |
| `apply_where_account_creation_required` | Remove the obsolete key; preserve the restriction by leaving `tier_2_session_based` empty |

3. Add `hard_boundaries.agent_fabricates_facts: false`. Retain all four mandatory
   `fact_integrity` flags as true. Add the template's white-label and conversational
   settings; `conversational_apply.attempt` must be false.
4. Use `post_run_audit.audit_sheet_path` for every review mode. If an older
   `batch.review_sheet_path` exists, move its value there after resolving any conflict.
   Full readback recording must remain true at every level.
5. Retain your existing `cover_letter_mode`. `SKIP_UNLESS_REQUIRED` leaves optional
   letters blank and escalates required ones without a supplied file. `DRAFT_IF_REQUIRED`
   permits grounded drafting when `autonomous_recovery.draft_cover_letter_when_required`
   is true. Do not silently change from one to the other.
6. Remove the stale `$schema` reference if it points to nonexistent `bio.schema.json`.
   Remove the unused `autonomous_recovery.auto_expand_search_when_thin` key: discovery
   preserves configured queries and never reads the private bio to expand them.
   Delete replaced keys only after comparing old and new behavior. Set `schema_version`
   to `2.0.0` when finished.

## Search configuration

Preserve queries, locations, filters, keyword/company exclusions, pagination, and append mode.
Move any old `ats_allowlist` restriction into the bio's enabled ATS list by taking the
intersection with existing enabled vendors. A missing or conflicting list needs manual
review; an empty intersection must not become unrestricted.

Replace `ats_allowlist` with `ats_capture`: `capture_tier_1`, `capture_tier_2`, and
`capture_unknown_hosts` are booleans. Set them to your chosen discovery scope; the template
captures all three, but capture never authorizes submission. Keep `output.jobs_file` as
`data/jobs.json`. Set `schema_version` to `2.0.0`.

## Existing queue

Work on a copy first. Preserve IDs, URLs, timestamps, existing reasons, and confirmation
evidence. Preserve every applied record and every deliberate user skip.

- Add missing `apply_shape: "unknown"`, `ats_tier: null`, `ats_host: null`,
  `white_label: false`, `resolution_hops: []`, and `encountered_conversational: false`.
  These are unknown/default metadata, not a claim about the destination.
- A previously pending row without a verified form shape becomes `needs_review` with
  `notes: "schema upgrade: classification needs reinspection"` (append to existing notes).
- Keep applied and skipped statuses unchanged. If an old skipped row lacks a reason,
  use `legacy skip; reason unavailable` and do not automatically reactivate it.
- Do not assume a vendor hostname proves a form or a session requirement. The grabber
  may revisit `needs_review` rows using the normal read-only discovery rules and refresh
  classification on observed evidence. Confirmed forms can then become pending.
- Historical applied records may retain unknown classification. Never revisit them
  for submission. Unknown shape must not be pending.
- When a manual link resolves a chatbot wrapper, classify the final destination as
  `form` if observed, update `apply_url`, and record `encountered_conversational: true`.
- Rename the old stats key `requires_account_creation_skipped` only if its meaning is
  known. Do not relabel historical skips as new captures; retain old counters as legacy
  metadata and start new counters at zero.

Set `schema_version` to `2.0.0`. Validate the full file before replacing the original
using the atomic write procedure in the grabber. Deduplication alone is not a migration.

## Verify and resume

Run `python scripts/validate.py`. Resolve errors and compare your saved operating settings
and application history with the backup. Do a dry run before resuming submissions.

On later application runs, the applier re-evaluates eligible quarantines and explicit
no-adapter skips once per run. It preserves deliberate skips, unknown legacy skip reasons,
applied rows, and quarantines with an uncertain submission outcome. See the applier §2.
