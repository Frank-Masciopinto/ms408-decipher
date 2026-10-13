# h30: the line as a unit (pre-registration)

Written and committed before any h30 computing. No translation claims: the question is only how lines are structured statistically.

## Data
- **MS 408:** running-text lines (the h14 table: paragraph text, labels excluded). These are analysed by hand × language: 1A, 2B and 3B (each ~10k tokens). 3A (0.7k tokens) is reported descriptively only.
- **Words:** words are the h14 EVA tokens. A line is an h14 `lid`; a paragraph starts at `para_initial`.
- **Controls:** raw line structure of the files in `data/controls/`. Each text is cut to its first ~10k tokens after the header. Paragraph = a blank-line-separated block.
  - **Verse:** Dante *Commedia* (pg1000), Ariosto *Orlando furioso* (pg3747), Macer Floridus (Latin hexameter herbal).
  - **Prose broken at the margin** (Gutenberg hard wrap at ~70 characters): Augustine *Confessiones* (pg33849, Latin), Manzoni (pg45334), Sidrach (pg44549).
  - **Recipe / list prose:** *Libro della cucina* (pg33954).
  - No true table text is available; I say so instead of faking one.

## Word classes (identical for MS and controls)
- **TYPE:** the 30 most frequent word types of that text, plus OTHER.
- **ONSET:** the first unit (EVA unit for MS, letter for controls); top 10 plus OTHER.
- **END:** the last unit; top 10 plus OTHER.
- **Position bins in line:** first, second, middle, penultimate, last (lines of ≥ 4 words).

## Measures (per text, or per hand for MS)
- **M1 Line length:** words/line and glyphs/line. Report mean, CV and the share of the modal length.
- **M2 Positional MI:** I(position bin; class) for TYPE, ONSET and END.
  - **Null:** words permuted across lines within the same stratum (MS: hand × quire; controls: blocks of 50 lines), with line lengths kept. 200 permutations.
  - **Report:** excess MI = obs − null mean, and z.
- **M3 Cross-line vs within-line dependency** (class END→ONSET and TYPE→TYPE):
  - **within:** I(class of word k; class of word k+1) inside lines;
  - **across:** I(class of last word of line i; class of first word of line i+1) on the same page;
  - **Null for across:** shuffle line order within page (MS) or within block (controls), 200 times.
- **M4 Rhyme-like endings:** P(END of line i == END of line i+1) and P(END of line i == END of line i+2), against the within-line rate P(END of word k == END of word k+1) and against the line-shuffle null.
- **M5 Paragraph structure:** first-line vs other-line length, and Jensen–Shannon divergence of the ONSET distribution of the first word (paragraph-initial line vs other lines), against a null permuting the paragraph-first label within stratum.
- **M6 Line grammar vs bag of words** (held-out by quire for MS, by contiguous fifths for controls; class = TYPE):
  - **(a) bag:** unigram;
  - **(b) positional unigram:** P(class | position bin);
  - **(c) within-line bigram** with line-start/line-end symbols;
  - **(d) a 4-state discrete HMM** (EM, numpy) over line-delimited class sequences, with an end symbol.
  - Additive smoothing 0.5. Report held-out bits/token gain of (b), (c) and (d) over (a).

## Predictions (MS 408, per hand)
- **L1 (not verse):** words/line CV of MS hands ≥ 0.25, closer to the prose and recipe controls than to the verse controls (Dante and Ariosto CV < 0.2). Rhyme-like line-end repetition (M4) is not above the line-shuffle null.
- **L2 (lines are units, not margin breaks):** MS positional excess MI for ONSET and END is ≥ 3× the mean of the hard-wrapped prose controls, with z > 5 in every main hand.
- **L3 (weak cross-line link):** MS across-line END→ONSET MI excess is < 50 % of its within-line value. Lines are more independent of each other than words within a line.
- **L4 (paragraph-initial lines are special):** onset JS z > 5 in every main hand; first lines are longer than other lines.
- **L5 (line grammar):** positional unigram (b) beats bag (a) on held-out data by ≥ 0.05 bits/token in every main hand, and by more than in any hard-wrapped prose control. The HMM (d) beats (a).
- **Interpretation rule:**
  - "list/table entry": L2 and L5 hold *and* the first and last positions carry most of the positional MI (≥ 60 %);
  - "verse": L1 fails;
  - "running prose broken at the margin": L2 fails.
