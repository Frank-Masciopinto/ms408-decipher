# Control comparison: MS 408 vs controls

> **MS 408 is undeciphered.** This is a screening comparison of descriptive statistics, not a decipherment, and no single metric is decisive. Controls are small in number and built from a few base texts (Latin, Italian, one small Middle High German text, Hebrew and Arabic prose); transformations are simplified illustrations of each family, NOT reproductions of published ciphers; generators are not fitted to MS 408. See [docs/CONTROLS.md](../../docs/CONTROLS.md).

Target size 35000 tokens per control (MS 408 running text: 34977 readable tokens); stochastic controls are means over 3 seeds. Controls use single characters as units; MS 408 uses the collapsed EVA segmentation (ch, sh, cth, ckh, cph, cfh as single units) unless marked raw. Tables: `comparison.csv` (means), `comparison_sd.csv`, `comparison_runs.csv`.

## 1. All corpora, selected metrics

| name | family | tokens | TTR | Zipf s | Heaps β | len | H1 | h2 | h3 | Δh2 shuf | vowel-like | pos-skew | adj-edit1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MS408 P (collapsed units) | MS 408 | 34977 | 0.205 | 0.985 | 0.747 | 4.466 | 3.901 | 2.217 | 1.954 | 1.348 | 0.222 | 0.923 | 0.034 |
| MS408 P (raw EVA chars) | MS 408 | 34977 | 0.205 | 0.985 | 0.747 | 4.993 | 3.879 | 2.079 | 1.851 | 1.495 | 0.286 | 0.950 | 0.034 |
| MS408 Currier A (collapsed) | MS 408 | 11300 | 0.292 | 0.943 | 0.774 | 4.156 | 3.940 | 2.321 | 2.019 | 1.234 | 0.269 | 0.958 | 0.038 |
| MS408 Currier B (collapsed) | MS 408 | 23128 | 0.210 | 1.021 | 0.737 | 4.620 | 3.859 | 2.048 | 1.801 | 1.457 | 0.259 | 0.909 | 0.032 |
| MS408 P tokens shuffled (collapsed) | MS 408 | 34977 | 0.205 | 0.985 | 0.747 | 4.466 | 3.901 | 2.217 | 1.954 | 1.346 | 0.222 | 0.923 | 0.018 |
| MS408 P letters shuffled in tokens (collapsed) | MS 408 | 34977 | 0.547 | 0.758 | 0.903 | 4.465 | 3.901 | 3.563 | 3.191 | -0.025 | 0.333 | 0.000 | 0.009 |
| plain:la_vulgate | natural-language plaintext (Latin/Italian/MHG) | 35000 | 0.201 | 0.875 | 0.755 | 5.315 | 3.949 | 3.213 | 2.513 | 0.666 | 0.273 | 0.409 | 0.003 |
| plain:la_augustine | natural-language plaintext (Latin/Italian/MHG) | 35000 | 0.274 | 0.963 | 0.804 | 5.437 | 3.915 | 3.162 | 2.579 | 0.686 | 0.286 | 0.571 | 0.006 |
| plain:it_dante | natural-language plaintext (Latin/Italian/MHG) | 35000 | 0.187 | 1.045 | 0.761 | 3.928 | 4.015 | 2.987 | 2.474 | 0.882 | 0.273 | 0.810 | 0.020 |
| plain:it_manzoni | natural-language plaintext (Latin/Italian/MHG) | 35000 | 0.186 | 0.985 | 0.746 | 4.588 | 4.005 | 2.996 | 2.439 | 0.901 | 0.238 | 0.810 | 0.011 |
| plain:de_walther_mhg | natural-language plaintext (Latin/Italian/MHG) | 9183 | 0.322 | 0.893 | 0.791 | 4.712 | 4.070 | 2.964 | 2.283 | 0.956 | 0.304 | 0.522 | 0.012 |
| abjad:la_vulgate | abjad (vowels removed) | 34630 | 0.129 | 0.980 | 0.703 | 2.832 | 3.568 | 3.029 | 2.345 | 0.454 | 0.529 | 0.471 | 0.068 |
| abjad:it_manzoni | abjad (vowels removed) | 32260 | 0.129 | 1.042 | 0.712 | 2.673 | 3.678 | 3.002 | 2.430 | 0.482 | 0.312 | 0.312 | 0.079 |
| monoalphabetic:la_vulgate | monoalphabetic substitution | 35000 | 0.201 | 0.875 | 0.754 | 5.315 | 3.949 | 3.213 | 2.513 | 0.665 | 0.273 | 0.409 | 0.003 |
| monoalphabetic:it_manzoni | monoalphabetic substitution | 35000 | 0.186 | 0.985 | 0.748 | 4.588 | 4.005 | 2.996 | 2.439 | 0.900 | 0.238 | 0.810 | 0.011 |
| caesar3:la_vulgate | monoalphabetic substitution | 35000 | 0.201 | 0.875 | 0.755 | 5.315 | 3.949 | 3.213 | 2.513 | 0.666 | 0.273 | 0.409 | 0.003 |
| caesar3:it_manzoni | monoalphabetic substitution | 35000 | 0.186 | 0.985 | 0.746 | 4.588 | 4.005 | 2.996 | 2.439 | 0.901 | 0.238 | 0.810 | 0.011 |
| vigenere_k3:la_vulgate | polyalphabetic (Vigenere) | 35000 | 0.303 | 0.725 | 0.812 | 5.315 | 4.356 | 3.827 | 2.892 | 0.487 | 0.369 | 0.238 | 0.002 |
| vigenere_k3:it_manzoni | polyalphabetic (Vigenere) | 35000 | 0.273 | 0.920 | 0.796 | 4.588 | 4.412 | 3.743 | 2.786 | 0.596 | 0.360 | 0.456 | 0.008 |
| vigenere_k6:la_vulgate | polyalphabetic (Vigenere) | 35000 | 0.378 | 0.683 | 0.845 | 5.315 | 4.571 | 4.190 | 3.188 | 0.349 | 0.410 | 0.090 | 0.001 |
| vigenere_k6:it_manzoni | polyalphabetic (Vigenere) | 35000 | 0.337 | 0.859 | 0.825 | 4.588 | 4.595 | 4.147 | 3.078 | 0.404 | 0.436 | 0.269 | 0.007 |
| nomenclator:la_vulgate | nomenclator-like syllable code | 35000 | 0.201 | 0.875 | 0.754 | 4.140 | 4.291 | 4.058 | 3.426 | 0.165 | 0.500 | 0.017 | 0.013 |
| nomenclator:it_manzoni | nomenclator-like syllable code | 35000 | 0.186 | 0.985 | 0.748 | 3.898 | 4.285 | 3.905 | 3.219 | 0.288 | 0.500 | 0.050 | 0.019 |
| verbose_2sym:la_vulgate | verbose cipher (letter -> 2 symbols) | 35000 | 0.566 | 0.746 | 0.917 | 10.630 | 3.798 | 2.870 | 2.365 | 0.901 | 0.500 | 0.396 | 0.000 |
| verbose_2sym:it_manzoni | verbose cipher (letter -> 2 symbols) | 35000 | 0.482 | 0.995 | 0.887 | 9.175 | 3.845 | 2.864 | 2.286 | 0.942 | 0.500 | 0.479 | 0.001 |
| naibbe_like:la_vulgate | Naibbe-inspired homophonic tiles | 35000 | 0.651 | 0.879 | 0.935 | 11.066 | 3.751 | 3.316 | 2.629 | 0.423 | 0.476 | 0.071 | 0.000 |
| naibbe_like:it_manzoni | Naibbe-inspired homophonic tiles | 35000 | 0.548 | 0.924 | 0.901 | 9.408 | 3.758 | 3.335 | 2.664 | 0.406 | 0.476 | 0.071 | 0.001 |
| reverse_words:la_vulgate | word reversal | 35000 | 0.201 | 0.875 | 0.755 | 5.315 | 3.949 | 3.294 | 2.675 | 0.584 | 0.273 | 0.409 | 0.003 |
| reverse_words:it_manzoni | word reversal | 35000 | 0.186 | 0.985 | 0.746 | 4.588 | 4.005 | 3.298 | 2.574 | 0.598 | 0.238 | 0.810 | 0.011 |
| alphagram:la_vulgate | anagram (alphagram) | 35000 | 0.194 | 0.883 | 0.751 | 5.315 | 3.949 | 2.532 | 2.220 | 1.345 | 0.364 | 0.955 | 0.006 |
| alphagram:it_manzoni | anagram (alphagram) | 35000 | 0.179 | 0.988 | 0.742 | 4.588 | 4.005 | 2.656 | 2.331 | 1.240 | 0.333 | 1.000 | 0.011 |
| shuffle_letters:la_vulgate | letters shuffled inside words | 35000 | 0.610 | 0.804 | 0.932 | 5.315 | 3.949 | 3.879 | 3.754 | -0.008 | 0.273 | 0.000 | 0.003 |
| shuffle_letters:it_manzoni | letters shuffled inside words | 35000 | 0.505 | 1.139 | 0.903 | 4.588 | 4.005 | 3.897 | 3.704 | -0.024 | 0.238 | 0.000 | 0.009 |
| shuffle_tokens:la_vulgate | shuffled tokens | 35000 | 0.201 | 0.875 | 0.756 | 5.315 | 3.949 | 3.213 | 2.513 | 0.664 | 0.273 | 0.409 | 0.008 |
| shuffle_tokens:it_manzoni | shuffled tokens | 35000 | 0.186 | 0.985 | 0.747 | 4.588 | 4.005 | 2.996 | 2.439 | 0.900 | 0.238 | 0.810 | 0.021 |
| plain:he_tanakh | natural abjad text (Hebrew/Arabic) | 35000 | 0.216 | 0.863 | 0.758 | 3.788 | 4.225 | 3.823 | 2.606 | 0.238 | 0.481 | 0.556 | 0.008 |
| plain_folded:he_tanakh | natural abjad, folded-alphabet variant (sensitivity only) | 35000 | 0.216 | 0.863 | 0.758 | 3.788 | 4.051 | 3.668 | 2.507 | 0.245 | 0.500 | 0.227 | 0.008 |
| plain:he_mishneh_torah | natural abjad text (Hebrew/Arabic) | 35000 | 0.252 | 0.866 | 0.781 | 4.025 | 4.256 | 3.866 | 2.695 | 0.261 | 0.370 | 0.481 | 0.008 |
| plain_folded:he_mishneh_torah | natural abjad, folded-alphabet variant (sensitivity only) | 35000 | 0.252 | 0.866 | 0.781 | 4.025 | 4.075 | 3.715 | 2.594 | 0.257 | 0.364 | 0.136 | 0.008 |
| plain:ar_quran | natural abjad text (Hebrew/Arabic) | 35000 | 0.233 | 0.894 | 0.775 | 4.261 | 4.157 | 3.627 | 2.612 | 0.408 | 0.303 | 0.576 | 0.006 |
| plain_folded:ar_quran | natural abjad, folded-alphabet variant (sensitivity only) | 35000 | 0.231 | 0.895 | 0.774 | 4.241 | 4.033 | 3.524 | 2.583 | 0.407 | 0.286 | 0.500 | 0.007 |
| plain:ar_muqaddimah | natural abjad text (Hebrew/Arabic) | 35000 | 0.291 | 0.869 | 0.819 | 4.458 | 4.299 | 3.743 | 3.039 | 0.381 | 0.364 | 0.576 | 0.003 |
| plain_folded:ar_muqaddimah | natural abjad, folded-alphabet variant (sensitivity only) | 35000 | 0.289 | 0.868 | 0.818 | 4.435 | 4.144 | 3.622 | 2.963 | 0.379 | 0.393 | 0.536 | 0.004 |
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
| reverse_words:he_tanakh | word reversal | 35000 | 0.216 | 0.863 | 0.758 | 3.788 | 4.225 | 3.618 | 2.517 | 0.446 | 0.481 | 0.556 | 0.008 |
| reverse_words:he_mishneh_torah | word reversal | 35000 | 0.252 | 0.866 | 0.781 | 4.025 | 4.256 | 3.694 | 2.745 | 0.433 | 0.370 | 0.481 | 0.008 |
| reverse_words:ar_quran | word reversal | 35000 | 0.233 | 0.894 | 0.775 | 4.261 | 4.157 | 3.580 | 2.602 | 0.456 | 0.303 | 0.576 | 0.006 |
| reverse_words:ar_muqaddimah | word reversal | 35000 | 0.291 | 0.869 | 0.819 | 4.458 | 4.299 | 3.550 | 2.596 | 0.573 | 0.364 | 0.576 | 0.003 |
| alphagram:he_tanakh | anagram (alphagram) | 35000 | 0.177 | 0.836 | 0.728 | 3.788 | 4.225 | 3.085 | 2.636 | 0.977 | 0.370 | 0.852 | 0.013 |
| alphagram:he_mishneh_torah | anagram (alphagram) | 35000 | 0.215 | 0.854 | 0.756 | 4.025 | 4.256 | 3.080 | 2.710 | 1.046 | 0.296 | 0.926 | 0.010 |
| alphagram:ar_quran | anagram (alphagram) | 35000 | 0.212 | 0.899 | 0.761 | 4.261 | 4.157 | 2.991 | 2.384 | 1.044 | 0.273 | 0.970 | 0.008 |
| alphagram:ar_muqaddimah | anagram (alphagram) | 35000 | 0.267 | 0.866 | 0.806 | 4.458 | 4.299 | 3.024 | 2.559 | 1.099 | 0.273 | 0.909 | 0.005 |
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
| markov_o2:it_manzoni | Markov character gibberish | 35000 | 0.390 | 1.079 | 0.863 | 4.592 | 4.006 | 2.998 | 2.427 | 0.918 | 0.238 | 0.762 | 0.028 |
| markov_o1:it_manzoni | Markov character gibberish | 35000 | 0.470 | 1.095 | 0.892 | 4.599 | 4.005 | 2.996 | 3.048 | 0.945 | 0.238 | 0.714 | 0.041 |
| iid_letters:it_manzoni | iid letters (no structure) | 35000 | 0.654 | 0.884 | 0.931 | 4.576 | 4.005 | 4.004 | 3.936 | -0.000 | 0.286 | 0.000 | 0.019 |
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

