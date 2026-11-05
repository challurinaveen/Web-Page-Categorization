# Web Page Categorisation

Work out **what kind of page** a web page is and **who it is written for**, from its URL and text
alone, cheaply enough to run across millions of pages.

Built against ten website scans — 34,319 records, 10,625 classifiable pages — with a taxonomy
derived from the data rather than handed down, and an 800-page benchmark so every number here is
measured instead of claimed.

---

## The answer, in one paragraph

Page type and audience **can** be classified at scale, but not by a cheap model trained on a handful
of sites. A rules + embedding cascade, trained on 800 labelled pages, reaches **44% (type, 23
classes) and 68% (audience, 7 classes) on sites it has never seen**, and it cannot be made
trustworthy by confidence-gating: no threshold reaches 90% accuracy at useful coverage, so ~97% of
pages would still need a stronger classifier. The brief's illustrative "15–25% escalate to an LLM"
does **not** hold. What does hold: the task is well-defined for an LLM — two independent annotators
agreed on 91% of types and 97% of audiences — and an LLM pass with **Haiku 5.5 gets 80.9% of types
and 90.4% of audiences right for $0.17 per 1,000 pages**. So the recommendation inverts: **LLM as
the primary classifier on de-duplicated pages; cheap tiers for filtering, site-level signals and
monitoring; distil LLM labels into the cheap tier over time.**

---

## The app

`streamlit_app.py` is a live demo: give it a URL, it crawls the site politely and classifies every
page with Haiku, showing the evidence and confidence behind each answer.

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Needs an Anthropic API key — in `ANTHROPIC_API_KEY`, in `.streamlit/secrets.toml`
(see `secrets.toml.example`), in `page_categorisation/.env`, or typed into the sidebar.
**A "See a sample" button needs no key**, if you only want to see the output.

The app runs **tier 3 only**. Tiers 1–2 need PyTorch and a 471 MB sentence encoder, more than a
small cloud dyno wants to carry — and per the table below it costs almost nothing in accuracy.
Nothing in the root `requirements.txt` pulls in torch or scikit-learn.

### Deploying to Streamlit Cloud

1. share.streamlit.io → **New app** → this repository, branch `main`
2. **Main file path:** `streamlit_app.py`
3. **Settings → Secrets**, paste one line:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```

Verified by cloning this repository to an empty directory and running it with no API key present:
the app starts, and the landing page and the sample both work without a key.

**Before making it public**, decide whether visitors should spend your API credit. As deployed,
anyone with the URL can classify up to 60 pages per run on your key. Either leave
`ANTHROPIC_API_KEY` out of Secrets so each visitor supplies their own in the sidebar — that path
already works — or keep the app private.

---

## What the numbers say

**Leave-one-site-out:** train on nine sites' gold labels, score the tenth cold, rotate. This is the
only honest way to answer "will it work on site #11".

| Approach | Page type (23 classes) | Audience (8 classes) | Cost / 1,000 pages |
|---|---|---|---|
| Majority class | 16% | 53% | free |
| Zero-shot embedding vs label descriptions | 17% | 50% | free |
| TF-IDF char-ngrams + logistic regression | 35% | 65% | free |
| Embeddings + logistic regression | 38% | 65% | free |
| Keyword / URL rules (tier 1)\* | 44% | 54% | free |
| Fusion LR (embedding + header + rules + host) | 44% | 63% | free |
| **Cascade, tiers 1–2**\* | **44%** (53% pop.-weighted) | **68%** (70% pop.) | free |
| **Claude Haiku 5.5, tier 3** | **80.9%** (88.8% pop.) | **90.4%** (92.1% pop.) | **$0.17** |

\* Rules and cascade thresholds were revised after error analysis on the gold set, so those two rows
are optimistic. Site-specific tokens that leaked into early rules were found and removed, and all
results re-run.

Classifying all 10,625 supplied pages with Haiku costs about **$1.82**.

### Why the cheap tiers fall short

- **Label-starved, not plateaued.** Held-out accuracy keeps rising with training sites (type 29% →
  44%, audience 48% → 63%, 1 → 9 sites). More labelled sites would help.
- **Site shift costs ~12 points.** Random-split CV gives 56% / 74%; the honest number is the LOSO one.
- **Large per-site spread** (type 28–55%, audience 25–84%).
- **Class structure:** strong where vocabulary is distinctive — Patient Support F1 .70, Safety
  Reporting .62, Clinical Evidence .61 — weak where the label is about *role* not words: Listing /
  Library .07, Gateway .06, Medical Education .16, Utility / Error .15.
- **No auto-publish tier.** Gating on joint confidence: ≥0.70 covers 2.8% of pages at 82%/95%;
  everything else, 97.2% of pages, comes out "unsure". The gate is honest — it just says "unsure"
  almost always.

---

## The data

| Fact | Value |
|---|---|
| Sites / records | 10 sites, 34,319 records (2.2k–6.1k each), 1.1 GB JSON |
| Classifiable pages | **10,625** (7,195 HTML + 3,430 PDF); the rest are images, viewer shells, errors |
| External-domain pages | **3,289 (31%)** — scans follow outbound links (PubMed, NICE, CMS, EMA) |
| Languages detected | 12+ (en 58%, es 13%, ja 13%, then pt, sv, fr, no, nl, fi, da, de, it) |
| Near-duplicate collapse | 10,625 → 8,622 units across 3,082 URL templates |
| Ground-truth labels supplied | none |

**One assumption in the brief did not hold.** It relies on the scan's *detected-language* and
*auto-translated text* fields. **Both are empty in all 34,319 records.** Language is detected from
the text instead (`langdetect` plus a kana check for Japanese).

**Boilerplate is the main text-quality problem.** On template-driven sites most of a page's text is
navigation, cookie banner and footer. It is stripped per host by line frequency — a line appearing
on ≥30% of a host's pages is boilerplate — but the raw page header is kept as a separate signal,
because that is where the audience is *declared*.

The ten scans are **not in this repository** (1.09 GB of client page content). They belong at
`content/<host>/<report id>/filetext.json`, relative to the repo root. On the original machine
`content/` was a Windows junction:

```cmd
mklink /J "...\Naveen Project\content" "...\astrazeneca-content\content"
```

---

## The approach

```
scan record ─► preprocess ─► Tier 1 rules ──confident──────────────► label
(URL + text)   strip nav,     multilingual keyword / URL patterns     + evidence
               detect lang,  └─not sure─► Tier 2 embeddings + LR ──► label + confidence
               host context        e5-small content & header            │
                                     confidence gate ──────────────────┴──► Tier 3  LLM
