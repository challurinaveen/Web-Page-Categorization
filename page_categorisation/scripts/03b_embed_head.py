"""Second embedding per page: its raw header (banner, nav, gating text) - carries site-declared audience."""
import numpy as np, pandas as pd
from sentence_transformers import SentenceTransformer
df = pd.read_parquet("data/features.parquet")
m = SentenceTransformer("intfloat/multilingual-e5-small", device="cpu"); m.max_seq_length = 128
E = m.encode(["query: " + h[:400] for h in df["head"]], batch_size=64, normalize_embeddings=True, show_progress_bar=False)
np.save("data/emb_head.npy", E.astype("float32")); print("head embeddings", E.shape)
