# Sources for the plant-ID table (data/plant_ids.csv)

Fetched 2026-10-12. Identifications are **contested proposals**, not facts.

- **Petersen** (incl. O'Neill and Holm as quoted by Petersen), **ELV_Grolier**, **ELV_Beinecke**: R. Zandbergen, "Pre-1960's tentative herb identifications", http://www.voynich.nu/extra/herb_oldid.html (table and Petersen marginal notes; the marginal cross-references to pharma folios give `data/pharma_herbal_pairs_extra.csv`).
- **Zandbergen_ZL**: comments in the ZL3b IVTFF transcription ("Plant ID", "RZ").
- **TuckerTalbert**: Tucker & Talbert 2013 / Tucker & Janick 2016–2019, "Identification of Phytomorphs in the Voynich Codex", https://hort.purdue.edu/newcrop/pdfs/hr44-ch1-phytomorphs.pdf (folio list as shown in search snippets; f2r and f25v via the voynichbotany.wordpress.com list). New World IDs; partial coverage here.
- **Vatne2022**: S. B. Vatne, "The Voynich plants and their names" / "The morphology of the Voynich plants", crackingthevoynichcipher.com (f1v, f2v, f3v, f4v, f9v only).
- **Sherwood_Bax**: S. Bax 2014, "A proposed partial decoding of the Voynich script" (quotes E. Sherwood's IDs for f2r, f3v) plus Bax's plant readings (f16r juniper, f29v Nigella, f41v coriander). Crib words in `data/bax_cribs.csv` are taken from the transcription at the loci Bax describes (first word / added label); exact spellings in his paper were not re-checked (PDF not retrievable from the box), so these are approximations.
- **ZL3b "Same plant as" comments** (Petersen, Stolfi, FSG, GL): parsed at run time by `h09_lib.same_plant_pairs`.

Genus/family columns are my normalisation of each proposal (first named taxon; `?` proposals kept).
