# AGENTS.md — working on sevenreadings

Read this first. It is the handoff for any AI session (or person) picking the
project up cold. The human maintainer works from **Android/Termux** (no Flutter
locally); the AI works in a **sandbox without network access**. Everything
below follows from those two facts.

## What this is

An offline, local-only Scripture study app (Flutter, six platforms) that reads
Bible text alongside seven traditions' commentary. Design and decisions:
`README.md`, `docs/adr/`. Content is a build artifact published as GitHub
Releases and pinned in `app/content.lock` by automation; nothing large is in git.

Current content (see `pipeline/sources.toml` for pins and licenses):

| id | what | status |
|----|------|--------|
| bsb, web, webc | English Bibles (BSB; WEB; WEB Catholic Edition with deuterocanon) | live |
| douay | Douay-Rheims (Challoner), the text quoted on the Haydock pages; Vulgate numbering mapped at ingest (`apply_vul`) | live; transcription unlicensed, treated as public domain (docs/licensing.md) |
| sblgnt | SBL Greek New Testament (CC BY 4.0) | live |
| byz | Byzantine Majority Text, Robinson-Pierpont 2018 (byztxt, The Unlicense), Received-Text numbering | live |
| wlc | Hebrew Bible, Westminster Leningrad Codex via OSHB (CC BY 4.0), Masoretic numbering mapped at ingest | live |
| lxx | Septuagint, Swete's edition via nathans/lxx-swete (CC BY-SA 4.0), LXX numbering mapped at ingest | live, known gaps: Exodus 36-40 and Proverbs 24-31 reordered, Ecclesiastes missing upstream |
| matthew_henry | Matthew Henry's Commentary, CCEL public-domain HTML edition | live (Protestant reading) |
| haydock | Haydock's Catholic Bible Commentary (1859), JohnBlood GitLab transcription; notes anchored where the Douay verses land | live (Catholic reading); same pin as douay |
| chrysostom | Chrysostom's NT homilies, CCEL ThML editions of NPNF 1/10-14 (files declare DC.Rights Public Domain); each homily anchored to its passage up to the next homily's | live (Orthodox reading): 478 homilies across all 17 books he preached on |
| rashi, ibn_ezra | Sefaria's database export on Hugging Face, pinned by commit; per book the largest English version whose recorded license is PD/CC0/CC BY/CC BY-SA, NC never read; Masoretic numbering followed through the WLC's ingest | live (Jewish readings): Rashi 11,050 entries in 39 books; Ibn Ezra 1,350 in 7 books (22 books have no open-licensed English; Hebrew-only for those is an open decision) |
| icc | International Critical Commentary, pre-1929 volumes, from the Internet Archive's hOCR (`_hocr.html`); chapter from each page's running head, notes split at bold verse numbers, sections at "I. 1-7." headings | live (Academic reading): Sanday-Headlam on Romans, 376 notes; OCR unproofread by design; more volumes are one `sources.toml` entry each |
| quran | Pickthall's Qur'an (1930, public domain) from Project Gutenberg #16955, shown at the Bible passages it parallels; the pairings are `pipeline/data/quran_parallels.tsv` (project data, CC0), one entry and one `parallels` row per pairing | live (Islamic reading): 178 pairings, 345 parallels; the file is the whole coverage, so a new line is a new reading |
| ibn_kathir | documented stub in `pipeline/sevenreadings_pipeline/sources/stubs.py` | not wired: no permissive English translation; the Arabic (Arabic Wikisource, CC BY-SA) plus machine translation is possible and would sit beside the Qur'an entries |

App: verse-by-verse phone layout, side-by-side on wide screens, translation
chips, book/chapter picker with Protestant/Catholic/Tanakh order, readings
sheet with collapsible Markdown entries, full-text search (verses per
translation, readings per source; a hit opens the chapter on that verse),
"About the texts" (book picker, last entry: licenses from the database and
the notices the pipeline stores in `meta.notices`), bookmarks and notes per
verse (readings sheet header; listed under "Bookmarks & notes" in the book
picker; stored in `UserDb`, never in content).

