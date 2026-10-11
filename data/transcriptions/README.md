# Third-party transcriptions (not committed)

The transliteration files are © their authors and come from <https://www.voynich.nu/data/>
(Rene Zandbergen's site). The `000_README.txt` that was read there states **no open licence**,
so the files are **git-ignored** and this repository commits only:

* `MANIFEST.json`: URLs, sizes, SHA256 checksums, retrieval dates and a licence note
* the fetch code `src/msdecipher/fetch.py`

Recreate and check the data:

```bash
python -m msdecipher fetch    # downloads into this folder and rewrites MANIFEST.json
python -m msdecipher verify   # compares local files with the committed checksums
```

If `verify` reports `MISMATCH`, upstream has updated a file since the manifest was written; results
may then differ slightly from `reports/`.

Files (IVTFF 2.0): `ZL3b-n.txt` (primary), `IT2a-n.txt`, `RF1b-e.txt` (EVA replications),
`GC2a-n.txt` (v101 alphabet; parser test only), `000_README.txt`.

Transcribers to cite: R. Zandbergen / G. Landini (ZL), T. Takahashi (IT), G. Claston (GC),
RF = automatic ZL+GC reference merge. If you want to redistribute the files, ask the maintainer first.

HTTP note: voynich.nu answers 406 to browser-spoofing User-Agents and to the stock
`python-requests` / `urllib` ones; the fetcher sends an honest descriptive User-Agent
(`msdecipher/0.1 (research tool; +<repo url>)`) which is accepted.
