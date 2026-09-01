# CLAUDE.md — Developer Guide

Guidance for Claude Code / Claude Cowork (and human contributors) working **on this
repository**.

> **Read this first, and read it fully.** This project drives a real browser, handles
> real PII, and submits real job applications under a real person's name. The
> constraints below are not style preferences — several of them are the reason the
> project is safe to use at all.

---

## 1. What this repo is

A **prompt-first agent harness**. The product is not a program; it is a pair of
carefully written steering files plus a private configuration schema. There is no
long-running service, no scraper, no database, no server.

```
config/*.json   →  prompts/01_job_grabber.md  →  data/jobs.json
data/jobs.json  →  prompts/02_job_applier.md  →  filled forms → human approval → submit
```

If you are about to write a Playwright script that logs into LinkedIn, you have
misread the project. The browser is driven by an agent under human supervision, on
purpose.

---

## 2. Repository layout

| Path | Purpose | Committed? |
|---|---|---|
| `README.md` | End-user documentation | ✅ |
| `CLAUDE.md` | This file — contributor/agent guide | ✅ |
| `LICENSE` | MIT | ✅ |
| `.gitignore` | **Privacy boundary.** Do not weaken. | ✅ |
| `config/bio.template.json` | PII schema with dummy values | ✅ |
| `config/search.template.json` | Search targeting schema | ✅ |
| `config/bio.json` | The user's real PII | 🔒 **never** |
| `config/search.json` | The user's real targeting | 🔒 never |
| `prompts/01_job_grabber.md` | Discovery steering file | ✅ |
| `prompts/02_job_applier.md` | Application steering file | ✅ |
| `data/jobs.example.json` | Output schema reference | ✅ |
| `data/jobs.json` | Generated queue + application history | 🔒 **never** |
| `data/resume.pdf` | The user's resume | 🔒 **never** |
| `data/screenshots/` | Review + confirmation captures | 🔒 never |
| `scripts/validate.py` | Offline config/queue validation | ✅ |
| `docs/ATS_NOTES.md` | Per-platform form quirks | ✅ |
| `docs/ROADMAP.md` | Open problems & wanted contributions | ✅ |
| `docs/SAFETY.md` | The guarantees, stated plainly | ✅ |

---

## 3. Non-negotiable invariants

Any change that violates one of these is rejected, regardless of how well it is
implemented. If a request asks for one, say no and explain which invariant it hits.

1. **Fact integrity.** This is the invariant the autonomy dial does not reach, and
   the reason unattended submission is defensible at all.
   - **Facts** — dates, GPA, work-authorization status, years of experience, salary,
     certifications, anything a recruiter can check — trace to `config/bio.json` or to
     a one-off answer the human gave in-session. Never inferred, never derived from a
     neighbouring field, never defaulted.
   - A required fact that is missing → **quarantine the row.** Never submit it.
   - Legal attestations answer only from the user's own config.
   - `voluntary_disclosures` are never substituted.
   - **Drafting prose is explicitly allowed** (cover letters, "why this company") when
     grounded in facts already in the config, and is flagged `✎ drafted` in the audit
     sheet. Never invent an accomplishment, metric, or affiliation to fill a box.
2. **Auditability.** A full readback is written to disk *before* an application is
   submitted, at every autonomy level. An agent may never submit a row it has not
   written a readback for, and may never raise its own `autonomy_level` or
   `escalation.mode` above what `config/bio.json` sets. Where human approval *is*
   required, the answer must be a real one — never generated, inferred, or defaulted
   from a timeout.
3. **No credential handling, ever.** No password fields, no account creation, no
   session-cookie manipulation, no stored `storage_state.json`.
   **This is a constraint on the agent, not a list of forbidden sites.** Working
   inside a session the human established is explicitly fine — that is how LinkedIn
   has always worked, and it is the model tier-2 adapters use. The agent uses a
   session; it never creates one.
