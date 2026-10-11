# Control comparison: MS 408 vs controls

> **MS 408 is undeciphered.** This is a screening comparison of descriptive statistics, not a decipherment, and no single metric is decisive. Controls are built from a modest number of base texts (Latin incl. herbal/medical, Italian, German, Hebrew and Arabic prose); transformations are simplified illustrations of each family, NOT reproductions of published ciphers; generators are not fitted to MS 408. See [docs/CONTROLS.md](../../docs/CONTROLS.md).

Target size 35000 tokens per sample (MS 408 running text: 34977 readable tokens). Plain texts are sampled in up to 3 non-overlapping size-matched windows; stochastic controls are means over 3 seeds. Controls use single characters as units; MS 408 uses the collapsed EVA segmentation (ch, sh, cth, ckh, cph, cfh as single units) unless marked raw. Tables: `comparison.csv` (means, all windows), `comparison_sd.csv`, `comparison_runs.csv`, `comparison_ci.csv` (jackknife SE per control row), `ms408_ci.csv`.

## 1. All corpora (window 0), selected metrics

16 further rows (later windows of the plain texts) are in `comparison.csv`.

| name | family | tokens | TTR | Zipf s | Heaps β | len | H1 | h2 | h3 | Δh2 shuf | vowel-like | pos-skew | adj-edit1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MS408 P (collapsed units) | MS 408 | 34977 | 0.205 | 0.985 | 0.747 | 4.466 | 3.901 | 2.217 | 1.954 | 1.348 | 0.222 | 0.923 | 0.034 |
| MS408 P (raw EVA chars) | MS 408 | 34977 | 0.205 | 0.985 | 0.747 | 4.993 | 3.879 | 2.079 | 1.851 | 1.495 | 0.286 | 0.950 | 0.034 |
| MS408 Currier A (collapsed) | MS 408 | 11300 | 0.292 | 0.943 | 0.774 | 4.156 | 3.940 | 2.321 | 2.019 | 1.234 | 0.269 | 0.958 | 0.038 |
| MS408 Currier B (collapsed) | MS 408 | 23128 | 0.210 | 1.021 | 0.737 | 4.620 | 3.859 | 2.048 | 1.801 | 1.457 | 0.259 | 0.909 | 0.032 |
| MS408 P tokens shuffled (collapsed) | MS 408 | 34977 | 0.205 | 0.985 | 0.747 | 4.466 | 3.901 | 2.217 | 1.954 | 1.346 | 0.222 | 0.923 | 0.018 |
| MS408 P letters shuffled in tokens (collapsed) | MS 408 | 34977 | 0.547 | 0.758 | 0.903 | 4.465 | 3.901 | 3.563 | 3.191 | -0.025 | 0.333 | 0.000 | 0.009 |
| plain:la_vulgate | natural-language plaintext (Latin/Italian/German) | 35000 | 0.201 | 0.875 | 0.757 | 5.315 | 3.949 | 3.213 | 2.513 | 0.665 | 0.273 | 0.409 | 0.003 |
| plain:la_augustine | natural-language plaintext (Latin/Italian/German) | 35000 | 0.274 | 0.963 | 0.807 | 5.437 | 3.915 | 3.162 | 2.579 | 0.686 | 0.286 | 0.571 | 0.006 |
| plain:la_pliny_herbal | natural-language plaintext (Latin/Italian/German) | 35000 | 0.273 | 0.807 | 0.800 | 5.906 | 3.963 | 3.227 | 2.665 | 0.687 | 0.273 | 0.619 | 0.003 |
| plain:la_pliny_general | natural-language plaintext (Latin/Italian/German) | 35000 | 0.378 | 0.772 | 0.854 | 5.971 | 3.956 | 3.246 | 2.753 | 0.664 | 0.286 | 0.619 | 0.002 |
| plain:la_celsus | natural-language plaintext (Latin/Italian/German) | 35000 | 0.219 | 0.909 | 0.767 | 5.563 | 3.931 | 3.167 | 2.512 | 0.703 | 0.286 | 0.476 | 0.004 |
| plain:la_isidore | natural-language plaintext (Latin/Italian/German) | 35000 | 0.270 | 0.915 | 0.806 | 5.671 | 3.953 | 3.198 | 2.601 | 0.692 | 0.273 | 0.524 | 0.004 |
| plain:la_macer | natural plaintext, UNDERSIZED (<80% of target; sensitivity only) | 13967 | 0.279 | 0.765 | 0.766 | 5.847 | 3.967 | 3.184 | 2.470 | 0.726 | 0.286 | 0.571 | 0.002 |
| plain:it_dante | natural-language plaintext (Latin/Italian/German) | 35000 | 0.187 | 1.045 | 0.756 | 3.928 | 4.015 | 2.987 | 2.474 | 0.882 | 0.273 | 0.810 | 0.020 |
| plain:it_manzoni | natural-language plaintext (Latin/Italian/German) | 35000 | 0.186 | 0.985 | 0.749 | 4.588 | 4.005 | 2.996 | 2.439 | 0.901 | 0.238 | 0.810 | 0.011 |
| plain:it_sidrach | natural-language plaintext (Latin/Italian/German) | 35000 | 0.143 | 1.045 | 0.714 | 4.088 | 3.987 | 2.979 | 2.355 | 0.879 | 0.280 | 0.826 | 0.057 |
| plain:it_ariosto | natural-language plaintext (Latin/Italian/German) | 35000 | 0.175 | 1.002 | 0.749 | 4.086 | 3.998 | 3.010 | 2.470 | 0.848 | 0.286 | 0.762 | 0.013 |
| plain:de_walther_mhg | natural plaintext, UNDERSIZED (<80% of target; sensitivity only) | 9183 | 0.322 | 0.893 | 0.784 | 4.712 | 4.070 | 2.964 | 2.283 | 0.954 | 0.304 | 0.522 | 0.012 |
| plain:de_faust | natural-language plaintext (Latin/Italian/German) | 30891 | 0.199 | 1.056 | 0.752 | 4.798 | 4.098 | 2.947 | 2.217 | 0.998 | 0.269 | 0.480 | 0.005 |
| abjad:la_vulgate | abjad (vowels removed) | 34630 | 0.129 | 0.980 | 0.701 | 2.832 | 3.568 | 3.029 | 2.345 | 0.453 | 0.529 | 0.471 | 0.068 |
| abjad:la_pliny_herbal | abjad (vowels removed) | 34595 | 0.171 | 0.871 | 0.735 | 3.190 | 3.558 | 3.140 | 2.551 | 0.354 | 0.471 | 0.375 | 0.051 |
| abjad:la_celsus | abjad (vowels removed) | 34611 | 0.133 | 0.970 | 0.702 | 2.961 | 3.533 | 3.056 | 2.401 | 0.387 | 0.438 | 0.500 | 0.069 |
| abjad:it_manzoni | abjad (vowels removed) | 32260 | 0.129 | 1.042 | 0.709 | 2.673 | 3.678 | 3.002 | 2.430 | 0.479 | 0.312 | 0.312 | 0.079 |
| abjad:it_sidrach | abjad (vowels removed) | 31803 | 0.088 | 1.113 | 0.655 | 2.402 | 3.672 | 2.956 | 2.193 | 0.480 | 0.250 | 0.278 | 0.152 |
| monoalphabetic:la_vulgate | monoalphabetic substitution | 35000 | 0.201 | 0.875 | 0.754 | 5.315 | 3.949 | 3.213 | 2.513 | 0.665 | 0.273 | 0.409 | 0.003 |
| monoalphabetic:la_pliny_herbal | monoalphabetic substitution | 35000 | 0.273 | 0.807 | 0.801 | 5.906 | 3.963 | 3.227 | 2.665 | 0.686 | 0.273 | 0.619 | 0.003 |
| monoalphabetic:la_celsus | monoalphabetic substitution | 35000 | 0.219 | 0.909 | 0.769 | 5.563 | 3.931 | 3.167 | 2.512 | 0.702 | 0.286 | 0.476 | 0.004 |
| monoalphabetic:it_manzoni | monoalphabetic substitution | 35000 | 0.186 | 0.985 | 0.748 | 4.588 | 4.005 | 2.996 | 2.439 | 0.900 | 0.238 | 0.810 | 0.011 |
| monoalphabetic:it_sidrach | monoalphabetic substitution | 35000 | 0.143 | 1.045 | 0.717 | 4.088 | 3.987 | 2.979 | 2.355 | 0.880 | 0.280 | 0.826 | 0.057 |
| caesar3:la_vulgate | monoalphabetic substitution | 35000 | 0.201 | 0.875 | 0.757 | 5.315 | 3.949 | 3.213 | 2.513 | 0.665 | 0.273 | 0.409 | 0.003 |
| caesar3:la_pliny_herbal | monoalphabetic substitution | 35000 | 0.273 | 0.807 | 0.800 | 5.906 | 3.963 | 3.227 | 2.665 | 0.687 | 0.273 | 0.619 | 0.003 |
| caesar3:la_celsus | monoalphabetic substitution | 35000 | 0.219 | 0.909 | 0.767 | 5.563 | 3.931 | 3.167 | 2.512 | 0.703 | 0.286 | 0.476 | 0.004 |
| caesar3:it_manzoni | monoalphabetic substitution | 35000 | 0.186 | 0.985 | 0.749 | 4.588 | 4.005 | 2.996 | 2.439 | 0.901 | 0.238 | 0.810 | 0.011 |
| caesar3:it_sidrach | monoalphabetic substitution | 35000 | 0.143 | 1.045 | 0.714 | 4.088 | 3.987 | 2.979 | 2.355 | 0.879 | 0.280 | 0.826 | 0.057 |
| vigenere_k3:la_vulgate | polyalphabetic (Vigenere) | 35000 | 0.303 | 0.725 | 0.812 | 5.315 | 4.356 | 3.827 | 2.892 | 0.487 | 0.369 | 0.238 | 0.002 |
| vigenere_k3:la_pliny_herbal | polyalphabetic (Vigenere) | 35000 | 0.391 | 0.732 | 0.855 | 5.906 | 4.371 | 3.834 | 3.034 | 0.501 | 0.394 | 0.344 | 0.001 |
| vigenere_k3:la_celsus | polyalphabetic (Vigenere) | 35000 | 0.331 | 0.827 | 0.825 | 5.563 | 4.350 | 3.788 | 2.884 | 0.518 | 0.382 | 0.245 | 0.001 |
| vigenere_k3:it_manzoni | polyalphabetic (Vigenere) | 35000 | 0.273 | 0.920 | 0.796 | 4.588 | 4.412 | 3.743 | 2.786 | 0.596 | 0.360 | 0.456 | 0.008 |
| vigenere_k3:it_sidrach | polyalphabetic (Vigenere) | 35000 | 0.217 | 0.949 | 0.767 | 4.088 | 4.404 | 3.717 | 2.696 | 0.604 | 0.372 | 0.552 | 0.047 |
| vigenere_k6:la_vulgate | polyalphabetic (Vigenere) | 35000 | 0.378 | 0.683 | 0.845 | 5.315 | 4.571 | 4.190 | 3.188 | 0.349 | 0.410 | 0.090 | 0.001 |
| vigenere_k6:la_pliny_herbal | polyalphabetic (Vigenere) | 35000 | 0.474 | 0.728 | 0.884 | 5.906 | 4.582 | 4.194 | 3.316 | 0.360 | 0.410 | 0.154 | 0.001 |
| vigenere_k6:la_celsus | polyalphabetic (Vigenere) | 35000 | 0.412 | 0.769 | 0.856 | 5.563 | 4.569 | 4.160 | 3.168 | 0.379 | 0.397 | 0.103 | 0.001 |
| vigenere_k6:it_manzoni | polyalphabetic (Vigenere) | 35000 | 0.337 | 0.859 | 0.825 | 4.588 | 4.595 | 4.147 | 3.078 | 0.404 | 0.436 | 0.269 | 0.007 |
| vigenere_k6:it_sidrach | polyalphabetic (Vigenere) | 35000 | 0.274 | 0.883 | 0.798 | 4.088 | 4.590 | 4.120 | 2.990 | 0.418 | 0.449 | 0.308 | 0.047 |
| nomenclator:la_vulgate | nomenclator-like syllable code | 35000 | 0.201 | 0.875 | 0.754 | 4.140 | 4.291 | 4.058 | 3.426 | 0.165 | 0.500 | 0.017 | 0.013 |
| nomenclator:la_pliny_herbal | nomenclator-like syllable code | 35000 | 0.273 | 0.807 | 0.801 | 4.786 | 4.296 | 4.052 | 3.529 | 0.202 | 0.483 | 0.033 | 0.008 |
| nomenclator:la_celsus | nomenclator-like syllable code | 35000 | 0.219 | 0.909 | 0.769 | 4.440 | 4.296 | 4.047 | 3.409 | 0.202 | 0.483 | 0.000 | 0.016 |
| nomenclator:it_manzoni | nomenclator-like syllable code | 35000 | 0.186 | 0.985 | 0.748 | 3.898 | 4.285 | 3.905 | 3.219 | 0.288 | 0.500 | 0.050 | 0.019 |
| nomenclator:it_sidrach | nomenclator-like syllable code | 35000 | 0.143 | 1.045 | 0.717 | 3.528 | 4.273 | 3.821 | 3.033 | 0.315 | 0.467 | 0.017 | 0.026 |
| verbose_2sym:la_vulgate | verbose cipher (letter -> 2 symbols) | 35000 | 0.566 | 0.746 | 0.917 | 10.630 | 3.798 | 2.870 | 2.365 | 0.901 | 0.500 | 0.396 | 0.000 |
| verbose_2sym:la_pliny_herbal | verbose cipher (letter -> 2 symbols) | 35000 | 0.675 | 0.824 | 0.941 | 11.812 | 3.813 | 2.888 | 2.374 | 0.903 | 0.479 | 0.396 | 0.000 |
| verbose_2sym:la_celsus | verbose cipher (letter -> 2 symbols) | 35000 | 0.602 | 0.888 | 0.918 | 11.125 | 3.799 | 2.849 | 2.342 | 0.926 | 0.479 | 0.375 | 0.000 |
| verbose_2sym:it_manzoni | verbose cipher (letter -> 2 symbols) | 35000 | 0.482 | 0.995 | 0.887 | 9.175 | 3.845 | 2.864 | 2.286 | 0.942 | 0.500 | 0.479 | 0.001 |
| verbose_2sym:it_sidrach | verbose cipher (letter -> 2 symbols) | 35000 | 0.411 | 1.006 | 0.871 | 8.175 | 3.860 | 2.805 | 2.248 | 1.001 | 0.458 | 0.479 | 0.003 |
| naibbe_like:la_vulgate | Naibbe-inspired homophonic tiles | 35000 | 0.651 | 0.879 | 0.935 | 11.066 | 3.751 | 3.316 | 2.629 | 0.423 | 0.476 | 0.071 | 0.000 |
| naibbe_like:la_pliny_herbal | Naibbe-inspired homophonic tiles | 35000 | 0.750 | 0.916 | 0.955 | 12.145 | 3.754 | 3.376 | 2.741 | 0.368 | 0.452 | 0.119 | 0.000 |
| naibbe_like:la_celsus | Naibbe-inspired homophonic tiles | 35000 | 0.674 | 0.799 | 0.934 | 11.541 | 3.752 | 3.323 | 2.637 | 0.418 | 0.476 | 0.024 | 0.000 |
| naibbe_like:it_manzoni | Naibbe-inspired homophonic tiles | 35000 | 0.548 | 0.924 | 0.901 | 9.408 | 3.758 | 3.335 | 2.664 | 0.406 | 0.476 | 0.071 | 0.001 |
| naibbe_like:it_sidrach | Naibbe-inspired homophonic tiles | 35000 | 0.491 | 0.950 | 0.892 | 8.417 | 3.760 | 3.327 | 2.642 | 0.413 | 0.500 | 0.071 | 0.004 |
| reverse_words:la_vulgate | word reversal | 35000 | 0.201 | 0.875 | 0.757 | 5.315 | 3.949 | 3.294 | 2.675 | 0.584 | 0.273 | 0.409 | 0.003 |
| reverse_words:la_pliny_herbal | word reversal | 35000 | 0.273 | 0.807 | 0.800 | 5.906 | 3.963 | 3.298 | 2.836 | 0.616 | 0.273 | 0.619 | 0.003 |
| reverse_words:la_celsus | word reversal | 35000 | 0.219 | 0.909 | 0.767 | 5.563 | 3.931 | 3.260 | 2.669 | 0.609 | 0.286 | 0.476 | 0.004 |
| reverse_words:it_manzoni | word reversal | 35000 | 0.186 | 0.985 | 0.749 | 4.588 | 4.005 | 3.298 | 2.574 | 0.598 | 0.238 | 0.810 | 0.011 |
| reverse_words:it_sidrach | word reversal | 35000 | 0.143 | 1.045 | 0.714 | 4.088 | 3.987 | 3.300 | 2.501 | 0.560 | 0.280 | 0.826 | 0.057 |
| alphagram:la_vulgate | anagram (alphagram) | 35000 | 0.194 | 0.883 | 0.753 | 5.315 | 3.949 | 2.532 | 2.220 | 1.345 | 0.364 | 0.955 | 0.006 |
| alphagram:la_pliny_herbal | anagram (alphagram) | 35000 | 0.262 | 0.805 | 0.793 | 5.906 | 3.963 | 2.530 | 2.262 | 1.384 | 0.455 | 1.000 | 0.004 |
| alphagram:la_celsus | anagram (alphagram) | 35000 | 0.210 | 0.903 | 0.761 | 5.563 | 3.931 | 2.513 | 2.189 | 1.357 | 0.381 | 0.905 | 0.005 |
| alphagram:it_manzoni | anagram (alphagram) | 35000 | 0.179 | 0.988 | 0.744 | 4.588 | 4.005 | 2.656 | 2.331 | 1.241 | 0.333 | 1.000 | 0.011 |
| alphagram:it_sidrach | anagram (alphagram) | 35000 | 0.136 | 1.047 | 0.707 | 4.088 | 3.987 | 2.653 | 2.295 | 1.207 | 0.400 | 0.957 | 0.057 |
| shuffle_letters:la_vulgate | letters shuffled inside words | 35000 | 0.610 | 0.804 | 0.932 | 5.315 | 3.949 | 3.879 | 3.754 | -0.008 | 0.273 | 0.000 | 0.003 |
| shuffle_letters:la_pliny_herbal | letters shuffled inside words | 35000 | 0.712 | 0.918 | 0.953 | 5.906 | 3.963 | 3.914 | 3.818 | -0.005 | 0.318 | 0.000 | 0.002 |
| shuffle_letters:la_celsus | letters shuffled inside words | 35000 | 0.644 | 0.977 | 0.933 | 5.563 | 3.931 | 3.869 | 3.744 | -0.007 | 0.317 | 0.016 | 0.003 |
| shuffle_letters:it_manzoni | letters shuffled inside words | 35000 | 0.505 | 1.139 | 0.903 | 4.588 | 4.005 | 3.897 | 3.704 | -0.024 | 0.238 | 0.000 | 0.009 |
| shuffle_letters:it_sidrach | letters shuffled inside words | 35000 | 0.433 | 1.110 | 0.891 | 4.088 | 3.987 | 3.859 | 3.629 | -0.024 | 0.293 | 0.000 | 0.052 |
| shuffle_tokens:la_vulgate | shuffled tokens | 35000 | 0.201 | 0.875 | 0.756 | 5.315 | 3.949 | 3.213 | 2.513 | 0.664 | 0.273 | 0.409 | 0.008 |
| shuffle_tokens:la_pliny_herbal | shuffled tokens | 35000 | 0.273 | 0.807 | 0.802 | 5.906 | 3.963 | 3.227 | 2.665 | 0.687 | 0.273 | 0.619 | 0.005 |
| shuffle_tokens:la_celsus | shuffled tokens | 35000 | 0.219 | 0.909 | 0.769 | 5.563 | 3.931 | 3.167 | 2.512 | 0.702 | 0.286 | 0.476 | 0.005 |
| shuffle_tokens:it_manzoni | shuffled tokens | 35000 | 0.186 | 0.985 | 0.747 | 4.588 | 4.005 | 2.996 | 2.439 | 0.900 | 0.238 | 0.810 | 0.021 |
| shuffle_tokens:it_sidrach | shuffled tokens | 35000 | 0.143 | 1.045 | 0.717 | 4.088 | 3.987 | 2.979 | 2.355 | 0.882 | 0.280 | 0.826 | 0.040 |
| plain:he_tanakh | natural abjad text (Hebrew/Arabic) | 35000 | 0.216 | 0.863 | 0.760 | 3.788 | 4.225 | 3.823 | 2.606 | 0.238 | 0.481 | 0.556 | 0.008 |
| plain_folded:he_tanakh | natural abjad, folded-alphabet variant (sensitivity only) | 35000 | 0.216 | 0.863 | 0.760 | 3.788 | 4.051 | 3.668 | 2.507 | 0.246 | 0.500 | 0.227 | 0.008 |
| plain:he_mishneh_torah | natural abjad text (Hebrew/Arabic) | 35000 | 0.252 | 0.866 | 0.781 | 4.025 | 4.256 | 3.866 | 2.695 | 0.262 | 0.370 | 0.481 | 0.008 |
| plain_folded:he_mishneh_torah | natural abjad, folded-alphabet variant (sensitivity only) | 35000 | 0.252 | 0.866 | 0.781 | 4.025 | 4.075 | 3.715 | 2.594 | 0.257 | 0.364 | 0.136 | 0.008 |
| plain:ar_quran | natural abjad text (Hebrew/Arabic) | 35000 | 0.233 | 0.894 | 0.779 | 4.261 | 4.157 | 3.627 | 2.612 | 0.411 | 0.303 | 0.576 | 0.006 |
| plain_folded:ar_quran | natural abjad, folded-alphabet variant (sensitivity only) | 35000 | 0.231 | 0.895 | 0.778 | 4.241 | 4.033 | 3.524 | 2.583 | 0.407 | 0.286 | 0.500 | 0.007 |
| plain:ar_muqaddimah | natural abjad text (Hebrew/Arabic) | 35000 | 0.291 | 0.869 | 0.815 | 4.458 | 4.299 | 3.743 | 3.039 | 0.380 | 0.364 | 0.576 | 0.003 |
| plain_folded:ar_muqaddimah | natural abjad, folded-alphabet variant (sensitivity only) | 35000 | 0.289 | 0.868 | 0.814 | 4.435 | 4.144 | 3.622 | 2.963 | 0.379 | 0.393 | 0.536 | 0.004 |
| vigenere_k3:he_tanakh | polyalphabetic (Vigenere) | 35000 | 0.326 | 0.795 | 0.820 | 3.788 | 4.551 | 4.231 | 2.942 | 0.236 | 0.457 | 0.136 | 0.005 |
| vigenere_k3:he_mishneh_torah | polyalphabetic (Vigenere) | 35000 | 0.370 | 0.738 | 0.837 | 4.025 | 4.557 | 4.280 | 3.056 | 0.219 | 0.383 | 0.148 | 0.004 |
| vigenere_k3:ar_quran | polyalphabetic (Vigenere) | 35000 | 0.341 | 0.801 | 0.830 | 4.261 | 4.623 | 4.112 | 2.970 | 0.425 | 0.364 | 0.242 | 0.005 |
| vigenere_k3:ar_muqaddimah | polyalphabetic (Vigenere) | 35000 | 0.407 | 0.793 | 0.859 | 4.458 | 4.699 | 4.196 | 3.342 | 0.397 | 0.374 | 0.232 | 0.002 |
| vigenere_k6:he_tanakh | polyalphabetic (Vigenere) | 35000 | 0.404 | 0.729 | 0.852 | 3.788 | 4.678 | 4.449 | 3.271 | 0.174 | 0.444 | 0.049 | 0.002 |
| vigenere_k6:he_mishneh_torah | polyalphabetic (Vigenere) | 35000 | 0.453 | 0.634 | 0.869 | 4.025 | 4.680 | 4.495 | 3.402 | 0.152 | 0.420 | 0.049 | 0.002 |
| vigenere_k6:ar_quran | polyalphabetic (Vigenere) | 35000 | 0.415 | 0.766 | 0.858 | 4.261 | 4.876 | 4.430 | 3.252 | 0.372 | 0.424 | 0.071 | 0.001 |
| vigenere_k6:ar_muqaddimah | polyalphabetic (Vigenere) | 35000 | 0.481 | 0.784 | 0.883 | 4.458 | 4.901 | 4.486 | 3.598 | 0.340 | 0.444 | 0.040 | 0.001 |
| verbose_2sym:he_tanakh | verbose cipher (letter -> 2 symbols) | 35000 | 0.512 | 0.744 | 0.893 | 7.576 | 3.822 | 3.004 | 2.662 | 0.771 | 0.438 | 0.292 | 0.000 |
| verbose_2sym:he_mishneh_torah | verbose cipher (letter -> 2 symbols) | 35000 | 0.568 | 0.734 | 0.907 | 8.050 | 3.835 | 3.019 | 2.683 | 0.776 | 0.417 | 0.292 | 0.000 |
| verbose_2sym:ar_quran | verbose cipher (letter -> 2 symbols) | 35000 | 0.541 | 0.821 | 0.902 | 8.523 | 3.806 | 2.926 | 2.569 | 0.844 | 0.479 | 0.333 | 0.000 |
| verbose_2sym:ar_muqaddimah | verbose cipher (letter -> 2 symbols) | 35000 | 0.606 | 0.784 | 0.922 | 8.917 | 3.823 | 3.004 | 2.635 | 0.787 | 0.458 | 0.375 | 0.000 |
| naibbe_like:he_tanakh | Naibbe-inspired homophonic tiles | 35000 | 0.573 | 0.751 | 0.910 | 8.225 | 3.739 | 3.253 | 2.532 | 0.463 | 0.452 | 0.190 | 0.000 |
| naibbe_like:he_mishneh_torah | Naibbe-inspired homophonic tiles | 35000 | 0.601 | 0.709 | 0.917 | 8.810 | 3.736 | 3.230 | 2.555 | 0.484 | 0.500 | 0.167 | 0.000 |
| naibbe_like:ar_quran | Naibbe-inspired homophonic tiles | 35000 | 0.584 | 0.745 | 0.913 | 9.133 | 3.733 | 3.220 | 2.548 | 0.492 | 0.452 | 0.143 | 0.000 |
| naibbe_like:ar_muqaddimah | Naibbe-inspired homophonic tiles | 35000 | 0.623 | 0.843 | 0.925 | 9.689 | 3.738 | 3.225 | 2.548 | 0.493 | 0.429 | 0.071 | 0.000 |
| reverse_words:he_tanakh | word reversal | 35000 | 0.216 | 0.863 | 0.760 | 3.788 | 4.225 | 3.618 | 2.517 | 0.445 | 0.481 | 0.556 | 0.008 |
| reverse_words:he_mishneh_torah | word reversal | 35000 | 0.252 | 0.866 | 0.781 | 4.025 | 4.256 | 3.694 | 2.745 | 0.434 | 0.370 | 0.481 | 0.008 |
| reverse_words:ar_quran | word reversal | 35000 | 0.233 | 0.894 | 0.779 | 4.261 | 4.157 | 3.580 | 2.602 | 0.456 | 0.303 | 0.576 | 0.006 |
| reverse_words:ar_muqaddimah | word reversal | 35000 | 0.291 | 0.869 | 0.815 | 4.458 | 4.299 | 3.550 | 2.596 | 0.574 | 0.364 | 0.576 | 0.003 |
| alphagram:he_tanakh | anagram (alphagram) | 35000 | 0.177 | 0.836 | 0.730 | 3.788 | 4.225 | 3.085 | 2.636 | 0.977 | 0.370 | 0.852 | 0.013 |
| alphagram:he_mishneh_torah | anagram (alphagram) | 35000 | 0.215 | 0.854 | 0.756 | 4.025 | 4.256 | 3.080 | 2.710 | 1.047 | 0.296 | 0.926 | 0.010 |
| alphagram:ar_quran | anagram (alphagram) | 35000 | 0.212 | 0.899 | 0.765 | 4.261 | 4.157 | 2.991 | 2.384 | 1.044 | 0.273 | 0.970 | 0.008 |
| alphagram:ar_muqaddimah | anagram (alphagram) | 35000 | 0.267 | 0.866 | 0.802 | 4.458 | 4.299 | 3.024 | 2.559 | 1.099 | 0.273 | 0.909 | 0.005 |
| shuffle_letters:he_tanakh | letters shuffled inside words | 35000 | 0.501 | 0.788 | 0.895 | 3.788 | 4.225 | 4.060 | 3.621 | -0.009 | 0.395 | 0.000 | 0.005 |
| shuffle_letters:he_mishneh_torah | letters shuffled inside words | 35000 | 0.570 | 0.857 | 0.909 | 4.025 | 4.256 | 4.127 | 3.740 | -0.009 | 0.309 | 0.000 | 0.004 |
| shuffle_letters:ar_quran | letters shuffled inside words | 35000 | 0.553 | 0.905 | 0.909 | 4.261 | 4.157 | 4.035 | 3.680 | -0.011 | 0.253 | 0.000 | 0.003 |
| shuffle_letters:ar_muqaddimah | letters shuffled inside words | 35000 | 0.621 | 0.881 | 0.928 | 4.458 | 4.299 | 4.124 | 3.767 | -0.011 | 0.222 | 0.000 | 0.001 |
| shuffle_tokens:he_tanakh | shuffled tokens | 35000 | 0.216 | 0.863 | 0.761 | 3.788 | 4.225 | 3.823 | 2.606 | 0.240 | 0.481 | 0.556 | 0.011 |
| shuffle_tokens:he_mishneh_torah | shuffled tokens | 35000 | 0.252 | 0.866 | 0.779 | 4.025 | 4.256 | 3.866 | 2.695 | 0.261 | 0.370 | 0.481 | 0.007 |
| shuffle_tokens:ar_quran | shuffled tokens | 35000 | 0.233 | 0.894 | 0.778 | 4.261 | 4.157 | 3.627 | 2.612 | 0.409 | 0.303 | 0.576 | 0.011 |
| shuffle_tokens:ar_muqaddimah | shuffled tokens | 35000 | 0.291 | 0.869 | 0.813 | 4.458 | 4.299 | 3.743 | 3.039 | 0.381 | 0.364 | 0.576 | 0.007 |
| markov_o2:la_vulgate | Markov character gibberish | 35000 | 0.478 | 0.876 | 0.888 | 5.323 | 3.949 | 3.213 | 2.501 | 0.689 | 0.273 | 0.424 | 0.013 |
| markov_o1:la_vulgate | Markov character gibberish | 35000 | 0.544 | 1.022 | 0.918 | 5.311 | 3.947 | 3.210 | 3.226 | 0.709 | 0.273 | 0.416 | 0.043 |
| iid_letters:la_vulgate | iid letters (no structure) | 35000 | 0.780 | 0.866 | 0.957 | 5.316 | 3.949 | 3.946 | 3.891 | 0.000 | 0.288 | 0.000 | 0.005 |
| markov_o2:la_pliny_herbal | Markov character gibberish | 35000 | 0.552 | 0.870 | 0.909 | 5.911 | 3.962 | 3.224 | 2.653 | 0.702 | 0.273 | 0.619 | 0.010 |
| markov_o1:la_pliny_herbal | Markov character gibberish | 35000 | 0.587 | 1.008 | 0.928 | 5.899 | 3.962 | 3.224 | 3.228 | 0.713 | 0.273 | 0.571 | 0.033 |
| iid_letters:la_pliny_herbal | iid letters (no structure) | 35000 | 0.842 | 0.847 | 0.969 | 5.899 | 3.962 | 3.960 | 3.913 | -0.000 | 0.333 | 0.000 | 0.003 |
| markov_o2:la_celsus | Markov character gibberish | 35000 | 0.503 | 0.909 | 0.893 | 5.551 | 3.933 | 3.167 | 2.502 | 0.721 | 0.286 | 0.524 | 0.011 |
| markov_o1:la_celsus | Markov character gibberish | 35000 | 0.562 | 1.020 | 0.919 | 5.543 | 3.930 | 3.165 | 3.193 | 0.737 | 0.286 | 0.603 | 0.036 |
| iid_letters:la_celsus | iid letters (no structure) | 35000 | 0.814 | 0.732 | 0.965 | 5.561 | 3.930 | 3.928 | 3.882 | -0.000 | 0.365 | 0.000 | 0.003 |
| markov_o2:it_manzoni | Markov character gibberish | 35000 | 0.390 | 1.079 | 0.863 | 4.592 | 4.006 | 2.998 | 2.427 | 0.918 | 0.238 | 0.762 | 0.028 |
| markov_o1:it_manzoni | Markov character gibberish | 35000 | 0.470 | 1.095 | 0.892 | 4.599 | 4.005 | 2.996 | 3.048 | 0.945 | 0.238 | 0.714 | 0.041 |
| iid_letters:it_manzoni | iid letters (no structure) | 35000 | 0.654 | 0.884 | 0.931 | 4.576 | 4.005 | 4.004 | 3.936 | -0.000 | 0.286 | 0.000 | 0.019 |
| markov_o2:it_sidrach | Markov character gibberish | 35000 | 0.338 | 1.118 | 0.852 | 4.077 | 3.987 | 2.979 | 2.339 | 0.897 | 0.284 | 0.667 | 0.049 |
| markov_o1:it_sidrach | Markov character gibberish | 35000 | 0.420 | 1.118 | 0.880 | 4.090 | 3.986 | 2.979 | 3.022 | 0.926 | 0.280 | 0.652 | 0.059 |
| iid_letters:it_sidrach | iid letters (no structure) | 35000 | 0.596 | 0.969 | 0.927 | 4.097 | 3.988 | 3.985 | 3.895 | -0.000 | 0.315 | 0.000 | 0.039 |
| markov_o2:he_tanakh | Markov character gibberish | 35000 | 0.351 | 0.851 | 0.834 | 3.782 | 4.224 | 3.817 | 2.556 | 0.276 | 0.457 | 0.667 | 0.016 |
| markov_o1:he_tanakh | Markov character gibberish | 35000 | 0.450 | 1.019 | 0.893 | 3.788 | 4.225 | 3.821 | 3.738 | 0.362 | 0.481 | 0.741 | 0.057 |
| iid_letters:he_tanakh | iid letters (no structure) | 35000 | 0.703 | 0.662 | 0.942 | 3.791 | 4.224 | 4.220 | 4.034 | -0.001 | 0.259 | 0.000 | 0.005 |
| markov_o2:he_mishneh_torah | Markov character gibberish | 35000 | 0.417 | 0.872 | 0.857 | 4.031 | 4.255 | 3.859 | 2.651 | 0.300 | 0.296 | 0.605 | 0.013 |
| markov_o1:he_mishneh_torah | Markov character gibberish | 35000 | 0.485 | 0.995 | 0.897 | 4.014 | 4.255 | 3.862 | 3.767 | 0.360 | 0.370 | 0.679 | 0.049 |
| iid_letters:he_mishneh_torah | iid letters (no structure) | 35000 | 0.751 | 0.617 | 0.954 | 4.021 | 4.255 | 4.251 | 4.083 | -0.001 | 0.272 | 0.000 | 0.004 |
| markov_o2:ar_quran | Markov character gibberish | 35000 | 0.409 | 0.908 | 0.866 | 4.257 | 4.156 | 3.619 | 2.568 | 0.450 | 0.313 | 0.667 | 0.018 |
| markov_o1:ar_quran | Markov character gibberish | 35000 | 0.493 | 1.051 | 0.907 | 4.273 | 4.161 | 3.622 | 3.529 | 0.524 | 0.303 | 0.606 | 0.056 |
| iid_letters:ar_quran | iid letters (no structure) | 35000 | 0.737 | 0.705 | 0.950 | 4.259 | 4.157 | 4.148 | 3.936 | 0.001 | 0.232 | 0.000 | 0.005 |
| markov_o2:ar_muqaddimah | Markov character gibberish | 35000 | 0.463 | 0.896 | 0.886 | 4.452 | 4.300 | 3.735 | 2.986 | 0.426 | 0.343 | 0.566 | 0.013 |
| markov_o1:ar_muqaddimah | Markov character gibberish | 35000 | 0.524 | 1.037 | 0.906 | 4.462 | 4.296 | 3.739 | 3.685 | 0.503 | 0.333 | 0.606 | 0.041 |
| iid_letters:ar_muqaddimah | iid letters (no structure) | 35000 | 0.777 | 0.672 | 0.958 | 4.462 | 4.300 | 4.295 | 4.074 | -0.001 | 0.242 | 0.000 | 0.005 |
| selfcitation_p0.15 | self-citation generator | 35000 | 0.117 | 0.703 | 0.640 | 5.786 | 3.676 | 3.383 | 2.434 | 0.223 | 0.302 | 0.302 | 0.169 |
| selfcitation_p0.3 | self-citation generator | 35000 | 0.214 | 0.553 | 0.751 | 4.939 | 3.603 | 3.477 | 2.841 | 0.091 | 0.254 | 0.048 | 0.127 |
| selfcitation_p0.5 | self-citation generator | 35000 | 0.341 | 0.556 | 0.834 | 5.038 | 3.649 | 3.585 | 3.148 | 0.046 | 0.254 | 0.000 | 0.095 |
| slot_grammar_p0.2 | slot-grammar generator | 35000 | 0.140 | 0.950 | 0.676 | 3.780 | 3.687 | 2.245 | 2.325 | 1.256 | 0.400 | 0.867 | 0.038 |
| slot_grammar_p0.35 | slot-grammar generator | 35000 | 0.192 | 0.878 | 0.732 | 4.096 | 3.669 | 2.305 | 2.395 | 1.219 | 0.400 | 0.867 | 0.026 |
| slot_grammar_p0.5 | slot-grammar generator | 35000 | 0.232 | 0.783 | 0.767 | 4.425 | 3.655 | 2.343 | 2.429 | 1.196 | 0.400 | 0.867 | 0.016 |
| markov_o2:ms408 | Markov o2 TRAINED ON MS 408 (matches by construction) | 35000 | 0.219 | 1.019 | 0.761 | 4.461 | 3.902 | 2.215 | 1.938 | 1.361 | 0.247 | 0.922 | 0.025 |

