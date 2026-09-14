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

## Consequences
`sr_core` (Dart) and `refs.py` (Python) implement the encoding twice, with
tests on identical fixtures. Change one, change both.
