# Contributing

Thanks for helping. This project is small on purpose — most valuable contributions are
improvements to the two prompt files, new ATS coverage, or better field mappings.

## Before you start

Two different lists, and they are often confused.

### Invariants — a PR may not weaken these

They constrain **what the agent does**. None of them names a platform.

- No invented **facts** — a row missing a required fact is quarantined, never guessed
- No submission without a full readback written to disk first
- No agent raising its own autonomy level or escalation mode above the config
- No credential entry or account creation *(working inside a session the user
  established is fine — that is how LinkedIn already works)*
- No CAPTCHA solving or evasion, no rate-limit evasion
- No supplying an SSN, government ID, or payment information
- The private paths stay gitignored

### Scope — this is a backlog, and it is open

Everything here is a gap, not a prohibition. **[docs/ROADMAP.md](docs/ROADMAP.md)** has
the details and the open design questions.

- **Tier-2 adapters** (Workday, iCIMS, SmartRecruiters, Jobvite, …) — the biggest
  coverage gap and the most interesting problem in the repo
- Discovery sources beyond LinkedIn, and cross-source dedupe
- Non-US work authorization modelling
- A fixture-based replay harness
- Accessibility and non-engineer documentation

LinkedIn Easy Apply sits between the two: excluded by design, but that is a design
argument. Open an issue rather than a PR.

## Setup

```bash
cp config/bio.template.json config/bio.json      # dummy data is fine
cp config/search.template.json config/search.json
python3 scripts/validate.py
```

## Good first contributions

- Newly observed form quirks in `docs/ATS_NOTES.md` — smallest useful PR there is
- Better field mappings in `prompts/02_job_applier.md` §4
- A new **tier-1** ATS adapter (see CLAUDE.md §6)
- README and docs clarity fixes

## If you want the hard one

A **tier-2 adapter**. Read `docs/ROADMAP.md` first — the Workday tenant-account model
and the stale-stored-profile problem are unsolved, and worth talking through in an
issue before you write code.

## PR checklist

- [ ] `python3 scripts/validate.py` exits 0
- [ ] `git status --short` shows none of the three private paths
- [ ] No real personal data anywhere in the diff (names, emails, phones, addresses)
- [ ] **No run data** — no employer names, job ids, posting titles, queries, result
      counts or run dates from a real discovery run. Examples are fully synthetic.
      Vendor behaviour belongs in docs; your search does not (CLAUDE.md §5.4)
- [ ] Prompts stayed generic — no hardcoded company, school, or year
- [ ] If the change is safety-relevant, README **and** the prompt file both updated
- [ ] Tested in `dry_run` mode against real postings; postings noted in the PR body

## Reporting a safety issue

If you find a path where the agent could submit without approval, enter credentials,
or leak PII, please open an issue marked **SAFETY** — those jump the queue.
