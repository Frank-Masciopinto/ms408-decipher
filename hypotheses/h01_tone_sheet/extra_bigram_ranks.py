"""Where do the sheet's 8 strings rank among all adjacent in-word EVA letter pairs of ZL3b running text? -> results/bigram_ranks.csv"""
from collections import Counter
import pandas as pd
import h01_lib as L

toks = L.all_tokens(L.load_folios(L.ROOT / "data" / "transcriptions" / "ZL3b-n.txt", "P"))
c = Counter(w[i:i + 2] for w in toks for i in range(len(w) - 1))
tot = sum(c.values())
rank = {b: r for r, (b, _) in enumerate(c.most_common(), 1)}
rows = [{"bigram": u, "rank": rank.get(u), "count": c[u], "share_pct": 100 * c[u] / tot} for u in L.sheet_units()]
df = pd.DataFrame(rows)
df["n_distinct_bigrams"] = len(c)
df.to_csv(L.HERE / "results" / "bigram_ranks.csv", index=False)
top = pd.DataFrame([{"rank": r, "bigram": b, "count": n, "share_pct": 100 * n / tot, "on_sheet": b in L.sheet_units()} for r, (b, n) in enumerate(c.most_common(15), 1)])
top.to_csv(L.HERE / "results" / "top15_bigrams.csv", index=False)
print(df.round(3).to_string()); print(top.round(2).to_string())
print("sheet bigrams in top 15:", int(top.on_sheet.sum()), " share of all pairs covered by the sheet's 8:", round(df.share_pct.sum(), 2))
