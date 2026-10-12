# h09 pre-registration (written and committed before any text statistic was computed)

Visual tags in `data/visual_tags.csv` were recorded by eye from `data/images/page_*.png` montages
(herbal: 5x3 grids at 300 px per page; other sections: 2x2 grids at 700 px). No transcription text was
looked at while tagging. Counts are approximate (`conf` = high/med/low). Herbal pages carry
`root_size` (0 none/small, 1 normal, 2 large/tuberous), `blue_flower`, `red_flower`.

Label-object categories come from the IVTFF locus subtypes in ZL3b (Zandbergen, IVTFF format, table 9):
Lc container (jar), Lf herb fragment (pharma), Ln nymph, Lt tube/tub, Ls star, Lz zodiac element,
La other astro element, Lp herbal plant, L0 unattached.

Predictions (one-sided, alpha 0.05, Holm across the family in each test block):
P1 Labels of the same object type share more word-initial bigrams / final bigrams / whole words than labels of different types (permutation of type labels, stratified by quire).
P2 Herbal-pharma "same plant" pairs listed in the ZL3b header comments (Petersen, Stolfi, FSG, GL) share more label/first-line vocabulary than random herbal-pharma pairs.
P3 A label word recurs in the running text of its own page more than in other pages of the same quire.
P4 Context words: words enriched on pages with high nymph/pool/water tag score ("water/bath" candidates), star score ("star"), jar/root score ("root/vessel"), tested by quire-block permutation of tag values, Holm-corrected.
P5 Transfer: "water" candidates selected on biological pages are enriched in herbal pages tagged with large roots / any water; "root" candidates selected in pharma pages are enriched in herbal pages with root_size=2. Null: candidate sets drawn from frequency-matched random words, and random tag sets.
Expectation stated in advance: because sections coincide with quires, most P4 effects are expected to be section/quire effects; P5 and within-section P3 are the tests that are not trivially section effects.
