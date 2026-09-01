# Contributing

Thanks for helping. This project is small on purpose — most valuable contributions are
improvements to the two prompt files, new ATS coverage, or better field mappings.

## Before you start

Read [CLAUDE.md](CLAUDE.md), especially **§3 Non-negotiable invariants**. A PR that
weakens any of them will be declined no matter how good the code is:

- No invented **facts** — a row missing a required fact is quarantined, never guessed
- No submission without a full readback written to disk first
- No agent raising its own autonomy level or escalation mode above the config
- No credential entry or account creation
- No CAPTCHA solving or evasion
- No LinkedIn Easy Apply
- No account-gated ATS platforms
- The three private paths stay gitignored

These are the project's boundary, not a backlog.

## Setup

```bash
cp config/bio.template.json config/bio.json      # dummy data is fine
cp config/search.template.json config/search.json
python3 scripts/validate.py
```

## Good first contributions

- A new **no-login** ATS adapter (see CLAUDE.md §6)
- Better field mappings in `prompts/02_job_applier.md` §4
- Newly observed form quirks in `docs/ATS_NOTES.md`
- README clarity fixes

## PR checklist

- [ ] `python3 scripts/validate.py` exits 0
- [ ] `git status --short` shows none of the three private paths
- [ ] No real personal data anywhere in the diff (names, emails, phones, addresses)
- [ ] Prompts stayed generic — no hardcoded company, school, or year
- [ ] If the change is safety-relevant, README **and** the prompt file both updated
- [ ] Tested in `dry_run` mode against real postings; postings noted in the PR body

## Reporting a safety issue

If you find a path where the agent could submit without approval, enter credentials,
or leak PII, please open an issue marked **SAFETY** — those jump the queue.