## 2. MS 408 confidence intervals (collapsed units)

Delete-one-page jackknife (one replicate per folio) and delete-one-block jackknife (blocks of 8 consecutive folios, a stand-in for quires), plus 100 bootstrap resamples by page and by block. The **jackknife SE is the one used** (larger of the two): resampling with replacement duplicates text and lowers the number of distinct types, which biases vocabulary-richness metrics (type/token ratio, hapax share, Heaps beta, word entropy) and makes their percentile CIs off-centre (see `ms408_ci.csv`, columns `boot_*`); the jackknife drops data instead.

| metric | estimate [95% CI = estimate ± 1.96 SE] | SE jackknife page | SE jackknife 8-page block | SE bootstrap 8-page block |
|---|---|---|---|---|
| type/token ratio | 0.205 [0.178, 0.232] | 0.0062 | 0.0139 | 0.0178 |
| hapax share of types | 0.687 [0.674, 0.700] | 0.0065 | 0.0067 | 0.1006 |
| top-10 token coverage | 0.127 [0.116, 0.138] | 0.0029 | 0.0055 | 0.0069 |
| word entropy H1 (bits) | 10.243 [10.024, 10.462] | 0.0575 | 0.1117 | 0.1098 |
| Zipf exponent s (MLE r10-1000) | 0.985 [0.936, 1.034] | 0.0128 | 0.0250 | 0.0220 |
| Heaps beta (text order) | 0.745 [0.706, 0.784] | 0.0199 | 0.0167 | 0.0272 |
| Heaps beta (shuffled tokens) | 0.747 [0.686, 0.808] | 0.0311 | 0.0101 | 0.0131 |
| mean word length (units) | 4.466 [4.330, 4.601] | 0.0300 | 0.0693 | 0.0649 |
| word length SD (units) | 1.648 [1.617, 1.679] | 0.0102 | 0.0157 | 0.0159 |
| unit entropy H1 (bits) | 3.901 [3.873, 3.930] | 0.0073 | 0.0145 | 0.0142 |
| conditional entropy h2 (bits) | 2.217 [2.125, 2.309] | 0.0199 | 0.0471 | 0.0440 |
| conditional entropy h3 (bits) | 1.954 [1.874, 2.033] | 0.0182 | 0.0404 | 0.0372 |
| h2 rise after within-word shuffle (bits) | 1.348 [1.280, 1.416] | 0.0243 | 0.0347 | 0.0315 |
| H1 / log2(alphabet size) | 0.821 [0.783, 0.858] | 0.0094 | 0.0191 | 0.0074 |
| h2 / H1 | 0.568 [0.548, 0.588] | 0.0044 | 0.0103 | 0.0096 |
| h3 / H1 | 0.501 [0.483, 0.518] | 0.0041 | 0.0088 | 0.0082 |
| H1 - h2 (bits) | 1.684 [1.616, 1.753] | 0.0157 | 0.0352 | 0.0326 |
| h2 rise after shuffle / H1 | 0.345 [0.326, 0.365] | 0.0064 | 0.0100 | 0.0091 |
| Sukhotin vowel-like share of alphabet | 0.222 [0.192, 0.252] | 0.0085 | 0.0154 | 0.0210 |
| word-initial vs final unit JSD (bits) | 0.659 [0.638, 0.680] | 0.0073 | 0.0107 | 0.0095 |
| share of positionally skewed units | 0.923 [0.923, 0.923] | 0.0000 | 0.0000 | 0.0041 |
| adjacent identical-token rate | 0.008 [0.007, 0.010] | 0.0005 | 0.0007 | 0.0006 |
| adjacent edit-distance-1 rate | 0.034 [0.030, 0.037] | 0.0011 | 0.0017 | 0.0014 |

