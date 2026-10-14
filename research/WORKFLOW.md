# Computational decipherment workflow — Beinecke MS 408 ("Voynich manuscript")

> **Status statement (read first).**
> Beinecke MS 408 is **undeciphered**. No proposed solution (language, cipher, or "it is gibberish") is accepted by the scholarly community, and Yale's own page says cryptographic approaches "have failed to decipher the text, if it is indeed encoded" (https://beinecke.library.yale.edu/beinecke/collections/beinecke-cipher-voynich-manuscript).
> This repository is a **research framework**: a set of reproducible stages for *measuring* the text, *testing* hypotheses against explicit null models, and *refusing to over-claim*. It is **not** a translation and must never output one as a result. Any "reading" produced by a later stage is a *hypothesis under test*, not a finding, until it passes the gates in Stage 12.

Date of survey: 11 Oct 2026 (Europe/Warsaw). Companion files: `PRIOR_WORK.md` (survey, links), `DATA_SOURCES.md` (corpora, download URLs, licences).
Reference keys like **[BL21]** are defined in `PRIOR_WORK.md`.

---

## 0. Big picture

```
 PDF/IIIF images ──► S1 page index ──► S3b visual glyph catalogue ─┐
                                                                    ├─► S4 units/tokens ─► S5 global stats
 IVTFF transcriptions ─► S2 harmonise ─► S3a glyph stats ───────────┘            │
                                                                                 ▼
   S9 cribs/anchors ◄─ S8 sections/hands/images ◄─ S7 word classes+syntax ◄─ S6 intra-word structure
        │                                                                        
        └──────────────► S10 generative nulls vs. models ─► S11 candidate-plaintext attacks ─► S12 gates ─► S13 repro
```

Key lessons from the literature that shape the design (details in `PRIOR_WORK.md`):

1. **Do not assume the units.** An EVA glyph is not proven to be a letter, a blank-delimited token is not proven to be a word, and a space is not proven to be a word boundary [RT26-preprint]. Stage 4 therefore treats units as hypotheses.
2. **Statistical "language-likeness" is not evidence of meaning.** Zipf-like frequencies, topic-like keyword clustering and low entropy have been reproduced by meaningless self-citation generators [TS20], by human-made gibberish [GB22], and by a hand-operable verbose cipher of real Latin/Italian [Gr25]. Every statistic must therefore be reported **against matched controls**, never in isolation.
3. **The text is heterogeneous.** Currier A/B "languages", ≥5 scribal hands, and sections correlate [Cu76][FD20][Za-intro]; pooling everything can create or hide effects. All stages stratify by section / hand / language and use quire- or bifolio-level resampling (pages are not independent).
4. **Transcription is itself a model.** Glyph identity and word-space decisions are subjective [Za-transcr]; results must be replicated on ≥2 independent transcriptions.

---

## Stage 0 — Ground rules, claim policy, pre-registration

**Objective.** Make the project falsifiable before any analysis is run.

**Inputs → outputs.** Nothing → `docs/CLAIMS_POLICY.md`, `ledger/hypotheses.yaml` (one entry per hypothesis: statement, units assumed, data subset, test, null model, success/failure thresholds, date registered, result, status).

**Methods.**
- Write each hypothesis *and its failure condition* into the ledger **before** looking at the result (pre-registration, even if informal; commit-hash timestamp is enough).
- Split data once: a **development** set (e.g. herbal A + herbal B quires) and a **held-out** set (e.g. recipes/"stars" quire, pharmaceutical, biological). Held-out quires are touched only by Stage 12.
- Multiple-comparison control: record how many hypotheses/mappings were tried (see Stage 11: search-space size matters for any claimed match).
- Language policy: results are reported as "consistent with / inconsistent with"; the word "decipherment" is reserved for a mapping that passes Stage 12 gates.

**Python.** `pyyaml`, `git`, `pre-commit`.

**Sketch.**
```yaml
# ledger/hypotheses.yaml
- id: H012
  registered: 2026-10-11
  statement: "Word-final glyph classes carry inflection-like information (abjad-like end-class)."
  units: {glyph: EVA-collapsed, token: ZL-certain-spaces}
  data: dev_split
  test: "HMM-2state (Baum-Welch) final-glyph separation vs. matched controls"
  null: [shuffled_within_token, naibbe_latin, selfcitation_generator, latin_vulgata]
  success: "separation score > 95th pct of nulls on dev AND on held-out"
  failure: "within null range on held-out"
  status: open
```

**Success / falsification.** Every later claim must trace to a ledger entry; any claim without one is excluded from reports.

**References.** Pre-registration practice (general); [RT26-preprint] for the explicit "unit names must follow validation" stance.

---

## Stage 1 — Image acquisition and page indexing

**Objective.** Hold the primary evidence (images) locally and map every image to a folio id used by transcriptions.

**Inputs → outputs.** `source/2002046.pdf` (Yale Digital Collections PDF, 214 pages, images only — no embedded transcription; text exists only in metadata/captions) → `data/images/page_####.png` (lossless, 300–400 dpi), `data/page_index.csv` (pdf_page ↔ folio id like `f17r`, `f70v2`, `fRos`; quire; bifolio; illustration type; fold-outs).

**Methods.**
- Extract page images with `pdfimages -all` (poppler, preserves original JPEG/JP2) rather than re-rasterising; verify DPI.
- Build the folio map from (a) the Beinecke catalogue/foliation, (b) the `$Q $P $I` page variables in IVTFF files, (c) manual check of fold-outs (f67–f73 zodiac/cosmological, `fRos`, f85–f86). Missing leaves (≈14) mean pdf-page index ≠ folio number.
- Prefer the IIIF manifest for the highest-resolution per-folio images if the PDF is downsampled (Yale Digital Collections exposes IIIF; see `DATA_SOURCES.md`). **Check the item's rights statement before redistributing images**; keep images out of git (use DVC/LFS or a download script).
- Image preprocessing for glyph work: colour-channel selection (ink vs. vellum), illumination flattening, deskew, binarisation (Sauvola), removal of painted/drawing layers (e.g. U-Net text/non-text segmentation). Voynich.nu notes that "processed text-only scans" are a stated need for OCR [Za-transcr].

**Python.** `pdf2image`/`pypdfium2`, `opencv-python`, `scikit-image`, `Pillow`, `pandas`, `requests` (IIIF), `torch` (optional segmentation).

**Sketch.**
```python
import subprocess, pathlib, pandas as pd
pathlib.Path("data/images").mkdir(parents=True, exist_ok=True)
subprocess.run(["pdfimages","-all","source/2002046.pdf","data/images/raw"], check=True)
subprocess.run(["pdfinfo","source/2002046.pdf"])          # sanity: pages, producer
# page_index.csv is hand-curated once, then validated:
idx = pd.read_csv("data/page_index.csv")
assert idx.folio.is_unique and len(idx) <= 214
```

