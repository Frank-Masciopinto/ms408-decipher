# h41: can a long-range statistic see a plaintext at MS sample size?

Pre-registered in [PREREG.md](PREREG.md) before this measurement. The numbers below are stream statistics. This note makes no translation claim.

## Question
h27 and h34–h39 could not separate Boccaccio from Zipf nonsense on the short-range fingerprint. This stage asks whether any of four long-range statistics can do so at 10,500 tokens, and, if one can, whether MS 408 sits nearer a cipher or a generator than plain Boccaccio on that statistic.

## Streams
Each scored stream is up to 10,500 word tokens. `new_type` and `mi100` use the whole stream. `burst` and `block_js` use only complete blocks of 200 tokens (52 blocks, 10,400 tokens, on a stream of 10,500).

- **real:** five non-overlapping windows of `it_boccaccio` (61,623 tokens), starts 0, 10500, 21000, 31500, 42000.
- **shuffle / zipf:** `h27_lib.shuffle_plaintext` and `h27_lib.zipf_plaintext` on the full Boccaccio token list, then `h27_lib.encrypt_swap` (Naibbe tables, suffix-swap copy at 5%). Builder seed and encrypt seed are the same integer, s = 1..5. `n_words_out` is 21,000; the scored stream is the first 10,500 ciphertext tokens.
- **real Naibbe:** the same `encrypt_swap` on the real Boccaccio token list, seeds 1..5. This arm is not in the separation test. It is the third cipher arm in V2.
- **C0:** h12's C0 engine, fit once on every paragraph word of hand 2B (10,722 tokens, seed 0, `n_random` 60, `n_local` 10, one worker) and generated at seeds 1..5. Fit distance 2.568791252903033 in 55.3 s. The grammar encoder does not read a plaintext; `FIT_PLAIN` files are not in this checkout, so the unused `plaintext()` call was replaced locally with a one-token placeholder. h12's file was not edited.
- **MS:** ZL3b paragraph words from the h14/h30 loader (comma is a word space). Hand 1A has 10,326 paragraph words, so that stream is the whole hand (51 blocks). Hands 2B and 3B are the first 10,500 of 10,722 and 10,835.

## Statistics
Words are atoms.

- **new_type:** fraction of types in the second half that are absent from the first half.
- **burst:** among the 50 most frequent types, the mean of (count in the busiest block) / (count / number of blocks).
- **mi100:** word-identity mutual information at lag 100 divided by mutual information at lag 1, in bits. A lag with no pairs contributes 0. If lag-1 MI is 0, the ratio is 0.
- **block_js:** mean Jensen–Shannon divergence, in bits, between unigram distributions of adjacent blocks.

A statistic passes only when `min(real) > max(shuffle)` and `min(real) > max(zipf)`. C0 is not part of that test.

## Results

| statistic | pass | real min | real max | shuffle min | shuffle max | zipf min | zipf max |
|---|---|---:|---:|---:|---:|---:|---:|
| new_type | fail | 0.5818692902319045 | 0.6272073250490516 | 0.5589767882520132 | 0.5794258373205742 | 0.5924147863658186 | 0.6140675613142064 |
| burst | pass | 4.159652016568825 | 4.781029295031292 | 3.3985184335917444 | 3.697430297038519 | 3.376958109692759 | 3.7377509856066924 |
| mi100 | fail | 0.9254644359719153 | 0.9400281729740418 | 0.9930965907938883 | 0.9958072271644837 | 0.9892567298642228 | 0.9960953542267098 |
| block_js | fail | 0.573066567106806 | 0.602289993481376 | 0.6913504329434357 | 0.7041854482570596 | 0.6793544329604723 | 0.7002245319111176 |

**V1 passes.** `burst` is the only statistic with the real windows entirely above both shuffle and zipf.

**V2 was scored and fails.** On `burst`, the reference means are plain Boccaccio 4.402081542330917, C0 3.5867051345582914, and the three cipher arms 3.543444437990193 (shuffle 3.518861106966517, zipf 3.555041851245959, real Naibbe 3.5564303557581036). Absolute distances:

| hand | burst | distance to plain | distance to C0 | distance to cipher-arm mean | closer to the nearer alternative |
|---|---:|---:|---:|---:|---|
| 1A | 5.219012840162134 | 0.8169312978312169 | 1.6323077056038424 | 1.6755684021719408 | no |
| 2B | 5.105382669895541 | 0.7033011275646244 | 1.51867753533725 | 1.5619382319053483 | no |
| 3B | 5.10075104898875 | 0.6986695066578328 | 1.5140459144304583 | 1.5573066109985567 | no |

Each hand is nearer plain Boccaccio than either C0 or the cipher-arm mean. The figure is `figures/plaintext_visibility.png`. Per-stream values are in `results/scores.json`; the verdict is in `results/STATUS.json` (`complete` true, `n_random` 60).

## Reproduce
From this directory, with `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`, and OMP/OPENBLAS/MKL/NUMEXPR threads set to 1:

```
python3 -m pytest test_h41.py -p no:cacheprovider -q
python3 run_h41.py
python3 summarise.py
```

`run_h41.py` keeps an existing `results/scores.json` and fills only missing arms. An optional argument replaces `n_random` (default 60).