Controls: delete-one-group jackknife (20 contiguous groups) per window-0 row, SE per metric in `comparison_ci.csv`. Median SE across controls for the key metrics: conditional entropy h2 (bits) 0.0051, conditional entropy h3 (bits) 0.0105, type/token ratio 0.0052, Zipf exponent s (MLE r10-1000) 0.0082.

## 3. Which hypothesis families is MS 408 consistent with? (prediction-interval verdicts)

For each family and metric the members (one per base text × window, seeds averaged) give a mean and an SD. MS 408 is `≈` when it lies in the 95% prediction interval, `↑`/`↓` when above/below, `?` when the family has fewer than 3 members. The interval includes MS 408's own sampling uncertainty (jackknife SE, larger of the page and 8-page-block versions). Excluded as hypotheses: the Markov model trained on MS 408 (circular), the folded-alphabet sensitivity rows and undersized texts. This **replaces** the earlier min/max-plus-arbitrary-tolerance bands.

| metric | anagram (alphagram) | slot-grammar generator | shuffled tokens | word reversal | self-citation generator | natural-language plain… | monoalphabetic substit… | Markov character gibbe… | natural abjad text (He… | abjad (vowels removed) | natural plaintext: Lat… | letters shuffled insid… | iid letters (no struct… | natural plaintext: her… | nomenclator-like sylla… | polyalphabetic (Vigene… | verbose cipher (letter… | Naibbe-inspired homoph… |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| type/token ratio | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ↓ | ≈ | ≈ | ≈ | ↓ | ↓ | ≈ | ≈ | ↓ | ↓ | ↓ |
| hapax share of types | ↑ | ≈ | ↑ | ↑ | ≈ | ≈ | ↑ | ↓ | ≈ | ↑ | ≈ | ↓ | ↓ | ≈ | ↑ | ≈ | ↓ | ↓ |
| top-10 token coverage | ≈ | ≈ | ≈ | ≈ | ↑ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ |
| word entropy H1 (bits) | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ↓ | ≈ | ≈ | ≈ | ↓ | ↓ | ≈ | ≈ | ↓ | ↓ | ↓ |
| Zipf exponent s (MLE r10-1000) | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ↑ | ≈ | ≈ |
| Heaps beta (text order) | ≈ | ≈ | ≈ | ≈ | ↓ | ≈ | ≈ | ↓ | ≈ | ≈ | ≈ | ↓ | ↓ | ≈ | ≈ | ↓ | ↓ | ↓ |
| Heaps beta (shuffled tokens) | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ↓ | ≈ | ≈ | ≈ | ↓ | ↓ | ≈ | ≈ | ≈ | ↓ | ↓ |
| mean word length (units) | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ↑ | ↓ | ≈ | ≈ | ↓ | ≈ | ≈ | ↓ | ↓ |
| word length SD (units) | ≈ | ≈ | ≈ | ≈ | ≈ | ↓ | ↓ | ≈ | ≈ | ≈ | ↓ | ≈ | ≈ | ↓ | ↓ | ≈ | ≈ | ↓ |
| unit entropy H1 (bits) | ≈ | ↑ | ≈ | ≈ | ↑ | ≈ | ≈ | ≈ | ↓ | ↑ | ≈ | ≈ | ≈ | ≈ | ↓ | ↓ | ↑ | ↑ |
| conditional entropy h2 (bits) | ≈ | ≈ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ |
| conditional entropy h3 (bits) | ≈ | ↓ | ↓ | ↓ | ≈ | ↓ | ↓ | ≈ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ |
| h2 rise after within-word shuffle (bits) | ≈ | ≈ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ |
| H1 / log2(alphabet size) | ≈ | ↓ | ≈ | ≈ | ≈ | ↓ | ↓ | ≈ | ≈ | ≈ | ↓ | ≈ | ≈ | ↓ | ↓ | ↓ | ↓ | ↓ |
| h2 / H1 | ↓ | ≈ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ |
| h3 / H1 | ↓ | ↓ | ↓ | ↓ | ≈ | ↓ | ↓ | ≈ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ |
| H1 - h2 (bits) | ↑ | ≈ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ |
| h2 rise after shuffle / H1 | ≈ | ≈ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ |
| Sukhotin vowel-like share of alphabet | ≈ | ↓ | ≈ | ≈ | ≈ | ↓ | ≈ | ≈ | ≈ | ≈ | ↓ | ≈ | ≈ | ↓ | ↓ | ↓ | ↓ | ↓ |
| word-initial vs final unit JSD (bits) | ↓ | ↓ | ↑ | ↑ | ↑ | ≈ | ≈ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ |
| share of positionally skewed units | ≈ | ↑ | ≈ | ≈ | ↑ | ≈ | ≈ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ |
| adjacent identical-token rate | ↑ | ↑ | ≈ | ↑ | ≈ | ↑ | ↑ | ≈ | ↑ | ≈ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ |
| adjacent edit-distance-1 rate | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ↑ | ≈ | ↑ | ≈ | ≈ | ↑ | ≈ | ≈ | ↑ | ↑ |

Column order = number of metrics inside the interval (highest first):

1. anagram (alphagram)
2. slot-grammar generator
3. shuffled tokens
4. word reversal
5. self-citation generator
6. natural-language plaintext (Latin/Italian/German)
7. monoalphabetic substitution
8. Markov character gibberish
9. natural abjad text (Hebrew/Arabic)
10. abjad (vowels removed)
11. natural plaintext: Latin only
12. letters shuffled inside words
13. iid letters (no structure)
14. natural plaintext: herbal/medical Latin
15. nomenclator-like syllable code
16. polyalphabetic (Vigenere)
17. verbose cipher (letter -> 2 symbols)
18. Naibbe-inspired homophonic tiles

### Summary per family

| family | n_members | inside (collapsed units) | outside (collapsed) | ? (collapsed) | inside (raw EVA) | outside (raw) | n_metrics |
|---|---|---|---|---|---|---|---|
| anagram (alphagram) | 9 | 17 | 6 | 0 | 15 | 8 | 23 |
| slot-grammar generator | 3 | 15 | 8 | 0 | 13 | 10 | 23 |
| shuffled tokens | 9 | 14 | 9 | 0 | 13 | 10 | 23 |
| word reversal | 9 | 13 | 10 | 0 | 12 | 11 | 23 |
| self-citation generator | 3 | 13 | 10 | 0 | 13 | 10 | 23 |
| natural-language plaintext (Latin/Italian/German) | 25 | 12 | 11 | 0 | 13 | 10 | 23 |
| monoalphabetic substitution | 10 | 12 | 11 | 0 | 12 | 11 | 23 |
| Markov character gibberish | 18 | 11 | 12 | 0 | 9 | 14 | 23 |
| natural abjad text (Hebrew/Arabic) | 6 | 11 | 12 | 0 | 10 | 13 | 23 |
| abjad (vowels removed) | 5 | 11 | 12 | 0 | 11 | 12 | 23 |
| natural plaintext: Latin only | 13 | 8 | 15 | 0 | 9 | 14 | 23 |
| letters shuffled inside words | 9 | 8 | 15 | 0 | 8 | 15 | 23 |
| iid letters (no structure) | 9 | 8 | 15 | 0 | 8 | 15 | 23 |
| natural plaintext: herbal/medical Latin | 5 | 8 | 15 | 0 | 10 | 13 | 23 |
| nomenclator-like syllable code | 5 | 8 | 15 | 0 | 9 | 14 | 23 |
| polyalphabetic (Vigenere) | 18 | 6 | 17 | 0 | 7 | 16 | 23 |
| verbose cipher (letter -> 2 symbols) | 9 | 3 | 20 | 0 | 4 | 19 | 23 |
| Naibbe-inspired homophonic tiles | 9 | 2 | 21 | 0 | 3 | 20 | 23 |

### Metrics where MS 408 falls OUTSIDE each family's prediction interval (collapsed units)

- **anagram (alphagram)** (n=9; 17/23 inside): hapax_share_of_types↑; unit_h2_over_H1↓; unit_h3_over_H1↓; unit_mi_adjacent↑; pos_jsd_initial_final↓; adjacent_identical_rate↑
- **slot-grammar generator** (n=3; 15/23 inside): unit_H1↑; unit_h3↓; unit_H1_norm↓; unit_h3_over_H1↓; sukhotin_vowel_like_share↓; pos_jsd_initial_final↓; pos_skewed_unit_share↑; adjacent_identical_rate↑
- **shuffled tokens** (n=9; 14/23 inside): hapax_share_of_types↑; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; unit_h2_over_H1↓; unit_h3_over_H1↓; unit_mi_adjacent↑; shuffle_gap_over_H1↑; pos_jsd_initial_final↑
- **word reversal** (n=9; 13/23 inside): hapax_share_of_types↑; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; unit_h2_over_H1↓; unit_h3_over_H1↓; unit_mi_adjacent↑; shuffle_gap_over_H1↑; pos_jsd_initial_final↑; adjacent_identical_rate↑
- **self-citation generator** (n=3; 13/23 inside): top10_token_coverage↑; heaps_beta_in_order↓; unit_H1↑; unit_h2↓; shuffle_gap_h2↑; unit_h2_over_H1↓; unit_mi_adjacent↑; shuffle_gap_over_H1↑; pos_jsd_initial_final↑; pos_skewed_unit_share↑
- **natural-language plaintext (Latin/Italian/German)** (n=25; 12/23 inside): word_length_sd_units↓; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; unit_H1_norm↓; unit_h2_over_H1↓; unit_h3_over_H1↓; unit_mi_adjacent↑; shuffle_gap_over_H1↑; sukhotin_vowel_like_share↓; adjacent_identical_rate↑
- **monoalphabetic substitution** (n=10; 12/23 inside): hapax_share_of_types↑; word_length_sd_units↓; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; unit_H1_norm↓; unit_h2_over_H1↓; unit_h3_over_H1↓; unit_mi_adjacent↑; shuffle_gap_over_H1↑; adjacent_identical_rate↑
- **Markov character gibberish** (n=18; 11/23 inside): type_token_ratio↓; hapax_share_of_types↓; word_entropy_H1↓; heaps_beta_in_order↓; heaps_beta_shuffled↓; unit_h2↓; shuffle_gap_h2↑; unit_h2_over_H1↓; unit_mi_adjacent↑; shuffle_gap_over_H1↑; pos_jsd_initial_final↑; pos_skewed_unit_share↑
- **natural abjad text (Hebrew/Arabic)** (n=6; 11/23 inside): unit_H1↓; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; unit_h2_over_H1↓; unit_h3_over_H1↓; unit_mi_adjacent↑; shuffle_gap_over_H1↑; pos_jsd_initial_final↑; pos_skewed_unit_share↑; adjacent_identical_rate↑; adjacent_edit1_rate↑
- **abjad (vowels removed)** (n=5; 11/23 inside): hapax_share_of_types↑; mean_word_length_units↑; unit_H1↑; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; unit_h2_over_H1↓; unit_h3_over_H1↓; unit_mi_adjacent↑; shuffle_gap_over_H1↑; pos_jsd_initial_final↑; pos_skewed_unit_share↑
- **natural plaintext: Latin only** (n=13; 8/23 inside): mean_word_length_units↓; word_length_sd_units↓; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; unit_H1_norm↓; unit_h2_over_H1↓; unit_h3_over_H1↓; unit_mi_adjacent↑; shuffle_gap_over_H1↑; sukhotin_vowel_like_share↓; pos_jsd_initial_final↑; pos_skewed_unit_share↑; adjacent_identical_rate↑; adjacent_edit1_rate↑
- **letters shuffled inside words** (n=9; 8/23 inside): type_token_ratio↓; hapax_share_of_types↓; word_entropy_H1↓; heaps_beta_in_order↓; heaps_beta_shuffled↓; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; unit_h2_over_H1↓; unit_h3_over_H1↓; unit_mi_adjacent↑; shuffle_gap_over_H1↑; pos_jsd_initial_final↑; pos_skewed_unit_share↑; adjacent_identical_rate↑
- **iid letters (no structure)** (n=9; 8/23 inside): type_token_ratio↓; hapax_share_of_types↓; word_entropy_H1↓; heaps_beta_in_order↓; heaps_beta_shuffled↓; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; unit_h2_over_H1↓; unit_h3_over_H1↓; unit_mi_adjacent↑; shuffle_gap_over_H1↑; pos_jsd_initial_final↑; pos_skewed_unit_share↑; adjacent_identical_rate↑
- **natural plaintext: herbal/medical Latin** (n=5; 8/23 inside): mean_word_length_units↓; word_length_sd_units↓; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; unit_H1_norm↓; unit_h2_over_H1↓; unit_h3_over_H1↓; unit_mi_adjacent↑; shuffle_gap_over_H1↑; sukhotin_vowel_like_share↓; pos_jsd_initial_final↑; pos_skewed_unit_share↑; adjacent_identical_rate↑; adjacent_edit1_rate↑
- **nomenclator-like syllable code** (n=5; 8/23 inside): hapax_share_of_types↑; word_length_sd_units↓; unit_H1↓; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; unit_H1_norm↓; unit_h2_over_H1↓; unit_h3_over_H1↓; unit_mi_adjacent↑; shuffle_gap_over_H1↑; sukhotin_vowel_like_share↓; pos_jsd_initial_final↑; pos_skewed_unit_share↑; adjacent_identical_rate↑
- **polyalphabetic (Vigenere)** (n=18; 6/23 inside): type_token_ratio↓; word_entropy_H1↓; zipf_mle_s_r10_1000↑; heaps_beta_in_order↓; unit_H1↓; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; unit_H1_norm↓; unit_h2_over_H1↓; unit_h3_over_H1↓; unit_mi_adjacent↑; shuffle_gap_over_H1↑; sukhotin_vowel_like_share↓; pos_jsd_initial_final↑; pos_skewed_unit_share↑; adjacent_identical_rate↑
- **verbose cipher (letter -> 2 symbols)** (n=9; 3/23 inside): type_token_ratio↓; hapax_share_of_types↓; word_entropy_H1↓; heaps_beta_in_order↓; heaps_beta_shuffled↓; mean_word_length_units↓; unit_H1↑; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; unit_H1_norm↓; unit_h2_over_H1↓; unit_h3_over_H1↓; unit_mi_adjacent↑; shuffle_gap_over_H1↑; sukhotin_vowel_like_share↓; pos_jsd_initial_final↑; pos_skewed_unit_share↑; adjacent_identical_rate↑; adjacent_edit1_rate↑
- **Naibbe-inspired homophonic tiles** (n=9; 2/23 inside): type_token_ratio↓; hapax_share_of_types↓; word_entropy_H1↓; heaps_beta_in_order↓; heaps_beta_shuffled↓; mean_word_length_units↓; word_length_sd_units↓; unit_H1↑; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; unit_H1_norm↓; unit_h2_over_H1↓; unit_h3_over_H1↓; unit_mi_adjacent↑; shuffle_gap_over_H1↑; sukhotin_vowel_like_share↓; pos_jsd_initial_final↑; pos_skewed_unit_share↑; adjacent_identical_rate↑; adjacent_edit1_rate↑

### Reading the matrix (auto-generated from the numbers above; hedged)

MS 408 (collapsed units): h2 = 2.22 bits, h3 = 1.95, h2 rise after within-word shuffle = 1.35 bits, Zipf s = 0.98, TTR = 0.21, 92% of units positionally skewed, adjacent edit-distance-1 rate 0.034.

- **conditional entropy h2 (bits)**: MS 408 is inside the prediction interval of anagram (alphagram), slot-grammar generator.
- **conditional entropy h3 (bits)**: MS 408 is inside the prediction interval of anagram (alphagram), Markov character gibberish, self-citation generator.
- **h2 rise after within-word shuffle (bits)**: MS 408 is inside the prediction interval of anagram (alphagram), slot-grammar generator.
- **h2 / H1**: MS 408 is inside the prediction interval of slot-grammar generator.
- **Zipf exponent s (MLE r10-1000)**: MS 408 is inside the prediction interval of natural-language plaintext (Latin/Italian/German), natural plaintext: Latin only, natural plaintext: herbal/medical Latin, abjad (vowels removed), monoalphabetic substitution, nomenclator-like syllable code, verbose cipher (letter -> 2 symbols), Naibbe-inspired homophonic tiles, word reversal, anagram (alphagram), letters shuffled inside words, shuffled tokens, natural abjad text (Hebrew/Arabic), Markov character gibberish, iid letters (no structure), self-citation generator, slot-grammar generator.
- **type/token ratio**: MS 408 is inside the prediction interval of natural-language plaintext (Latin/Italian/German), natural plaintext: Latin only, natural plaintext: herbal/medical Latin, abjad (vowels removed), monoalphabetic substitution, nomenclator-like syllable code, word reversal, anagram (alphagram), shuffled tokens, natural abjad text (Hebrew/Arabic), self-citation generator, slot-grammar generator.
- **share of positionally skewed units**: MS 408 is inside the prediction interval of natural-language plaintext (Latin/Italian/German), monoalphabetic substitution, word reversal, anagram (alphagram), shuffled tokens.
- **adjacent edit-distance-1 rate**: MS 408 is inside the prediction interval of natural-language plaintext (Latin/Italian/German), abjad (vowels removed), monoalphabetic substitution, polyalphabetic (Vigenere), nomenclator-like syllable code, word reversal, anagram (alphagram), letters shuffled inside words, shuffled tokens, Markov character gibberish, iid letters (no structure), self-citation generator, slot-grammar generator.

- Metrics where MS 408 is inside **every** family interval (non-discriminating here): none.
- Metrics where MS 408 is outside **every** family interval (no control family reproduces it with these settings): none.

What this does and does not say: the table shows which simplified control families have statistics consistent with MS 408's on each metric. Families with `?` have too few members to judge. No family matches on all metrics, and the families that match on the most metrics (e.g. the slot-grammar generator) were designed with Voynichese structure in mind, so their match is not independent evidence. Matching on many metrics is not proof of a mechanism, and mismatching is not refutation: the controls are crude, intervals optimistic and several families (verbose/homophonic ciphers, self-citation generators) have parameters that could be tuned toward MS 408.

### z-scores of MS 408 against the natural-text families (collapsed units)

z = (MS − family mean) / sqrt(SD²(1+1/n) + SE²); |z| beyond roughly 2-3 (t-limit by n) = outside.

| metric | MS 408 | natural-language plaintext n=25 | natural plaintext: Latin only n=13 | natural plaintext: herbal/medical  n=5 | natural abjad text n=6 |
|---|---|---|---|---|---|
| type/token ratio | 0.21 | -0.24 | -1.03 | -0.76 | -1.17 |
| hapax share of types | 0.69 | 1.78 | 1.20 | 1.89 | 2.19 |
| top-10 token coverage | 0.13 | -1.48 | -1.59 | -2.22 | -0.36 |
| word entropy H1 (bits) | 10.24 | -0.02 | -1.27 | -1.49 | -2.22 |
| Zipf exponent s (MLE r10-1000) | 0.98 | 0.40 | 1.42 | 2.11 | 2.46 |
| Heaps beta (text order) | 0.74 | -0.74 | -1.34 | -0.82 | -2.44 |
| Heaps beta (shuffled tokens) | 0.75 | -0.46 | -1.04 | -0.75 | -0.90 |
| mean word length (units) | 4.47 | -0.63 | -4.35 | -4.62 | 1.28 |
| word length SD (units) | 1.65 | -4.30 | -10.24 | -20.51 | 0.73 |
| unit entropy H1 (bits) | 3.90 | -1.77 | -1.92 | -2.11 | -5.00 |
| conditional entropy h2 (bits) | 2.22 | -6.79 | -16.86 | -16.32 | -13.29 |
| conditional entropy h3 (bits) | 1.95 | -4.28 | -7.03 | -5.95 | -4.06 |
| h2 rise after within-word shuffle (bits) | 1.35 | 4.68 | 17.14 | 17.82 | 12.02 |
| H1 / log2(alphabet size) | 0.82 | -3.11 | -3.44 | -3.66 | -1.06 |
| h2 / H1 | 0.57 | -5.57 | -20.86 | -20.69 | -15.59 |
| h3 / H1 | 0.50 | -3.59 | -7.41 | -6.43 | -3.49 |
| H1 - h2 (bits) | 1.68 | 5.14 | 23.42 | 23.50 | 14.81 |
| h2 rise after shuffle / H1 | 0.35 | 5.11 | 15.61 | 15.90 | 12.56 |
| Sukhotin vowel-like share of alphabet | 0.22 | -2.30 | -3.15 | -3.22 | -2.05 |
| word-initial vs final unit JSD (bits) | 0.66 | 1.89 | 14.15 | 24.47 | 10.50 |
| share of positionally skewed units | 0.92 | 1.84 | 3.81 | 3.19 | 8.42 |
| adjacent identical-token rate | 0.01 | 6.53 | 10.53 | 12.29 | 9.20 |
| adjacent edit-distance-1 rate | 0.03 | 1.73 | 9.18 | 8.55 | 11.04 |

## 4. Herbal / medical / encyclopaedic Latin controls

Added because MS 408's herbal section is a large part of the text. Pliny XX-XXVII (plant remedies, Perseus/Mayhoff), Celsus *De medicina*, Macer Floridus *De viribus herbarum* (verse, only ~14k tokens: undersized), Pliny VII-XI (non-botanical) and Isidore *Etymologiae* for comparison. Vocabulary-level numbers (TTR, Zipf, Heaps) depend on topic: a plant catalogue has many rare names.

| name | family | tokens | TTR | Zipf s | Heaps β | len | H1 | h2 | h3 | Δh2 shuf | vowel-like | pos-skew | adj-edit1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MS408 P (collapsed units) | MS 408 | 34977 | 0.205 | 0.985 | 0.747 | 4.466 | 3.901 | 2.217 | 1.954 | 1.348 | 0.222 | 0.923 | 0.034 |
| plain:la_pliny_herbal | natural-language plaintext (Latin/Italian/German) | 35000 | 0.273 | 0.807 | 0.800 | 5.906 | 3.963 | 3.227 | 2.665 | 0.687 | 0.273 | 0.619 | 0.003 |
| plain:la_pliny_herbal@w1 | natural-language plaintext (Latin/Italian/German) | 35000 | 0.275 | 0.807 | 0.803 | 5.971 | 3.974 | 3.247 | 2.670 | 0.680 | 0.273 | 0.714 | 0.003 |
| plain:la_pliny_general | natural-language plaintext (Latin/Italian/German) | 35000 | 0.378 | 0.772 | 0.854 | 5.971 | 3.956 | 3.246 | 2.753 | 0.664 | 0.286 | 0.619 | 0.002 |
| plain:la_celsus | natural-language plaintext (Latin/Italian/German) | 35000 | 0.219 | 0.909 | 0.767 | 5.563 | 3.931 | 3.167 | 2.512 | 0.703 | 0.286 | 0.476 | 0.004 |
| plain:la_celsus@w1 | natural-language plaintext (Latin/Italian/German) | 35000 | 0.203 | 0.877 | 0.756 | 5.529 | 3.962 | 3.213 | 2.539 | 0.682 | 0.273 | 0.476 | 0.009 |
| plain:la_celsus@w2 | natural-language plaintext (Latin/Italian/German) | 34414 | 0.210 | 0.897 | 0.759 | 5.468 | 3.938 | 3.172 | 2.483 | 0.703 | 0.286 | 0.524 | 0.005 |
| plain:la_isidore | natural-language plaintext (Latin/Italian/German) | 35000 | 0.270 | 0.915 | 0.806 | 5.671 | 3.953 | 3.198 | 2.601 | 0.692 | 0.273 | 0.524 | 0.004 |
| plain:la_isidore@w1 | natural-language plaintext (Latin/Italian/German) | 35000 | 0.279 | 0.906 | 0.809 | 5.717 | 3.961 | 3.234 | 2.620 | 0.660 | 0.261 | 0.545 | 0.004 |
| plain:la_isidore@w2 | natural-language plaintext (Latin/Italian/German) | 35000 | 0.315 | 0.977 | 0.832 | 5.553 | 3.953 | 3.199 | 2.661 | 0.688 | 0.286 | 0.667 | 0.003 |
| plain:la_macer | natural plaintext, UNDERSIZED (<80% of target; sensitivity only) | 13967 | 0.279 | 0.765 | 0.766 | 5.847 | 3.967 | 3.184 | 2.470 | 0.726 | 0.286 | 0.571 | 0.002 |

## 5. Alphabet-size normalisation

Raw entropies grow with alphabet size. Two corrections: (i) normalised metrics in the main table (`H1/log2 A`, `h2/H1`, `h3/H1`, `H1−h2`, shuffle-gap/H1), and (ii) an OLS of each metric on log2(alphabet size) over the natural-language rows (Latin/Italian/German + Hebrew/Arabic, full-size windows) and MS 408's value vs the prediction interval at MS 408's own alphabet size.

MS 408 has 27 unit types with ≥20 tokens (collapsed EVA); natural texts range 21-33. 'extrapolated' = MS 408 outside that range.

| metric | MS 408 | predicted at MS alphabet | slope per log2 A | r | z | verdict | extrapolated | n |
|---|---|---|---|---|---|---|---|---|
| unit entropy H1 (bits) | 3.901 | 4.129 | 0.463 | 0.839 | -3.427 | ↓ | False | 31 |
| conditional entropy h2 (bits) | 2.217 | 3.458 | 1.060 | 0.744 | -5.905 | ↓ | False | 31 |
| conditional entropy h3 (bits) | 1.954 | 2.612 | 0.299 | 0.407 | -4.379 | ↓ | False | 31 |
| h2 rise after within-word shuffle (bits) | 1.348 | 0.545 | -0.690 | -0.671 | 4.779 | ↑ | False | 31 |
| H1 - h2 (bits) | 1.684 | 0.670 | -0.597 | -0.572 | 5.402 | ↑ | False | 31 |
| h2 / H1 | 0.568 | 0.836 | 0.164 | 0.613 | -5.734 | ↓ | False | 31 |
| h3 / H1 | 0.501 | 0.632 | -0.000 | -0.002 | -3.549 | ↓ | False | 31 |
| mean word length (units) | 4.466 | 4.468 | -1.444 | -0.396 | -0.003 | ≈ | False | 31 |

Normalised metrics, MS 408 vs the natural-text rows (all windows):

| metric | MS 408 | natural min | natural median | natural max |
|---|---|---|---|---|
| H1 / log2(alphabet size) | 0.821 | 0.824 | 0.891 | 0.913 |
| h2 / H1 | 0.568 | 0.719 | 0.808 | 0.909 |
| h3 / H1 | 0.501 | 0.541 | 0.631 | 0.707 |
| H1 - h2 (bits) | 1.684 | 0.389 | 0.755 | 1.151 |
| h2 rise after shuffle / H1 | 0.345 | 0.056 | 0.175 | 0.244 |

## 6. MS 408 vs each single control (bootstrap z)

Per control row (window 0): number of the 23 metrics where |z| < 2 using only the two bootstrap SEs, and the median |z|. Ten closest controls (full table: `control_z_summary.csv`, per metric `control_z.csv`). Note that very small SEs make |z| large even for modest differences.

| name | family | n_metrics | within_2se | median_abs_z |
|---|---|---|---|---|
| markov_o2:ms408 | Markov o2 TRAINED ON MS 408 (matches by construction) | 23 | 17 | 0.45 |
| alphagram:ar_quran | anagram (alphagram) | 23 | 8 | 7.65 |
| alphagram:la_celsus | anagram (alphagram) | 23 | 6 | 5.68 |
| shuffle_tokens:it_manzoni | shuffled tokens | 23 | 6 | 7.12 |
| plain:it_manzoni | natural-language plaintext (Latin/Italian/German) | 23 | 6 | 8.26 |
| caesar3:it_manzoni | monoalphabetic substitution | 23 | 6 | 8.26 |
| monoalphabetic:it_manzoni | monoalphabetic substitution | 23 | 6 | 8.26 |
| reverse_words:it_manzoni | word reversal | 23 | 6 | 8.26 |
| alphagram:ar_muqaddimah | anagram (alphagram) | 23 | 5 | 5.24 |
| plain:de_walther_mhg | natural plaintext, UNDERSIZED (<80% of target; sensitivity only) | 23 | 5 | 5.29 |

## 7. Natural abjad texts (Hebrew, Arabic)

Consonantal Hebrew (Tanakh Genesis+Exodus; Maimonides, *Mishneh Torah*) and Arabic (Quran; Ibn Khaldun, *Muqaddimah*), one native letter = one unit, vowel points/diacritics removed. `plain:` rows use the main normalisation (Hebrew final forms ך ם ן ף ץ kept as separate letters; Arabic alif-hamza variants folded into alif); `plain_folded:` rows fold Hebrew final forms into the medial letters and reduce the Arabic alphabet further (ى→ي, ة→ه, ؤ→و, ئ→ي, hamza deleted), as a sensitivity check. A 1-to-1 Latin transliteration would give the same numbers (tested), so no separate transliterated run is shown.

| name | tokens | TTR | Zipf s | Heaps β | len | alphabet | H1 | h2 | h3 | Δh2 shuf | vowel-like | pos-skew | JSD ini/fin |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MS408 P (collapsed units) | 34977 | 0.205 | 0.985 | 0.747 | 4.466 | 27 | 3.901 | 2.217 | 1.954 | 1.348 | 0.222 | 0.923 | 0.659 |
| plain:he_tanakh | 35000 | 0.216 | 0.863 | 0.760 | 3.788 | 27 | 4.225 | 3.823 | 2.606 | 0.238 | 0.481 | 0.556 | 0.302 |
| plain_folded:he_tanakh | 35000 | 0.216 | 0.863 | 0.760 | 3.788 | 22 | 4.051 | 3.668 | 2.507 | 0.246 | 0.500 | 0.227 | 0.128 |
| plain:he_mishneh_torah | 35000 | 0.252 | 0.866 | 0.781 | 4.025 | 27 | 4.256 | 3.866 | 2.695 | 0.262 | 0.370 | 0.481 | 0.310 |
| plain:he_mishneh_torah@w1 | 34655 | 0.220 | 0.941 | 0.764 | 3.969 | 27 | 4.305 | 3.858 | 2.611 | 0.304 | 0.333 | 0.593 | 0.343 |
| plain_folded:he_mishneh_torah | 35000 | 0.252 | 0.866 | 0.781 | 4.025 | 22 | 4.075 | 3.715 | 2.594 | 0.257 | 0.364 | 0.136 | 0.112 |
| plain:ar_quran | 35000 | 0.233 | 0.894 | 0.779 | 4.261 | 33 | 4.157 | 3.627 | 2.612 | 0.411 | 0.303 | 0.576 | 0.275 |
| plain:ar_quran@w1 | 35000 | 0.248 | 0.876 | 0.785 | 4.233 | 33 | 4.183 | 3.682 | 2.673 | 0.383 | 0.333 | 0.576 | 0.255 |
| plain_folded:ar_quran | 35000 | 0.231 | 0.895 | 0.778 | 4.241 | 28 | 4.033 | 3.524 | 2.583 | 0.407 | 0.286 | 0.500 | 0.238 |
| plain:ar_muqaddimah | 35000 | 0.291 | 0.869 | 0.815 | 4.458 | 33 | 4.299 | 3.743 | 3.039 | 0.380 | 0.364 | 0.576 | 0.301 |
| plain_folded:ar_muqaddimah | 35000 | 0.289 | 0.868 | 0.814 | 4.435 | 28 | 4.144 | 3.622 | 2.963 | 0.379 | 0.393 | 0.536 | 0.258 |

Auto-generated summary (hedged; 4 texts, 2 languages, two sizes of corpus):

- h2: MS 408 2.22 bits; Hebrew/Arabic 3.63-3.87 (folded variants 3.52-3.72). h3: MS 408 1.95; abjad 2.61-3.04.
- h2 rise after within-word letter shuffle: MS 408 1.35 bits; abjad 0.24-0.41 (Latin/Italian/German plain texts: 0.65-1.00).
- Share of positionally skewed units: MS 408 0.92; abjad 0.48-0.59 (folded 0.14-0.54).
- Zipf s: MS 408 0.98; abjad 0.86-0.94. Heaps beta (shuffled): MS 408 0.75; abjad 0.76-0.81. TTR: MS 408 0.21; abjad 0.22-0.29.
- Mean word length: MS 408 4.47 units; abjad 3.79-4.46.

### What adding Hebrew/Arabic changes in the family verdicts

Verdicts for MS 408 (collapsed units) per family and metric, computed without and with the Hebrew/Arabic bases/transformations (`verdict_shift_abjad.csv`). Families that gain Hebrew/Arabic members get wider intervals.

22 of 391 existing family-metric verdicts change:

| family | metric | verdict_before | verdict_after |
|---|---|---|---|
| polyalphabetic (Vigenere) | type/token ratio | ≈ | ↓ |
| polyalphabetic (Vigenere) | word entropy H1 (bits) | ≈ | ↓ |
| polyalphabetic (Vigenere) | Zipf exponent s (MLE r10-1000) | ≈ | ↑ |
| polyalphabetic (Vigenere) | Heaps beta (text order) | ≈ | ↓ |
| polyalphabetic (Vigenere) | word length SD (units) | ↓ | ≈ |
| verbose cipher (letter -> 2 symbols) | word entropy H1 (bits) | ≈ | ↓ |
| verbose cipher (letter -> 2 symbols) | word length SD (units) | ↓ | ≈ |
| verbose cipher (letter -> 2 symbols) | unit entropy H1 (bits) | ≈ | ↑ |
| word reversal | word length SD (units) | ↓ | ≈ |
| word reversal | word-initial vs final unit JSD (bits) | ≈ | ↑ |
| anagram (alphagram) | word length SD (units) | ↓ | ≈ |
| anagram (alphagram) | conditional entropy h2 (bits) | ↓ | ≈ |
| anagram (alphagram) | conditional entropy h3 (bits) | ↓ | ≈ |
| anagram (alphagram) | Sukhotin vowel-like share of alphabet | ↓ | ≈ |
| letters shuffled inside words | word entropy H1 (bits) | ≈ | ↓ |
| letters shuffled inside words | word length SD (units) | ↓ | ≈ |
| shuffled tokens | word length SD (units) | ↓ | ≈ |
| shuffled tokens | word-initial vs final unit JSD (bits) | ≈ | ↑ |
| Markov character gibberish | word entropy H1 (bits) | ≈ | ↓ |
| Markov character gibberish | word length SD (units) | ↓ | ≈ |
| Markov character gibberish | H1 / log2(alphabet size) | ↓ | ≈ |
| iid letters (no structure) | word length SD (units) | ↓ | ≈ |

New family "natural abjad text (Hebrew/Arabic)": MS 408 is inside the prediction interval for 11 of 23 metrics: type/token ratio, hapax share of types, top-10 token coverage, word entropy H1 (bits), Zipf exponent s (MLE r10-1000), Heaps beta (text order), Heaps beta (shuffled tokens), mean word length (units), word length SD (units), H1 / log2(alphabet size), Sukhotin vowel-like share of alphabet.
Outside: unit entropy H1 (bits)↓, conditional entropy h2 (bits)↓, conditional entropy h3 (bits)↓, h2 rise after within-word shuffle (bits)↑, h2 / H1↓, h3 / H1↓, H1 - h2 (bits)↑, h2 rise after shuffle / H1↑, word-initial vs final unit JSD (bits)↑, share of positionally skewed units↑, adjacent identical-token rate↑, adjacent edit-distance-1 rate↑.

## 8. Sample-size sensitivity (first 9,000 tokens of each)

| name | n_tokens | type_token_ratio | zipf_mle_s_r10_1000 | heaps_beta_in_order | unit_H1 | unit_h2 | unit_h3 | shuffle_gap_h2 | pos_skewed_unit_share |
|---|---|---|---|---|---|---|---|---|---|
| MS408 P first 9000 | 9000 | 0.303 | 0.955 | 0.754 | 3.950 | 2.339 | 1.988 | 1.210 | 0.913 |
| plain:la_vulgate first 9000 | 9000 | 0.267 | 0.844 | 0.834 | 3.929 | 3.184 | 2.392 | 0.660 | 0.550 |
| plain:la_augustine first 9000 | 9000 | 0.375 | 0.911 | 0.868 | 3.917 | 3.155 | 2.517 | 0.688 | 0.500 |
| plain:la_pliny_herbal first 9000 | 9000 | 0.355 | 0.793 | 0.778 | 3.946 | 3.199 | 2.536 | 0.689 | 0.667 |
| plain:la_pliny_general first 9000 | 9000 | 0.508 | 0.696 | 0.873 | 3.961 | 3.226 | 2.682 | 0.679 | 0.619 |
| plain:la_celsus first 9000 | 9000 | 0.344 | 0.845 | 0.779 | 3.933 | 3.151 | 2.445 | 0.718 | 0.450 |
| plain:la_isidore first 9000 | 9000 | 0.352 | 0.851 | 0.799 | 3.962 | 3.178 | 2.458 | 0.710 | 0.619 |
| plain:la_macer first 9000 | 9000 | 0.324 | 0.768 | 0.770 | 3.962 | 3.176 | 2.435 | 0.727 | 0.571 |
| plain:it_dante first 9000 | 9000 | 0.284 | 0.981 | 0.789 | 4.008 | 2.969 | 2.390 | 0.883 | 0.810 |
| plain:it_manzoni first 9000 | 9000 | 0.298 | 0.947 | 0.822 | 4.007 | 2.995 | 2.398 | 0.897 | 0.810 |
| plain:it_sidrach first 9000 | 9000 | 0.217 | 1.005 | 0.703 | 3.976 | 2.952 | 2.275 | 0.896 | 0.857 |
| plain:it_ariosto first 9000 | 9000 | 0.277 | 0.959 | 0.767 | 4.000 | 2.996 | 2.371 | 0.856 | 0.762 |
| plain:de_walther_mhg first 9000 | 9000 | 0.321 | 0.892 | 0.751 | 4.069 | 2.957 | 2.277 | 0.958 | 0.522 |
| plain:de_faust first 9000 | 9000 | 0.318 | 0.996 | 0.787 | 4.082 | 2.928 | 2.210 | 1.003 | 0.478 |
| plain:he_tanakh first 9000 | 9000 | 0.297 | 0.853 | 0.883 | 4.195 | 3.751 | 2.303 | 0.246 | 0.556 |
| plain:he_mishneh_torah first 9000 | 9000 | 0.343 | 0.779 | 0.836 | 4.254 | 3.799 | 2.408 | 0.293 | 0.519 |
| plain:ar_quran first 9000 | 9000 | 0.329 | 0.837 | 0.817 | 4.148 | 3.581 | 2.429 | 0.419 | 0.606 |
| plain:ar_muqaddimah first 9000 | 9000 | 0.462 | 0.783 | 0.857 | 4.274 | 3.786 | 2.926 | 0.327 | 0.469 |

The first 9,000 tokens of MS 408 are mostly herbal-section text in manuscript order; the point is only how far TTR, Zipf, Heaps and entropies move when the sample shrinks to the size of the smallest controls.

## Caveats

- Family members are a handful of base texts (several windows of the same book are not independent), so prediction intervals understate the true spread of 'all texts of that kind'; `?` means fewer than 3 members.
- SEs are delete-one-block jackknife SEs (MS 408: pages and 8-page blocks; controls: 20 contiguous groups). They capture sampling noise only: not transcription uncertainty, not model misspecification, not the choice of unit segmentation. For smooth metrics the jackknife is reliable; for rank/threshold statistics (Zipf fit, Sukhotin share) it is only indicative.
- The 8-page block approximates quire structure only (the repo has no folio→quire map); the page jackknife is usually the lower SE, the block jackknife the larger. The larger is used.
- Per-control z-scores use only the two jackknife SEs; they say 'distinguishable from this one text at this noise level', not 'is this kind of text'.
- Hebrew/Arabic: consonantal normalisation is our choice (maqaf/hyphen splits words, Arabic clitics like و- and ال- stay attached, Quranic marks and diacritics dropped); none is a model of whatever language MS 408 may encode.
- Tokenization is a free choice: controls are normalised to a-z with diacritics folded; MS 408 uses a transcription (ZL 3b) with uncertain spaces split and unreadable tokens dropped, and unit segmentation (collapsed vs raw) changes unit-level metrics (see the `raw` columns in `verdict_summary.csv`).
- Poetry (Dante, Ariosto, Faust, Walther, Macer) and prose differ; MS 408 pages are not independent samples (sections, hands, Currier A/B).
- `Markov o2 trained on MS 408` reproduces h2 by construction and is not a hypothesis. The slot-grammar generator's inventories were written with published descriptions of Voynichese in mind, so its match is expected, not independent evidence.
- The verbose / Naibbe-inspired controls are measured on single symbols; the cipher's natural unit (a 2-3 symbol group) would give different unit statistics. The self-citation generator is a copy-and-mutate toy (parameters 0.15/0.3/0.5, not fitted).
- Ranking families by the count of metrics inside the interval is only a convenience for ordering columns; the metrics are strongly correlated, so the count is not a likelihood.
- No metric here is decisive; several hypotheses (self-citation generators, verbose ciphers) are known to reproduce parts of the profile.
