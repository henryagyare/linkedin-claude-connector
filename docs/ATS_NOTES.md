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

## Out of scope — account required

Recorded as `Requires Account Creation` and skipped:

`myworkdayjobs.com` · `icims.com` · `taleo.net` / `oraclecloud.com` ·
`successfactors.com` / `sapsf.com` · `brassring.com` · `jobvite.com` (when gated) ·
`smartrecruiters.com` (when gated) · `avature.net` · `phenompeople.com` ·
`eightfold.ai` · `ripplematch.com` · Handshake

Classification is by **behavior**, not hostname alone: if the first thing a page asks
for is an account or a login, it is out of scope regardless of vendor.
