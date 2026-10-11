"""Section effect of each map's per-folio pitch statistics with the permutation done WITHIN Currier language (A / B / ?), so that the
well-known A-B vocabulary difference cannot by itself produce a 'section' effect. Cross-fitted maps (fit on one folio parity, evaluate on the
other). Writes results/section_stratified.csv."""
import sys
import numpy as np
import pandas as pd
import h02_lib as L


def strat_perm_eta(x, sections, lang, n_perm, rng):
    obs = L.eta_squared(x, sections)
    c = 0
    for _ in range(n_perm):
        perm = sections.copy()
        for g in np.unique(lang):
            ix = np.where(lang == g)[0]
            perm[ix] = rng.permutation(sections[ix])
        c += L.eta_squared(x, perm) >= obs - 1e-12
    return obs, (1 + c) / (1 + n_perm)


def main(n_perm=1000):
    rng = np.random.default_rng(3)
    rows = []
    for tok in ("T1", "T2"):
        t = L.build_ms(tok)
        sections = np.array(t.folio_section)
        lang = np.array(t.folio_language)
        keep = np.isin(sections, ["herbal", "biological", "pharmaceutical", "stars", "cosmological", "astronomical", "text-only"])
        st = {f: L.unit_stats(t, t.fold != f, slot_grammar=True, seed=1) for f in (0, 1)}
        for m in L.map_names(True):
            words = {}
            for f in (0, 1):
                pv = L.build_map(m, st[f], t.inv)
                te = t.fold == f
                words[f] = L.light_word_stats(pv, t.U[te], t.L[te])
            for key in ("meanP", "mai", "mono"):
                x = np.where(keep, L.folio_means(t, words, key), np.nan)
                eta, p = strat_perm_eta(x, sections, lang, n_perm, rng)
                rows.append({"tok": tok, "map": m, "folio_stat": key, "eta2_section": eta, "p_section_within_language": p})
        print(tok, "done", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(L.HERE / "results" / "section_stratified.csv", index=False)


if __name__ == "__main__":
    main()