## Setting up a session (AI side)

(The maintainer's side — what to upload and the prompt to paste — is in
`docs/workflow.md`, "Starting an AI session".)

The maintainer uploads the repo as a Termux `tar` of `~/sevenreadings` made
with this command (kept here so it can be pasted; the upload arrives named
`sevenreadings_tar.gz`, and paths inside start with
`data/data/com.termux/files/home/`):

```
rm -rf ~/sevenreadings.tar.gz && tar -czvf ~/sevenreadings.tar.gz ~/sevenreadings
```

It contains `pipeline/.cache` (the fetched upstreams, ~200 MB), which the AI
can use in place of the network. With the archive, the maintainer uploads a
ruff wheel or the `pipeline-wheels` artifact from the `Tools for offline
review` workflow when the sandbox lacks them.

```
mkdir -p /home/claude/in && tar -xzf /mnt/user-data/uploads/sevenreadings*tar.gz -C /home/claude/in
rm -rf /home/claude/sevenreadings && cp -r /home/claude/in/data/data/com.termux/files/home/sevenreadings /home/claude/
pip install --break-system-packages --no-index <uploaded>.whl        # ruff alone, or:
pip install --break-system-packages --no-index --find-links wheels -r wheels/requirements.txt
cd /home/claude/sevenreadings/pipeline && ruff check . && ruff format --check .
python -m pytest -q                        # if pytest is installed
python tests/_run_without_pytest.py        # otherwise
```

If `git` is available, `git log --oneline | head` confirms which commit you
have. The sandbox filesystem may reset between conversations; keep the copy in
`/home/claude/sevenreadings` current and re-request the tarball if unsure.

## What the AI can and cannot verify

- **Python (pipeline)**: fully. ruff (the same version CI resolves) and the
  test suite run locally. Never hand over Python that hasn't passed
  `ruff check` and `ruff format --check`.
- **Dart/Flutter**: not at all. No SDK, no pub cache, no network. Write to
  `dart format`'s 80-column, "short" style (the workspace pins `sdk: ^3.6.0`,
  so the pre-3.7 formatter applies), check every line is ≤ 80 columns, and
  let CI be the judge. When CI fails, the maintainer uploads the run's log zip.
