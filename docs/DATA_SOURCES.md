# Data sources — transcriptions, images, controls, tools

Checked 11 Oct 2026 (Europe/Warsaw). HTTP status was confirmed from the box for the listed URLs unless marked otherwise. **Licensing note:** none of the voynich.nu data files states an explicit open licence in the README that was read; they are publicly downloadable research resources. Cite the transcribers, keep copies out of git or under a clear "third-party data" notice, and contact the maintainers if you plan to redistribute. Image rights: use the item's *Access and Usage Rights* statement on Yale Digital Collections; Yale says reuse depends on the item and intended use and users must secure needed permissions.

## 1. Primary images

| Item | URL | Notes |
|---|---|---|
| Yale PDF (this project) | https://collections.library.yale.edu/pdfs/2002046.pdf | 214 pages, ~118 MB, images only. Already at `source/2002046.pdf`. HTTP 200. Record page returned HTTP 403 to the automated fetcher; open in a browser to read the rights statement. |
| Beinecke digital library record | https://brbl-dl.library.yale.edu/vufind/Record/3519597 | High-resolution zoomable images; "download all" option per Beinecke. |
| Beinecke collection page (access policy) | https://beinecke.library.yale.edu/beinecke/collections/beinecke-cipher-voynich-manuscript | Original is access-restricted; high-res images available for research; facsimiles (Yale UP 2016, Siloé 2017) exist. |
| Yale IIIF | Yale Digital Collections exposes IIIF Presentation manifests at `.../manifests/{oid}` (OID is the numeric object id; confirm the OID for MS 408 via the record) | Prefer for per-folio full-resolution crops. *Search-derived; confirm endpoint before scripting.* |
| Multispectral f1r scan | via Lisa Fagin Davis' blog (referenced in [Za-sp]) | Shows later additions on f1r. *URL not captured.* |

## 2. Transliterations (IVTFF 2.0 unless noted) — base: https://www.voynich.nu/data/

Directory index (fetched 2026): `000_README.txt, AB.docx, CD2a-n.txt, FG2a-n.txt, GC2a-n.txt, IT2a-n.txt, RF1b-e.txt, RF1b-er.txt, VT0e-n.txt, ZL3b-n.txt, beta/, ivtff.xlsx, pics/, previous/, sta/, temp/, voyn_101.txt`.

| File | URL | What / use |
|---|---|---|
| **ZL3b-n.txt** | https://www.voynich.nu/data/ZL3b-n.txt | Zandbergen–Landini (v3b, 13 May 2025), Extended EVA, 5385 loci (P 4130, L 1029, C 84, R 142); uncertain spaces and alternative readings marked. **Primary text.** Smoke-tested: parses to 5385 loci. HTTP 200. |
| **GC2a-n.txt** | https://www.voynich.nu/data/GC2a-n.txt | Glen Claston's v101 transcription in v101 alphabet (independent second transcriber; contains one spurious f89v2 label per README). |
| **RF1b-e.txt / RF1b-er.txt** | https://www.voynich.nu/data/RF1b-e.txt , …/RF1b-er.txt | Reference transliteration (automatic ZL+GC merge via STA1), extended / reduced Eva. For coverage checks and consensus experiments. |
| IT2a-n.txt | https://www.voynich.nu/data/IT2a-n.txt | Takahashi (as in Landini–Stolfi interlinear, 1999 state), basic lower-case EVA. Third independent reader. |
| VT0e-n.txt | https://www.voynich.nu/data/VT0e-n.txt | Takahashi version used at voynichese.com. |
| CD2a-n.txt | https://www.voynich.nu/data/CD2a-n.txt | Currier–D'Imperio (Currier alphabet), 2196 loci, incomplete (≈40%). |
| FG2a-n.txt | https://www.voynich.nu/data/FG2a-n.txt | Friedman First Study Group (FSG alphabet), 4060 loci, paragraph text mostly. |
| voyn_101.txt | https://www.voynich.nu/data/voyn_101.txt | Original unmodified v101 file (high-ASCII bytes). |
| ivtff.xlsx | https://www.voynich.nu/data/ivtff.xlsx | Locus-type counts per page and per quire. |
| 000_README.txt | https://www.voynich.nu/data/000_README.txt | Dataset notes; IVTFF with `$H` (Fagin Davis hand) and `$C` (Currier hand) page variables. |
| beta/ | https://www.voynich.nu/data/beta/ | Beta files incl. `LSI_ivtff_0d.txt` (interlinear in IVTFF), `RF.zip`, Pliny-based test texts (`pliny_norm.txt`, `pliny_mod1.txt`, `pliny_mod2.txt`) — handy as Latin controls. Subject to change. |
| STA alphabet material | https://www.voynich.nu/extra/sta.html | Super Transliteration Alphabet definition (PDFs linked from that page). |
| Landini–Stolfi interlinear (EVA, 1.6e6, 1998) | https://ic.unicamp.br/~stolfi/EXPORT/voynich/ | Historic; links to the interlinear and word-colour pages. |
| Per-token coordinates (voynichese.com snapshot) | https://github.com/lrozanova/voynich-units (analysis snapshot refers to voynichese.com archive commit `66f8adaa…`) | Coarse, 3-px grid; use with caution. |