**Success / falsification.** Every folio with transcribed text in the reference transliteration (ZL: 5385 loci) maps to exactly one image; spot-check 20 random loci visually. Failure = unmapped folios or mismatched order (stop; fix before Stage 3b).

**References.** Beinecke Voynich page and Yale IIIF notes (DATA_SOURCES.md); voynich.nu transliteration page [Za-transcr].

---

## Stage 2 — Transliteration ingestion and harmonisation

**Objective.** Get clean, versioned, machine-readable text (loci with metadata) from **several independent transcribers**, so every later result can be replicated across them.

**Inputs → outputs.** IVTFF 2.0 files (ZL 3b, GC/v101 2a, IT 2a, RF 1b, CD, FG; see `DATA_SOURCES.md`) → `data/processed/{ZL,GC,IT,RF}.parquet` with columns: `folio, locus_n, locus_type (P0/Pb/L*/C*/R*), text_raw, text_clean, tokens, uncertain_space_positions, page_vars (Q,P,I,L,H,C), source`.

**Methods.**
- Parse IVTFF: page lines `<f17r> <! $Q=.. $L=A $H=1>`; locus lines `<f1r.2,+P0>`; `.` certain space, `,` uncertain space, `{..}` ligature, `[a:o]` alternatives, `@nnn;` high-ASCII rare glyph, `?` illegible, `<!comment>`, `<%>/<$>` paragraph start/end, `<->` drawing intrusion = space [IVTFF]. Locus types P (running text), L (labels), C (circular), R (radial).
- Keep **alternative readings and uncertain spaces as data**, not noise (they are evidence for Stage 4).
- Convert alphabets with Zandbergen's `bitrans` rules (EVA ↔ v101 ↔ STA ↔ Currier/FSG) or the `ivtt` tool for filtering; do *not* hand-roll alphabet conversions.
- Build an alignment between transcriptions (line-level, then token-level) and compute **inter-transcriber agreement** (token exact match, glyph-level edit distance, Cohen's κ for uncertain spaces). Use the Reference transliteration (RF, built from ZL+GC) for coverage checks.
- Do not mix in the later hand additions (e.g. f1r margin key by a later owner, month names on zodiac pages, f116v pseudo-Latin/German) — they are tagged/commented in IVTFF; keep them in a separate `extraneous` table.

**Python.** `re`, `pandas`, `pyarrow`, `rapidfuzz`/`python-Levenshtein`, `biopython`-style `pairwise2` or `edlib` for alignment; C tools `ivtt`, `bitrans` via `subprocess`.

**Sketch (smoke-tested against ZL3b: yields 5385 loci; Currier-A top token `daiin`, B top token `chedy`).**
```python
import re
LOCUS = re.compile(r"^<(?P<folio>f[0-9A-Za-z]+)\.(?P<n>\d+),(?P<flag>[@+*=&~/-])?"
                   r"(?P<type>[A-Z][0-9a-z]?)(?:;(?P<src>\w))?>\s+(?P<text>.*)$")
PAGE  = re.compile(r"^<(?P<folio>f[0-9A-Za-z]+)>\s+<!\s*(?P<vars>.*)>")

def parse_ivtff(lines):
    pv, rows = {}, []
    for line in lines:
        line = line.rstrip("\n")
        if not line or line.startswith("#"): continue
        if (m := PAGE.match(line)):
            pv[m["folio"]] = {k.lstrip("$"): v for k, v in
                              (kv.split("=") for kv in m["vars"].split() if "=" in kv)}
        elif (m := LOCUS.match(line)):
            rows.append(dict(folio=m["folio"], n=int(m["n"]), type=m["type"],
                             raw=m["text"], page=pv.get(m["folio"], {})))
    return rows

def clean(t):                       # keep first alternative; drop comments/ligature braces
    t = re.sub(r"<![^>]*>", "", t)
    t = re.sub(r"<[%$~-]>", ".", t)
    t = re.sub(r"\[([^\]:]+)(?::[^\]]*)?\]", r"\1", t)
    t = re.sub(r"[{}]", "", t)
    t = re.sub(r"@\d+;", "?", t)
    return t.strip(".")

def tokens(row):                    # '.' and ',' both split; keep the distinction elsewhere
    return [w for w in re.split(r"[.,]+", clean(row["raw"])) if w and "?" not in w]
```
(Known gotcha: locus flags include `~` and `/`; the first draft that omitted them mis-parsed 11 loci.)

**Success / falsification.** Parsed locus count equals the file header/IVTFF inventory (5385 for ZL 3b: P 4130, L 1029, C 84, R 142). Inter-transcriber token agreement and κ for uncertain spaces are reported; if a downstream effect appears in only one transcription, it is treated as a **transcription artefact until shown otherwise**.

**References.** [Za-transcr], [Za-sp], [IVTFF], [Re95], [LSI]; Currier/D'Imperio [Cu76][DI78].

---

## Stage 3 — Recognise and catalogue all glyphs ("letters")

You asked for step 1 = *recognise and catalogue all letters used*. This has two complementary halves.

### 3a. Catalogue from transcriptions (fast, available now)

**Objective.** Inventory of glyph types and their distributional behaviour.

**Inputs → outputs.** Stage-2 tables → `results/glyphs/inventory.csv` (glyph, count, share, rank, first/last/medial share, line-initial / paragraph-initial share, per-section & per-hand counts, co-occurrence with gallows, bigram partners), `results/glyphs/rare_glyphs.csv` (Extended-EVA high-ASCII codes, hapax glyphs).

**Methods.**
- Frequency + **positional distribution** (initial / medial / final within token; line-initial; paragraph-initial — gallows are strongly enriched at paragraph starts [Za-writing][RT26-preprint]).
- Family structure: Basic EVA (~25 frequent symbols), "weirdoes"/rare glyphs (Reeds X1–X128 → Extended EVA, STA families) [Za-transcr]. Use the STA family/member scheme to compare transcribers without forcing a single glyph alphabet.
- Candidate **composite units** (ch, sh, cth/ckh/cph/cfh, ee, in/iin/ain…) are *flagged*, not merged, here; merging happens in Stage 4.
- Compare inventories across sections/hands (Currier A vs B; Fagin Davis hands 1–5) with χ² / Jensen–Shannon divergence and bootstrap over quires.

**Python.** `collections.Counter`, `pandas`, `scipy.stats`, `numpy`.

**Sketch.**
```python
import pandas as pd, collections
def glyph_table(token_lists):                 # token_lists: list[list[str]]
    tot, ini, fin, med = (collections.Counter() for _ in range(4))
    for toks in token_lists:
        for w in toks:
            for i, g in enumerate(w):
                tot[g] += 1
                (ini if i == 0 else fin if i == len(w)-1 else med)[g] += 1
    df = pd.DataFrame({"n": tot, "initial": ini, "medial": med, "final": fin}).fillna(0)
    for c in ("initial", "medial", "final"): df[c] /= df["n"]
    return df.sort_values("n", ascending=False)
```

### 3b. Catalogue from the images (independent of any transcriber)

**Objective.** Test whether the transcribers' glyph categories (and the "how many letterforms are there?" question) are supported by the pixels. This is the only stage that can *correct* the input alphabet.

**Inputs → outputs.** Cleaned page images + approximate line/word boxes (from voynichese.com coordinates, from Stage-1 text segmentation, or from semi-automatic line finding) → `data/glyph_crops/*.png`, `results/glyphs/visual_clusters.csv` (crop id, folio, hand, cluster id, nearest transcribed glyph), confusion matrix *visual cluster × EVA/v101 glyph*.

**Methods.**
1. Line detection → connected-component / stroke-skeleton analysis (many Voynich glyphs are ligatured; Zandbergen's "aaa" stroke alphabet is a stroke-level intermediate representation [Za-sp]).
2. Glyph/word segmentation: assisted OCR — align a reference transliteration (RF) to the image, then refine boundaries (Zandbergen's "assisted OCR" programme is exactly this [Za-sp]).
3. Feature extraction: HOG/shape context, or self-supervised embeddings (SimCLR/DINO on crops); cluster with HDBSCAN/GMM; visualise with UMAP.
4. Compare clusters to transcription labels per **scribal hand** (Fagin Davis used Archetype/DigiPal and glyph-specific traits such as [k], [n]-finial, gallows loops to separate hands [FD20][FD22]); within-hand variation vs. between-hand variation separates "different letter" from "different scribe".
5. Treat uncertain-space gaps as measurable physical quantities (box-gap analysis shows "uncertain" separators are physically narrower [RT26-preprint]); output a per-gap *continuous* spacing feature for Stage 4.

**Python.** `opencv-python`, `scikit-image`, `torch`/`torchvision`, `timm`, `scikit-learn`, `hdbscan`, `umap-learn`, `matplotlib`; optional `kraken`/`Transkribus` for line segmentation (note: no trained model exists for this script; expect to train/annotate).

**Sketch.**
```python
import numpy as np, cv2
from sklearn.cluster import HDBSCAN
from sklearn.preprocessing import StandardScaler
def hog_feat(img):  # img: 32x32 uint8 glyph crop
    hog = cv2.HOGDescriptor((32,32),(16,16),(8,8),(8,8),9)
    return hog.compute(img).ravel()
X = StandardScaler().fit_transform(np.stack([hog_feat(c) for c in crops]))
labels = HDBSCAN(min_cluster_size=25).fit_predict(X)
# then: pd.crosstab(labels, eva_label_of_crop, normalize="columns")
```

**Success / falsification.**
- *Supported:* visual clusters map ≥ ~90% purely onto transcription glyph classes for frequent glyphs, and the rare-glyph set is stable across hands.
- *Falsified / revise:* a transcription class splits into two stable visual clusters that co-vary with context (not with hand) → candidate *new letter*; two classes merge visually → candidate *allograph*. Report cluster stability (ARI over resampled crops) and inter-hand effects. Do not change the working alphabet without a ledger entry.

**References.** [FD20][FD22] (hands, glyph traits), [Za-sp] (STA, aaa, assisted OCR), [Za-writing] (character set, gallows, initials, rare chars), [Re95], [DI78].

---

## Stage 4 — Unit and token segmentation: what are the "letters" and "words"?

**Objective.** Decide, *empirically and with controls*, the working analytical units; produce several alternative segmentations rather than one.

**Inputs → outputs.** Stage-2 tokens + Stage-3 glyph classes + per-gap spacing feature → `data/processed/segmentations/{eva_glyph, eva_collapsed, bpe64, slot12, space_erased_bpe}.parquet`.

**Methods.**
- *Glyph-level alternatives:* raw EVA characters; **collapsed composites** (ch, sh, cth, ckh, cph, cfh, ee, iin, in); Zattera's 12-slot alphabet [Ze22]; strokes (aaa).
- *Data-driven units:* byte-pair encoding (BPE) / Morfessor / unigram-LM within tokens; track the **conditional-dependence gap** D_k = H(U_k) − H(U_{k,t+1}|U_{k,t}) across merge counts k — a trough around k≈32–64 has been reported [RT26-preprint] (verbose and homophonic ciphers also produce one, so it is a *descriptor*, not a diagnosis).
- *Token-level alternatives:* certain spaces only; certain+uncertain; spaces erased and re-learned (test whether learned units cross the "certain" spaces: they rarely do, but cross "uncertain" ones far more often [RT26-preprint]).
- Report all downstream stages **on each segmentation**; an effect that exists in only one is flagged.

**Python.** `sentencepiece`, `tokenizers`, `morfessor`, `numpy`, `pandas`.

**Sketch.**
```python
import math, collections
def H(c): n = sum(c.values()); return -sum(v/n*math.log2(v/n) for v in c.values())
def dep_gap(unit_seqs):                      # unit_seqs: list[list[unit]] (within-token, no cross-space pairs)
    uni, pair, first = collections.Counter(), collections.Counter(), collections.Counter()
    for s in unit_seqs:
        uni.update(s)
        for a, b in zip(s, s[1:]): pair[(a, b)] += 1; first[a] += 1
    return H(uni) - (H(pair) - H(first))     # marginal minus conditional entropy
# k sweep: learn BPE merges on glyph strings, apply, compute dep_gap; compare to Latin/Italian + Naibbe + self-citation controls
```

**Success / falsification.** A unit hypothesis "survives" if (i) it is stable under quire-level cross-fitting (learn on N−1 quires, score on the held-out one), (ii) it separates the manuscript from matched shuffled/random-boundary controls, and (iii) it holds on ≥2 transcriptions. It is falsified if the optimum merge count or boundary behaviour changes with transcriber or with held-out quire.

**References.** [RT26-preprint], [Ze22], [St00], [Se16], [Za-sp].

---

## Stage 5 — Global statistics: frequency, Zipf, Heaps, entropy, compression, burstiness

**Objective.** Quantify properties usually used to argue "language vs. not-language" — and calibrate what each can and cannot show.

**Inputs → outputs.** Segmentations + control corpora (`DATA_SOURCES.md`: Latin/Italian/German/Hebrew/Arabic/Chinese-pinyin texts, Vulgate, herbals; matched in token count and line template) → `results/stats/summary.csv`, plots.

**Methods and metrics.**
- Rank-frequency (Zipf exponent via MLE for power laws, not OLS on log-log; compare with `powerlaw`/Clauset method), Heaps' exponent β (vocabulary growth), hapax share, type/token ratio, top-50 coverage.
- Entropies: H₁ (unigram), **conditional** h₂ = H(X_{t+1}|X_t), h₃; word-level H; Miller–Madow or NSB bias correction; length-matched windows. Known: Voynichese character conditional entropy is unusually low versus Latin/Italian/English (≈2.7 bits vs ≈3.5, composite-collapsed EVA) [RT26-preprint][LB20], while word entropy is not anomalous (≈9.9 bits/word for the stars section, between Dante and Pliny) [Za-ent].
- Compression ratio (gzip/bz2/PPM/`zstandard`) as a model-free check.
- Repetition metrics: immediate word repeats, triple repeats, edit-distance-1 neighbours (self-citation signature) [TS20][GB22].
- Word-length distribution & **length autocorrelation** (positive in Voynichese and in gibberish; negative in most natural languages) [GB22].
- Burstiness / long-range structure: per-word dispersion, Montemurro–Zanette entropy-based keyword detection (information in the *ordering* of words vs. shuffled text; reported optimal scale ≈800 words) [MZ13], Amancio et al. word-network + intermittency measures [Am13].
- Section/Currier-stratified versions of all of the above.

**Python.** `numpy`, `scipy`, `powerlaw`, `statsmodels`, `networkx`, `zstandard`, `nltk`.

**Sketch (smoke-tested on ZL3b P0 tokens: Zipf slope ≈ −1.10 for ranks 10–1000, Heaps β ≈ 0.72 — OLS shown only as a quick look).**
```python
import math, collections, random
def mi(pairs):
    j = collections.Counter(pairs); a = collections.Counter(p[0] for p in pairs)
    b = collections.Counter(p[1] for p in pairs); n = len(pairs)
    return sum(v/n * math.log2(v*n/(a[x]*b[y])) for (x, y), v in j.items())
def cap(lines, k=2000):                      # cap vocabulary (rest -> <UNK>) to tame plug-in bias
    top = {w for w, _ in collections.Counter(w for l in lines for w in l).most_common(k)}
    return [[w if w in top else "<UNK>" for w in l] for l in lines]
def adjacent_order_excess(lines, nshuf=100, seed=1):
    L = cap(lines); big = lambda ls: [(a, b) for l in ls for a, b in zip(l, l[1:])]
    obs = mi(big(L)); rng = random.Random(seed)
    sh = [mi(big([rng.sample(l, len(l)) for l in L])) for _ in range(nshuf)]
    return obs - sum(sh)/len(sh)             # bits beyond within-line-shuffle baseline
```
Smoke test (ZL3b, P0 lines, 2000-type cap, 30 shuffles): excess ≈ 0.08 bits, i.e. small — consistent in magnitude with the ≈0.066 bits (0.79% of token entropy) reported by [RT26-preprint], far below prose controls (2–10%).

**Success / falsification.** *Not* "pass/fail for language". Output is a **profile**: each metric with CI (bootstrap over quires), alongside controls (natural-language prose, catalogue/herbal text, gibberish, Naibbe cipher output, self-citation output). A proposed generative or linguistic model must reproduce the *whole profile* (see Stage 10). Metrics that all controls (cipher + generator) also reproduce are marked **non-discriminating**.

**References.** [Be76], [Za-ent], [LB20], [MZ13], [Am13], [GB22], [BG22], [TS20], [RK11].

---

## Stage 6 — Intra-word structure: positional, morphological, vowel/consonant

**Objective.** Describe the internal grammar of tokens ("how words are built") without assuming a language.

**Inputs → outputs.** Segmentations → `results/morph/slot_grammar.json`, `results/morph/affixes.csv`, `results/morph/char_classes.csv`.

**Methods.**
- **Slot / layer grammars** (reproduce, then test): Stolfi's crust–mantle–core model (word ≈ crust-prefix · mantle-prefix · core(gallows) · mantle-suffix · crust-suffix; ~75% whole-crust words) [St00]; earlier prefix–midfix–suffix with "soft/hard" letters [St97]; Zattera's 12-slot alphabet (86.6% of tokens fit) [Ze22]. Evaluate: coverage on held-out quires, generative perplexity, and how many *non-words* the grammar over-generates (grammars with millions of admissible strings fit trivially [RT26-preprint]).
- **Affix/morpheme discovery:** Morfessor Baseline/FlatCat; Harris' successor-variety; suffix-stripping curves; compare to Latin/Hebrew/Arabic controls. Look for paradigm-like families (e.g. `-edy / -ody / -ey`, `qo-` prefix, `-aiin / -ain / -iin`).
- **Character-class induction:** Sukhotin's algorithm (vowel/consonant) and 2–5 state HMMs trained with Baum–Welch on *units* [Su-Gu91][RK11][CN80]. Reddy & Knight found final characters cluster separately (abjad-like hint) [RK11]. *Smoke test:* Sukhotin on raw EVA tokens (ZL3b P0) returns `o, h, a, y, n, g, b, u` as "vowels" — `h` appears only because `ch`/`sh` are un-collapsed digraph glyphs, a concrete demonstration of why Stage 4 must precede Stage 6 and why outputs are hypotheses.
- Positional effects: line-initial, line-final, paragraph-initial (gallows), "line as a unit" effects, cross-boundary glyph coupling (last glyph of token t ↔ first glyph of t+1; ≈0.2 bits, mostly `y→q`) [Cu76][RT26-preprint]. Control for line-length confounds (short lines at paragraph ends bias estimates) [RT26-preprint].
- Currier A/B contrasts at sub-word level (e.g. `qo-`/`-edy` frequent in B; `-aiin`, `ot-`/`ol-` patterns different) [Cu76][Za-intro][St-AxB].

**Python.** `morfessor`, `hmmlearn` (or hand-rolled Baum–Welch with `numpy`), `networkx`, `scikit-learn`, `pomegranate`.

**Sketch.**
```python
import numpy as np
from hmmlearn.hmm import CategoricalHMM
def fit_char_hmm(words, alphabet, n_states=2, seeds=range(10)):
    idx = {c: i for i, c in enumerate(alphabet)}
    X = np.array([idx[c] for w in words for c in "^"+w+"$"]).reshape(-1, 1)   # '^','$' in alphabet
    lens = [len(w)+2 for w in words]
    best = max((CategoricalHMM(n_components=n_states, n_iter=200, random_state=s).fit(X, lens)
                for s in seeds), key=lambda m: m.score(X, lens))
    return best.emissionprob_          # inspect which glyphs load on which hidden class
```

**Success / falsification.**
- A word-structure model is *supported* if it predicts held-out-quire tokens (coverage and per-glyph cross-entropy) better than a unigram/order-k Markov baseline *and* better than the controls' fitted models at equal parameter count.
- Vowel/consonant or abjad claims are supported only if they replicate across transcriptions/segmentations and across Currier A and B, and are **absent** in shuffled-within-token controls. They are falsified if class assignments are unstable across HMM seeds or flip under glyph-collapse (as the `h` example shows).

**References.** [St00][St97][Ze22][RK11][Cu76][Za-intro][Su-Gu91].

---

## Stage 7 — Word-class induction and sentence structure (verbs, names, nouns, function words)

You asked for step 2 = *use logic to understand verbs, names and other categories of text and sentences*. Without a known language, "verb" and "name" cannot be *identified*, only **hypothesised from distributional behaviour** and later checked against cribs (Stage 9). This stage generates *testable classes*.

**Objective.** Partition tokens (or token-types) into distributional classes and describe their syntax-like behaviour, then test whether the structure is language-like.

**Inputs → outputs.** Token sequences with locus type/section → `results/classes/word_clusters.parquet` (token → cluster; stability scores), `results/classes/class_transition_matrix.csv`, `results/classes/candidate_roles.md` (clusters labelled only by *behavioural* tags, e.g. "high-frequency, position-initial, evenly distributed across pages" = candidate function words).

**Methods.**
1. **Frequency-tier bands:** top ~50 types (candidate function/closed-class items: evenly distributed across pages/sections, weakly topic-dependent) vs. mid-frequency, topic-bursty types (candidate content words) vs. hapax tail (candidate names/rare nouns/inflectional variants). Dispersion statistics: Juilland's D, Gries' DP, TF-IDF "spikiness", Montemurro–Zanette keyword information [MZ13], and "special words" per page [St-sw].
2. **Distributional clustering:** left/right-context vectors → Brown clustering; HMM/Bayesian POS induction (e.g. Gibbs-sampled HMM with Dirichlet priors); k-means/GMM on PPMI-SVD embeddings; `word2vec`/fastText on units (tiny corpus ≈35k tokens → use only high-frequency types, bootstrapped; report stability, e.g. adjusted Rand index across resamples and across Currier A/B).
3. **Morphology-aware classes:** group tokens by shared stems under Stage-6 affix analysis; test whether suffix/prefix families behave like inflectional paradigms (consistent class transition behaviour per suffix).
4. **Syntax-like structure:** token-class bigram/trigram models; entropy of class sequence vs. token sequence; long-range dependency (mutual information vs. distance, compared with shuffled and with controls); line/paragraph-initial and -final class biases; test "is word order informative at all?" using within-line shuffles (adjacent identity order ≈0.8% of token entropy vs 2–10% in prose controls [RT26-preprint]; Reddy–Knight found weak word-order predictability and page-order continuity [RK11]).
5. **Name-like candidates:** types that are (i) rare, (ii) clustered on a single page/section, (iii) occur as *labels* near an illustration and recur in the running text of the same page. Existing label/text-co-occurrence work: Stolfi's "Name of the Sunflower", label occurrence maps, f77v labels [St-labels].
6. **Unit sensitivity:** repeat on each Stage-4 segmentation. Because adjacent-token *identity* carries so little information while *edge glyphs* are strongly coupled [RT26-preprint], class induction on whole-token identity may be the wrong scale — also run it at morph/unit level.

**Python.** `scikit-learn`, `gensim`, `nltk`, `brown-clustering`/`wcluster`, `hmmlearn`, `pymc`/`numpyro` (Bayesian HMM), `networkx`, `scipy`.

**Sketch.**
```python
import numpy as np, collections
from sklearn.decomposition import TruncatedSVD
from sklearn.cluster import KMeans
def ppmi_context_matrix(lines, vocab, window=1):
    idx = {w:i for i,w in enumerate(vocab)}
    C = np.zeros((len(vocab), 2*len(vocab)))           # left ⊕ right contexts
    for l in lines:
        for i, w in enumerate(l):
            if w not in idx: continue
            if i > 0 and l[i-1] in idx:   C[idx[w], idx[l[i-1]]] += 1
            if i+1 < len(l) and l[i+1] in idx: C[idx[w], len(vocab)+idx[l[i+1]]] += 1
    tot = C.sum(); pw = C.sum(1, keepdims=True)/tot; pc = C.sum(0, keepdims=True)/tot
    with np.errstate(divide="ignore", invalid="ignore"):
        P = np.maximum(np.log((C/tot)/(pw@pc)), 0); P[~np.isfinite(P)] = 0
    return P
vocab = [w for w,_ in collections.Counter(w for l in lines for w in l).most_common(300)]
Z = TruncatedSVD(20, random_state=0).fit_transform(ppmi_context_matrix(lines, vocab))
clusters = KMeans(8, n_init=20, random_state=0).fit_predict(Z)   # then: stability via bootstrap ARI
```
(Untested sketch.)

**Success / falsification.**
- Clusters count as *real* only if stable (ARI ≥ ~0.6 under bootstrap over quires; replicate on a second transcription; replicate in both Currier A and B or differ in an interpretable, pre-registered way).
- Class-based sequence models must beat unclustered baselines on held-out quires.
- "Syntax" is *not supported* if class bigram structure is no stronger than in shuffled-within-line controls; "language-like word order" is *not supported* where the manuscript's adjacent-order excess sits below every prose control (as currently reported), though lists, labels and formulaic text can legitimately have weak order [RT26-preprint] — so this alone is not evidence of meaninglessness.
- Never label a cluster "verb"/"name" in a results table; use behavioural tags. Semantic labels belong only in Stage 9/11 hypothesis entries.

**References.** [RK11][MZ13][Am13][St-sw][St-labels][RT26-preprint][Br92], [RK11b]; for unsupervised POS induction in low-resource settings, standard NLP references (Goldwater & Griffiths 2007, Clark 2003) — *not re-verified this session*.

---

## Stage 8 — Document structure: sections, hands, Currier A/B, topics, text–image relationship

**Objective.** Establish the macro-structure that all other stages must stratify on; test whether text correlates with illustrations.

**Inputs → outputs.** Page-level feature vectors (char/bigram/token frequencies; slot-grammar usage), page metadata ($I illustration type, $L Currier language, $H Fagin Davis hand, $Q quire) → `results/structure/page_clusters.csv`, `results/structure/section_similarity.png`, `results/structure/topic_model.json`.

**Methods.**
- **Page clustering:** hierarchical/spectral clustering over page-level distributions; compare clusters with Currier A/B [Cu76], Zandbergen's RZ languages A/B/C (2024 reclassification) [Za-intro], Zattera's per-section slot grammars (classify pages from four short character sequences) [Ze22], and Fagin Davis hands 1–5 (split along bifolios, with three documented exceptions) [FD20][Za-writing]. Quantify how much of the A/B split is explained by *hand*, *section/topic*, *date of writing* — they are confounded [RT26-preprint].
- **Topic modelling:** LDA / NMF / BERTopic-style over page bags-of-tokens; is page similarity higher within illustration sections than across? (Reddy–Knight: yes, within sections, and adjacent pages are more similar than random order; Montemurro–Zanette: Herbal–Pharmaceutical strongest linkage, Recipes–Astrological also linked [RK11][MZ13].) Test with page-order permutation.
- **Text–image link tests:**
  - *Labels ↔ nearby text:* are label tokens over-represented on their own page's running text? [St-labels]
  - *Plant labels / herbal pages:* does vocabulary similarity track *visual* plant similarity (e.g. image-embedding distance between plant drawings vs. text-distance between pages)? A positive result would be one of the few independent, non-circular links.
  - *Zodiac/star pages:* labels vs. zodiac icon count and order; month names written later in a Romance (northern French) hand are *not* Voynichese and must be excluded from the corpus [Za-writing].
- **Codicology as covariate:** quire, bifolio, missing leaves, ink changes, later additions (f1r margin key, f116v) — include as nuisance variables.

**Python.** `scikit-learn`, `gensim`/`bertopic`, `scipy.cluster`, `umap-learn`, `torch`/`open_clip` for plant-image embeddings, `statsmodels` (mixed-effects with quire random effect).

**Sketch.**
```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import adjusted_rand_score
from scipy.cluster.hierarchy import linkage, fcluster
pages = {f: " ".join(toks) for f, toks in tokens_by_folio.items()}      # herbal+bio+... pages
X = TfidfVectorizer(token_pattern=r"\S+", min_df=3, sublinear_tf=True).fit_transform(pages.values())
Zl = linkage(X.toarray(), "ward"); c = fcluster(Zl, t=6, criterion="maxclust")
print(adjusted_rand_score(c, [meta[f]["I"] for f in pages]),        # vs. illustration type
      adjusted_rand_score(c, [meta[f]["H"] for f in pages]))        # vs. scribal hand
```
(Untested sketch.)

**Success / falsification.** Page-order permutation and page-label permutation tests (with quire-block permutation to respect clustering). A text–image link is claimed only if it survives block-permutation and holds on both A and B text. If section/hand fully explain apparent "topic" structure, report that — it is itself a result.

**References.** [Cu76][FD20][FD22][Za-intro][Ze22][RK11][MZ13][Am13][GB22 (gibberish also has section-like word-placement biases)].

---

## Stage 9 — Cribs and anchors

**Objective.** List every *independent* handle into meaning, rank them by reliability, and avoid circular use.

**Inputs → outputs.** Locus table (label loci L*, circular/radial C*/R*), image annotations → `data/anchors/anchors.yaml`: each anchor = (source, folio/locus, Voynichese token(s), putative meaning, **independence rating**, risk).

**Candidate anchors (ranked by independence from the transcription).**
1. **Non-Voynichese writing on the pages** — month names in a later hand on the zodiac pages (`mars, aberil, may, jong, iollet, augst, septe(m)b(r), octe(m)bre, nove(m)bre, decebre`; northern-French-like) are *not* ciphertext, but they are **independent cleartext pairing months ↔ zodiac emblems ↔ adjacent Voynichese labels**. They date from a later hand, so they tell you what a *later reader* believed, not what the author wrote — rate as weak-to-moderate [Za-writing]. Colour annotations (`rot`, single letters) on early herbal pages and the f66r/f116v marginalia likewise.
2. **Label ↔ illustration pairs:** star labels, zodiac labels (299 Lz loci), nymph labels (Ln, 63), container/herb-fragment labels in the pharmaceutical section (Lc 40, Lf 194), whole-plant labels (Lp, only 3) [IVTFF/Za-sp]. Test if a *label's identity* is predictable from the *picture class* (e.g., 12 zodiac signs; repeated container shapes) better than chance → this tests whether labels are lexical at all.
3. **Repetition-structure cribs:** repeated paragraph-initial formulae, "titles" (last-line right/centre-justified), key-like sequences in margins; numerals (the f57v/f49v sequences) — structure only, no semantics.
4. **Plant identifications by art historians** (e.g. sunflower, capsicum claims) — highly disputed; treat as *low* independence and rate by identification quality, not by confidence of the claimant.
5. **Date/place of origin evidence** (radiocarbon on vellum: early 15th century; ink consistent; humanist-style handwriting; Central Europe per Yale) constrains *candidate plaintext languages* but not the mapping.

**Methods.** Pre-register each crib's *predicted* Voynichese outcome; then test with permutation (shuffle label↔picture assignment). Cribs must be used to **test** a mapping learned elsewhere, not to **fit** it, otherwise circular.

**Python.** `pandas`, `scipy.stats` (permutation tests), `numpy`.

**Sketch.**
```python
import random
def label_predictability(pairs, n_perm=10000, seed=0):    # pairs: [(picture_class, label_token)]
    def score(p):                                          # fraction of items whose token matches the modal token of their class
        by = {}; [by.setdefault(c, []).append(t) for c, t in p]
        return sum(max(map(ts.count, set(ts))) for ts in by.values()) / len(p)
    obs = score(pairs); toks = [t for _, t in pairs]; rng = random.Random(seed); ge = 0
    for _ in range(n_perm):
        rng.shuffle(toks); ge += score([(c, t) for (c, _), t in zip(pairs, toks)]) >= obs
    return obs, (ge+1)/(n_perm+1)
```
(Untested sketch.)

**Success / falsification.** An anchor is *validated* if its predicted token/picture association exceeds permutation null at p < 0.01 after correction across all anchors tried, and replicates in an independent transcription. Anchors that fail are removed from any model that used them.

**References.** [Za-writing] (extraneous writing, month names, colour annotations), [St-labels], [IVTFF], [Beinecke page], [FD20].

---

## Stage 10 — Generative-model hypothesis testing (nulls vs. cipher vs. language)

**Objective.** Compare *mechanisms* by whether they reproduce the entire Stage-5/6/7 profile — not any single statistic.

**Candidate mechanisms (each implemented as a text *generator* so it can be run through the identical pipeline):**
- **M0:** within-line / within-token shuffles; order-k Markov glyph generators (negative controls).
- **M1 — natural language, simple substitution:** *rejected as a one-to-one letter substitution of tested plaintexts* — conditional entropy invariant under relabelling and Voynichese h₂ is far below Latin/Italian/English [RT26-preprint][LB20]. Keep as a calibration control only.
- **M2 — verbose / homophonic / nulls / abbreviation / syllabic ciphers:** e.g. Greshko's Naibbe cipher (Latin/Italian → Voynich-like EVA, 15th-century hand-operable, code on GitHub) [Gr25]; Bowern & Gaskell's 22 transformations (bigraph merges and null insertion lower conditional entropy) [BG22].
- **M3 — meaningless but non-random text:** Rugg's grille/table method [Ru04], Schinner's stochastic model [Sc07], Timm–Schinner self-citation generator [TS20], human-written gibberish [GB22].
- **M4 — natural language in unknown/constructed script and idiolect** (phonetic "invented alphabet", e.g. proposals of an East-Asian-type syllabic language [St-Chinese]; proto-Romance claim [Ch19] — *criticised* [Ke19]); tested through Stage 11.
- **M5 — hybrid** (structured codebook + nulls + abbreviation).

**Inputs → outputs.** Source plaintexts for M2 (Latin/Italian/German/Hebrew/Arabic herbals, Vulgate, Pliny, Dioscorides translations; `DATA_SOURCES.md`) → `synthetic/<mechanism>/<seed>.ivtff`-like files → `results/profile/<mechanism>.csv`.

**Methods.**
- Run every generator through Stages 4–8 *unchanged*; build a **discrimination matrix**: rows = metrics, columns = (Voynich, M0…M5); colour cells where the mechanism's CI includes the manuscript's value.
- Rank mechanisms by how many metrics they reproduce **and** how many degrees of freedom were tuned (penalise tuned parameters, e.g. AIC/BIC-like or ABC / simulation-based inference; Approximate Bayesian Computation fits generator parameters to summary statistics, then checks held-out statistics).
- Metrics identified in the literature as *discriminating right now* between Voynichese and the best two imitators (Naibbe, self-citation): cross-token edge-glyph coupling (≈0.2 bits in the manuscript vs ≈0.006–0.009 for both imitators), hapax-rich vocabulary (≈70% singleton types vs 41% / 59–60%), the graded "uncertain-space" regime [RT26-preprint]. Treat these as **targets for any new model** (preprint; verify before relying on them).

**Python.** `numpy`, `scipy`, `pandas`, `abcpy`/`pymc` (ABC), `sbi`, `joblib` for parallel seeds.

**Sketch.**
```python
def profile(text_lines):                       # same function for manuscript and every generator
    return dict(h2=cond_entropy(text_lines), hapax=hapax_share(text_lines),
                adj_order=adjacent_order_excess(text_lines), edge=edge_info(text_lines),
                zipf=zipf_mle(text_lines), lenacf=word_len_autocorr(text_lines), gz=gzip_ratio(text_lines))
V = profile(voynich_lines)
for name, gen in generators.items():
    P = [profile(gen(seed=s)) for s in range(50)]
    report[name] = {k: (np.percentile([p[k] for p in P], [2.5, 97.5]), V[k]) for k in V}
```
(Untested sketch; `cond_entropy` etc. are the Stage-5 helpers.)

**Success / falsification.**
- A mechanism is **falsified** for a metric where the manuscript lies outside its 95% generator range on the held-out quires and under ≥2 transcriptions.
- Do **not** declare "it's gibberish" or "it's a cipher" from a partial match; as of the cited work, both a meaningless generator and a real-text cipher reproduce much of the standard profile, so the field remains open [BL21][GB22][BG22][TS20][Gr25].

**References.** [RT26-preprint], [Gr25], [TS20], [GB22], [BG22], [Sc07], [Ru04], [LB20], [BL21], [Ch19][Ke19].

---

## Stage 11 — Candidate-plaintext attacks (language identification, substitution/homophonic solving, anagram, cognate matching)

**Objective.** *If and only if* Stage 10 leaves a text-bearing hypothesis alive, search for a mapping to a candidate plaintext, with the **search-space penalty** made explicit.

**Inputs → outputs.** Stage-4 units, candidate language models (character n-gram LMs for Latin, medieval Latin with abbreviations, Italian, Occitan, German, Czech, Hebrew, Arabic, etc.; `DATA_SOURCES.md`) → `results/attacks/<hypothesis>/{mapping.json, decoded_sample.txt, score_table.csv}` — always written together with the **null-score distribution**.

**Methods.**
- **Language identification of the plaintext via structure, not letters:** Hauer & Kondrak (TACL 2016): identify language by *character-frequency/decomposition patterns invariant to substitution and anagramming*; on Voynich it ranked Hebrew first, but the authors state the output is not syntactically or semantically consistent and needs expert validation [HK16].
- **Substitution/homophonic solvers:** hill-climbing/simulated annealing with n-gram LM (Knight et al. 2006; Ravi & Knight 2011 Bayesian/EM for homophonic ciphers e.g. Zodiac), beam search; for lost-language decipherment, Snyder–Barzilay–Knight (2010) and Luo–Cao–Barzilay (2019, neural + min-cost flow for Ugaritic/Linear B) — these need a **known related language and cognate overlap**, which Voynich lacks, so apply only as methodology tests on known ciphers first [SBK10][LCB19].
- **Calibration is mandatory:** every solver is first run on synthetic ciphers of the *same* plaintext with known keys (including Naibbe-type verbose homophonic output) to measure recall, and on *wrong-language* targets to measure false-positive scores. A recent preprint calibrates exactly this and finds Voynichese gives no above-surrogate language match for the tested families, while Naibbe also evades it [RT26-preprint] — so "no solver hit" is weak evidence either way.
- **Anagram/transposition**: word-level anagram decoding with a lexicon and Viterbi over word LM (Hauer–Kondrak second stage).
- **Cognate/lexical tests** only against pre-registered anchors (Stage 9).
- **Search-space accounting:** record the number of (language × unit-set × mapping-family × solver-setting) combinations tried; any "plausible reading" must beat the best score obtained by the same pipeline on *shuffled* input of equal size. A pseudo-translation that "sounds meaningful" on a short passage is not evidence (high-degree-of-freedom mappings can produce any text — Cheshire's proto-Romance reading is the standard cautionary example [Ke19][Ch19]).

**Python.** `numpy`, `numba`, `kenlm` or `nltk.lm`/custom char n-gram; `hmmlearn`; `networkx` (min-cost-flow), `torch` (neural aligners); optionally `pygad`/custom SA for key search.

**Sketch.**
```python
import math, random, collections
def char_lm(corpus, n=4, alpha=0.1):
    counts = collections.defaultdict(collections.Counter)
    for i in range(len(corpus)-n): counts[corpus[i:i+n-1]][corpus[i+n-1]] += 1
    V = len(set(corpus))
    return lambda ctx, ch: math.log((counts[ctx][ch]+alpha)/(sum(counts[ctx].values())+alpha*V))
def score(cipher, key, lm, n=4):
    plain = "".join(key[u] for u in cipher)                  # unit -> plaintext char (many-to-one allowed)
    return sum(lm(plain[i:i+n-1], plain[i+n-1]) for i in range(len(plain)-n+1))
def anneal(cipher, units, alphabet, lm, iters=200000, T0=2.0, seed=0):
    rng = random.Random(seed); key = {u: rng.choice(alphabet) for u in units}; cur = score(cipher, key, lm)
    for t in range(iters):
        u = rng.choice(units); old = key[u]; key[u] = rng.choice(alphabet); new = score(cipher, key, lm)
        T = T0*(1-t/iters)+1e-3
        if new < cur and rng.random() > math.exp((new-cur)/T): key[u] = old
        else: cur = new
    return key, cur
# Always compare cur against anneal() on shuffled-cipher and wrong-language LMs; report the z-score.
```
(Untested sketch; real runs need incremental scoring.)

**Success / falsification.** Gates in Stage 12. Quick rejects: decoded text has per-character LM score within the shuffled-input null; mapping unstable across random restarts and quire halves; mapping has more free parameters than the data's effective information can constrain.

**References.** [HK16][KNRY06][RK11b][SBK10][LCB19][RT26-preprint][Ke19][Ch19].

---

## Stage 12 — Validation, falsification, and claim gating

**Objective.** Define in advance what would count as a real result, and block claims that don't meet it.

**Gates (all must pass for a candidate mapping/model to be called a *decipherment hypothesis with support*; passing does **not** prove it):**
1. **Out-of-sample prediction.** Mapping/model fitted on development quires must produce statistically significant structure on held-out quires/hands/sections (e.g. decoded text LM score ≫ shuffled-input null; class structure replicates).
2. **Transcription independence.** Replicates on ≥2 independent transcriptions (e.g. ZL and GC/v101) and with alternative space/ligature decisions.
3. **Null-model dominance.** Better than *all* generators in Stage 10 on the full profile, with the same degrees of freedom budget.
4. **Independent anchors.** Predicts ≥ N pre-registered cribs (Stage 9) it was **not** fitted on, e.g. picture-class ↔ label, zodiac order.
5. **Semantic coherence test by blinded experts.** Decoded passages in the *held-out* section are evaluated by medievalists/linguists unaware of which passage is real vs. a control decoding of shuffled text.
6. **Cross-section consistency.** Same mapping explains the A/B difference as a *linguistic or encoding* variable; mapping can't be re-tuned per section.
7. **Reproducibility.** Fresh clone + `make reproduce` regenerates the figure/table (Stage 13).
8. **External review.** Posting for critique (e.g. Voynich Ninja, Bowern's lab, peer review) before any public "solution" statement.

**Falsification bookkeeping.** Maintain `ledger/negative_results.md`; negative results are first-class outputs (the field's history is mostly failed readings: Cheshire proto-Romance [Ke19], plus a 2025–26 spate of claimed solutions and self-withdrawn partial solves surfaced in search results, not vetted here).

**Python.** `scipy.stats`, `statsmodels.stats.multitest` (Holm/Benjamini–Hochberg), `numpy`.

**Sketch.**
```python
from statsmodels.stats.multitest import multipletests
pvals = [r["p"] for r in anchor_results]
reject, p_adj, *_ = multipletests(pvals, alpha=0.01, method="holm")
```

**References.** [Ke19][Ch19] for what over-claiming looks like; [BL21] for the field's consensus statement of what is and is not known.

---

## Stage 13 — Reproducibility, repository layout, and hygiene

**Layout.**
```
voynich-decipher/
├─ README.md                  # status statement (undeciphered; research framework)
├─ source/2002046.pdf         # (DVC/LFS; 118 MB; check Yale rights statement before redistribution)
├─ data/{raw,processed,anchors,images}/   # raw = pristine downloads with checksums
├─ research/{WORKFLOW,PRIOR_WORK,DATA_SOURCES}.md
├─ src/voynich/{ivtff.py,units.py,stats.py,morph.py,classes.py,structure.py,generators/,attacks/}
├─ notebooks/                 # exploratory only; results must be re-derived by scripts
├─ ledger/{hypotheses.yaml,negative_results.md}
├─ results/                   # generated; never hand-edited
├─ tests/                     # parser round-trips, known-answer tests, regression of headline numbers
├─ Makefile / dvc.yaml        # make reproduce
└─ environment.yml | pyproject.toml (pinned) + CITATION.cff + LICENSE
```
**Practices.** Pin data versions (ZL 3b, GC 2a, IVTFF 2.0, ivtt 2.4) and store SHA-256 of every download; fixed random seeds; bootstrap over **quires/bifolios**; unit tests with known-answer fixtures (e.g. ZL3b must parse to 5385 loci; P=4130, L=1029, C=84, R=142); CI runs the cheap stages; record software versions; license code (MIT/Apache) and data separately; cite all transcribers and the Yale source; keep the "undeciphered" banner in README and generated reports.

**Libraries (suggested `pyproject` extras).** core: `numpy scipy pandas pyarrow scikit-learn statsmodels networkx matplotlib seaborn pyyaml rapidfuzz zstandard`; text/NLP: `nltk gensim sentencepiece tokenizers morfessor hmmlearn powerlaw`; vision: `opencv-python scikit-image pillow torch torchvision timm umap-learn hdbscan pdf2image pypdfium2`; repro: `dvc pytest pre-commit hypothesis`.

**Success / falsification.** A third party can reproduce every headline number from a clean clone; if a number changes across transcription versions, the report says so.

---

## Appendix A — Minimal first-week plan

1. Stage 1 (images + folio map) and Stage 2 (ZL + GC + IT parsers, agreement report).
2. Stage 3a glyph table + Stage 4 collapsed-EVA/BPE sweep + Stage 5 profile with ≥3 controls (Latin herbal, Naibbe output, self-citation output).
3. Stage 6 slot-grammar reproduction (Stolfi + Zattera) and Sukhotin/HMM *with* collapsed units.
4. Stage 8 page clustering vs. hand/section; Stage 7 high-frequency class induction.
5. Commit the ledger and the held-out split **before** touching Stages 10–12.

## Appendix B — What is established vs. disputed (short form; sources in `PRIOR_WORK.md`)

| Topic | Broadly agreed | Disputed / open |
|---|---|---|
| Date & material | Vellum radiocarbon-dated to early 15th c.; script and drawings contemporary; provenance traceable from the 17th c. (Beinecke) | Authorship, place, purpose |
| Text is statistically non-random | Strong regularities (word structure, Zipf-like word frequencies, section/page effects) | Whether regularity implies *language*; gibberish and ciphers can imitate much of it |
| Currier A/B | Real, robust statistical split; correlates with hands and sections | Whether = languages, dialects, topics, encodings, or time of writing |
| Scribes | ≥2 (Currier); 5 hands per Fagin Davis (2020) | Exact page attributions in a few places; link to A/B |
| Units | EVA is a *transliteration* convention, not a claim about letters | Letters vs. syllables vs. verbose groups; word spaces |
| Entropy | Character-level conditional entropy unusually low; word entropy not anomalous | Cause (language type, encoding, generation process) |
| Solutions | None accepted | Many claims; proto-Romance (Cheshire 2019) widely refuted |