```

- **Type and audience are separate axes.** Audience is split further into *declared* ("intended for
  HCPs only", detected in 6 languages) and *content-based*, so the two can be compared.
- **Site-level context is free and strong.** If most pages on a host carry a declaration, the host's
  other pages inherit it. No labels needed; works on any new scan.
- **Taxonomy v1.1**, data-driven then checked by clustering: 23 types, 8 audiences. There is no
  "Employee" content in the sample (no intranet); "Form / Request" and "Legal & Compliance" were
  added after cluster review.
- **Clustering did not yield the taxonomy.** Embedding clusters grouped pages by site and clinical
  topic, not by function. Clustering validated and extended a human-defined taxonomy; it did not
  replace one.

### URL-rule boundary guards

URL rules are matched with a left word boundary only, so a bare alternative also matches any longer
word it prefixes. A scan of the gold set found 885 such prefix matches, **almost all deliberate**
(`congres`→congress, `sustainab`→sustainability, `oncolog`→oncology). A blanket right-hand boundary
would break those, so only the two observed firing wrongly were guarded: **`form(?!at)`** and
**`data(?!set)`**.

Effect on the benchmark: **none** — every type-axis figure unchanged to 4 decimal places. Effect
off-domain: **substantial** — see "A site outside the data" below.

---

## How it was measured

**Gold set.** 800 pages, 80 per site, stratified by site × URL template with quotas close to the
population (32% external, 23% PDF) and inverse-probability weights so population-level accuracy can
be estimated. Two independent annotators labelled all 800 from a written guide
(`page_categorisation/gold/ANNOTATION_GUIDE.md`); a third pass adjudicated the 89 disagreements.

| Agreement | Raw | Cohen's κ |
|---|---|---|
| Page type | 91.3% | **0.905** |
| Audience | 97.0% | **0.952** |

Self-reported confidence ranks errors well: pages marked "certain" (53%) agreed 99.5% of the time;
"probable" 85%; "guess" 66%.

> **The caveat that applies to every number on this page.** Both annotators are the same model
> family working from the same guide that is also Haiku's system prompt. So these are agreement
> figures with a consistent, documented process — not human-verified truth — and because the errors
> are correlated, κ is an upper bound for independent humans. Treat the set as **silver** until
> spot-checked. 200 human-checked pages would pin accuracy to ±5.5 points; 80 pages only ±8.8.

### The LLM tier, measured

`llm_tier.py` run on all 800 gold pages (8 parallel requests, system prompt = the annotation guide,
cached, JSON-schema output). A first run capped replies at 300 tokens and 152 of 800 failed — the
model writes a reasoning step before its answer; the cap is now 1,500 and the reported run has
**0 errors**.

| | Page type | Audience |
|---|---|---|
| **Haiku 5.5** | **80.9%** (95% range 78.1–83.4) | **90.4%** (88.4–92.2) |
| Haiku, population-weighted | 88.8% | 92.1% |
| Cheap cascade, same pages | 44.1% | 67.8% |
| Right only by Haiku / only by cascade | 329 / 35 | 213 / 32 |

**Its own confidence ranks its errors**, which is what makes routing on it defensible:

| Confidence | Share of pages | Page type | Audience |
|---|---|---|---|
| 3 — certain | 38.8% (310) | 92.6% | 97.4% |
| 2 — probable | 55.6% (445) | 76.0% | 87.6% |
| 1 — guess | 5.6% (45) | 48.9% | 68.9% |

A rule written *before* the run — Haiku must reach ≥90% type and ≥95% audience on pages it calls
certain — was **met at 92.6% / 97.4%**, though the type result's 95% range (89–95%) starts just
below 90%.

**Honesty check.** Haiku agrees with annotator A on 81.0% of types and with B on 79.8%; the
annotators agree with each other on 91.2%. Haiku is ~10 points below the labelling process itself.

**Where it is weak:** by site, type 68–91%. Weakest types with n ≥ 10: R&D & Science 36% (14),
Product Information 60% (55), Other 60% (15), Login / Registration 70% (27). Commonest confusions:
Product Information → Prescribing Information, Disease & Therapy Area → Homepage / Hub. PDFs and
HTML score the same (80.7% vs 80.9%); external-domain pages score lower on audience (86.2% vs 92.4%).

**Agreement with the cheap cascade is a free second signal:** when both agree on type, accuracy is
88.3% (45% of pages); agreeing *and* Haiku certain, 94.4% (24.5% of pages).

---

## Cost, speed and scale

Measured on a shared 32-vCPU CPU VM, no GPU, with another process using ~9 cores — so conservative.

| Stage | Throughput | Cost per 1,000 pages |
|---|---|---|
| Featurise (boilerplate, title, URL tokens, language) | ~170 pages/s/core | free |
| Tier 1 — rules | ~190 pages/s/core | free |
| Tier 2 — e5-small embeddings (CPU) | ~30 pages/s | free (~9.4 VM-hours per million) |
| **Tier 3 — Haiku 5.5, 8 parallel requests** | **4.3 pages/s** | **$0.171** |
| Tier 3 without prompt caching | — | $0.43 |

Caching the guide — 2,923 tokens, identical on every request, read at a tenth of list price — is
what takes $0.43 down to $0.17. Sonnet 5.5 would be $5.51 per 1,000 and has never been measured.

Three levers not yet applied: collapse near-duplicate templates first (−19% of units here, more on
templated sites); classify only changed pages on re-scan; the Batch API's half price (a list-price
fact, untested).

---

## Key findings

1. **The cheap tier is not enough on its own** with ~700 labels. 44% / 68% on unseen sites, and
   confidence gating cannot rescue it. Measured escalation is ~97%, not the 15–25% assumed.
2. **LLM classification works and is cheap.** 80.9% / 90.4% for $0.17 per 1,000; its "certain"
   answers (39% of pages) are right 92.6% / 97.4%.
3. **Audience is mostly a site-level property.** 45% of true-HCP pages state "intended for HCPs
   only" in their own header, 52% counting the declaration inherited from their site. Declared share
   per host: medicalinformation-US 99%, azone.es 93%, myastrazeneca.co.uk 78%, myastrazeneca.be 54%,
   medicalinformation.pt 23%, the five corporate sites 0–1%. Free, label-free, site-transferable.
4. **Declared vs content audience finds real compliance candidates.** Of 235 pages counted as
   HCP-only, **12 (5%) are patient-facing** — patient information, a US medication guide — on sites
   that mostly declare HCP-only; all 12 inherit the declaration rather than stating it. Also: a
   navigation link reading "Profesionales Sanitarios" is *not* a declaration, and naïve keyword
   matching confuses the two.
5. **Third-party pages are ~31% of the crawl** and PDFs ~32%. Both need explicit policy.
6. **The taxonomy needs a v1.2:** add *Policy / Regulatory Document* and *Out-of-scope external
   page*; define Product Information vs Clinical Evidence on brand sites, and Legal & Compliance vs
   Sustainability for disclosures. Hub vs Listing is inherently fuzzy.
7. **Templates dominate crawls**, so naïve sampling flatters any model. Accuracy is therefore
   reported template-balanced *and* population-weighted side by side (44% vs 53% type).

### A site outside the data

A 200-page crawl of `huggingface.co` — a developer platform, deliberately nothing like a pharma
site — run through the same pipeline. 162 pages were classifiable and **100% escalated past the
cheap tiers**; the LLM tier cost $0.0238.

| | Tiers 1–2 | Haiku |
|---|---|---|
| Top labels | Clinical Evidence 6, R&D & Science 8, Form / Request 1, Patient Support 1 | Listing / Library 84, Other 27, Utility / Error 23, Homepage / Hub 18 |
| Verdict | 16 of 162 pages given a label that cannot exist on this site | no pharma label at all; "Unclear" for 125 of 162 audiences rather than forcing a category |

The two tiers agree on only 36% of types here (43% of audiences) against 45% of types on the pharma
sites — and where they disagree, it is the cheap tier that is wrong. The URL-rule guards cut false
pharma labels from 47 to 16. The example run is kept in `page_categorisation/examples/`; its tier
1–2 labels were recomputed on 2026-11-03 after the guards landed, while the paid tier-3 answers were
reused rather than re-requested.

---

## Recommendations

1. **Haiku as the primary tier**, with its own confidence doing the routing: "certain" ships,
   "probable" ships for audit, "guess" goes to a human. Next: re-measure after fixing its weak spots.
2. **Re-architect the cascade around cost and risk, not accuracy:** pre-filter shells and errors,
   collapse templates and duplicates, use host-level declared audience as a prior, run the LLM on
   one representative per template and propagate with a consistency check, and send only
   low-confidence output plus a random audit sample to people.
3. **Distil, don't hand-tune:** use LLM labels on a few thousand pages across ≥20 sites to train the
   cheap tier. The learning curve says that is where accuracy comes from, and it sets ongoing cost.
4. **Validate the gold set with humans** — 200 pages pins accuracy to ±5.5 points. Freeze taxonomy
   v1.2 with a versioned guide and recompute κ.
5. **Test on a genuinely new site before any rollout.** Every number here comes from ten sites that
   also shaped the taxonomy and the rules.
6. **Add monitoring:** per-site escalation rate with a cap and alert, calibration checks on each
   audited batch, and drift in the declared-vs-content mismatch rate.

---

## Limitations — read before quoting any number

- Gold labels are LLM-made (correlated errors, not domain experts); κ is optimistic.
- Rules were tuned after error analysis on the same gold set, so their LOSO scores and the
  cascade's are optimistic. Learned models were not tuned per held-out site.
- 10 sites, 800 labels. Rare classes (Investor 7, Safety 6, Contact 9, Media 13) are too small for
  reliable per-class metrics. No Job Seeker pages were drawn in the sample.
- Tier 3 was measured with Haiku 5.5 only. Sonnet was not run. The ~64 h/million extrapolation and
  the Batch API discount are untested.
- Page text only — no rendering, images, or structure beyond the scan's text lines.
- The scan's `Shortest path` parent information is sparse for PDFs and was barely used.
- Original numbers came from scikit-learn 1.7.2; a 2026-11-01 re-run used 1.9.0, which moves figures
  by up to ~0.1 point on its own. Treat sub-0.5-point differences as environmental.
- The taxonomy is pharma-specific and does not transfer across industries.

---

## Running the pipeline

Everything below runs from the `page_categorisation` folder:

```bash
cd page_categorisation
pip install -r requirements.txt     # sentence-transformers pulls PyTorch: 2-3 GB
```

**Check the install** (10 seconds, no API key, no network, no model download):

```bash
python tests/test_offline.py        # expect: 19 passed, 0 failed
```

**Classify a supplied scan** — tiers 1–2 only, free:

```bash
python scripts/classify_scan.py ../content/<host>/<id>/filetext.json -o out.jsonl
```

The first run downloads the text encoder (~471 MB). Verified output on `myastrazeneca.be`:

```
617 pages | featurise 5.9s, model load 24.0s, classify 17.1s (36.2 pages/s)
tiers {'rules': 476, 'model': 141} | status {'sampled': 10, 'llm_review': 607}
```

**Turn on the LLM tier** — this is the only part that costs money:

```bash
python scripts/classify_scan.py <scan> --llm escalate --yes -o out.jsonl   # only gated pages
python scripts/classify_scan.py <scan> --llm all --yes -o out.jsonl        # every page
```

Nothing is sent without `--yes`; every other run prints what it *would* have cost. `--llm-max-pages N`
caps a trial. The key comes from `ANTHROPIC_API_KEY` or a `sk-ant-…` line in `./.env`, and is never
printed. Default model is `claude-haiku-5-5`.

**Classify a site nobody gave you a scan for:**

```bash
python scripts/crawl_site.py https://example.com -o new_site_scan.json --max-pages 200
python scripts/classify_scan.py new_site_scan.json -o new_site_results.jsonl
```

The crawler **always honours robots.txt** — there is no override flag — runs single-threaded with a
1-second gap, retries rate limits, and stops at 200 pages unless told otherwise. Useful flags:
`--same-host`, `--no-pdf`, `--delay`, `--retries`. **Only crawl sites you are allowed to crawl.**

### What comes out

One JSON line per page: `url, page_type, type_conf, audience, audience_conf, declared_audience,
tier (rules|model|llm), status, evidence[], taxonomy`. Once tier 3 has run, also `llm_conf` (the
model's own 1–3), `llm_evidence`, `cascade_type`, `cascade_audience`, `agree_type`, `agree_audience`
— the cheap tier's answer is kept beside the LLM's because the two agreeing is itself a signal.

`status` is the routing decision: `auto` ships, `sampled` ships but is audited, `llm_review`
escalates to tier 3, `human_review` goes to a person, `llm_error` means the request failed and the
cheap label was kept. `type_conf` / `audience_conf` always mean the same thing — calibrated
P(correct) — whichever tier produced the label.

### Reproducing the benchmark (~20 minutes)

`bash scripts/run_all_eval.sh` runs steps 2 onward but assumes `data/features.parquet` exists. On a
clean machine run the full sequence:

```bash
python scripts/01_ingest.py ../content data/records.parquet   # needs ~4 GB RAM
python scripts/02_features.py
python scripts/06_benchmark.py
python scripts/08_analyse.py
python scripts/10_train_final.py
python scripts/09_scale_cost.py
python scripts/07_learning_curve.py type
python scripts/07_learning_curve.py audience
python scripts/08_analyse.py
```

Expected landing points — anything far off means something is wrong:

| Check | Expected |
|---|---|
| Records ingested | 34,319 → 10,625 classifiable |
| Rules, page type | 0.4425 |
| Cascade, page type | ~0.44–0.48 |
| Cascade, audience | ~0.68 |
| Learning curve, 9 training sites | 0.4437 type / 0.6313 audience |
| Escalation share | ~97% |
| Haiku on the 800 gold pages | 80.9% type / 90.4% audience |

And for the off-domain example, which needs no API key — run
`python scripts/classify_scan.py examples/my_scan.json -o out.jsonl` and compare against
`examples/my_results.jsonl`: 200 crawled → 162 classifiable, 100% escalation, 36% type / 43%
audience agreement, 16 pages given a pharma-only label.

### Rebuilding the review deck

```bash
node scripts/deck/build_week1_deck.js ../Week1_Prototype_Review.pptx
```

15 slides, needs node and `pptxgenjs`. Every figure is read from `results/*.json`,
`examples/my_results.jsonl` and this README — change a measurement there and rebuild rather than
editing a slide.

---

## Layout

```
.
├── streamlit_app.py           the live demo (tier 3 only)
├── requirements.txt           light deps, what Streamlit Cloud installs
├── tests_app.py               8 headless Streamlit checks
└── page_categorisation/
    ├── requirements.txt       the full research stack (PyTorch, scikit-learn)
    ├── src/pagecat/           preprocess · rules · models · cascade · scan · fetch · llm_tier · taxonomy
    ├── scripts/01…14_*.py     the experiment, in order
    ├── scripts/classify_scan.py   the prototype CLI
    ├── scripts/crawl_site.py      crawl a live site into the scan format
    ├── scripts/deck/          deck tooling, not part of the pipeline
    ├── tests/test_offline.py  19 checks: cost model, tier-3 wiring, URL guards, scan reader
    ├── gold/                  the 800-page benchmark, both annotators, the annotation guide
    ├── results/               every measured number, as JSON
    ├── figures/               the five charts
    ├── models/cascade.pkl     the trained tier-2 model
    ├── examples/              a finished run on huggingface.co
    └── data/                  large rebuildable intermediates — git-ignored, 169 MB
```

Not in this repository, by `.gitignore`: the client scans (`content/`), the rebuildable
intermediates (`data/`), the generated decks, and `.env`.

## Checks

```bash
python page_categorisation/tests/test_offline.py  # 19 — library internals
python tests_app.py                               # 8  — the Streamlit app, headless
```

Both run with no API key, no network and no model download.

Neither exercises a real API call: they drive `llm_tier` through a stub client. The tier-3 request
itself is only proven by running the app.
