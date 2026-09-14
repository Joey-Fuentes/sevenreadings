# ADR 0003: One canonical verse id; commentary anchors to ranges

**Status:** accepted

## Context
The seven sources do not agree on what a "verse" is. Rashi and Ibn Ezra use
Masoretic numbering (Psalm titles are verse 1, Joel has four chapters).
Haydock quotes the Douay-Rheims (Vulgate) numbering. Chrysostom preaches on
pericopes, Matthew Henry on paragraphs, ICC on verses within a critical unit.
Ibn Kathir is not anchored to the Bible at all.

## Decision
- Every verse has a canonical integer id in English/Protestant versification:
  `book*1_000_000 + chapter*1_000 + verse`. Ids sort canonically; verse 0 is
  chapter-level (superscriptions, whole-chapter notes); 999 is the chapter-end
  sentinel.
- `commentary_entries` anchor to an inclusive `[start_verse_id, end_verse_id]`
  range. "Readings for verse V" is `start <= V AND end >= V`.
- `versification_map(scheme, book, chapter, verse) -> canonical id` normalises
  Masoretic/Vulgate/LXX numbering at pipeline time; the app never sees
  non-canonical references.
- `parallels` links a Bible range to external material (Quran passages).
- Partial coverage is the norm. The UI lists all seven perspectives for every
  verse and states plainly when one has nothing there.

## Extension: deuterocanon (2026-09)
Book ids 67-75 were appended for the Catholic deuterocanon. Ids never move;
display order per tradition lives in `book_orders`. Greek Esther keeps its own
numbering as book 69. Greek Daniel is split at ingest: whatever overlaps
Hebrew Daniel is stored under Daniel at canonical numbers (Greek 3:91 becomes
Daniel 3:24, with `native_ref = '3:91'`), and only the additions (3:24-90,
13, 14) live in book 75 "Daniel (Greek additions)". The Letter of Jeremiah is
stored as Baruch 6. See `pipeline/sevenreadings_pipeline/deuterocanon.py`.

## Extension: original languages (2026-09)
Hebrew (WLC) arrives in Masoretic numbering and is renumbered at ingest by
`pipeline/sevenreadings_pipeline/versification.py`: a rule table for chapter
boundary shifts (Joel 3-4, Malachi 3-4, ...) plus psalm-title offsets derived
by comparing MT and English verse counts. MT verses that land on one English
verse are joined; `native_ref` keeps the MT numbers. The build logs every
remaining mismatch against the reference translation, so the rule table is
corrected from data. The `versification_map` table stays for lookups the app
may want later; ingest-time normalisation is the primary mechanism.

## Extension: Septuagint (2026-09)
Swete's LXX (via nathans/lxx-swete) is renumbered by `apply_lxx`: the LXX
psalm scheme (9 = Hebrew 9+10, the offset-by-one run, the 113-116 and
146-147 splits, 151 kept), Jeremiah's rearranged oracles, the 3 Kingdoms
20/21 swap, and a short table of LXX-vs-English verse shifts. The digitised
edition follows the English chapter breaks in all but six chapters, so the
Hebrew rule table is not applied to it. Known gaps at their LXX numbers:
Exodus 36-40 and Proverbs 24-31 (reordered). Corpus defects (missing
Ecclesiastes, OCR-lost verses, stray chapter-boundary lines) are reported
by the build; the stray lines are repaired at parse time.

## Consequences
`sr_core` (Dart) and `refs.py` (Python) implement the encoding twice, with
tests on identical fixtures. Change one, change both.
