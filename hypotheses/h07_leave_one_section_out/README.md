# h07 — leave-one-section-out falsification test

**Question.** Is MS 408's section-to-section change better *predicted* as (a) a no-plaintext generator switching settings or as (b) a topic-plaintext hybrid whose
vocabulary changes because the subject changes? Here each model has to predict a section it has never seen. Nothing here decodes MS 408. It is still undeciphered.

## Design (pre-registered in `results/prereg.json`, written before any prediction)
* 5 folds, one per section class (herbal, recipes, biological, pharmaceutical, cosmo-astro). Every model is fitted only on the other 4 sections plus the text-only
  folios: the grammar, engine, pools, tilts, codebook context and hybrid engine parameters. The held-out folios add only their token counts and Currier labels to the layout.
* How the held-out section gets its settings, fixed before any held-out text is used:
  * **nearest**: the training section with the closest Currier-A folio share (metadata only). Resolved as herbal→pharmaceutical, recipes→biological,
    biological→cosmo-astro, pharmaceutical→herbal, cosmo-astro→biological.
  * **pooled**: settings fitted on all training text together.
  * **random-section null**: a random training section, drawn per seed.
* Family (a): the h06 section-varying (SV) variants P50, U and EUP25, each under the nearest and pooled rules.
  Family (b): A1 (Naibbe tokens) and A2 (whole-word codebook) hybrids. The held-out section encodes its topical Latin work (`TOPIC_WORK`); the null gives it a random other work.
  Baseline: C0g, one global copy-modify engine with no section dependence.
* Predicted statistics: each is measured on the generated held-out section *relative to the generated other sections of the same run*, and compared with the
  same statistic on the real MS 408 held-out section relative to the real other sections (definitions in `h07_lib.STAT_LABELS`):
  token overlap, new-type rate, hapax share, TTR, mean word-JS to the other sections (plus the 4-vector pattern), unit JS, mean length, unit H1/h2, and top-30 rank stability.
* 8 seeds per model. `predictions_runs.csv`, `prereg.json` and the SHA256 manifest (`predictions_manifest.json`) were written first. `score` refuses to run if
  they have changed. MS 408 SE = delete-one-block jackknife (blocks of 3 held-out folios). z = (gen mean − MS)/sqrt(SD_gen²(1+1/n) + SE_MS²).

## Results (`results/summary_by_generator.csv`; 50 cells = 5 sections × 10 statistics)

| model | family | mean \|z\| | in 95 % PI | mean rel. error | JS-pattern r | section-specific params |
|---|---|---|---|---|---|---|
| SV U nearest | a | 4.66 | 14/50 | 0.45 | 0.52 | 451 |
| SV P50 nearest (primary a) | a | 4.70 | 11/50 | 0.37 | 0.56 | 255 |
| A1 topic-matched | b | 4.90 | 12/50 | 0.52 | 0.60 | 0 (+7 engine) |
| SV EUP25 nearest | a | 4.95 | 7/50 | 0.37 | 0.62 | 611 |
| C0g global baseline | – | 5.06 | 16/50 | 0.50 | 0.60 | 0 (+6 engine) |
| A2 topic-matched (primary b) | b | 6.31 | 12/50 | 0.50 | 0.34 | 0 (+7 engine) |
| SV EUP25 random-section null | null | 2.53* | 28/50* | 0.33 | 0.32 | 611 |
| A2 random-topic null | null | 3.85* | 25/50* | 0.35 | 0.09 | 0 |

\*The nulls mix settings across seeds. That widens their seed spread and so shrinks \|z\|. Judge them by relative error, not by \|z\|.

* **Primary comparison:** SV P50 nearest beats A2 topic-matched. Mean \|z\| is 4.70 vs 6.31, SV is better in 30 of 46 cells, Wilcoxon p = 0.0098. Relative error is 0.37 vs 0.50 (p = 0.001).
  A1 topic-matched vs SV P50 nearest: no significant \|z\| difference (p = 0.61).
* **No model predicts unseen sections well.** Each gets only 7–16 of 50 cells inside its 95 % interval, about what the global baseline gets. None of the SV rows beats the
  global baseline after Holm correction (all raw p ≥ 0.23 on \|z\|).
* **Neither rule beats its own random version.** The pre-registered nearest-section rule is not better than a random training section (relative error 0.37 vs 0.33). The topical
  plaintext is not better than a random plaintext: A2 random-topic has *lower* error than A2 topic-matched (0.35 vs 0.50).
* **Where the models fail** (`fig3`, `mean_absz_by_stat_selected.csv`). Every real held-out section is *more novel* than copy-modify models predict. The new-type rate is
  0.62/0.61/0.44/0.39/0.30 against about 0.47/0.48/0.38/0.28/0.24 from C0g, SV P50 is barely better, and C0g/SV overpredict token overlap. The A2 codebook overshoots the other way:
  overlap ≈ 0.28 vs 0.78–0.89, and a new-type rate around 0.7–0.78. The real text sits between "same engine, new settings" and "new subject, new code words". Hapax share is predicted well by all copy-modify models (\|z\| ≈ 1.7).

## Verdict
The only pre-registered head-to-head that is significant favours the **setting-switch family over the topic codebook**: SV P50 nearest predicts the held-out
sections better than A2 topic-matched. This is a weak, negative-leaning result, not support for a generator:
1. the setting-switch models do not beat a global no-section copy-modify baseline;
2. choosing the "right" settings (nearest) is no better than choosing at random;
3. choosing the topically right Latin is no better than choosing a random text.
So **neither "language-like topic shift" nor "generator setting switch" carries real predictive information about an unseen section**. In both families, what
the held-out section looks like is set by the shared engine, not by the section-specific part. The data reject the topic codebook *in the form tested* most clearly. A whole-word
code for topic Latin produces far too little vocabulary overlap between sections. Every model underestimates how much new vocabulary a new section brings.

## Caveats
* There are only 5 held-out units, and they differ a lot in size (976 to 11.6k tokens). Cosmo-astro is small, so its SEs are wide and it is easy to "predict".
* The z-scores assume the 8-seed spread is the model's predictive spread. Mixture nulls get credit for that spread (see *). Relative error has no such inflation.
* Engine searches were shortened (30 random + 3×8 local candidates per fit) to make 5 folds × many models feasible. Better-tuned models might do somewhat better.
* The "nearest" rule uses one metadata feature (Currier-A share). Other pre-registrable rules (illustration similarity, quire position) were not tried, and trying them now would be peeking.
* Some top-30 rank correlations are undefined (NaN) when a generated held-out section contains none of the top words. They are left out of means.
* The topic hybrids use the same five Latin works as the hybrid stage. "Topical Latin" is a proxy for whatever the real underlying text might be.

## Files
`h07_lib.py` (statistics, jackknife, nearest rule, prereg), `run_h07.py predict|score`, `test_h07.py`; `results/`: `prereg.json`, `predictions_runs.csv`,
`predictions_manifest.json`, `parameter_counts.csv`, `ms408_heldout_stats.csv`, `ms408_heldout_jackknife_se.csv`, `scores_long.csv`, `summary_by_generator.csv`,
`mean_absz_by_section.csv`, `mean_absz_by_stat_selected.csv`, `paired_comparisons.csv`, `predict_log.txt`; `figures/fig1–3`.
Reproduce: `python run_h07.py predict` (~30 min), then `python run_h07.py score`.