## 2. Which hypothesis families does MS 408 fall inside?

For every family the band is [min, max] of its members' means, widened by a per-metric tolerance (see `controls_metrics.METRIC_INFO`; round numbers, not confidence intervals). `≈` MS 408 inside the band, `↑` above, `↓` below. The `Markov o2 trained on MS 408` control is excluded: it is built from MS 408 itself.

| metric | slot-grammar generat… | shuffled tokens | natural-language pla… | word reversal | anagram (alphagram) | natural abjad text (… | monoalphabetic subst… | nomenclator-like syl… | Markov character gib… | letters shuffled ins… | polyalphabetic (Vige… | iid letters (no stru… | self-citation genera… | abjad (vowels remove… | verbose cipher (lett… | Naibbe-inspired homo… |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| type/token ratio | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ↓ | ↓ | ↓ | ↓ | ≈ | ↑ | ↓ | ↓ |
| hapax share of types | ↑ | ≈ | ≈ | ≈ | ↑ | ≈ | ↑ | ↑ | ↓ | ↓ | ≈ | ↓ | ↑ | ↑ | ↓ | ↓ |
| top-10 token coverage | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ↓ | ↓ | ≈ | ≈ | ≈ | ↑ | ↑ | ↓ | ≈ | ↑ |
| word entropy H1 (bits) | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ↓ | ↓ | ↓ | ↓ | ≈ | ↑ | ↓ | ↓ |
| Zipf exponent s (MLE r10-1000) | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ↑ | ↑ | ≈ | ≈ | ≈ |
| Heaps beta (text order) | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ↓ | ↓ | ↓ | ↓ | ↓ | ≈ | ↓ | ↓ |
| Heaps beta (shuffled tokens) | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ↓ | ↓ | ≈ | ↓ | ≈ | ≈ | ↓ | ↓ |
| mean word length (units) | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ↑ | ↓ | ↓ |
| word length SD (units) | ≈ | ≈ | ↓ | ≈ | ≈ | ≈ | ↓ | ↓ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ↓ | ↓ |
| unit entropy H1 (bits) | ↑ | ≈ | ≈ | ≈ | ≈ | ↓ | ≈ | ↓ | ≈ | ≈ | ↓ | ≈ | ↑ | ↑ | ≈ | ≈ |
| conditional entropy h2 (bits) | ≈ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ |
| conditional entropy h3 (bits) | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ | ↓ |
| h2 rise after within-word shuffle (bits) | ≈ | ↑ | ↑ | ↑ | ≈ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ |
| Sukhotin vowel-like share of alphabet | ↓ | ≈ | ≈ | ≈ | ↓ | ↓ | ≈ | ↓ | ≈ | ≈ | ↓ | ≈ | ≈ | ↓ | ↓ | ↓ |
| word-initial vs final unit JSD (bits) | ↓ | ↑ | ↑ | ↑ | ↓ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ |
| share of positionally skewed units | ≈ | ↑ | ↑ | ↑ | ≈ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ |
| adjacent identical-token rate | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ≈ | ↓ | ≈ | ≈ | ≈ |
| adjacent edit-distance-1 rate | ≈ | ≈ | ≈ | ↑ | ↑ | ↑ | ↑ | ≈ | ≈ | ↑ | ↑ | ≈ | ↓ | ↓ | ↑ | ↑ |

Column order = number of metrics inside the band (highest first):

1. slot-grammar generator
2. shuffled tokens
3. natural-language plaintext (Latin/Italian/MHG)
4. word reversal
5. anagram (alphagram)
6. natural abjad text (Hebrew/Arabic)
7. monoalphabetic substitution
8. nomenclator-like syllable code
9. Markov character gibberish
10. letters shuffled inside words
11. polyalphabetic (Vigenere)
12. iid letters (no structure)
13. self-citation generator
14. abjad (vowels removed)
15. verbose cipher (letter -> 2 symbols)
16. Naibbe-inspired homophonic tiles

### Summary per family

| family | n_members | inside (collapsed units) | outside (collapsed) | inside (raw EVA) | outside (raw) | n_metrics |
|---|---|---|---|---|---|---|
| slot-grammar generator | 3 | 13 | 5 | 9 | 9 | 18 |
| shuffled tokens | 6 | 13 | 5 | 13 | 5 | 18 |
| natural-language plaintext (Latin/Italian/MHG) | 5 | 12 | 6 | 12 | 6 | 18 |
| word reversal | 6 | 12 | 6 | 12 | 6 | 18 |
| anagram (alphagram) | 6 | 12 | 6 | 13 | 5 | 18 |
| natural abjad text (Hebrew/Arabic) | 4 | 10 | 8 | 10 | 8 | 18 |
| monoalphabetic substitution | 4 | 9 | 9 | 9 | 9 | 18 |
| nomenclator-like syllable code | 2 | 8 | 10 | 7 | 11 | 18 |
| Markov character gibberish | 12 | 8 | 10 | 8 | 10 | 18 |
| letters shuffled inside words | 6 | 7 | 11 | 7 | 11 | 18 |
| polyalphabetic (Vigenere) | 12 | 7 | 11 | 7 | 11 | 18 |
| iid letters (no structure) | 6 | 6 | 12 | 6 | 12 | 18 |
| self-citation generator | 3 | 6 | 12 | 6 | 12 | 18 |
| abjad (vowels removed) | 2 | 5 | 13 | 6 | 12 | 18 |
| verbose cipher (letter -> 2 symbols) | 6 | 4 | 14 | 4 | 14 | 18 |
| Naibbe-inspired homophonic tiles | 6 | 3 | 15 | 3 | 15 | 18 |

### Metrics where MS 408 falls OUTSIDE each family (collapsed units)

- **slot-grammar generator** (13/18 inside): hapax_share_of_types↑; unit_H1↑; unit_h3↓; sukhotin_vowel_like_share↓; pos_jsd_initial_final↓
- **shuffled tokens** (13/18 inside): unit_h2↓; unit_h3↓; shuffle_gap_h2↑; pos_jsd_initial_final↑; pos_skewed_unit_share↑
- **natural-language plaintext (Latin/Italian/MHG)** (12/18 inside): word_length_sd_units↓; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; pos_jsd_initial_final↑; pos_skewed_unit_share↑
- **word reversal** (12/18 inside): unit_h2↓; unit_h3↓; shuffle_gap_h2↑; pos_jsd_initial_final↑; pos_skewed_unit_share↑; adjacent_edit1_rate↑
- **anagram (alphagram)** (12/18 inside): hapax_share_of_types↑; unit_h2↓; unit_h3↓; sukhotin_vowel_like_share↓; pos_jsd_initial_final↓; adjacent_edit1_rate↑
- **natural abjad text (Hebrew/Arabic)** (10/18 inside): unit_H1↓; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; sukhotin_vowel_like_share↓; pos_jsd_initial_final↑; pos_skewed_unit_share↑; adjacent_edit1_rate↑
- **monoalphabetic substitution** (9/18 inside): hapax_share_of_types↑; top10_token_coverage↓; word_length_sd_units↓; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; pos_jsd_initial_final↑; pos_skewed_unit_share↑; adjacent_edit1_rate↑
- **nomenclator-like syllable code** (8/18 inside): hapax_share_of_types↑; top10_token_coverage↓; word_length_sd_units↓; unit_H1↓; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; sukhotin_vowel_like_share↓; pos_jsd_initial_final↑; pos_skewed_unit_share↑
- **Markov character gibberish** (8/18 inside): type_token_ratio↓; hapax_share_of_types↓; word_entropy_H1↓; heaps_beta_in_order↓; heaps_beta_shuffled↓; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; pos_jsd_initial_final↑; pos_skewed_unit_share↑
- **letters shuffled inside words** (7/18 inside): type_token_ratio↓; hapax_share_of_types↓; word_entropy_H1↓; heaps_beta_in_order↓; heaps_beta_shuffled↓; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; pos_jsd_initial_final↑; pos_skewed_unit_share↑; adjacent_edit1_rate↑
- **polyalphabetic (Vigenere)** (7/18 inside): type_token_ratio↓; word_entropy_H1↓; heaps_beta_in_order↓; unit_H1↓; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; sukhotin_vowel_like_share↓; pos_jsd_initial_final↑; pos_skewed_unit_share↑; adjacent_edit1_rate↑
- **iid letters (no structure)** (6/18 inside): type_token_ratio↓; hapax_share_of_types↓; top10_token_coverage↑; word_entropy_H1↓; zipf_mle_s_r10_1000↑; heaps_beta_in_order↓; heaps_beta_shuffled↓; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; pos_jsd_initial_final↑; pos_skewed_unit_share↑
- **self-citation generator** (6/18 inside): hapax_share_of_types↑; top10_token_coverage↑; zipf_mle_s_r10_1000↑; heaps_beta_in_order↓; unit_H1↑; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; pos_jsd_initial_final↑; pos_skewed_unit_share↑; adjacent_identical_rate↓; adjacent_edit1_rate↓
- **abjad (vowels removed)** (5/18 inside): type_token_ratio↑; hapax_share_of_types↑; top10_token_coverage↓; word_entropy_H1↑; mean_word_length_units↑; unit_H1↑; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; sukhotin_vowel_like_share↓; pos_jsd_initial_final↑; pos_skewed_unit_share↑; adjacent_edit1_rate↓
- **verbose cipher (letter -> 2 symbols)** (4/18 inside): type_token_ratio↓; hapax_share_of_types↓; word_entropy_H1↓; heaps_beta_in_order↓; heaps_beta_shuffled↓; mean_word_length_units↓; word_length_sd_units↓; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; sukhotin_vowel_like_share↓; pos_jsd_initial_final↑; pos_skewed_unit_share↑; adjacent_edit1_rate↑
- **Naibbe-inspired homophonic tiles** (3/18 inside): type_token_ratio↓; hapax_share_of_types↓; top10_token_coverage↑; word_entropy_H1↓; heaps_beta_in_order↓; heaps_beta_shuffled↓; mean_word_length_units↓; word_length_sd_units↓; unit_h2↓; unit_h3↓; shuffle_gap_h2↑; sukhotin_vowel_like_share↓; pos_jsd_initial_final↑; pos_skewed_unit_share↑; adjacent_edit1_rate↑

### Reading the matrix (auto-generated from the numbers above; hedged)

MS 408 (collapsed units): h2 = 2.22 bits, h3 = 1.95, h2 rise after within-word shuffle = 1.35 bits, Zipf s = 0.98, TTR = 0.21, 92% of units positionally skewed, adjacent edit-distance-1 rate 0.034.

- **conditional entropy h2 (bits)**: MS 408 is inside the band of slot-grammar generator.
- **conditional entropy h3 (bits)**: MS 408 is inside the band of **no** control family.
- **h2 rise after within-word shuffle (bits)**: MS 408 is inside the band of anagram (alphagram), slot-grammar generator.
- **Zipf exponent s (MLE r10-1000)**: MS 408 is inside the band of natural-language plaintext (Latin/Italian/MHG), abjad (vowels removed), monoalphabetic substitution, polyalphabetic (Vigenere), nomenclator-like syllable code, verbose cipher (letter -> 2 symbols), Naibbe-inspired homophonic tiles, word reversal, anagram (alphagram), letters shuffled inside words, shuffled tokens, natural abjad text (Hebrew/Arabic), Markov character gibberish, slot-grammar generator.
- **type/token ratio**: MS 408 is inside the band of natural-language plaintext (Latin/Italian/MHG), monoalphabetic substitution, nomenclator-like syllable code, word reversal, anagram (alphagram), shuffled tokens, natural abjad text (Hebrew/Arabic), self-citation generator, slot-grammar generator.
- **share of positionally skewed units**: MS 408 is inside the band of anagram (alphagram), slot-grammar generator.
- **adjacent edit-distance-1 rate**: MS 408 is inside the band of natural-language plaintext (Latin/Italian/MHG), nomenclator-like syllable code, shuffled tokens, Markov character gibberish, iid letters (no structure), slot-grammar generator.

- Metrics where MS 408 is inside **every** family band (non-discriminating here): none.
- Metrics where MS 408 is outside **every** family band (no control family reproduces it with these settings): conditional entropy h3 (bits), word-initial vs final unit JSD (bits).

What this does and does not say: the table shows which simplified control families have statistics near MS 408's on each metric. No family matches on all metrics, and the families that match on the most metrics (e.g. the slot-grammar generator) were designed with Voynichese structure in mind, so their match is not independent evidence. Matching on many metrics is not proof of a mechanism, and mismatching is not refutation: the controls are crude, tolerances arbitrary and several families (verbose/homophonic ciphers, self-citation generators) have parameters that could be tuned toward MS 408.

## 2b. Natural abjad texts (Hebrew, Arabic)

Consonantal Hebrew (Tanakh Genesis+Exodus; Maimonides, *Mishneh Torah*) and Arabic (Quran; Ibn Khaldun, *Muqaddimah*), one native letter = one unit, vowel points/diacritics removed. `plain:` rows use the main normalisation (Hebrew final forms ך ם ן ף ץ kept as separate letters; Arabic alif-hamza variants folded into alif); `plain_folded:` rows fold Hebrew final forms into the medial letters and reduce the Arabic alphabet further (ى→ي, ة→ه, ؤ→و, ئ→ي, hamza deleted), as a sensitivity check. A 1-to-1 Latin transliteration would give the same numbers (tested), so no separate transliterated run is shown.

| name | tokens | TTR | Zipf s | Heaps β | len | alphabet | H1 | h2 | h3 | Δh2 shuf | vowel-like | pos-skew | JSD ini/fin |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MS408 P (collapsed units) | 34977 | 0.205 | 0.985 | 0.747 | 4.466 | 27 | 3.901 | 2.217 | 1.954 | 1.348 | 0.222 | 0.923 | 0.659 |
| plain:he_tanakh | 35000 | 0.216 | 0.863 | 0.758 | 3.788 | 27 | 4.225 | 3.823 | 2.606 | 0.238 | 0.481 | 0.556 | 0.302 |
| plain_folded:he_tanakh | 35000 | 0.216 | 0.863 | 0.758 | 3.788 | 22 | 4.051 | 3.668 | 2.507 | 0.245 | 0.500 | 0.227 | 0.128 |
| plain:he_mishneh_torah | 35000 | 0.252 | 0.866 | 0.781 | 4.025 | 27 | 4.256 | 3.866 | 2.695 | 0.261 | 0.370 | 0.481 | 0.310 |
| plain_folded:he_mishneh_torah | 35000 | 0.252 | 0.866 | 0.781 | 4.025 | 22 | 4.075 | 3.715 | 2.594 | 0.257 | 0.364 | 0.136 | 0.112 |
| plain:ar_quran | 35000 | 0.233 | 0.894 | 0.775 | 4.261 | 33 | 4.157 | 3.627 | 2.612 | 0.408 | 0.303 | 0.576 | 0.275 |
| plain_folded:ar_quran | 35000 | 0.231 | 0.895 | 0.774 | 4.241 | 28 | 4.033 | 3.524 | 2.583 | 0.407 | 0.286 | 0.500 | 0.238 |
| plain:ar_muqaddimah | 35000 | 0.291 | 0.869 | 0.819 | 4.458 | 33 | 4.299 | 3.743 | 3.039 | 0.381 | 0.364 | 0.576 | 0.301 |
| plain_folded:ar_muqaddimah | 35000 | 0.289 | 0.868 | 0.818 | 4.435 | 28 | 4.144 | 3.622 | 2.963 | 0.379 | 0.393 | 0.536 | 0.258 |

Auto-generated summary (hedged; 4 texts, 2 languages, two sizes of corpus):

- h2: MS 408 2.22 bits; Hebrew/Arabic 3.63-3.87 (folded variants 3.52-3.72). h3: MS 408 1.95; abjad 2.61-3.04.
- h2 rise after within-word letter shuffle: MS 408 1.35 bits; abjad 0.24-0.41 (Latin/Italian/MHG plain texts: 0.67-0.96).
- Share of positionally skewed units: MS 408 0.92; abjad 0.48-0.58 (folded 0.14-0.54).
- Zipf s: MS 408 0.98; abjad 0.86-0.89. Heaps beta (shuffled): MS 408 0.75; abjad 0.76-0.82. TTR: MS 408 0.21; abjad 0.22-0.29.
- Mean word length: MS 408 4.47 units; abjad 3.79-4.46.

### What adding Hebrew/Arabic changes in the family verdicts

Verdicts for MS 408 (collapsed units) per family and metric, computed without (earlier Latin/Italian/MHG-only bases) and with the Hebrew/Arabic bases/transformations (`verdict_shift_abjad.csv`). Families that gain Hebrew/Arabic members get wider bands.

13 of 270 existing family-metric verdicts change:

| family | metric | verdict_before | verdict_after |
|---|---|---|---|
| polyalphabetic (Vigenere) | word length SD (units) | ↓ | ≈ |
| word reversal | hapax share of types | ↑ | ≈ |
| word reversal | top-10 token coverage | ↓ | ≈ |
| word reversal | word length SD (units) | ↓ | ≈ |
| anagram (alphagram) | top-10 token coverage | ↓ | ≈ |
| anagram (alphagram) | word length SD (units) | ↓ | ≈ |
| letters shuffled inside words | word length SD (units) | ↓ | ≈ |
| shuffled tokens | hapax share of types | ↑ | ≈ |
| shuffled tokens | top-10 token coverage | ↓ | ≈ |
| shuffled tokens | word length SD (units) | ↓ | ≈ |
| Markov character gibberish | word length SD (units) | ↓ | ≈ |
| iid letters (no structure) | word length SD (units) | ↓ | ≈ |
| iid letters (no structure) | Sukhotin vowel-like share of alphabet | ↓ | ≈ |

New family "natural abjad text (Hebrew/Arabic)": MS 408 is inside the band for 10 of 18 metrics: type/token ratio, hapax share of types, top-10 token coverage, word entropy H1 (bits), Zipf exponent s (MLE r10-1000), Heaps beta (text order), Heaps beta (shuffled tokens), mean word length (units), word length SD (units), adjacent identical-token rate.
Outside: unit entropy H1 (bits)↓, conditional entropy h2 (bits)↓, conditional entropy h3 (bits)↓, h2 rise after within-word shuffle (bits)↑, Sukhotin vowel-like share of alphabet↓, word-initial vs final unit JSD (bits)↑, share of positionally skewed units↑, adjacent edit-distance-1 rate↑.

## 3. Sample-size sensitivity (first 9,000 tokens of each)

| name | n_tokens | type_token_ratio | zipf_mle_s_r10_1000 | heaps_beta_in_order | unit_H1 | unit_h2 | unit_h3 | shuffle_gap_h2 | pos_skewed_unit_share |
|---|---|---|---|---|---|---|---|---|---|
| MS408 P first 9000 | 9000 | 0.303 | 0.955 | 0.754 | 3.950 | 2.339 | 1.988 | 1.210 | 0.913 |
| plain:la_vulgate first 9000 | 9000 | 0.267 | 0.844 | 0.834 | 3.929 | 3.184 | 2.392 | 0.660 | 0.550 |
| plain:la_augustine first 9000 | 9000 | 0.375 | 0.911 | 0.868 | 3.917 | 3.155 | 2.517 | 0.688 | 0.500 |
| plain:it_dante first 9000 | 9000 | 0.284 | 0.981 | 0.789 | 4.008 | 2.969 | 2.390 | 0.883 | 0.810 |
| plain:it_manzoni first 9000 | 9000 | 0.298 | 0.947 | 0.822 | 4.007 | 2.995 | 2.398 | 0.897 | 0.810 |
| plain:de_walther_mhg first 9000 | 9000 | 0.321 | 0.892 | 0.751 | 4.069 | 2.957 | 2.277 | 0.958 | 0.522 |
| plain:he_tanakh first 9000 | 9000 | 0.297 | 0.853 | 0.883 | 4.195 | 3.751 | 2.303 | 0.246 | 0.556 |
| plain:he_mishneh_torah first 9000 | 9000 | 0.343 | 0.779 | 0.836 | 4.254 | 3.799 | 2.408 | 0.293 | 0.519 |
| plain:ar_quran first 9000 | 9000 | 0.329 | 0.837 | 0.817 | 4.148 | 3.581 | 2.429 | 0.419 | 0.606 |
| plain:ar_muqaddimah first 9000 | 9000 | 0.462 | 0.783 | 0.857 | 4.274 | 3.786 | 2.926 | 0.327 | 0.469 |

The first 9,000 tokens of MS 408 are mostly herbal-section text in manuscript order; the point is only how far TTR, Zipf, Heaps and entropies move when the sample shrinks to the size of the small Middle High German control.

## Caveats

- Few controls per family (2-3 from 1-2 Latin/Italian bases; Hebrew/Arabic add 4 more bases to the transformation families, so those bands are wider and mix scripts), so family bands are crude and partly reflect the base text.
- Hebrew/Arabic: consonantal normalisation is our choice (maqaf/hyphen splits words, Arabic clitics like و- and ال- stay attached, Quranic marks and diacritics dropped); Hebrew is Biblical and Mishnaic-rabbinic, Arabic is Quranic rhymed prose and 14th-c. Maghribi prose; none is a model of whatever language MS 408 may encode.
- Tokenization is a free choice: controls are normalised to a-z with diacritics folded; MS 408 uses a transcription (ZL 3b) with uncertain spaces split and unreadable tokens dropped, and unit segmentation (collapsed vs raw) changes unit-level metrics (see the `raw` columns in `verdict_summary.csv`).
- Poetry (Dante, Walther) and prose (Augustine, Manzoni) differ; MS 408 pages are not independent samples (sections, hands, Currier A/B).
- `Markov o2 trained on MS 408` reproduces h2 by construction and is not a hypothesis. The slot-grammar generator's inventories were written with published descriptions of Voynichese in mind (see `controls_transforms.slot_grammar`), so its match is expected, not independent evidence.
- The verbose / Naibbe-inspired controls are measured on single symbols; the cipher's natural unit (a 2-3 symbol group) would give different unit statistics. The self-citation generator here is a simple copy-and-mutate toy (parameters 0.15/0.3/0.5, not fitted), far from the published Timm-Schinner generator.
- Ranking families by the count of metrics inside the band is only a convenience for ordering columns; the metrics are strongly correlated, so the count is not a likelihood.
- Tolerances are arbitrary round numbers; `≈` means 'not clearly separated', not 'consistent with'.
- No metric here is decisive; several hypotheses (self-citation generators, verbose ciphers) are known to reproduce parts of the profile.
