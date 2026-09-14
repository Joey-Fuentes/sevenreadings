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
| rashi, ibn_ezra, chrysostom, ibn_kathir, icc | documented stubs in `pipeline/sevenreadings_pipeline/sources/stubs.py` | not wired; see the Planned table in `docs/licensing.md` for what each needs (chrysostom: switch upstream to CCEL; ibn_kathir: no permissive English exists) |

App: verse-by-verse phone layout, side-by-side on wide screens, translation
chips, book/chapter picker with Protestant/Catholic/Tanakh order, readings
sheet with collapsible Markdown entries, full-text search (verses per
translation, readings per source; a hit opens the chapter on that verse),
"About the texts" (book picker, last entry: licenses from the database and
the notices the pipeline stores in `meta.notices`). No notes or bookmarks
yet (the schema and `UserDb` exist for them).

## Setting up a session (AI side)

The maintainer will upload two things: the repo as `sevenreadings_tar.gz`
(a Termux `tar` of `~/sevenreadings`, so paths start with
`data/data/com.termux/files/home/`) and a ruff wheel or the `pipeline-wheels`
artifact from the `Tools for offline review` workflow.

```
mkdir -p /home/claude/in && tar -xzf /mnt/user-data/uploads/sevenreadings_tar.gz -C /home/claude/in
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

## Where to go next

In rough order of value: Chrysostom from CCEL's NPNF (public domain; not
the HistoricalChristianFaith database, which states no license), the Jewish
commentaries from Sefaria-Export filtered to versions whose `license` is
public domain or CC BY, notes/bookmarks,
scroll-to-verse in the wide layout, Exodus 36-40 and Proverbs 24-31 LXX
tables, Play Asset Delivery if the AAB passes 200 MB. Each new source: verify
the upstream and its license from the actual repository, write the parser
against a real sample, wire
`sources.toml`, fixtures, tests, then the `lock → build → push` loop.
