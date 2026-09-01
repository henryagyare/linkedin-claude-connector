<div align="center">

# 🔗 linkedin-claude-connector

**Find real jobs on LinkedIn. Apply on the company's actual ATS. Never submit without you.**

A free, open-source agent harness that pairs **Claude Code** and **Claude Cowork** with
your own browser to discover external job postings on LinkedIn and fill out
applications on **Greenhouse, Ashby, Lever, and BambooHR** — pausing for your explicit
approval before every single submit.

[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
[![Human in the loop](https://img.shields.io/badge/submits-human--approved-brightgreen.svg)](#-the-human-in-the-loop-gate)
[![No Easy Apply](https://img.shields.io/badge/LinkedIn%20Easy%20Apply-excluded-red.svg)](#-scope)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-blue.svg)](CONTRIBUTING.md)

</div>

---

## Why this exists

Mass-apply bots are a bad deal for everyone. They spray low-quality applications,
they get accounts banned, and they hand a stranger's script your personal data.

This project takes the opposite position:

- **You stay in the loop.** The agent fills the form; *you* click yes. Every time.
- **Your data never leaves your machine.** `bio.json` and your resume are hard-blocked
  from version control by design.
- **Only honest surfaces.** Public, no-login application forms. No credential entry,
  no CAPTCHA solving, no account creation, no LinkedIn Easy Apply.
- **Generic by construction.** The prompts know nothing about you. Your
  `config/search.json` and `config/bio.json` decide everything — the same repo works
  for a Summer 2027 internship hunt or a senior backend search.

It is a **tedium remover**, not an application cannon.

---

## 🎯 Scope

| | |
|---|---|
| ✅ **In scope** | Greenhouse · Ashby · Lever · BambooHR — external, no-login application forms |
| ❌ **Excluded** | LinkedIn Easy Apply (never touched, by design) |
| ⏭️ **Auto-skipped** | Workday, iCIMS, Taleo, SuccessFactors, Jobvite, SmartRecruiters, Avature, Eightfold, and anything else that gates on account creation — logged as `Requires Account Creation` |
| 🚫 **Never** | Entering passwords, creating accounts, solving CAPTCHAs, supplying SSN / government ID / bank details, submitting without your approval |

---

## 🏗️ Architecture

Two agents, one file between them. That is the whole design.

```mermaid
flowchart LR
    subgraph CFG["Your config (never committed)"]
        A1["config/search.json<br/><i>what to look for</i>"]
        A2["config/bio.json<br/><i>who you are</i>"]
        A3["data/resume.pdf"]
    end

    subgraph P1["① Grabber · prompts/01_job_grabber.md"]
        B1["Search LinkedIn"] --> B2["Scroll + paginate"]
        B2 --> B3{"Easy Apply?"}
        B3 -- yes --> B4["SKIP"]
        B3 -- no --> B5["Follow external link"]
        B5 --> B6{"Which ATS?"}
        B6 -- "GH / Ashby / Lever / Bamboo" --> B7["Capture"]
        B6 -- "Workday / iCIMS / …" --> B8["Requires Account Creation"]
    end

    HUB[("data/jobs.json<br/>the queue")]

    subgraph P2["② Applier · prompts/02_job_applier.md"]
        C1["Open apply_url"] --> C2["Map fields ← bio.json"]
        C2 --> C3["Upload resume"]
        C3 --> C4["📸 Screenshot + readback"]
        C4 --> C5{{"HUMAN APPROVAL"}}
        C5 -- yes --> C6["Submit once"]
        C5 -- "skip / edit" --> C7["Log, no submit"]
    end

    A1 --> P1
    P1 --> HUB
    HUB --> P2
    A2 --> P2
    A3 --> P2
    P2 --> HUB
```

**Why a file in the middle?** Discovery and application are separate human decisions,
separated by a durable, inspectable artifact. You can open `data/jobs.json` in an
editor, delete the jobs you do not want, and only then start applying. Nothing is
hidden in an agent's head.

---

## 📁 Repository layout

```
linkedin-claude-connector/
├── README.md                      ← you are here
├── CLAUDE.md                      ← developer guide for agents working ON this repo
├── LICENSE                        ← MIT
├── .gitignore                     ← hard-blocks bio.json, resume.pdf, jobs.json
│
├── config/
│   ├── bio.template.json          ← copy → bio.json, then fill in (PII, gitignored)
│   └── search.template.json       ← copy → search.json, then set your queries
│
├── prompts/
│   ├── 01_job_grabber.md          ← steering file: LinkedIn discovery → jobs.json
│   └── 02_job_applier.md          ← steering file: jobs.json → filled forms → your approval
│
├── data/
│   ├── jobs.example.json          ← the output schema, with samples
│   ├── jobs.json                  ← 🔒 generated queue (gitignored)
│   ├── resume.pdf                 ← 🔒 your resume (gitignored)
│   └── screenshots/               ← 🔒 review + confirmation captures (gitignored)
│
├── scripts/
│   └── validate.py                ← offline sanity checks on your config & queue
│
└── docs/
    ├── ATS_NOTES.md               ← per-platform form quirks
    └── SAFETY.md                  ← the guarantees, stated plainly
```

---

## 🚀 Setup

### Prerequisites

- [Claude Code](https://claude.com/claude-code) or **Claude Cowork** (desktop app)
- A browser the agent can drive — the **Claude in-app browser** or **Claude in Chrome**
- Python 3.9+ (only for the optional `scripts/validate.py`)
- A LinkedIn account **you are already signed into in that browser**

### 1. Clone

```bash
git clone https://github.com/<your-username>/linkedin-claude-connector.git
cd linkedin-claude-connector
```

### 2. Create your private config

```bash
cp config/bio.template.json  config/bio.json
cp config/search.template.json config/search.json
```

Open `config/bio.json` and replace every value with your own.

> **Leave a field as `"ASK_ME"` on purpose** for anything you want to answer by hand
> each time (e.g. "Why do you want to work here?"). The agent will stop and ask
> instead of inventing something.

Then set your targeting in `config/search.json`:

```jsonc
{
  "queries": ["Software Engineer Intern Summer 2027"],
  "locations": ["United States"],
  "linkedin_filters": { "date_posted": "PAST_WEEK", "experience_level": ["INTERNSHIP"] },
  "exclude_keywords": ["senior", "clearance required"]
}
```

### 3. Add your resume

```bash
cp /path/to/your/resume.pdf data/resume.pdf
```

### 4. Confirm nothing private can be committed

```bash
git check-ignore -v config/bio.json data/resume.pdf data/jobs.json
```

All three must print a matching `.gitignore` rule. If any does not — **stop** and fix
it before your first commit.

Optional deeper check:

```bash
python3 scripts/validate.py
```

---

## ▶️ Running it

### Phase 1 — Grab jobs

Open the repo in Claude Code / Cowork with a browser attached, then:

```
Read prompts/01_job_grabber.md and follow it using config/search.json.
```

The agent will search LinkedIn, scroll and paginate, skip every Easy Apply posting,
follow the "Apply on company website" links, classify the destination ATS, and write
`data/jobs.json` — checkpointing every 10 cards.

It ends with a summary and **stops**. It will not start applying on its own.

```
── Discovery complete ──────────────────────────────
LinkedIn cards seen   : 118
External ATS captured : 24   → greenhouse 11 · ashby 6 · lever 5 · bamboohr 2
Easy Apply skipped    : 71
Account-required skip : 19
────────────────────────────────────────────────────
```

### Phase 2 — Curate (recommended)

Open `data/jobs.json` yourself. Delete anything you do not actually want. Set
`"status": "skipped"` on the maybes. This one minute is the highest-leverage step in
the whole workflow.

### Phase 3 — Apply

```
Read prompts/02_job_applier.md and work the queue in data/jobs.json.
Start in dry-run for the first three.
```

For each job the agent opens the form, maps your `bio.json` onto it field by field,
uploads your resume, screenshots the filled form, and then stops:

```
── REVIEW: Example Labs — Software Engineer Intern, Summer 2027 ──
  Name       : Jordan Rivera
  Email      : jordan.rivera.example@gmail.com
  Resume     : Jordan_Rivera_Resume.pdf ✓ uploaded
  Work auth  : Authorized: Yes · Requires sponsorship: No
  EEO fields : Prefer not to say (5 fields, unchanged)
  Left blank : Cover letter (optional)
────────────────────────────────────────────────────────────────
Submit this application? (yes / edit <field> / skip / stop run)
```

Answer `yes` and it submits **once**, captures the confirmation, and moves on.
Answer anything else and it does not.

---

## 🛡️ The Human-in-the-Loop gate

The agent runs at whatever autonomy you set — including fully unattended. What does
**not** change with the dial is factual integrity:

> **Nothing is ever asserted to an employer that you did not state.**
> The agent writes prose. It does not invent facts. A row missing a required fact is
> set aside, never guessed.

That rule is what makes unattended submission defensible, so it holds at every level.

Set the dial with `agent_policy.autonomy_level`:

| Level | The agent | You review |
|---|---|---|
| `SUPERVISED` | Fills one form, stops | Each application, one at a time |
| `BATCH_REVIEW` **(default)** | Fills the whole batch uninterrupted, writes a review sheet | All of them, on one sheet |
| `TRUSTED_BATCH` | Same, but auto-approves rows where *every* field resolved cleanly from `bio.json` | Only the rows that needed a judgment call |
| `AUTOPILOT` | Submits clean rows unattended, never pausing | Nothing during the run — a full audit sheet after |

`TRUSTED_BATCH` auto-approves a row only if every required field came straight from
your config, nothing was drafted, nothing was substituted, the resume upload was
visually confirmed, and the company and title matched. A drafted cover letter, a
substituted dropdown, or a retried field routes that row to you.

A full readback of every application is written to `data/review/<run-id>.md` **before**
that application is sent — at every level, including `AUTOPILOT`. Nobody has to read
it, but what was sent is always reconstructable. `dry_run: true` disables submission
entirely at every level.

### Escalation: quarantine, don't interrupt

At high volume, "stop and ask" is the bottleneck. So it isn't the default —
`escalation.mode: "QUARANTINE_AND_CONTINUE"` is:

> When the agent hits something it can't resolve, it **parks that one job with a
> reason and keeps working the queue.** No message, no waiting. You get the pile at
> the end, with the exact fix for each.

A run of sixty produces exactly one message:

```
Submitted        : 38   (greenhouse 19 · ashby 11 · lever 6 · bamboohr 2)
Account required : 5    — expected, not errors

⚠ QUARANTINED — 3, none submitted, each needs one thing from you:
   Acme Robotics     required fact missing: years_of_experience_python
   Vertex Analytics  legal attestation not in config
   Helio Systems     identity mismatch — page showed "Senior Platform Engineer"
   Fix the first two in bio.json and they clear, along with future rows.
```

Only five things stop a run outright, and they stop rather than ask because nobody may
be watching: a CAPTCHA, a credential wall, a request for an SSN or payment details, a
rate-limit warning, or a broken config. Everything else quarantines. If quarantines
pass `max_quarantined_before_abort`, the run aborts — that many failures means a
systemic problem, and burning the queue against it wastes the queue.

### What the agent handles on its own

No interruption for any of this — it is all reversible:

retrying dropped field input (React forms drop it constantly) · re-deriving a changed
page layout by role and label · picking an unambiguous dropdown match (`TX` → `Texas`) ·
**drafting cover letters and open-ended answers** from your resume, grounded only in
facts already in your config · filling optional fields from your resume · re-ordering
the queue by deadline · widening a thin search · deduping and reclassifying · carrying
on past a dead posting.

Escalation is reserved for what is genuinely undecidable: a missing **fact** (a date, a
GPA, an authorization status), a legal attestation, or a hard boundary below.

### Defensive halts

| Situation | What the agent does |
|---|---|
| 🤖 **CAPTCHA** | **Stops the run**, checkpoints, reports how far it got. Never solves or bypasses one — no config flag opens this. |
| 🔐 **Login wall** | LinkedIn auth → stops the run (never types credentials). An *application* login wall → routine skip as `Requires Account Creation`. |
| ❓ **Missing fact / legal attestation** | **Quarantines the row and continues.** Never guesses a checkable claim, at any autonomy level. |
| 🧭 **Layout drift** | Re-derives the layout by role and label, verifies against two cards, continues. Quarantines only if it can no longer tell Easy Apply from an external apply. |
| 🆔 **SSN / ID / payment request** | **Stops the run.** Never required to apply — a page asking is compromised or not an application form. |
| 🚨 **SSN / ID / payment request** | Hard stop. These are never required to apply. |
| ⏱️ **Rate limit** | Checkpoints, reports, stops. Never tries to evade it. |

---

## 🔒 Privacy

Three files hold everything personal, and all three are blocked at the VCS boundary:

| File | Contains | Status |
|---|---|---|
| `config/bio.json` | Name, contact, address, work authorization, pay expectations | 🔒 gitignored |
| `data/resume.pdf` | Your resume | 🔒 gitignored |
| `data/jobs.json` | Your search results and application history | 🔒 gitignored |

Plus, defensively: `**/bio.json`, `**/resume.pdf`, `**/jobs.json`, `data/screenshots/`,
`.env`, and every common credential filename. Nothing is uploaded anywhere — the agent
runs on your machine, in your browser, against your session.

**Before your first push,** run `git status` and confirm none of those three appear.

---

## ⚖️ Responsible use

This tool automates a browser you control, using data you own, on public application
forms. That said:

- **You are responsible for every application submitted under your name.** Read the
  review block before you type `yes`.
- LinkedIn's Terms of Service restrict automated access. The agent behaves like a
  slow human — human-paced scrolling, no parallel scraping, no CAPTCHA evasion, no
  credential automation — but **you are accepting the risk to your own account.**
  Keep runs small.
- Quality beats volume, every time. `max_applications_per_run` defaults to 10 for a
  reason.
- Never point this at a platform requiring an account. That exclusion is a feature.

---

## 🤝 Contributing

PRs welcome — especially new ATS adapters (documented as prompt sections, not
hardcoded selectors), better field mappings, and accessibility fixes.

See [CONTRIBUTING.md](CONTRIBUTING.md) and the engineering standards in
[CLAUDE.md](CLAUDE.md).

**One hard rule for contributors:** no PR may weaken the human-in-the-loop gate, add
CAPTCHA solving, add credential entry, or add support for an ATS requiring account
creation. Those are not features awaiting implementation. They are the boundary.

---

## 📄 License

MIT — see [LICENSE](LICENSE). Free forever, for everyone.

<div align="center">
<sub>Built for job seekers who would rather spend their evening preparing than retyping their phone number for the fortieth time.</sub>
</div>
