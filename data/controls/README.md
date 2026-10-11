# Control texts

Public-domain / openly licensed texts used as comparison material for the MS 408 statistics
(`python -m msdecipher controls-fetch`). The downloaded files are **git-ignored**; this
directory only carries `MANIFEST.json` (URL, SHA256, size, licence note, fetch date) so the
data can be re-fetched and verified (`python -m msdecipher controls-verify`).

| id | text | language | licence |
|---|---|---|---|
| la_vulgate | Vulgata Clementina (1598), Genesis + Exodus (la.wikisource.org) | Latin | 1598 edition PD; Wikisource platform text CC BY-SA 4.0 |
| la_augustine | Augustine, *Confessiones* (Gutenberg #33849) | Latin | PD (USA) |
| it_dante | Dante, *Divina Commedia* (Gutenberg #1000) | Italian | PD (USA) |
| it_manzoni | Manzoni, *I promessi sposi* (Gutenberg #45334) | Italian | PD (USA) |
| de_walther_mhg | Walther von der Vogelweide, selected poems (Gutenberg #35795), ~9k tokens only | Middle High German | PD (USA) |

Not covered: Hebrew/Arabic (abjad) natural texts, Greek, Occitan, Czech, Old French, and a true
herbal/medical Latin (no clean public-domain plain-text source was found quickly).
