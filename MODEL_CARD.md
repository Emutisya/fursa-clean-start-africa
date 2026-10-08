# Model and data card

## Purpose

Fursa is an offline **catalogue discovery** experiment. It retrieves fictional practice opportunities and illustrative evidence-review pathways from controlled, user-selected skills. It is not a classifier of people, hiring model, reoffending model, credential issuer or assessment system.

## Data provenance

All text was manually authored for this prototype. No public or private datasets were downloaded; no resumes, justice records, real employer openings or personal evidence were used.

The catalogue has:

- 13 English-language skill descriptions, including an intentionally unsupported astronomy skill.
- 9 explicitly fictional opportunity documents.
- 12 simulated pathway documents, one for each supported practical skill.
- 12 synthetic evidence choices, each mapped to one skill.

The **34 fitting documents** are the opportunity descriptions expanded with their skill descriptions, pathway descriptions expanded with their skill descriptions, and the 13 standalone skill descriptions. Evidence selections, geographic setting labels and human-review flags are not model features. A city is not an input, relevance filter or promise of availability. Titles are displayed, but scoring uses `catalog.document()`, not titles.

## Learned classical baseline

The stdlib implementation fits an unsupervised TF-IDF retrieval model, learning a vocabulary and per-term weights from the fitting documents:

```text
tokenization = lowercase ASCII alphabetic sequences
IDF(t) = log((1 + document_count) / (1 + document_frequency(t))) + 1
TF(t) = 1 + log(term_count(t))
vector(t) = TF(t) * IDF(t), then L2 normalize
similarity(q, d) = sum(q[t] * d[t])
```

Unknown terms are ignored. No stemming, semantic embeddings, synonym expansion or language detection is used. Catalogued skill selections expand into their fixed descriptions. Sort by descending similarity, with ID as a deterministic tie-breaker. A fixed **0.08** cutoff rejects negligible overlap; at most three opportunities and three pathways are returned. The cutoff is an illustrative design constant, not a calibrated decision threshold or an evaluation-tuned probability.

Evidence does not contribute to vector construction. For each retrieved opportunity, rule-based explanations list common declared skills, top shared weighted terms, other skills to explore, and missing simulated work samples. These gaps are neither a requirement to submit a real document nor an eligibility decision.

No credential recognition, human assessment or qualification standard is implemented. Pathway text suggests asking a provider whether recognition of prior learning is possible; it does not establish a legal route in any particular country.

## Evaluation protocol and observed run

`fursa.evaluate.CASES` contains **14 held-out query documents** with manually specified relevance sets: 12 positive queries and 2 negative queries. One positive query has two relevant opportunities. Two positive synonym-only challenges use vocabulary missing from the fitting corpus and receive no match.

Only catalogue documents are fitted. Held-out queries and their labels are not used to fit IDF, choose weights or select the threshold. Evaluation checks exact normalized token-sequence disjointness against fitting documents and uniqueness within held-out queries. This prevents exact duplicate leakage, **not all conceptual overlap**: the queries deliberately refer to the same skill domains and mostly use catalogue vocabulary.

The synthetic labels use this rubric: a query about a practical domain is relevant to the opportunity explicitly covering that domain; a query about both timber and metal is relevant to both associated opportunities. Astronomy and unrelated music terms have no relevant opportunities. Labels do not mean an employer would accept a person.

Recorded in `evaluation.json`:

| Metric | Observed | Interpretation |
| --- | ---: | --- |
| Mean recall@3, positives | 0.833333 | Relevant opportunity coverage |
| Mean precision@3, positives | 0.305556 | Hits / 3; unfilled positions count as misses |
| Mean reciprocal rank, positives | 0.833333 | First relevant returned rank; no match = 0 |
| Correct negative abstention | 1.000000 (2/2) | Only two negative examples, no confidence claim |

The raw cases, predictions, corpus SHA-256, vocabulary size and document count are recorded alongside the averages. Re-running the command reproduces those observations; CI compares the full report with the checked-in report.

This set is too small and hand-authored to estimate real deployment quality. Domain labels were authored with knowledge of the catalogue, not by independent annotators. Easy lexical overlap explains strong performance on basic cases; synonym failures demonstrate a known limitation. No train/test subject split is meaningful here because there are no people or personal records. No pathway-relevance benchmark, fairness benchmark, prospective evaluation or real-world impact study was conducted.

## Privacy and prohibited use

Accepted JSON keys are exactly `skills` and `evidence`. Values must belong to fixed allowlists, with duplicate and cross-skill evidence checks. Sensitive fields, biography text and unknown skill values are rejected.

Do not use this model to:

- Infer criminal history, offence type, protected traits or reoffending.
- Score employability, assess character, issue a credential or certify competence.
- Automate applications, hiring, eligibility or denial.
- Claim legal compliance, equitable outcomes, provider recognition or employer endorsement.

No server-side persistence or request-body logging occurs. This is not an anonymous production platform: requests exist briefly in memory, the operating system/browser may retain unrelated diagnostics, and exported JSON is a deliberate local file. No real evidence upload is supported.

## Limitations and future checks

Vocabulary coverage, English-only tokenization and a tiny catalogue sharply limit retrieval. Lexical overlap can surface weak suggestions. These scores are uncalibrated similarities, not probabilities or person-level ratings. No-match is a catalogue or representation gap, never a judgement about the user.

Sensitive-input exclusion tests prove the API boundary, not social fairness. Future research would require consented representative query sets, multilingual/local vocabulary checks, independent relevance annotation, subgroup discovery-coverage analysis with appropriate governance, provider verification and human-led appeals. Any production design must establish privacy, infrastructure security and jurisdiction-specific credential recognition independently.
