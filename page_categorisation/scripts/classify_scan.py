#!/usr/bin/env python
"""Prototype CLI: classify every page in a DCR scan file.

  python scripts/classify_scan.py content/<site>/<id>/filetext.json -o out.jsonl [--limit N]
  python scripts/classify_scan.py <scan> --llm escalate --yes    # + tier 3 on the pages tiers 1-2 cannot settle
  python scripts/classify_scan.py <scan> --llm all --yes         # + tier 3 on every page (the recommended mode)

Input  = the standard scan JSON (list of records).  Output = one JSON line per classified page:
  url, page_type, type_conf, audience, audience_conf, declared_audience, tier, status, evidence, taxonomy
  plus, once tier 3 has run: llm_conf, llm_evidence, cascade_type, cascade_audience, agree_type, agree_audience.

Tier 3 is the only part that costs money. It is off by default and never runs without --yes: every other
invocation just prints what it would have cost. Default model is Haiku 5.5, the cheapest tier-3 option
(~$0.17 per 1,000 pages measured, the README, "The LLM tier, measured"); --llm-model claude-sonnet-5-5 costs 20x that.
"""
import argparse, json, os, re, sys, time, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
from pagecat import llm_tier
from pagecat.cascade import Cascade, apply_llm
from pagecat.scan import featurise

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("scan"); ap.add_argument("-o", "--out", default="-"); ap.add_argument("--limit", type=int)
ap.add_argument("--models", default="models/cascade.pkl")
ap.add_argument("--llm", choices=("off", "escalate", "all"), default="off",
                help="tier 3: off (default), escalate = only pages gated 'llm_review', all = every page")
ap.add_argument("--llm-model", default=os.environ.get("PAGECAT_LLM_MODEL", "claude-haiku-5-5"),
                help="default claude-haiku-5-5, the cheapest; claude-sonnet-5-5 costs 20x more")
ap.add_argument("--llm-concurrency", type=int, default=8, help="parallel requests (8 = the measured 4.3 pages/s)")
ap.add_argument("--llm-max-pages", type=int, help="send at most N pages to tier 3, for a cheap trial run")
ap.add_argument("--yes", action="store_true", help="confirm the tier-3 spend; without it the run stops at the estimate")
a = ap.parse_args()

t0 = time.time(); recs = json.load(open(a.scan, encoding="utf-8")); df = featurise(recs)
if a.limit: df = df.head(a.limit)
t1 = time.time(); casc = Cascade.load(a.models); t2 = time.time()
preds = casc.predict(df); t3 = time.time()
rows = list(df.itertuples())

# tier 3 selection. With --llm off this is still computed, so the run can report what tier 3 would cost.
sel = [i for i, p in enumerate(preds) if a.llm == "all" or p.status == "llm_review"]
if a.llm_max_pages: sel = sel[:a.llm_max_pages]
est = llm_tier.estimate_usd([rows[i] for i in sel], a.llm_model)
llm_t, usages, n_err = 0.0, [], 0

if a.llm == "off":
    print("tier 3 off: %d pages are gated 'llm_review'; sending those to %s would cost about $%.2f "
          "(--llm escalate --yes)" % (len(sel), a.llm_model, est), file=sys.stderr)
    sel = []
elif not sel:
    print("tier 3: nothing to send", file=sys.stderr)
else:
    print("tier 3: %d of %d pages -> %s, estimated $%.2f ($%.3f per 1,000)"
          % (len(sel), len(preds), a.llm_model, est, 1000 * est / len(sel)), file=sys.stderr)
    if not a.yes:                 # nothing is sent, but the tier 1-2 labels are still written below
        print("not sending: re-run with --yes to spend it. Tier 1-2 labels are still written to the output.",
              file=sys.stderr)
        sel = []

if sel:
    if not os.environ.get("ANTHROPIC_API_KEY"):              # ./.env holds the key; never printed
        m = re.search(r"sk-ant-[A-Za-z0-9_\-]+", open(".env").read()) if os.path.exists(".env") else None
        if not m: sys.exit("no ANTHROPIC_API_KEY in the environment and no sk-ant key in ./.env")
        os.environ["ANTHROPIC_API_KEY"] = m.group()
    import anthropic
    client = anthropic.Anthropic(max_retries=4)
    t4 = time.time()
    ans = llm_tier.run(client, [rows[i] for i in sel], model=a.llm_model, concurrency=a.llm_concurrency)
    llm_t = time.time() - t4
    apply_llm(preds, sel, ans)
    usages = [o["usage"] for o in ans if "usage" in o]
    n_err = sum(o.get("type") is None for o in ans)

fh = sys.stdout if a.out == "-" else open(a.out, "w", encoding="utf-8")
for p in preds: fh.write(p.to_json() + "\n")

tiers = {k: n for k in ("rules", "model", "llm") if (n := sum(p.tier == k for p in preds))}
st = {k: n for k in ("auto", "sampled", "llm_review", "human_review", "llm_error")
      if (n := sum(p.status == k for p in preds))}
print("%d pages | featurise %.1fs, model load %.1fs, classify %.1fs (%.1f pages/s) | tiers %s | status %s"
      % (len(preds), t1 - t0, t2 - t1, t3 - t2, len(preds) / (t3 - t2), tiers, st), file=sys.stderr)
if usages:
    agree = [p.agree_type for p in preds if p.agree_type is not None]
    print("tier 3: %d pages in %.0fs (%.1f pages/s), %d failed | cost $%.4f ($%.3f per 1,000, estimated $%.3f) | "
          "agrees with the cheap tier on %.0f%% of types"
          % (len(sel), llm_t, len(sel) / max(llm_t, 1e-9), n_err, llm_tier.usd(usages, a.llm_model),
             1000 * llm_tier.usd(usages, a.llm_model) / len(sel), 1000 * est / len(sel),
             100 * sum(agree) / max(len(agree), 1)), file=sys.stderr)
