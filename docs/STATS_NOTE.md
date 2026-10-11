# Note: what the statistics in this repo are, and are not

Everything produced by `msdecipher` stages 1–5 (`reports/`, `glyphs/`) is a **description of a
transcription**. It is not decoding, not translation, and not evidence that MS 408 contains a
language.

* **MS 408 is undeciphered.** No proposed solution is accepted. This repo claims none.
* **Inputs are a model.** A transcription fixes glyph identities and word spaces by human judgement.
  A "token" is a blank-delimited chunk, not a proven word; a "unit" (after segmentation) is not a
  proven letter. Alternative readings and uncertain spaces are kept as data; the default analysis
  uses the first-listed reading and treats uncertain spaces as word spaces (the opposite choice is
  reported side by side).
* **Language-like numbers are weak evidence.** Zipf-like rank–frequency, a Heaps exponent below 1,
  low conditional entropy and a clean vowel/consonant split have been reproduced by meaningless text
  generators, hand-made gibberish and some ciphers (see `PRIOR_WORK.md`). No control corpora (Latin,
  Italian, Hebrew, shuffled text, cipher or gibberish generators) have been run yet, so these numbers
  cannot currently discriminate between hypotheses. That is Stages 5/10 of `WORKFLOW.md`.
* **Sukhotin's algorithm** only proposes which units behave like "vowels" *distributionally*. It is run
  after segmentation (raw EVA calls `h` a vowel purely because `ch`/`sh` are split) and its labels are
  reported with page-bootstrap stability. Treat the labels as hypotheses; nothing is claimed about
  phonetic values.
* **No word classes.** Nothing here labels any token as a verb, noun, name or any other category; that
  belongs to a later stage and would need the validation gates of `WORKFLOW.md` Stage 12.
* **Pseudo-replication.** Pages and lines are not independent samples; the only uncertainty
  estimates computed so far are a page bootstrap (Sukhotin) and a page-label permutation (A vs B).
  Quire-level resampling is future work.
* **Currier A/B** comes from the transcription's `$L` page variable (derived from Currier's own
  classification), so A-vs-B differences are a consistency check, not an independent finding.
* **Replication** on `IT2a` and `RF1b` is shown; an effect present in only one transcription is to be
  treated as a transcription artefact.

Regenerate every number with `python -m msdecipher run-all`.