4. **No CAPTCHA solving or evasion.** Detect → pause → hand to the human → wait.
   Solver services and evasion heuristics are out of bounds permanently.
5. **No Easy Apply.** The LinkedIn-internal path is excluded by design, not by
   omission.
6. **Platform coverage is scope, not an invariant.** `ats_support` in the user's
   config decides which platforms apply; tier-2 (session-based) platforms are an
   **open contribution area**, not a prohibition — see `docs/ROADMAP.md`. Discovery
   captures every tier regardless, so a new adapter inherits a populated queue.
   What stays fixed is invariant 3: the agent never creates the session.
7. **The three private paths stay gitignored.** `config/bio.json`,
   `data/resume.pdf`, `data/jobs.json`. Never `git add -f` them. Never add an example
   containing real data.
8. **Prompts stay generic.** No user's name, school, graduation year, or target
   company may appear in `prompts/`. Personalization belongs in `config/`, always.
9. **Never request SSN, government ID, or payment information.** If a form does, the
   agent halts and reports.
10. **Voluntary EEO answers are never substituted.** Default is "Prefer not to say";
    only `voluntary_disclosures` in the user's own file can change it.

---

## 4. Development workflow

```bash
git clone <fork-url> && cd linkedin-claude-connector
cp config/bio.template.json config/bio.json      # dummy data is fine for dev
cp config/search.template.json config/search.json

python3 scripts/validate.py                       # schema + gitignore checks
git check-ignore -v config/bio.json data/resume.pdf data/jobs.json
```

### Before every commit

```bash
git status --short          # none of the three private paths may appear
python3 scripts/validate.py # must exit 0
```

### Branch & commit conventions

- Branches: `feat/ashby-multistep`, `fix/greenhouse-iframe`, `docs/readme-arch`
- Commits: Conventional Commits — `feat(prompts): handle Lever multi-page forms`
- Scopes: `prompts` · `config` · `docs` · `scripts` · `ci`
- One logical change per PR. A PR that touches a prompt **and** the gitignore is two PRs.

---

## 5. Coding & authoring standards

### 5.1 Prompt files (`prompts/*.md`) — the primary source code

Treat these with the rigor of production code.

- **Imperative, unambiguous, testable.** "Read the button's label text and check for
  an external-link indicator" — not "identify external applications."
- **Every instruction states its failure mode.** What does the agent do when the thing
  is missing, ambiguous, or different from the description?
- **Structure is fixed** and must be preserved when editing:
  `Prime directives → Inputs → Main loop → Mappings → Defensive protocols →
  Human gate → Output contract → Run summary`.
- **Defensive protocols use a consistent shape:** trigger → action → literal message
  to the user → resume condition.
- **Never hardcode a CSS selector as the only strategy.** Describe the element by its
  visible label and role first; selectors are hints, and ATS vendors ship redesigns.
- **Bound every loop.** Retries, pages, and applications all carry explicit caps.
- **Prefer a table to a paragraph** for any mapping the agent must look up.
- Keep lines under ~100 characters so diffs stay reviewable.

### 5.2 JSON schemas (`config/*.template.json`, `data/*.example.json`)

- Every template ships a `_README` array explaining its own use — the file must be
  self-documenting when a user opens it alone.
- Every template carries a `schema_version`; bump the minor for additive fields, the
  major for renames or removals, and note the change in the PR description.
- Dummy data is **obviously** dummy: `Jordan Rivera`, `example.com`, `555 013 4477`.
  Never a real name, a real address, or a real phone number.
- `null` means unknown. `""` means intentionally blank. `"ASK_ME"` means the agent
  must stop and ask. Do not blur those three.
- Additive changes only where possible — a user's existing `bio.json` should keep
  working after an upgrade.

### 5.3 Scripts (`scripts/*.py`)

