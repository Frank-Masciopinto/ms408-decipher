"""Build h31 corpora (h19 cells + Hebrew/Arabic + C0) and cache to results/corpora.json (git-ignored: licences)."""
import json
import sys
from h31_lib import HERE, ROOT

OUT = HERE / "results" / "corpora.json"


def build():
    if OUT.exists(): return json.loads(OUT.read_text())
    import run_h19 as R19
    from msdecipher.controls_text import load_tokens
    from msdecipher.mech_naibbe import NaibbeCipher
    cells = R19.ms_cells()
    for cid in R19.CTRL + ["he_tanakh", "ar_quran"]: cells["NAT_" + cid] = R19.paginate(load_tokens(cid, R19.NTOK), cid, "ctrl", "char")
    for name, cid in R19.CIPH.items():
        cells["GEN_" + name] = R19.paginate(NaibbeCipher().encrypt(load_tokens(cid, None), seed=0, n_words_out=R19.NTOK), name, "ciph", "eva")
    sys.path.insert(0, str(ROOT / "hypotheses" / "h12_per_hand_copy_modify")); import run_h12 as R12
    ws = [w for p in cells["MS_2B"]["pages"] for w in p["words"]]
    m = R12.fit(ws, seed=0); g = [w for w in R12.generate(m, R19.NTOK, 0) if w]
    cells["GEN_C0_2B"] = R19.paginate(g, "c0", "gen", "eva")
    out = {k: dict(pages=[dict(id=p["id"], words=list(p["words"]), bif=p["bif"]) for p in v["pages"]]) for k, v in cells.items()}
    OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(out)); return out


if __name__ == "__main__":
    c = build(); print({k: sum(len(p["words"]) for p in v["pages"]) for k, v in c.items()})
