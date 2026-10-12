"""Top candidate word-meaning pairs: global enrichment (section-confounded) next to the within-quire test of the same word."""
import pandas as pd
from pathlib import Path
R = Path(__file__).resolve().parent / "results"; rows = []
for tag, meaning in [("water", "water/bath"), ("nymph", "woman/nymph"), ("star", "star"), ("root", "root"), ("jar", "vessel/jar")]:
    g = pd.read_csv(R / f"t4_enrich_{tag}_global.csv"); w = pd.read_csv(R / f"t4_enrich_{tag}_within_quire.csv").set_index("word")
    for r in g.head(5).itertuples():
        rows.append(dict(tag=tag, candidate_meaning=meaning, word=r.word, count=r.count, r_global=round(r.r, 3), rate_ratio=round(r.rate_ratio, 1),
                         p_holm_global=r.p_holm, r_within_quire=round(w.r.get(r.word), 3), p_within_quire=round(w.p.get(r.word), 4),
                         p_holm_within_quire=round(w.p_holm.get(r.word), 4)))
pd.DataFrame(rows).to_csv(R / "candidate_word_meanings.csv", index=False); print(pd.DataFrame(rows).to_string())
