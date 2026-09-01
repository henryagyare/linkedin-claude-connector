# Safety Guarantees

Plain statements of what this project does and does not do. Each one corresponds to a
specific instruction in a prompt file; the citation is there so you can verify it
yourself rather than trusting this page.

## What it will never do

| Guarantee | Enforced in |
|---|---|
| Never invent a **fact** — dates, GPA, work authorization, experience, salary — at any autonomy level | `02_job_applier.md` §0.2, §6.3 |
| Never submit a row whose required facts did not come from your config; quarantine it instead | `02_job_applier.md` §7.4 |
| Never submit a row without writing a full readback to disk first | `02_job_applier.md` §1.1, §7.4 |
| Never substitute a voluntary EEO answer | `02_job_applier.md` §0.4, §4 |
| Never raise its own autonomy level or escalation mode above your config | `02_job_applier.md` §7.5 |
| Never enter a password, create an account, or handle credentials *(working inside a session you established is fine — that is how LinkedIn already works)* | `01_job_grabber.md` §0.2 · `02_job_applier.md` §0.3, §6.2 |
| Never solve, bypass, or automate around a CAPTCHA | `01_job_grabber.md` §7.1 · `02_job_applier.md` §6.1 |
| Never touch LinkedIn Easy Apply | `01_job_grabber.md` §0.3, §2.4 |
| Never *create* an account to apply — a sign-in wall quarantines, never an attempt | `01_job_grabber.md` §4.2 · `02_job_applier.md` §6.2 |
| Never submit a tier-2 platform's pre-populated values without reconciling them against your config | `02_job_applier.md` §6.2 |
| Never supply an SSN, government ID, or payment information | `02_job_applier.md` §6.6 |
| Never change a voluntary EEO answer away from your stated preference | `02_job_applier.md` §0.4, §4 |
| Never commit your PII | `.gitignore` (hard-blocked, defense in depth) |

## What it does when something goes wrong

Every abnormal condition resolves to the same shape: **screenshot → stop → tell the
human exactly what is on screen and what is needed → wait.** No retry loops, no
workarounds, no silent continuation.

| Condition | Behavior |
|---|---|
| CAPTCHA / bot check | Pause, browser stays open, you solve it, reply `resume`; state re-verified before continuing |
| LinkedIn login wall | Pause, you sign in manually; the agent never types credentials |
| Application sign-in wall | Tier-2 handling: applied if you enabled that adapter and are signed in, quarantined if you are not, skipped if no adapter exists yet. Never a sign-in attempt. |
| Unmapped required field | Prose and unambiguous selects resolved autonomously and flagged; a missing **fact** or legal attestation quarantines the row. One-off answers are used once and never written into `bio.json` |
| Page layout drift | Re-derived by role and label, verified against two cards; stops only when the Easy Apply / external fork becomes uncertain |
| Company/title mismatch | Mark `needs_review`, never fill the form |
| Rate limit | Checkpoint, report, stop — never evade |
| Write failure | Keep results in memory, report, offer the JSON inline |

## Data handling

- Everything runs on your machine, in your browser, against your own session.
- Nothing is uploaded anywhere. There is no server and no telemetry.
- `config/bio.json`, `data/resume.pdf`, and `data/jobs.json` are gitignored three ways:
  by exact path, by `**/` glob, and by directory rule.
- Screenshots taken for the review gate live in `data/screenshots/` and are gitignored.

## What is still on you

- You are responsible for every application submitted under your name. Read the review
  block before typing `yes`.
- LinkedIn's Terms of Service restrict automated access. The agent behaves like a slow
  human, but the account risk is yours. Keep runs small.
- Quality beats volume. `max_applications_per_run` defaults to 10 deliberately.

## A note on autonomy

This project supports fully unattended operation. At `AUTOPILOT` the agent submits
applications without asking, and at `QUARANTINE_AND_CONTINUE` it never interrupts a
run — it parks what it cannot resolve and hands you the pile at the end. That is a
supported configuration, not a workaround.

What the dial does not reach is **factual integrity**. The agent will write your cover
letter; it will not invent your GPA, your graduation date, your years of experience, or
your work-authorization status. A row missing a required fact is quarantined rather
than guessed — because the cost of a wrong answer is not a bad application, it is a
false statement to an employer, made at scale, under your name, that you never saw.

That is also why every submission gets a full readback on disk before it is sent, even
when nobody is watching. Unattended is fine. Unreconstructable is not.

The practical advice, which is advice and not a rule: run `BATCH_REVIEW` for one batch
on each new ATS before switching that config to `AUTOPILOT`. You are checking the field
mappings, not the agent's honesty.

The hard boundaries — CAPTCHAs, credentials, account creation, rate-limit evasion —
are not autonomy settings. They are the difference between a tool that automates
*your* work and one that circumvents someone else's access controls, and no config
flag exposes them.

Note what those boundaries do **not** say: they name no platform. Which sites this
project supports is a scope question with an open backlog
([docs/ROADMAP.md](ROADMAP.md)) — session-based platforms like Workday are a gap
waiting on an adapter, not a prohibition. The constraint is that the agent uses a
session you established rather than creating one, which is exactly what it already
does with LinkedIn.
