"""Embed every unit (multilingual-e5-small, CPU) and cluster across all sites.

Cluster summaries (size, site mix, distinctive URL tokens, example titles) are what a
reviewer names - deck slide 8 steps 1-3. Output: data/emb.npy, results/clusters.txt
"""
import sys
import time

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer

MODEL = "intfloat/multilingual-e5-small"
K = int(sys.argv[1]) if len(sys.argv) > 1 else 60

df = pd.read_parquet("data/features.parquet")
try:
    E = np.load("data/emb.npy")
    assert len(E) == len(df)
except Exception:
    from sentence_transformers import SentenceTransformer
    import torch
    torch.set_num_threads(32)
    m = SentenceTransformer(MODEL, device="cpu")
    m.max_seq_length = 256
    t0 = time.time()
    E = m.encode(["query: " + t for t in df.embed_text], batch_size=64, normalize_embeddings=True,
                 show_progress_bar=False)
    dt = time.time() - t0
    print(f"embedded {len(df)} in {dt:.0f}s = {len(df)/dt:.1f} pages/s on CPU")
    np.save("data/emb.npy", E.astype("float32"))

km = KMeans(n_clusters=K, n_init=3, random_state=0).fit(E)
df["cluster"] = km.labels_
df[["uid", "cluster"]].to_parquet("data/clusters.parquet")

# distinctive url tokens per cluster (c-TF-IDF)
docs = df.groupby("cluster").url_toks.apply(lambda s: " ".join(s))
cv = CountVectorizer(token_pattern=r"[^\s]{3,}", min_df=2, max_features=30000)
X = cv.fit_transform(docs)
T = TfidfTransformer().fit_transform(X)
vocab = np.array(cv.get_feature_names_out())

with open("results/clusters.txt", "w") as f:
    for c in range(K):
        g = df[df.cluster == c]
        top = vocab[np.argsort(-T[c].toarray()[0])[:10]]
        sites = g.site.str.replace("www.", "", regex=False).value_counts().head(3)
        f.write(f"\n### C{c}  n={len(g)}  pdf={g.is_pdf.mean():.0%} 3p={g.third_party.mean():.0%} "
                f"sites={dict(sites)}\n  tokens: {' '.join(top)}\n")
        ex = g.sample(min(6, len(g)), random_state=0)
        for r in ex.itertuples():
            f.write(f"   - [{r.lang}] {r.title[:70]!r}  {r.url[:110]}\n")
print("wrote results/clusters.txt")