- **The integration test** (`app/integration_test/app_test.dart`): CI's
  `dart` job formats and analyzes it; only `screenshots.yml` runs it (an
  Android emulator, the Linux build under Xvfb; `docs/workflow.md`, "The
  checklist in CI"). Its `screenshots-<target>` artifacts are the
  evidence: PNGs, launch timings, the view size, logcat on Android. What the test asserts was checked against the sample database
  and a full offline build of the content (`pipeline/.cache` has every
  upstream but one Ibn Ezra listing; build with `--only` and everything
  except `ibn_ezra` to reproduce), so a red run is a runtime problem, not a
  wrong expectation, unless the content changed. Two things the runs
  taught: every `ListView` builds lazily and a finder for anything below
  the fold finds nothing until the test scrolls there, and it scrolls by
  jumping the `ScrollPosition` (`scrollTo`), because synthetic drags
  moved nothing on the Linux build while they worked on the emulator;
  and it is one `testWidgets`, because the binding resets the Android
  screenshot surface between tests.
- **Upstream data**: no network. To learn how a source is laid out, ask the
  maintainer to run a command in Termux and paste the output (see
  `docs/workflow.md`, "Inspecting an upstream"). Don't guess file layouts;
  every guess so far cost a round trip.
- **Never use `/tmp`, anywhere, in any command or script.** Termux has no
  writable `/tmp` (`Permission denied`), so a command that extracts or
  writes there fails and every command chained after it fails too. Scratch
  space is `~/scratch` (`mkdir -p ~/scratch`) on the maintainer's side and
  `/home/claude` on the AI's side. Python code uses `tempfile` / pytest's
  `tmp_path`, which honour `$TMPDIR`; never a literal path.

## How changes are delivered

The AI produces a unified diff; the maintainer applies it with `git apply`.

```
# before editing
cd /home/claude && rm -rf sr_before && cp -r sevenreadings sr_before
# ... edit /home/claude/sevenreadings ...
cd /home/claude/sevenreadings/pipeline && ruff format . && ruff check . && python -m pytest -q
cd /home/claude && diff -ruN -x __pycache__ -x .ruff_cache sr_before sevenreadings > name.patch
cp name.patch /mnt/user-data/outputs/     # then present it
```

Rules that keep patches applying cleanly:

- `app/content.lock` is written by the content bot. Never include it in a patch
  (copy the maintainer's version into both trees before diffing).
- `pipeline/sources.toml` carries real upstream checksums that only the
  maintainer can compute (network). Keep the reference copy's pins identical
  to theirs; when adding a source, leave `sha256 = "TODO"` and give them the
  `srp lock` command. If unsure whether pins match, exclude the file from the
  diff (`-x sources.toml`) and hand over the toml edit as a small Python
  snippet instead (sed with `#` or `/` in the text has bitten us).
- One patch per logical change; the maintainer commits with a message you
  suggest. Their order is always `git add -A && git commit … && git pull && git push`
  because the content bot pushes to `main` after every content release.

## Conventions and traps (learned the hard way)

- Verse ids: `book*1_000_000 + chapter*1_000 + verse`; verse 0 = chapter-level
  material (titles, introductions); 999 = chapter end. Books 1-66 Protestant
  order, 67-75 deuterocanon. Ids never change; display order lives in
  `book_orders`. Dart (`sr_core`) and Python (`refs.py`) both implement this,
  with tests on identical fixtures: change one, change both.
- Content schema lives once, in `packages/sr_data/lib/src/schema/content.drift`,
  as plain SQL. Bump `SCHEMA_VERSION` (pipeline `db.py`) and
  `ContentDb.contentSchemaVersion` together on any change.
- drift: a column named `text` collides with `Table.text()`; `key` is a
  reserved word in its parser. Generated data classes are the singular of the
  table name (`translations` → `Translation`), so avoid table names whose
  singular collides with sr_core types (`CanonBook` exists for that reason).
- Sources are renumbered at ingest to canonical ids (`versification.py`); the
  build prints every verse that has no counterpart in the reference
  translation, per book. Trust that report over memory: the Hebrew rule table
  was right first time; the Septuagint's was corrected three times from data.
- The Swete LXX digitisation advances chapter numbers one line early in ~90
  places; `parse_tokens` repairs that. Its Psalms are LXX-numbered throughout.
- An unpinned source (`sha256 = "TODO"`, `COMMIT` in a url) aborts the build
  at that source; the partial database makes `probe` print `0/N` everywhere.
  `srp lock --write <source>` records the hash; `docs/workflow.md` has the
  loop in one block. Hand the maintainer that block, not a paraphrase.
- `probe` is chapter-N-against-chapter-N; for LXX/Vulgate psalms use the
  build report instead.
- `/tmp` does not exist for the maintainer (Termux). Absolute rule: no
  `/tmp` in commands, docs, scripts or tests. Use `~/scratch` there and
  `/home/claude` in the sandbox.
- Haydock/Douay: one GitLab archive feeds two sources. The site's index
  pages (`index.html`, `id330.html`) decide which `idNNN.html` is which
  chapter; the archive also holds stale duplicates and a mis-titled page, so
  titles are only cross-checked and logged. The `confraternity/` sister site
  has the same page shape and is skipped by path. Douay verse lines come as
  `8 text`, `*8 text` and, in the psalms the Vulgate splits differently
  (9, 113, 115, 147), `10(1) text` = Hebrew(Vulgate); the parser keeps the
  Vulgate number and, on those psalms, aliases the Hebrew number for the
  notes (Haydock says `Ver. 11` for `11(2)`). Lines break at the *English*
  verse boundaries, so a Vulgate number can sit mid-line (`...commanded: 8
  and a congregation`, `thy sword 14 from the enemies`); the parser splits
  there when the number is the next in sequence. The cross-reference list
  under the verses is not always behind a rule; `N: ...` lines end the
  verses. Numbers the transcription simply dropped (Genesis 49:25, Psalm
  12:7 ...) stay in the report. `VUL_RULES` holds chapter-boundary shifts settled from the
  build report; single-verse splits and joins inside a chapter are reported,
  not mapped. Notes cite the canonical verse and add `(Douay c:v)` when the
  numbering differs.
- Sefaria versions: never hardcode a version title as "the" text. Sefaria
  records a license per version; `sources/sefaria.py` reads them all and
  picks by the allow-list, and the build prints the pick per book. If a
  version's license changes upstream, the next build changes the pick and
  says so. Hugging Face URLs for the export are long: `web_fetch` refuses
  them over 250 characters, so inspect through the tree pages instead.
- CCEL's site policy is non-commercial for "CCEL works"; the ThML files
  themselves declare DC.Rights Public Domain and we ship only the
  public-domain text from them (not the staff description in the header).
  `sources/chrysostom/NOTICE.md` records that reasoning.
- Commentaries in another numbering follow a translation that was renumbered
  from data: Haydock through the Douay's `trace`, Rashi and Ibn Ezra through
  `versification.translation_trace(conn, "wlc")`. Build them with that
  translation in `--only`, or the build says it fell back to the rule table.
- The Islamic reading is the Qur'an, not a commentary: a Bible passage gets
  the Qur'an passage that retells or answers it. Coverage is exactly the
  pairings in `pipeline/data/quran_parallels.tsv`; a verse with no pairing
  shows "No reading". Add pairings there, one line each, with the basis in
  the note when it is exegetical rather than textual. `refs.parse_ref`
  handles the Bible side ("Gen 44:18-45:15"); the Qur'an side is "s:a-b".
- ICC volumes: add one per `urls`/`sha256`/`books`/`authors` entry, prefer
  the Toronto scans (`...uoft`), and read the build line for the volume:
  `notes per chapter` should be dense and the "kept without one" count small.
  Missing verses are usually the OCR losing the bold number, not the text;
  the surrounding note absorbs it. Do not try to fix OCR in the parser.
- `pubspec.lock` is generated and committed by `.github/workflows/lockfile.yml`
  (on the pinned Flutter; runs when a pubspec.yaml changes, or on demand with
  `upgrade` to move to newer versions deliberately). With it committed, CI
  resolves exactly what is locked; before it existed, a transitive release
  broke a build with no change of ours (objective_c 9.6.1, 2026-09-15), fixed
  with a dated `dependency_overrides` entry in the root `pubspec.yaml`. Keep
  such overrides until the lockfile and the Flutter pin have moved past them.
- Every shipped source has `pipeline/sources/<id>/NOTICE.md`; the build
  concatenates them into `meta.notices` and the app shows them. CC BY and
  CC BY-SA sources (sblgnt, wlc, lxx) require that attribution in what we
  distribute, so a new source without a NOTICE is a licensing bug, not a
  cosmetic one. `docs/licensing.md` records the reasoning per source.
- `htmltext.blocks` keeps bold only with `keep_bold=True` (Haydock's
  `Ver. N.` markers); Matthew Henry's output is unchanged by that.
- FTS5 `remove_diacritics 2` does not fold Greek accents or Hebrew points in
  the SQLite builds seen so far; search for Greek with accents. A folded
  index column is the fix if that matters.
- ruff: imports must be sorted (I001) and unused loop variables renamed (B007);
  line length 100; ruff measures display width, so Hebrew/Greek lines look
  longer than they count. `tests/_run_without_pytest.py` has no
  `pytest.mark`; write loops, not `parametrize`.
- Pages deploys only when all CI jobs pass on `main`; the content workflow
  re-triggers CI after pinning, because pushes made with the built-in token do
  not start workflows on their own.
- `reactivecircus/android-emulator-runner` runs every line of its `script`
  in a separate shell: `cd`, variables, `set -e` all end with the line.
  The first `screenshots.yml` run (2026-09-15) `cd app`-ed, ran `flutter
  drive` from the repo root, found no target, and passed. Its `script` is
  one command, `bash tools/checklist.sh <device>`, and the script itself
  fails unless eight screenshots and both timings came out of the run. A
  workflow that can pass without doing its work is a bug of the same kind
  as untested code.
- `setState(() => _x = _load())` returns the Future to `setState`, which
  asserts in debug builds only; the phone's release APK ran it for days,
  the emulator test failed on it at the first bookmark. Write the block
  form. Likewise a `TextEditingController` disposed the moment `showDialog`
  returns is still in use by the dialog animating out; a dialog owns its
  controller (`_NoteDialog`). The integration test runs a debug build, so
  it sees every assert the release build hides; treat its failures as real
  even when the phone disagrees.



## Targets: built is not the same as working

`build.yml` builds all six targets on demand and weekly; `release.yml`
publishes them on a `v*` tag. First full run: 2026-09-15 (dispatched; the
weekly cron had never fired). Results and state:

| target | built (2026-09-15) | signed | run by a person | needs |
|--------|--------------------|--------|-----------------|-------|
| Web | yes; every push (smoke) and Pages deploy | n/a | yes, daily, on Pages | — |
| Linux x64 | yes, tar.gz 80 MB; every push (smoke) | n/a | no; the checklist runs under Xvfb in `screenshots.yml` (written 2026-09-15, first run pending) | a person to run the tarball once; then Flatpak if wanted. Linux arm64 was dropped: Flutter publishes no arm64 Linux SDK |
| Android | yes: APK 126.5 MB, AAB 125.4 MB — under Play's 200 MB cap, so no Play Asset Delivery at this content size (ADR 0004) | debug key | yes (2026-09-15: the APK installed on the maintainer's phone; first-launch copy, readings, search, a bookmark surviving restart all worked). The same checklist is `app/integration_test/app_test.dart`, run on an emulator by `screenshots.yml`: green 2026-09-15 on sample and on release content; release: first launch 5.0 s (the 167 MB copy included, debug build), second 0.16 s, eight screenshots | a signing key (`app/android/key.properties`, never committed); Play account for the store |
| Windows | yes, zip 82 MB | no | no | a person to run it once; code signing is optional (SmartScreen warns without it) |
| macOS | yes, .app 214.6 MB, zip 89 MB | no | no | Developer ID certificate and notarization in the workflow (the comment in build.yml marks the spot); a person to run it once |
| iOS | yes, `--no-codesign` .app 185.7 MB | no | no | Apple developer account, provisioning, App Store or TestFlight; cannot be installed as built |

What "run by a person" checks, per target: the app opens, the content
database copies out of the bundle on first launch (native targets) or
imports into browser storage (web), Genesis 1 shows the Bibles, a verse
shows readings, search works, a bookmark survives a restart. The same
list is the integration test (`app/integration_test/app_test.dart`), with
one honest difference: its "restart" is a second app instance in the same
process after the first was disposed, not a process restart.

`gh run list --workflow=build.yml --limit 5` shows whether the jobs still
pass; `gh run list --workflow=screenshots.yml` the same for the emulator
checklist; a red one gets its log zip uploaded. Nothing in this table can
be done from the AI's side except the workflow changes (signing steps once
certificates exist, and reading logs). Accounts, certificates and devices
are the maintainer's. The plan for stores, automated per-target testing
with screenshots, donations, a local LLM chat and a narrator is
`docs/plan.md`, as spikes with acceptance and abandon conditions; it is the
roadmap for everything app-side from here.

