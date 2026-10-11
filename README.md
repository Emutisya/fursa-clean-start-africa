# Fursa | Clean Start Africa

### Your skills should travel further than your past.

**Fursa is a skill-first opportunity discovery engine.** It assembles a
user-selected skills passport, matches those skills to opportunities and
assessment pathways, and makes missing evidence visible so a human can help
plan the next step.

[![CI](https://github.com/Emutisya/fursa-clean-start-africa/actions/workflows/ci.yml/badge.svg)](https://github.com/Emutisya/fursa-clean-start-africa/actions/workflows/ci.yml)

## The invention thesis

Learning a skill and having that skill recognized are different problems.
For people rebuilding their lives after incarceration, practical experience
may not arrive with the evidence, introductions or recognition needed to
make the next opportunity accessible.

Fursa explores a bridge between **what someone can do**, **what evidence they
can choose to present**, and **where that evidence needs human assessment**.
It does not turn a person's history into a prediction of their future.
Incarceration is the problem context, not a model input.

The global ambition is a learner-controlled recognition infrastructure: portable
evidence, transparent assessment routes, and skill-based discovery across
institutions and borders. Recognition would come from accountable assessors and
qualified issuers, not an AI-generated certificate.

## Experience the working system

| Step | What Fursa does today |
| --- | --- |
| Select | Accepts skills from a bounded synthetic catalog |
| Assemble | Builds an explicitly unverified skills passport from selected skills and evidence |
| Discover | Uses learned TF-IDF vectors to rank fictional opportunities and simulated pathways |
| Explain | Shows skill overlap, matching terms and missing evidence |
| Carry | Exports a user-controlled synthetic passport as JSON |
| Review | Keeps competence assessment, credential recognition and hiring outside the model |

The interactive dashboard performs actual Python-backed inference. Evidence
selections change the gap explanation, not the opportunity ranking. A missing
match identifies a coverage gap, not a person's lack of potential.

### Design choices that matter

- **Skills lead.** Criminal history and protected characteristics are outside the input contract.
- **Discovery is not selection.** No employability score or automated hiring decision.
- **Evidence is explicit.** A checked box never becomes a verified qualification.
- **The core is portable.** Local inference needs no external APIs or downloaded weights.

**Current release:** a working local ML research prototype. Opportunities,
evidence and assessment pathways are fictional. It does not issue recognized
credentials, submit applications, place people in jobs or operate an employment
service.

## Quickstart

Clone the standalone project:

```powershell
git clone https://github.com/Emutisya/fursa-clean-start-africa.git
Set-Location fursa-clean-start-africa
```

Python **3.11 or newer**. No third-party Python dependencies, installation, API keys, network access or downloaded weights are needed.

From this project's directory, in PowerShell:

```powershell
python -m fursa serve
```

Open **http://127.0.0.1:8765**. Try Workshop maker, Energy learner, Enterprise helper or Explore a gap. Choose skills, optionally attach synthetic evidence, then explore. Export downloads only the selected, explicitly unverified synthetic passport as JSON.

The HTML is a single file with inline styles and scripts: `web\index.html`. Its layout can be previewed directly, but **learned inference requires the local Python server**, not `file://`. There is no fake JavaScript fallback. Use `?clawpilotTheme=dark` or `?clawpilotTheme=light` to override the system theme.

### Run alongside the other projects

All four projects default to port 8765. Use a separate terminal and port 8767
for Fursa when running the collection together:

```powershell
python -m fursa serve --port 8767
```

Open **http://127.0.0.1:8767**; `/api/health` reports model readiness. Keep MCP
Shield on 8765, the Guardian on 8766, and Maternity Health Copilot on 8768.
Alternatively, `--port 0` selects an available port and prints its URL. Valid
ports are 0 through 65535. An occupied port produces a startup error with a
recovery instruction, not a traceback; choose another port rather than stopping
an unrelated process.

### CLI

```powershell
python -m fursa catalog
python -m fursa match --skills "carpentry,welding" --evidence "e-carpentry"
python -m fursa match --skills "astronomy"
python -m fursa train --output models\tfidf.json
python -m fursa evaluate --output evaluation.json
python -m unittest discover -s tests -v
```

`astronomy` is deliberately catalogued without an opportunity or pathway. A no-match response means **catalogue coverage is absent**, not that someone is unsuitable.

Match responses include query diagnostics: known and unknown lexical terms,
token coverage, selected skills without catalogue opportunities or pathways,
and a catalogue-specific no-match explanation. A nonempty vector can still
have no resource match; token coverage is not a confidence or ability measure.

Each ranked resource also exposes **all** shared term contributions with the
query/resource normalized weights. Their products sum to its unrounded cosine
score; the display similarity remains rounded. The first six terms remain in
`shared_terms` for compact consumers. These are lexical explanations, not
causal evidence about a person's abilities.

Dashboard opportunity cards provide keyboard-operable contribution details with
captioned tables and row/column headers. All lexical terms are inspectable,
including terms omitted from the compact shared-term list. Values display six
decimals; any rounding difference does not affect retrieval.

Invalid dashboard skill selections are marked with `aria-invalid`, associated
with the recovery message and focused for correction before any request is
sent. Editing or reset clears the invalid state; rejected free text never
reaches inference.

The catalogue-skill toolbar has one Tab stop with Left/Right wraparound,
Home/End navigation and native Enter/Space toggles. Selection updates preserve
the active button's focus and announce `aria-pressed` without thirteen Tab stops.

Pending dashboard inference can be cancelled with its button or Escape.
Selections are retained, the explore button regains focus and late responses
cannot restore results or enable export. Cancellation is local; it is not a
claim that an already-received loopback request was erased from memory.

Dashboard coverage details distinguish unsupported selected skills from known
query vocabulary, and expose cutoff/limit/tie-break and computation fingerprints.
No-match results offer an explicit focus-return action to catalogue selections,
without suggesting that a user is unsuitable or must acquire another skill.

After valid inference, the dashboard can print a deliberately labelled
unverified discussion summary containing bounded selections, fictional
resources, simulated gaps and human-review questions. Print layout excludes
controls; editing/reset disables it and clears generated content. Printing
creates only a user-controlled local document, never a credential or submission.

Before displaying/exporting inference, the dashboard validates synthetic/review
flags, known resource IDs, finite bounded scores, current catalogue provenance,
requested selections and the portable passport checksum. Malformed or
wrong-prototype responses clear results and keep export/print disabled, including
rendering failures. This prevents accidental local contract confusion, not
authentication of a server or issuer.

`python -m fursa inspect` prints reproducible fitted vocabulary, IDF and actual
fit-document frequencies, plus resource vector sizes/norms and corpus provenance.
This is model inspection, not a new model or an outcome evaluation.

`python -m fursa inspect-term timber` traces an exact fitted vocabulary term
to opportunity, pathway and `skill:` fit documents with raw term counts and
normalized weights. It makes frequency-based IDF inspectable, not a real-world
measure of how important a skill is.

Every match carries method, fit-corpus and full-catalogue SHA-256 fingerprints,
the query fingerprint, cutoff, result limit and deterministic tie-break rule.
The catalogue hash includes simulated evidence and descriptive metadata;
the corpus hash concerns fit text only. Evidence selections do not change query
provenance or rankings. Fingerprints establish reproducibility, not authenticity.

CLI discovery supports `match --skills "solar,electrical,spreadsheets" --limit 12`
for a bounded expanded view (1 through 12, default 3). The cutoff and ranking
remain unchanged; smaller views are prefixes of larger ones. The HTTP input
schema and published evaluation continue to use the default top three.

`python -m fursa match-batch models\selections.json --output models\results.json`
accepts a UTF-8 JSON array of one to sixteen ordinary skills/evidence selection
objects, capped at 32768 bytes. All scenarios validate before inference or
output. Results retain zero-based input indices; they are simulations, not
person profiles, and are never aggregated into an ability ranking.

Skill names and evidence IDs must exactly match `catalog`. Empty, duplicate, unknown or sensitive inputs are rejected. Selected evidence must belong to a selected skill. Evidence flags change gap explanations, **never the ranking**.

Simulated pathway responses and cards now explain declared skill overlap,
lexical terms/cosine and optional simulated sample gaps just like opportunities.
Selecting a sample changes discussion text, never pathway rank or verification.

Training produces inspectable learned IDF weights in an ignored `models` directory. The tiny model is fitted deterministically on startup for CLI and HTTP inference; the persisted file is an audit artifact, not a required runtime dependency. Editing the catalogue intentionally changes its fingerprint and requires regenerating the published evaluation.

Training now exports `fursa.tfidf-audit.v1` with synthetic/review flags, tokenizer,
settings, catalogue/corpus fingerprints and fitted document frequencies.
`python -m fursa verify-model models\tfidf.json` independently refits the current
catalogue and checks provenance, vocabulary, frequencies and finite IDF weights
(absolute tolerance 1e-12 for platform math). It never loads file weights for
inference, authenticates an issuer or accepts personal training documents.

`python -m fursa compare-models models\before.json models\after.json` validates
synthetic audit shapes and the IDF/frequency formula, then reports vocabulary,
frequency, document-count, cutoff and provenance differences. Historical
fingerprints are descriptive and unverified; this does not train/load a model,
compare people or establish that retrieval improved. Optional `--output` saves it.

For POSIX systems, use `models/tfidf.json` in the training command instead. All other commands are identical.

## Experience and architecture

### Portable synthetic selections

`python -m fursa passport --skills "solar,electrical" --evidence e-solar --output models\passport.json`
atomically exports the versioned `fursa.synthetic-passport.v1` envelope with
canonical sorted selections, explicit unverified/synthetic/human-review flags,
catalogue fingerprint and a canonical content checksum. There are no names,
identifiers for people, artifacts or issuer claims. Checksums detect accidental
changes; they are not signatures, authentication or recognized credentials.
Dashboard exports use the same versioned envelope and can be validated by the CLI.

`python -m fursa import-passport models\passport.json` validates the versioned
envelope before matching. It rejects unknown fields, duplicate JSON keys,
non-UTF-8/oversized files, noncanonical selections, changed safety flags,
checksum mismatches and a different catalogue fingerprint. Older legacy dashboard
exports are intentionally not silently converted. Import is local and does not
upload or store a profile. A stale catalogue requires deliberate review/re-export.

The dashboard also imports versioned passports **locally**, checking file size,
strict UTF-8, exact fields, safety flags, allowed sorted selections, duplicate
keys, catalogue fingerprint and content checksum before replacing selections.
No file or metadata is uploaded; inference requires a separate Explore action.
Invalid files preserve existing selections, and reset/edit supersedes pending imports.

`python -m fursa convert-legacy-passport models\old.json --output models\v1.json`
deliberately converts the exact older dashboard envelope after bounded UTF-8,
field/safety and current skill/evidence validation. Unknown fields are rejected,
not discarded. Old files lack catalogue provenance, so review current mappings
before conversion; the new checksum does not authenticate the old document.

`python -m fursa compare-passports models\before.json models\after.json` validates
both envelopes and reports selection/evidence differences and before/after
resource ranks. This compares simulation states, not people, progress or ability.
Evidence-only changes leave rankings unchanged.

`python -m fursa merge-passports models\a.json models\b.json --output models\merged.json`
validates two to four envelopes and exports the deduplicated union of their
bounded selections. No input is rewritten. Merging simulations does not verify
evidence, transfer qualifications or establish any person's skills.

`python -m fursa edit-passport models\a.json --remove-skills solar --add-skills carpentry --output models\b.json`
deliberately revises a validated simulation. Removing a skill also removes its
selected simulated evidence. `--add-evidence` and `--remove-evidence` are optional
comma-separated IDs. Conflicting, duplicate, already-selected additions,
unselected removals and an empty final skill set are rejected.

### Offline catalogue browsing

`python -m fursa browse --kind opportunity --skills "bookkeeping,spreadsheets"`
lists fictional items containing **all** selected skills, sorted by ID without
ranking or eligibility judgements. Omit `--skills` to browse everything, or use
`--kind pathway` for simulated review routes. Unknown and duplicate filters are
rejected. An empty list describes catalogue coverage, not suitability.

`python -m fursa detail o-solar` retrieves a fictional resource by exact ID,
its simulated evidence options and overlapping review pathways. These links
are catalogue associations, not mandatory requirements or provider agreements.

`python -m fursa compare o-accounts o-dispatch` compares two to four distinct
fictional resources, including pathways. It reports common skills and a
presence matrix without choosing a winner or inferring eligibility.

`python -m fursa skill-map` exposes catalogue coverage for every bounded skill:
fictional resource IDs, simulated evidence, retrieval terms and skills that
co-occur in catalogue opportunities. Counts are not labour-market demand.

`python -m fursa related o-accounts` finds other fictional opportunities and
pathways sharing a catalogue skill, explaining shared and additional skills.
It excludes the source and makes no qualification-equivalence claims.

The dashboard's full-catalogue browser uses bounded kind/skill dropdowns and
explicit loading. It lists fictional resources by ID without scoring or
changing passport selections, distinguishes empty filters from unsuitability,
and cancels stale catalogue requests on filter changes.

Catalogue cards open a native modal showing simulated evidence options, linked
pathways and optional pathway steps. Keyboard focus stays in the modal; Escape
or Close aborts pending detail work, clears detail content and returns focus to
the invoking card. Inspection never changes selections or verifies samples.

The browser's comparison tray accepts two to four fictional resources across
catalogue filters and displays a captioned skill-presence matrix and shared
skills. It never picks a winner. Removing a choice cancels stale comparison
work and preserves keyboard focus; Reset clears the tray and comparison.

`python -m fursa review-plan o-solar --skills solar --evidence e-solar` builds
an optional discussion plan separating unselected skills from unverified
simulated sample selections. Questions concern human criteria, consent,
recognition and appeals; it does not assess competence or approve evidence.

`python -m fursa combined-review o-accounts o-dispatch --skills spreadsheets --evidence e-spreadsheets`
consolidates optional simulated evidence topics across two to four fictional
resources, listing each sample once with explicit resource links. Unselected
skills and selected samples remain distinct; shared evidence is not equivalence,
approval or a mandatory checklist.

`python -m fursa preview-additions --skills astronomy` explores each unselected
catalogue skill as a hypothetical additional checkbox, reporting changes in
all surviving opportunity results (limit 12). This helps understand catalogue
coverage, not decide which skill someone should learn or predict outcomes.

`python -m fursa sensitivity --skills "carpentry,welding"` reports top-three
leave-one-selection-out results, entered/dropped IDs and set Jaccard overlap.
A sole removed skill is explicitly marked as an empty hypothetical selection,
not sent as an invalid passport. This tests lexical dependence, not skill value.

`python -m fursa audit-ranking --skills spreadsheets` reports every fictional
opportunity/pathway cosine, whether it passes the fixed cutoff, and its signed
distance from that cutoff. Unlike discovery, zero/below-cutoff rows are retained
for inspection only. Margins are not confidence or suitability estimates.

`python -m fursa evidence-audit --skills "carpentry,welding" --evidence e-carpentry`
toggles every available selected-skill sample in a separate simulation, compares
both resource rankings/scores/contributions and lists gap-explanation changes.
The invariant is observed rather than assumed. No sample becomes verified;
an unsupported skill with no samples produces an empty scenario list.

```text
Single-file HTML / Python CLI
          |
strict skills + evidence schema (no personal attributes)
          |
selected skill descriptions
          |
learned TF-IDF vocabulary + IDF, log TF, L2 normalization
          |
cosine retrieval of opportunities and simulated pathways
          |
term overlap + skill overlap + evidence gaps
          |
human review required; no automated consequential action
```

| File | Responsibility |
| --- | --- |
| `fursa\catalog.py` | Explicit, fictional skill, work-sample, opportunity and pathway catalogue |
| `fursa\model.py` | Learned TF-IDF, cosine retrieval, strict validation and transparent explanations |
| `fursa\evaluate.py` | Held-out queries and manually assigned relevance sets |
| `fursa\server.py` | Loopback-only HTTP backend and inline HTML delivery |
| `fursa\__main__.py` | Reproducible training, evaluation, matching and serving CLI |
| `web\index.html` | Accessible, responsive Clawpilot-themed interactive demo |
| `tests\test_fursa.py` | ML, input exclusion, evidence and real local HTTP regression tests |
| `evaluation.json` | Observed metrics and every held-out prediction |
| `MODEL_CARD.md` | Model/data provenance, methodology and deployment limits |

### Local API

- `GET /` serves the interactive demo.
- `GET /api/health` reports model readiness.
- `GET /api/catalog` lists accepted skills and simulated evidence.
- `GET /api/resources?kind=opportunity&skill=spreadsheets` browses fictional
  resources (repeat `skill` to require all). Unique filters, one kind, at most
  16 query fields and 2048 query characters; unknown parameters are rejected.
- `GET /api/resources/o-solar` retrieves detail and linked simulated evidence.
- `GET /api/compare?id=o-accounts&id=o-dispatch` compares two to four distinct IDs.
- `GET /api/skills` exposes the bounded catalogue skill/coverage map.
- `POST /api/match`, `Content-Type: application/json`, accepts:

```json
{"skills": ["solar", "electrical"], "evidence": ["e-solar"]}
```

The response contains a synthetic passport, up to three fictional opportunities, up to three simulated pathways, missing evidence and shared terms. A similarity is an uncalibrated **cosine similarity**, not a probability of employment, suitability, credential award or successful assessment.

HTTP uses 400 for invalid input, 403 for disallowed origin/Host, 413 for an absent/oversized body, 415 for wrong media type, and 404 for unknown routes. There is no application, credential-issuance, upload or user-account endpoint.

Selection validation responses distinguish stable `selection_*` error codes
(object/count/unknown/duplicate/cross-skill evidence) and a `/api/catalog`
recovery route. Invalid JSON/framing uses `request_invalid_input`. Error text
never echoes rejected names, biographies or other values; no request is retained.

Loopback requests require exactly one Host and at most one Origin header.
Ambiguous repeated authority/media headers are rejected even when identical.
JSON media types are case-insensitive; only an optional UTF-8 charset is accepted.
These local boundaries are not a production-server security certification.

The local demo caps active connections at eight rather than creating unlimited
handler threads. Excess connections receive 503 `server_busy` with `Retry-After:
1`; disconnects/timeouts release capacity. This bounded localhost resource guard
is not a production admission-control or denial-of-service guarantee.

## Observed synthetic evaluation

See the full recorded run in [`evaluation.json`](evaluation.json), not an aspirational performance claim.

- Fit: **34 catalogue documents**, learned vocabulary of **87 terms**.
- Held-out evaluation: **14 distinct queries**, 12 with relevant opportunities and 2 without.
- **Recall@3: 0.8333**, **MRR: 0.8333**, **precision@3: 0.3056** on positive cases.
- **Correct abstention: 2/2** on the two negative cases.
- Two synonym-only positive queries fail to retrieve anything. They remain in the report rather than being removed.

Relevance labels are manually authored synthetic sets, not employer or assessor judgements. Recall is relevant items retrieved divided by relevant items available. Precision@3 always divides by 3, even if fewer than three results survive the fixed 0.08 similarity cutoff. MRR uses the first relevant rank among returned results. Negative cases are excluded from positive relevance averages and assessed separately.

The held-out texts are not fit documents; normalized token-count bags are checked for exact overlap and reordered query duplicates. Queries intentionally share domain vocabulary with the catalogue, as retrieval queries should. Most are easy lexical scenarios, with only two synonym challenges. This is **not** an independently collected test population, robust semantic evaluation or proof of generalization. Real users' outcomes have not been evaluated.

`python -m fursa evaluate --kind pathway --output pathway-evaluation.json`
records a distinct 15-query synthetic pathway benchmark: all 12 domains, two
negative cases and one synonym-only failure. Labels describe catalogue relevance,
not accredited providers, assessment success or credential eligibility. Reports
identify their resource kind and separate benchmark provenance.

`python -m fursa inspect-case q13` (or `inspect-case p15 --kind pathway`) drills
into an exact authored case: token counts/IDF/vector weights, every resource's
full-precision cosine, manual relevance and whether it was returned, outside
top three, below cutoff or blocked by an empty vocabulary vector. Arbitrary
free-text queries are not accepted by this diagnostic command.

### Optional real-browser smoke test

Recorded evaluation cases include known/unknown term coverage, missed relevant
and extra retrieved IDs, returned similarities/shared terms, and an explicit
outcome category. A lexical vocabulary miss differs from a known-vector
abstention. Categories describe synthetic relevance labels, not user outcomes.

`python -m fursa compare-evaluations evaluation.json evaluation.json` compares
recorded metrics and changed rankings only after checking finite bounded
metrics, unique top-three cases and matching benchmark/query/relevance
provenance. Aggregate metrics are independently recomputed from rankings.
Inputs are limited to one MiB of strict UTF-8 JSON. Corpus changes
are flagged rather than hidden. Deltas are not statistical significance or
evidence of real-user improvement; optional `--output` saves the comparison.

`python -m fursa evaluation-curves` reports positive-query recall, precision
and NDCG for every catalogue depth from 1 through 9 at the unchanged cutoff.
Precision divides by requested depth even when fewer rows survive. Depth three
reproduces published metrics; deeper views do not repair missing vocabulary.
Use `--output models\curves.json` to save this separate diagnostic artifact.

`python -m fursa evaluation-cutoffs` inspects seven fixed lexical cutoffs using
full-precision scores and the same synthetic cases. It reports rankings, recall,
precision and negative abstention, reproducing the default at 0.08. It does not
choose a cutoff, tune the model or establish calibration. Optional `--output`
saves the diagnostic separately; match and published evaluation stay unchanged.

`python -m fursa evaluation-slices` separates positive/negative queries with
known versus empty vectors and single versus multiple relevance labels. Every
slice lists case IDs, denominator and applicable means (otherwise `null`).
These tiny overlapping lexical slices are not demographic, fairness or
independent-population analyses. Optional `--output` saves the report.

`python -m fursa evaluation-baselines` compares always-abstain, catalogue-ID
order and unweighted unique-term overlap controls with fitted TF-IDF on the same
cases, showing each prediction and retrieval/abstention metric. Labels never
generate control rankings. This is a lexical sanity check, not evidence of
deployment superiority. Optional `--output` saves the diagnostic.

The application does not need Node or a browser automation package. If Node 22+ and Edge are already installed, the included CDP smoke test can exercise actual HTTP-backed presets, evidence changes, no-match, validation, reset, responsive layout and themes.

On Windows, `pwsh -File tests\run-browser-smoke.ps1` starts an isolated server
and installed Edge with OS-assigned ports, checks readiness, runs CDP assertions,
and stops only its own process tree by PID. Its unique ignored `.browser-check`
profile/export directory is removed afterward. No packages are installed and
existing export files are not overwritten. The manual setup below remains usable.

In one PowerShell window, run `python -m fursa serve --port 8769`. In another, from this project directory:

```powershell
& 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe' --headless=new --remote-debugging-port=9229 --user-data-dir="$PWD\.browser-check" --no-first-run about:blank
```

In a third window:

```powershell
node tests\browser-smoke.mjs http://127.0.0.1:8769 http://127.0.0.1:9229
```

Close the dedicated browser process and server afterward, and remove the ignored `.browser-check` profile. Do not expose the browser's debugging port publicly. This check is optional; CI's Python suite exercises inference and real loopback HTTP without a browser.

## Safety, privacy and limits

- **Do not enter real personal data.** Only controlled skill names and synthetic evidence IDs are accepted. Unknown fields are rejected, not passed to the model.
- Criminal history, offence type, protected characteristics, reoffending predictions and employability scores are outside the input contract and purpose.
- No persistent server profiles, request-body logging, cookies, browser storage, telemetry or external requests. Current selections live in browser memory and requests in server memory. Reset clears the UI; reload discards selections. An intentional export creates a local file the user controls.
- The local standard-library server is **not a production web server**. It binds only to loopback, restricts inference origin/Host, caps request bodies and times out body reads. Do not expose it on a network, run behind an Internet proxy or treat these measures as a security audit.
- Cities are illustrative context only, not location input or ranking factors. There is no inference about who a person is, why they learned a skill or whether they meet legal requirements.
- A skill-only model can still miss vocabulary or reproduce catalogue coverage gaps. Excluding sensitive fields is **not proof of fairness** or absence of proxy discrimination. Any deployment needs community participation, consent, fairness assessment and jurisdiction-specific review.
- Evidence checkboxes are simulations, not proofs. They neither authenticate artifacts nor establish competence. Human advisers and assessors must independently check safety, validity, recognition and alternatives.
- No hiring or denial automation. No partner claims, measured social impact, placement claims or recognized credentials.

## From working core to portable recognition infrastructure

1. **Community-led evidence design.** Work with people with lived experience and civil-society organizations to define useful, voluntary evidence without disclosing incarceration. Establish consent, deletion, appeals and independent oversight before any pilot.
2. **Portable, verifiable evidence.** Explore open verifiable-credential standards, learner-controlled wallets, minimum disclosure, issuer verification, revocation and accessible offline presentation. A signed claim must not become a universal employability score.
3. **Local assessment and recognition.** Investigate recognition of prior learning with actual accredited providers and qualifications authorities. Publish verified recognition scope, costs and accessibility per jurisdiction. The demo has no provider agreements.
4. **Employer partnerships.** Seek opt-in, inclusive employers and human-supported introductions with transparent skill criteria. Verify genuine opportunities and feedback processes. No employer has agreed to participate.
5. **Multilingual and cross-border discovery.** Evaluate local terminology, uneven internet access and qualification portability with representative, consented relevance data. Compare better retrieval methods to this honest baseline; assess abstention and disparate discovery coverage before deployment.
6. **Measure outcomes responsibly.** Agree on learner-defined evidence usefulness and access to human review, then independently assess benefits and harms. Do not infer reoffending, promise jobs or claim impact from synthetic retrieval scores.

## Contributing and publication

Published at [Emutisya/fursa-clean-start-africa](https://github.com/Emutisya/fursa-clean-start-africa).
The repository includes GitHub Actions running tests,
training, reproducible metric comparison and CLI inference on Windows/Linux
with Python 3.11/3.13. CI uses platform-provided checkout/setup actions; the
application itself has no network dependencies.

Keep additions fictional until a consented, reviewed research protocol exists.
Add focused tests for behavior changes and update the model card and recorded
evaluation. Do not add personal biographies or sensitive labels to training data.