- **Standard library only.** No dependency may be required to validate a config.
- Python 3.9+, type hints, `pathlib`, no network calls, no writes outside `data/`.
- Exit `0` on success and non-zero on failure, with a human-readable reason.
- Scripts are **helpers**, never the automation path — nothing in `scripts/` may drive
  a browser or submit anything.

### 5.4 Documentation

- Second person, present tense, plain words. "You" is the job seeker.
- Every user-facing claim about safety must correspond to an actual instruction in a
  prompt file. If the README says the agent pauses on CAPTCHAs, §7.1 of the grabber and
  §6.1 of the applier must say so too. **Docs and prompts drift apart silently — check
  both on every safety-relevant change.**

---

## 6. Adding a new ATS

The MVP covers four tier-1 platforms. Both tiers are open for contribution.

### 6.1 Tier 1 — public form, no sign-in

1. Add host patterns and job-ID extraction to `prompts/01_job_grabber.md` §4.1.
2. Add a platform subsection to `prompts/02_job_applier.md` §4.1: form framework
   (server- vs client-rendered), resume upload mechanism, iframe behavior, multi-step
   flow, known field quirks.
3. Add the slug to `agent_policy.ats_support.tier_1_no_login` in
   `config/bio.template.json`, and to `TIER_1_KNOWN` in `scripts/validate.py`.
4. Document quirks in `docs/ATS_NOTES.md`; update the tier table in `README.md`.
5. **Test in `dry_run` against at least three real postings.** Note which in the PR.

### 6.2 Tier 2 — session-based

Same steps, plus the parts that make tier 2 its own problem. Read `docs/ROADMAP.md`
before starting; several of these are unsolved and worth an issue first.

6. **Session verification before filling.** Detect an authenticated session
   affirmatively (account menu, populated profile) — never by attempting a submit and
   seeing what happens. Not signed in → quarantine, never a sign-in attempt.
7. **Tenant awareness where it applies.** Workday scopes accounts per employer, so
   "signed in" is per-tenant. An adapter that treats it globally will silently
   quarantine everything or, worse, act on the wrong session.
8. **Reconcile pre-populated fields.** Tier-2 platforms autofill from a stored profile
   that may be stale or parsed from an old resume. Every pre-filled field is
   unverified input: read it back, compare against `bio.json`, quarantine on a
   mismatch you cannot resolve. **This is invariant 1, not a nicety** — a stale stored
   profile submitting an old graduation date across forty applications, unattended, is
   exactly the failure mode this project must not have.
9. Add the slug to `_tier_2_adapters_wanted` → `tier_2_session_based` in the template,
   and leave it **out** of the default enabled list. Users opt in.
10. Test the not-signed-in path explicitly: it must quarantine cleanly and never
    attempt authentication.

---

## 7. Testing

There is no unit-test suite for prompt behavior; the tests are structured manual runs.

**Grabber checklist**
- [ ] An Easy Apply posting is skipped without a click
- [ ] An external posting resolves to the final URL after redirects
- [ ] Each of the four in-scope ATS classifies with `ats_confidence: high`
- [ ] A Workday link is captured with `ats_tier: 2`, not dropped silently
- [ ] With no tier-2 adapter enabled, that row skips at apply time with a
      `no tier-2 adapter` reason — never a sign-in attempt
- [ ] Re-running does not duplicate records or overwrite `applied` entries
- [ ] A mid-run interruption loses at most one checkpoint of work

**Applier checklist**
- [ ] Preflight fails cleanly on a missing `bio.json` or resume
- [ ] A required field with no mapping triggers a stop-and-ask
- [ ] The review block lists every filled field plus what was left blank
- [ ] `dry_run: true` refuses to submit even when the human answers `yes`
- [ ] `skip` and `stop run` do exactly what they say
- [ ] A post-submit validation error re-runs the **full** review gate
- [ ] EEO fields remain "Prefer not to say" unless `bio.json` says otherwise

---

## 8. When in doubt

Ask the human. This repository's whole thesis is that a five-second question is
cheaper than a wrong application sent under someone's name.