## Known gaps (recorded, not scheduled)

Everything below is deferred on purpose, with its state as of 2026-09-15.
None is hidden in a log; this list is the place to look.

- **Ibn Ezra, 22 books; Rashi on Psalms** — no open-licensed English version
  in Sefaria's export (the build lists them). The Hebrew is complete and
  public domain. Decision open: ship Hebrew there, labelled (the reader
  handles RTL), or leave "No reading". Recommendation: ship the Hebrew.
- **Chrysostom on Matthew: 86 of 90 homilies** — four divisions in npnf110
  did not parse (no scripCom, title not a passage, or nested a level down).
  `SELECT heading FROM commentary_entries WHERE source_id='chrysostom' AND
  start_verse_id/1000000=40` against the built database shows which are
  missing; the fixture then gets their shape.
- **ICC Romans: OCR losses** — the `1. Παῦλος` line is absent from the
  Archive's text (its content sits in the `1-7.` section note); 95 pages had
  no readable running head (their text goes to the open note). The parser
  is fitted to this scan; the remaining losses are the OCR's. Better text
  means proofreading, the Google-digitised copy, or Tesseract on the JP2s.
- **Qur'an 17:33** — merged into a neighbouring verse in Gutenberg #16955;
  the Exodus 20 entry ships the other seventeen verses. Fix: take that one
  verse (or the whole text) from Wikisource's 1930 edition.
