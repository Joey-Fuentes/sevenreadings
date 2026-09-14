# Licensing matrix

Decisions are made per source, recorded in `pipeline/sources.toml`
(`license_status`) and surfaced in the app. `blocked` sources are skipped by
the pipeline. Statements below are my reading as of the scaffold date and
must be verified against the actual upstream files before shipping.

| # | Source | Perspective | Original text | English text we would ship | Status |
|---|--------|-------------|---------------|----------------------------|--------|
| - | Berean Standard Bible | Bible | n/a | Public domain (CC0, 2023) | clear |
| - | World English Bible | Bible | n/a | Public domain | clear |
| - | World English Bible Catholic Edition | Bible (deuterocanon) | n/a | Public domain; no imprimatur; deuterocanon derived from RV Apocrypha/Brenton | clear |
| - | SBL Greek New Testament | Greek NT | n/a | CC BY 4.0 (SBL / Logos, 2010; v1.2 2023) | clear |
| - | Westminster Leningrad Codex (Open Scriptures) | Hebrew Bible | Public domain text | OSHB markup CC BY 4.0 | clear |
| 1 | Rashi (Sefaria-Export) | Jewish literal | Hebrew: public domain | Per text; several Sefaria translations are CC-BY-NC or have other terms | review |
| 2 | Ibn Ezra (Sefaria-Export) | Jewish rationalist | Hebrew: public domain | Per text; English coverage is partial | review |
| 3 | Haydock (1859) | Catholic | Public domain | Public domain; check the transcription project's own license | review |
| 4 | Chrysostom, NPNF (Schaff, 1888-90) | Orthodox | Greek: public domain | Public domain; check database/markup license | review |
| 5 | Matthew Henry (1706-21) | Protestant | n/a | Public domain; check database license | review |
| 6 | Tafsir Ibn Kathir | Islamic | Arabic: public domain | No public-domain English known; the common abridgment is copyrighted | blocked |
| 7 | ICC (pre-1929 volumes) | Academic | n/a | Public domain in the US for volumes published before 1929; later volumes excluded | review |

Notes
- "NC" licenses block paid distribution and are incompatible with the
  original PD/CC0-only requirement. Decide before wiring Rashi/Ibn Ezra.
- For #6, options are: commission or find a permissively licensed English
  rendering; ship Arabic only; or substitute another classical tafsir with a
  clear English translation.
- Keep each source's upstream `LICENSE` and a `NOTICE.md` in
  `pipeline/sources/<id>/`. The app's "About the texts" screen renders them.
