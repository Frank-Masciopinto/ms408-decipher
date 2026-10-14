# h45: is the last-glyph link a vowel/consonant pattern?

Pre-registered in `PREREG.md` before this measurement. The numbers are stream statistics. This note makes no translation claim.

## Measure

A pair is the last unit of a word and the first unit of the next word, and only when both words sit on the same line.
Sukhotin is fit on within-word adjacent units of that same stream. Units it calls vowels are V. Every other unit it scored is C. A pair that uses an unscored unit is dropped.
MI_glyph is the plug-in mutual information of the glyph pair, in bits. MI_class is the same quantity for the class pair. share = MI_class / MI_glyph. A stream with MI_glyph = 0 is excluded.
Manuscript, self-citation, and gap-rule streams use collapsed EVA units (`h13_lib.SEG`). Natural-language streams use characters.

## Streams

Manuscript hands are the whole ZL3b paragraph hand from the h14 table (comma is a word space), in the h30 line order. Controls are the first 10,500 tokens of Boccaccio, Libro della cucina, Pliny herbal books XX-XXVII, and Macer Floridus, cut on the source lines of those tokens.
Self-citation is the first 10,500 tokens of `fitted_s1`, on its own whitespace lines. The gap rule fits `h34_lib.fit_table` on collapsed units of the hand 2B lines and applies `h34_lib.apply_rule` at strength 1 to every token of `fitted_s1`, with numpy seed 45.

| stream | n | lines | pairs | MI_glyph | MI_class | share |
|---|---|---|---|---|---|---|
| MS 1A | 10326 | 1477 | 8849 | 0.16827250521933423 | 0.009690432117274057 | 0.05758773309188626 |
| MS 2B | 10722 | 1227 | 9495 | 0.28442934300288397 | 0.01867185639968303 | 0.06564673040605978 |
| MS 3B | 10835 | 1100 | 9735 | 0.26557025705741283 | 0.01521076401963646 | 0.057275856822882436 |
| Boccaccio | 10500 | 63 | 10437 | 0.10468174819115547 | 0.000221399383009099 | 0.0021149759803859003 |
| Cucina | 10500 | 1043 | 9457 | 0.13926228614021924 | 0.0007102977755724512 | 0.005100431676507684 |
| Pliny XX-XXVII | 10500 | 1374 | 9126 | 0.06122885929688234 | 2.6585562050937886e-05 | 0.0004341998586325382 |
| Macer | 10500 | 1698 | 8802 | 0.2287178666043858 | 0.04808471207815729 | 0.21023592425041984 |
| self-citation | 10500 | 1209 | 9291 | 0.01623364605651391 | 3.300614299493244e-05 | 0.0020331934600538123 |
| gap rule | 48671 | 5408 | 43263 | 0.20823934709041178 | 0.00019220168188047778 | 0.0009229844626675146 |

## Sukhotin vowels

Pick order from `msdecipher.stats.sukhotin`.

- MS 1A: o a y n e g u
- MS 2B: o e a y n h z
- MS 3B: o a e n y f u c
- Boccaccio: e a o i u
- Cucina: e o a i u h x
- Pliny XX-XXVII: i e u a o y
- Macer: u i e a o y
- self-citation: o a d i
- gap rule: a o d i

## Predictions

- C1. Median share of the four controls is at least 0.25: **fail**. Median `0.0036077038284467924`.
- C2. Scored only if C1 passes. Every manuscript hand is below the lowest control: **not scored**. Lowest control `0.0004341998586325382`.
- C3. Scored only if C1 passes. Self-citation and the gap-rule stream are both below the lowest control: **not scored**.

The figure is `figures/edge_classes.png`. Per-stream records are in `results/streams.json`. The verdict is in `results/STATUS.json`.

## Reproduce

```
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python -m pytest -p no:cacheprovider hypotheses/h45_edge_link_classes/test_h45.py
python hypotheses/h45_edge_link_classes/run_h45.py
python hypotheses/h45_edge_link_classes/summarise.py
```

numpy 2.5.4, python 3.12.3.
