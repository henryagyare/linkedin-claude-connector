# Roadmap & Wanted Contributions

The MVP covers four platforms because those were the fastest path to something that
works — **not** because the rest are off limits. Almost everything below is open, and
the interesting problems are near the top.

If you are looking for somewhere to start, `docs/ATS_NOTES.md` is the accumulated
field knowledge and `CLAUDE.md` §5 is the authoring standard for prompt files.

---

## The two-tier model

Understanding this is most of what you need to contribute an adapter.

| Tier | What it means | Status |
|---|---|---|
| **Tier 1** | Public application form, no sign-in | Greenhouse, Ashby, Lever, BambooHR — shipped |
| **Tier 2** | Needs a session **the user signed into themselves** | Open. No adapters yet. |

The project's constraint has never been "no login sites." It is **the agent never
authenticates.** That distinction matters because the agent *already* operates inside
an authenticated session — your LinkedIn one — and has since day one. It uses the
session you established; it does not create one, does not type credentials, and does
not store a token.

A tier-2 adapter applies the same model to Workday, iCIMS, or anything else: you sign
in, the agent works inside that session, and if you are not signed in the row is
quarantined rather than attempted.

Discovery already captures tier-2 postings with `"ats_tier": 2`. So a new adapter
ships into an **already-populated queue** — users who have been running discovery for
weeks get retroactive coverage the day it lands.

---

## 🔥 Wanted: tier-2 adapters

### Workday — the big one

Workday is the largest single gap in coverage; for many campus and finance pipelines
it is most of the funnel. It is also the hardest, because of a genuinely interesting
structural problem:

**Every employer is a separate tenant with a separate account.** `acme.wd1.myworkdayjobs.com`
and `globex.wd5.myworkdayjobs.com` share a UI and nothing else — not your login, not
your profile, not your saved resume. A user with 40 Workday applications has 40
accounts. That breaks the "one session, many applications" assumption every tier-1
adapter is built on.

Open design questions, and there is no settled answer to any of them:

- How does the agent detect "signed in **to this tenant**" as distinct from "signed in
  to Workday generally"?
- Should the queue group by tenant, so a user signs into one tenant and the agent
  clears every job there in one pass? (Probably — but the grouping has to survive
  quarantines and partial runs.)
- Workday pre-populates from a stored profile per tenant. That profile may be stale,
  or parsed from an older resume. **This is a fact-integrity problem, not a
  convenience one** — a stale stored profile asserting an old graduation date, across
  40 applications, unattended, is exactly the failure this project must not have. What
  is the right read-back-and-compare contract?
- Multi-page flows with server-side state: how does an adapter resume a partially
  completed application rather than starting over?

That last cluster is the reason Workday hasn't been done yet. It is a real design
problem and a good one.

### iCIMS, SmartRecruiters, Jobvite, Avature, Eightfold

Structurally easier than Workday — closer to a single account across employers. The
main work is session detection and field mapping. Good first tier-2 adapters.

### A generic tier-2 contract

Rather than five bespoke adapters, is there a shared shape? Session verification,
tenant awareness, pre-populated-field reconciliation, and multi-step state recovery
are common to all of them. A well-designed contract in `prompts/` that individual
platforms specialize would be worth more than any single adapter.

---

## Also wanted

**Discovery**
- Sources beyond LinkedIn — company boards directly, Greenhouse/Ashby job APIs, aggregators
- Cross-source dedupe (the same job posted to LinkedIn *and* a company board)
- Better ATS classification for white-labelled and embedded boards
- Using the `needs_review` log to surface which unrecognized host recurs most — the
  project telling you which adapter to write next

**Application quality**
- Cover letter drafting that is actually good, and honest about the user's background
- Per-company tailoring from the job description, without drifting into invented facts
- Detecting and handling assessment redirects (HackerRank, CodeSignal) as a distinct outcome

**Work authorization beyond the US**
- The schema is US-shaped today: `authorized_to_work_in_us`, H1B, I-9. UK, EU, and
  Canadian applications ask different questions with different legal meanings.
  Generalizing this well — without making the common case verbose — is a real
  modelling problem and would open the project to a lot more people.

**Robustness**
- A replay harness: saved ATS pages as fixtures so adapter changes can be tested
  without hitting live postings
- Structured run telemetry (local only) to spot which mappings fail most
- Recovery from a run interrupted mid-application

**Accessibility & docs**
- Screen-reader-friendly review and audit sheets
- A walkthrough for non-engineers — the current README assumes a terminal

---

## What is not on the table

Short list, and none of it is about which platforms are supported:

- The agent entering credentials or creating accounts
- Solving or bypassing CAPTCHAs
- Evading rate limits or detection
- Fabricating facts on an application
- Supplying an SSN, government ID, or payment information

These constrain the agent's behavior, not the project's scope. A PR that widens
platform coverage is welcome; one that opens one of these is not, because they are
what separates a tool that automates *your* work from one that circumvents someone
else's access controls — and the second kind is what gets tools like this blocked for
everybody.

**LinkedIn Easy Apply** sits apart from both lists: it is excluded by design, because
the point of this project is reaching the employer's own ATS where applications are
actually read. If you disagree, open an issue — that is a design argument worth
having, not a rule.