Versions to record in the repo: ZL 3b, GC 2a, IT 2a, RF 1b, IVTFF 2.0 (format doc 2.0.x), ivtt 2.4, bitrans 1.5.

## 3. Tools

| Tool | URL | Notes |
|---|---|---|
| **ivtt** (Intermediate Voynich Transliteration Tool) v2.4 | source https://www.voynich.nu/software/ivtt/ivtt.c ; manual https://www.voynich.nu/software/ivtt/IVTT_manual.pdf ; format https://www.voynich.nu/software/ivtt/IVTFF_format.pdf | C; filter by page variables/locus type; versions < 2.4 have known bugs. An online ivtt port (Feb 2026) is linked from [Za-sp]. |
| **bitrans** v1.5 | https://www.voynich.nu/software/bitrans/ | Rules-file driven alphabet conversion (EVA↔v101↔STA↔Currier/FSG). Earlier versions buggy. |
| Naibbe cipher code (MIT, © 2025 greshko) | https://github.com/greshko/naibbe-cipher | Generates Voynich-like ciphertext from Latin/Italian; **null/competing model**. |
| Gibberish study code + data | https://github.com/danielgaskell/voynich | Code/gibberish datasets under a "modified MIT" licence; Voynichese and meaningful-text datasets have separate terms (see its README). |
| Lindemann–Bowern corpus/code | https://github.com/chirila/Voynich-public | Multilingual comparison corpora from the entropy paper; licence not confirmed (README fetch returned 404). |
| Units/boundary analysis package (MIT, © 2026 L. Rozanova) | https://github.com/lrozanova/voynich-units | Reproduction drivers for [RT26-preprint] (preprint; verify). |
| Self-citation generator (Timm–Schinner) | Zenodo 10.5281/zenodo.2531632 (per [RT26-preprint]) | Java, reported MIT. *DOI not independently resolved.* |

## 4. Control corpora (plaintext candidates and matched nulls)

Keep each control at the **same token count and line-length template** as the manuscript subset it is compared with.

| Corpus | Source | Notes / licence |
|---|---|---|
| Latin prose/botany/medicine (Pliny, Celsus, Caesar, Vulgate, Dioscorides translations) | Perseus Digital Library / Tesserae (https://www.perseus.tufts.edu , https://tesserae.caset.buffalo.edu) *(not re-verified)*; Latin Library; Vulgate texts | Perseus texts mostly CC BY-SA; check each. |
| English/French/German/Italian narratives, herbals (e.g. Culpeper) | Project Gutenberg (https://www.gutenberg.org) | Public domain (strip headers). |
| Medieval herbals, alchemical and "secrets" books (Latin/German/Italian/Czech) | Beinecke, Wellcome Collection, e-codices, manuscripta.at *(search by item)* | Check each item's rights. Useful as genre-matched controls. |
| Hebrew (e.g. Sefaria API), Arabic, Chinese pinyin (Gutenberg 26888 *Bencao Beiyao*, 23950 *Three Kingdoms*) | https://www.sefaria.org , Project Gutenberg | Used as controls in [RT26-preprint]; Hebrew relevant to [HK16]. |
| Pliny-derived test texts at voynich.nu | https://www.voynich.nu/data/beta/ | Used in Zandbergen's cipher experiments. |
| Synthetic nulls | generated in-repo (Stage 10): shuffles, Markov glyph generators, Naibbe cipher output, self-citation generator, human gibberish from [GB22] | Reproducible by seed. |

## 5. Suggested `data/raw` manifest (checksum everything)

```
data/raw/ZL3b-n.txt   https://www.voynich.nu/data/ZL3b-n.txt   sha256:<fill after download>
data/raw/GC2a-n.txt   https://www.voynich.nu/data/GC2a-n.txt   sha256:<fill>
data/raw/IT2a-n.txt   https://www.voynich.nu/data/IT2a-n.txt   sha256:<fill>
data/raw/RF1b-e.txt   https://www.voynich.nu/data/RF1b-e.txt   sha256:<fill>
data/raw/000_README.txt https://www.voynich.nu/data/000_README.txt
data/raw/ivtt.c       https://www.voynich.nu/software/ivtt/ivtt.c
```
Download with `python -m msdecipher fetch` (checksums in `data/transcriptions/MANIFEST.json`; the files themselves are git-ignored, see `data/transcriptions/README.md`). Plain `curl -L` also works. voynich.nu answers HTTP 406 to browser-spoofing User-Agents and (observed 11 Oct 2026) to the stock `python-requests` and `Python-urllib` ones, but accepts curl's default and an honest descriptive User-Agent, which is what the fetcher sends.
