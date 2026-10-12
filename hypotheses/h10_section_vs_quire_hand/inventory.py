"""Metadata-only inventory: where section / illustration type and quire / hand / Currier language are NOT confounded.
Token counts are running-text sizes only (no vocabulary statistics)."""
import sys
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h09_image_context_cribs"))
import h09_lib as H9  # noqa: E402


def pages():
    q = pd.read_csv(ROOT / "data" / "quires.csv", dtype=str, keep_default_na=False)
    lo = H9.parse(); bags = H9.page_bags(lo, ("P", "C", "R"))
    q["tokens"] = q.page.map(lambda p: sum(bags[p].values()) if p in bags else 0)
    q["order"] = range(len(q))
    q["hand"] = q.lfd_hand.replace("", "?"); q["lang"] = q.currier_language.replace("", "?")
    q["stratum"] = "Q" + q.quire + "|h" + q.hand + "|" + q.lang
    return q


def inventory(q):
    rows = []
    for level, key in [("quire", ["quire"]), ("hand", ["hand"]), ("quire x hand x lang", ["stratum"]), ("hand x lang", ["hand", "lang"])]:
        for k, g in q.groupby(key):
            for col in ("section", "illustration"):
                c = g.groupby(col).agg(pages=("page", "size"), tokens=("tokens", "sum"))
                c = c[c.tokens > 0]
                if len(c) > 1:
                    rows.append(dict(level=level, unit=k if isinstance(k, str) else "|".join(map(str, k)), by=col,
                                     n_classes=len(c), detail="; ".join(f"{i}:{r.pages}p/{r.tokens}t" for i, r in c.iterrows()),
                                     min_class_tokens=int(c.tokens.min()), total_tokens=int(c.tokens.sum())))
    # reverse: sections containing >1 hand / quire / language
    for sec, g in q.groupby("section"):
        for col in ("hand", "lang", "quire", "stratum"):
            c = g.groupby(col).agg(pages=("page", "size"), tokens=("tokens", "sum")); c = c[c.tokens > 0]
            if len(c) > 1:
                rows.append(dict(level=f"within section {sec}", unit=sec, by=col, n_classes=len(c),
                                 detail="; ".join(f"{i}:{r.pages}p/{r.tokens}t" for i, r in c.iterrows()),
                                 min_class_tokens=int(c.tokens.min()), total_tokens=int(c.tokens.sum())))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    q = pages(); q.to_csv(HERE / "results" / "pages.csv", index=False)
    inv = inventory(q); inv.to_csv(HERE / "results" / "inventory.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 140)
    print(inv.to_string())
