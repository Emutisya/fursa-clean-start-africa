# Fursa | Clean Start Africa

**A skill-first discovery prototype for a future where practical experience can travel across institutions and borders.**

People rebuilding their lives after incarceration may have valuable practical skills but lack recognized evidence, trusted introductions or clear routes to assessment. Fursa explores a bridge from **selected skills → a skills passport → fictional opportunities → evidence gaps → simulated assessment pathways**.

This is a **working, offline ML research prototype**, not an employment service. It neither asks about incarceration nor uses it in inference. Every opportunity, sample and pathway is fictional. No credentials, offers, hiring decisions or eligibility decisions are issued.

## Quickstart

Python **3.11 or newer**. No third-party Python dependencies, installation, API keys, network access or downloaded weights are needed.

From this project's directory, in PowerShell:

```powershell
python -m fursa serve
```

Open **http://127.0.0.1:8765**. Try Workshop maker, Energy learner, Enterprise helper or Explore a gap. Choose skills, optionally attach synthetic evidence, then explore. Export downloads only the selected, explicitly unverified synthetic passport as JSON.

The HTML is a single file with inline styles and scripts: `web\index.html`. Its layout can be previewed directly, but **learned inference requires the local Python server**, not `file://`. There is no fake JavaScript fallback. Use `?clawpilotTheme=dark` or `?clawpilotTheme=light` to override the system theme.

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

Skill names and evidence IDs must exactly match `catalog`. Empty, duplicate, unknown or sensitive inputs are rejected. Selected evidence must belong to a selected skill. Evidence flags change gap explanations, **never the ranking**.

Training produces inspectable learned IDF weights in an ignored `models` directory. The tiny model is fitted deterministically on startup for CLI and HTTP inference; the persisted file is an audit artifact, not a required runtime dependency. Editing the catalogue intentionally changes its fingerprint and requires regenerating the published evaluation.

For POSIX systems, use `models/tfidf.json` in the training command instead. All other commands are identical.

## Experience and architecture

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
- `POST /api/match`, `Content-Type: application/json`, accepts:

```json
{"skills": ["solar", "electrical"], "evidence": ["e-solar"]}
```

The response contains a synthetic passport, up to three fictional opportunities, up to three simulated pathways, missing evidence and shared terms. A similarity is an uncalibrated **cosine similarity**, not a probability of employment, suitability, credential award or successful assessment.

HTTP uses 400 for invalid input, 403 for disallowed origin/Host, 413 for an absent/oversized body, 415 for wrong media type, and 404 for unknown routes. There is no application, credential-issuance, upload or user-account endpoint.

## Observed synthetic evaluation

See the full recorded run in [`evaluation.json`](evaluation.json), not an aspirational performance claim.

- Fit: **34 catalogue documents**, learned vocabulary of **87 terms**.
- Held-out evaluation: **14 distinct queries**, 12 with relevant opportunities and 2 without.
- **Recall@3: 0.8333**, **MRR: 0.8333**, **precision@3: 0.3056** on positive cases.
- **Correct abstention: 2/2** on the two negative cases.
- Two synonym-only positive queries fail to retrieve anything. They remain in the report rather than being removed.

Relevance labels are manually authored synthetic sets, not employer or assessor judgements. Recall is relevant items retrieved divided by relevant items available. Precision@3 always divides by 3, even if fewer than three results survive the fixed 0.08 similarity cutoff. MRR uses the first relevant rank among returned results. Negative cases are excluded from positive relevance averages and assessed separately.

The held-out texts are not fit documents; normalized token sequences are checked for exact overlap and query duplicates. Queries intentionally share domain vocabulary with the catalogue, as retrieval queries should. Most are easy lexical scenarios, with only two synonym challenges. This is **not** an independently collected test population, robust semantic evaluation or proof of generalization. The pathway rankings and real users' outcomes have not been evaluated.

### Optional real-browser smoke test

The application does not need Node or a browser automation package. If Node 22+ and Edge are already installed, the included CDP smoke test can exercise actual HTTP-backed presets, evidence changes, no-match, validation, reset, responsive layout and themes.

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

## Global roadmap: aspirations, not commitments

1. **Community-led evidence design.** Work with people with lived experience and civil-society organizations to define useful, voluntary evidence without disclosing incarceration. Establish consent, deletion, appeals and independent oversight before any pilot.
2. **Portable, verifiable evidence.** Explore open verifiable-credential standards, learner-controlled wallets, minimum disclosure, issuer verification, revocation and accessible offline presentation. A signed claim must not become a universal employability score.
3. **Local assessment and recognition.** Investigate recognition of prior learning with actual accredited providers and qualifications authorities. Publish verified recognition scope, costs and accessibility per jurisdiction. The demo has no provider agreements.
4. **Employer partnerships.** Seek opt-in, inclusive employers and human-supported introductions with transparent skill criteria. Verify genuine opportunities and feedback processes. No employer has agreed to participate.
5. **Multilingual and cross-border discovery.** Evaluate local terminology, uneven internet access and qualification portability with representative, consented relevance data. Compare better retrieval methods to this honest baseline; assess abstention and disparate discovery coverage before deployment.
6. **Measure outcomes responsibly.** Agree on learner-defined evidence usefulness and access to human review, then independently assess benefits and harms. Do not infer reoffending, promise jobs or claim impact from synthetic retrieval scores.

## Contributing and publication

This directory is designed to become its own public repository, `emutisya/fursa-clean-start-africa`. It includes an MIT license and GitHub Actions running tests, training, reproducible metric comparison and CLI inference on Windows/Linux with Python 3.11/3.13. CI uses platform-provided checkout/setup actions; the application itself has no network dependencies.

Keep additions fictional until a consented, reviewed research protocol exists. Add focused tests for behavior changes and update the model card and recorded evaluation. Do not add personal biographies or sensitive labels to training data. No Git repository, commit or push is created by the project setup.

**License:** [MIT](LICENSE).