- **`analysis_options.yaml` in CI** — drift codegen modifies
  `app/analysis_options.yaml` and `packages/sr_data/analysis_options.yaml`
  on the runner (seen in the lockfile workflow's `git status --short`); the
  changes are never committed and have not been read. One run printing the
  diff settles whether to commit or ignore them.
- **Embedded psalm titles** — Psalms 23, 25, 87, 100, 130 carry their title
  inside verse 1 in the Hebrew, LXX and Douay numbering; those texts show
  no Title row there. A text heuristic could split them; not done.
- **Wide layout: no scroll-to-verse** — search hits highlight the row in
  each column but do not scroll to it on screens over 720 px.
- **Collapsed previews only collapse paragraphs** — a reading opens
  showing its first paragraph, but Rashi's and Haydock's notes have no
  paragraph breaks, so they open in full (seen in the emulator screenshots,
  2026-09-15). A character cap on the preview, cut at a sentence end,
  would fix it; not done.
- **Greek search needs accents** — FTS5 `remove_diacritics 2` does not fold
  polytonic Greek in the SQLite builds tested; `λόγος` finds John 1:1,
  `λογος` does not. A custom tokenizer or a stripped shadow column would fix
  it.
- **LXX reorder tables** — Exodus 36-40 and Proverbs 24-31 follow the LXX
  order, not the Hebrew; the mapping tables are not written, so those
  chapters' LXX text sits under LXX chapter numbers.
- **Islamic tafsir** — no open-licensed English of Ibn Kathir or another
  classical tafsir exists; the Arabic (Arabic Wikisource, CC BY-SA) plus
  labelled machine translation is the only route. Blocked on that decision,
  not on code; the Qur'an pairings are the Islamic reading meanwhile.

## Where to go next

App-side: `docs/plan.md`, in the order at its end. Item 1 (the integration
test and the Android emulator job) is done and measured; next is item 2
(S3: Flathub manifest and PWA; D1: the donations screen with links).
Content-side, below.

In rough order of value: extend the Qur'an pairings (the file is the whole
of the Islamic reading's coverage); more ICC volumes (Plummer's Luke 1896,
Skinner's Genesis 1910, Driver's Deuteronomy 1895, Briggs's Psalms 1906-07 —
Psalms needs MT numbering through the WLC trace like Rashi); Hebrew-only
fallback for Ibn Ezra books without a usable English version (a decision,
not code); a tafsir beside the Qur'an entries if an open English one
appears; find out what drift codegen writes into the two
`analysis_options.yaml` files in CI (the lockfile workflow prints
`git status --short`; commit the change or ignore it deliberately),
scroll-to-verse in the wide layout, Exodus 36-40 and Proverbs 24-31 LXX
tables, Play Asset Delivery if the AAB passes 200 MB. Each new source: verify
the upstream and its license from the actual repository, write the parser
against a real sample, wire
`sources.toml`, fixtures, tests, then the `lock → build → push` loop.
