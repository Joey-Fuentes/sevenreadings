# Licensing matrix

Decisions are made per source, recorded in `pipeline/sources.toml`
(`license_status`), spelled out in `pipeline/sources/<id>/NOTICE.md`, and
shipped: the pipeline concatenates the notices of every built source into
`meta.notices` in the content database, and the app renders them on the
"About the texts" screen (book picker, last entry) together with each
translation's and source's license from the database. `blocked` sources are
skipped by the pipeline. Audited September 2026 against the upstream
repositories and sites themselves.

The rule: a text may ship if it is public domain or under a license that
permits redistribution including commercial redistribution. CC BY and
CC BY-SA qualify (attribution and a license link are required, and the
notices carry them); any NC license does not.

## Two layers

Every historical text is judged twice: the underlying work, and the
digitisation we actually copy. Works by authors dead more than seventy
years, or published before 1929, are public domain everywhere we ship. A
digitisation with an explicit permissive license is clear on its own terms.
A digitisation that states nothing is judged as a faithful reproduction of
a public-domain work: such reproductions carry no new copyright — in the
United States under Feist Publications v. Rural Telephone (1991, "originality,
not sweat of the brow, is the touchstone") and Bridgeman Art Library v.
Corel (1999); in the EU and UK under the Infopaq (C-5/08) originality
standard. That reasoning is the basis for the Haydock transcription and is
written into its NOTICE so it is not re-argued.

## Shipping

| Source | What | Underlying text | Digitisation we ship | Status |
|--------|------|-----------------|----------------------|--------|
| bsb | Berean Standard Bible | n/a | Public domain, CC0 dedication 30 April 2023 (berean.bible/terms) | clear |
| web | World English Bible | n/a | Public domain; "World English Bible" is an eBible.org trademark on the name, text shipped unchanged | clear |
| webc | WEB Catholic Edition | n/a | Public domain; deuterocanon from the RV Apocrypha and Brenton, both public domain | clear |
| douay | Douay-Rheims, Challoner | Public domain (1582-1610, 1749-52) | JohnBlood transcription, no license stated; treated as public domain (see Two layers). Explicitly licensed fallback: github.com/xxruyle/Bible-DouayRheims, MIT | clear |
| sblgnt | SBL Greek New Testament | n/a | CC BY 4.0 (Faithlife/SBLGNT LICENSE); attribution + license link in NOTICE | clear |
| byz | Byzantine Majority Text, Robinson-Pierpont 2018 | n/a | The Unlicense; README: "All the code and text ... is in the Public Domain" | clear |
| wlc | Westminster Leningrad Codex via Open Scriptures Hebrew Bible | Public domain | OSHB markup CC BY 4.0; required attribution line in NOTICE | clear |
| lxx | Septuagint, Swete (nathans/lxx-swete) | Public domain edition | CC BY-SA 4.0 (First1KGreek / Open Greek and Latin). Share-alike binds the text and adaptations of it, not the MIT app that bundles it | clear |
| haydock | Haydock's Catholic Bible Commentary (1859) | Public domain (1859; author d. 1849) | JohnBlood transcription, no license stated; treated as public domain (see Two layers) | clear |
| matthew_henry | Matthew Henry's Commentary (1706-21) | Public domain | CCEL HTML edition: "Public domain text. No rights reserved. May be distributed freely." | clear |

## Planned

| Source | Underlying text | Digitisation | Status and what stands in the way |
|--------|-----------------|--------------|-----------------------------------|
| chrysostom | NPNF translations (Schaff, 1886-90): public domain | Take the text from CCEL's NPNF editions (public domain, no terms) or Wikisource. HistoricalChristianFaith/Commentaries-Database (the current stub's upstream) states no license and aggregates other material: do not use it until it does. Avoid newadvent.org, whose editor asserts copyright on his edition | review: switch upstream to CCEL, then wire |
| rashi, ibn_ezra | Hebrew: public domain | Sefaria-Export records a `license` per version (Public Domain, CC0, CC-BY, CC-BY-SA; CC-BY-NC case by case). Ship only versions whose field is one of the first four. The Strickman-Silver Ibn Ezra (1988-2004) and the Metsudah Chumash are copyrighted: never. Friedlander's Ibn Ezra on Isaiah (1873) is public domain | review: read each version's `license` field before wiring |
| ibn_kathir | Arabic: public domain | No public-domain or permissive (non-NC) English translation exists; the common English is the copyrighted Darussalam abridgement. spa5k/tafsir_api is MIT as software only; its English texts come from quran.com / QUL under their terms | blocked for English. Options: Arabic only, or another classical tafsir once a permissively licensed English is verified |
| icc | ICC volumes published before 1929: public domain in the US (e.g. Driver, Deuteronomy 1895; Moore, Judges 1895; Sanday-Headlam, Romans 1895; Plummer, Luke 1896; Toy, Proverbs 1899; Gray, Numbers 1903) | Internet Archive OCR of public-domain scans is itself public domain (no originality); IA's terms govern site access, not the text. Wikisource has little of it | review: work, not permission — one volume at a time, proofread |

## Open questions and whom to ask

- JohnBlood transcription: no action required; if the transcriber ever
  publishes terms, they take precedence and this file is updated. A polite
  request for a CC0/CC BY LICENSE file can go via the site's Contact page.
- HistoricalChristianFaith/Commentaries-Database: only relevant if CCEL
  proves unusable; ask by GitHub issue what the database's license is and
  which entries are the public-domain NPNF/ANF text.
- Sefaria: no one to ask; the answer is in the export metadata.
