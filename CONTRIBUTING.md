# Contributing

Thanks for helping study the Voynich manuscript (MS 408). Ground rules: **no claimed translation without a test that could fail**, and every result reported with its null.

## Setup
`pip install -e ".[dev]"`, `python -m msdecipher fetch`, `python -m pytest`.

## Adding a hypothesis
1. Open a "New hypothesis" issue first.
2. Create `hypotheses/hNN_short_name/` with `README.md`, `run_hNN.py`, `test_hNN.py`, `results/`.
3. **Pre-register**: commit `PREREG.md` *before* computing, stating:
   - claim and prediction; metric; null model(s) (keep hand and quire fixed where relevant); multiple-testing correction; pass/fail rule.
4. Run, then report verdict, numbers and caveats in the README, and add a row to `FINDINGS.md` (keep existing content).
5. Tests: unit tests for new functions; real-data tests may skip if data is missing.

## Research log
Every PR that adds or changes analysis must add (or update) an entry in [RESEARCH_LOG.md](RESEARCH_LOG.md), following its "How to add an entry" note, and must update its Dead ends / Open leads summary if the verdict changes them.

## Pull requests
Small, focused PRs. Do not commit transcription files or rendered page images (git-ignored). Use the PR template.

Be kind; see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
