# ATS Field Notes

Observed behavior of the four in-scope platforms. Append findings here as you hit them;
`prompts/02_job_applier.md` §4.1 carries the condensed version the agent actually reads.

---

## Greenhouse — `boards.greenhouse.io`, `job-boards.greenhouse.io`

- Mostly server-rendered; standard inputs behave predictably.
- **Embedded boards** are common: `careers.example.com/jobs/123` wrapping a
  `#grnhse_app` iframe. Switch into the frame before querying fields; record the
  company-page URL as `apply_url` since that is where the working form lives.
- Resume upload offers Attach / Dropbox / Google Drive / "enter manually" —
  always use **Attach** with a local file. Cloud options require third-party auth.
- An **autofill-from-resume** step may pre-populate fields. Its parser is imperfect
  (phone numbers into name fields is a classic). Re-verify every field afterward.
- Custom questions render *below* the standard block. The submit button being visible
  is not proof you have seen every field — scroll to the true bottom.
- Job ID: trailing numeric path segment.

## Ashby — `jobs.ashbyhq.com`

- Fully client-rendered React. Programmatic input frequently does not register;
  the read-back check in §3.5 is mandatory here, not optional.
- Resume upload is a **drop-zone**, not a bare `<input>` — click it to open the picker.
- Multi-step forms are common. "Next" advances a step and is **not** a submit;
  only the final action requires the human gate.
- Typeahead fields (school, location) must have a real option clicked — an
  un-selected typeahead submits empty.
- Job ID: trailing UUID segment.

## Lever — `jobs.lever.co`

- Classic multipart form, the most stable of the four.
- URL fields are bracketed: `urls[LinkedIn]`, `urls[GitHub]`, `urls[Portfolio]` —
  map straight onto `social_links`.
- Custom questions render as separate `<fieldset>` cards with their own required
  markers; each card can carry its own validation.
- Resume input is `input[name="resume"]`; on success the page displays the parsed
  filename. Confirm that before proceeding.
- Job ID: trailing UUID segment.

## BambooHR — `*.bamboohr.com/careers/*`

- Served from the company's own subdomain; the form may render in an iframe.
- **"Desired salary" is frequently a required free-text field** — use
  `compensation.salary_answer_text`.
- Education and experience use an "Add another" repeater pattern. Fill only the first
  row unless the posting requires more.
- Field labels vary more between tenants than on the other three platforms; lean on
  visible-label matching rather than selectors.
- Job ID: trailing numeric segment.

---

---

## Tier 2 — session-based (adapters wanted)

`myworkdayjobs.com` · `icims.com` · `taleo.net` / `oraclecloud.com` ·
`successfactors.com` / `sapsf.com` · `brassring.com` · `jobvite.com` ·
`smartrecruiters.com` · `avature.net` · `phenompeople.com` · `eightfold.ai` ·
`ripplematch.com` · Handshake

These need a session **you** signed into. No adapters exist yet, so today they are
captured by discovery (`"ats_tier": 2`) and skipped at apply time with
`"skip_reason": "no tier-2 adapter for <vendor> yet"`. That is a gap, not a policy —
**[ROADMAP.md](ROADMAP.md) has the contribution path and the open design questions.**

Early field notes for anyone starting an adapter:

**Workday** — every employer is a separate tenant with a separate account
(`acme.wd1.` and `globex.wd5.` share nothing). "Signed in" must be evaluated
per-tenant. Pre-populates from a stored per-tenant profile that is frequently stale —
reconcile every pre-filled field against `bio.json` before submitting. Multi-page with
server-side state, so partial applications can be resumed rather than restarted.

**iCIMS** — closer to a single account across employers than Workday. Session
detection is the main work. Likely the easiest first tier-2 adapter.

**SmartRecruiters / Jobvite** — gate inconsistently; some postings are fully public.
Classify by observed behavior per posting, not by hostname.

Classification is by **behavior**, not hostname alone: if the first thing a page asks
for is a sign-in, treat it as tier 2 regardless of vendor, and record the vendor you
observed — that log is how the project learns which adapter to write next.

---

## LinkedIn results-pane mechanics

Observed September 2026. Platform behaviour, not the output of any particular search —
these hold for anyone running discovery.

**Classify the apply control on its accessible name.** The visible label is just
"Apply" for both external and Easy Apply postings, but the accessible name is explicit:
`"Apply to <job title> on company website"` for external. Read the a11y tree; do not
classify from a screenshot, visible text, or the external-link glyph.

**Never cache the apply element's ref across cards.** The detail pane re-renders in
place and **reuses ref ids** — the same ref points at whichever job is currently
selected. A ref captured for job A silently becomes job B's apply control after another
card is clicked. Re-resolve after every click, and check the job title inside the
accessible name against the card you clicked. This is the most likely path to applying
to the wrong posting.

**White-label career domains are common.** "Apply on company website" frequently lands
on the employer's own domain (`careers.<employer>.com`) rather than a vendor host. That
is a wrapper, not an unknown platform — resolve one hop to find the board underneath.
Large traditional employers white-label heavily, so hostname-only classification will
under-count applyable postings.

**Conversational apply exists as a third shape.** Some career sites offer
`Apply (opens in <assistant>)` or `Chat To Apply` — a chatbot (Paradox/Olivia, Mya)
rather than a form. These pages usually also offer a plain
`Go to manually apply` link, which is the path an adapter should always prefer.

---

## A note on run data

**Findings about a vendor belong here. Findings about your search do not.**

The test: would this observation hold for a different user running different queries? If
yes, it is platform behaviour and belongs in this file. If it is a fact about *your* run
— which queries you ran, which employers came back, how many results, when — it belongs
in `data/`, which is gitignored, and nowhere else.

This matters because a public repo under your own name that logs your run output
discloses your job search: what you are targeting, which employers, and when you were
looking. Employer names, LinkedIn job ids, posting titles, and result counts from a real
run are all run data. Vendor hostname *patterns* (`jobs.ashbyhq.com`), UI mechanics, and
apply-control behaviour are not.

If you want to contribute a distribution (e.g. "white-label was ~30% of external
postings across ~200 results"), aggregate counts with no employer names and no dates
tied to a person are fine and genuinely useful — see `docs/ROADMAP.md`. Per-row data
never is.
