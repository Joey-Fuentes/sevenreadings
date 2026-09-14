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
| sblgnt | SBL Greek New Testament (CC BY 4.0) | live |
| wlc | Hebrew Bible, Westminster Leningrad Codex via OSHB (CC BY 4.0), Masoretic numbering mapped at ingest | live |
| lxx | Septuagint, Swete's edition via nathans/lxx-swete (CC BY-SA 4.0), LXX numbering mapped at ingest | live, known gaps: Exodus 36-40 and Proverbs 24-31 reordered, Ecclesiastes missing upstream |
| matthew_henry | Matthew Henry's Commentary, CCEL public-domain HTML edition | live (Protestant reading) |
| rashi, ibn_ezra, haydock, chrysostom, ibn_kathir, icc | documented stubs in `pipeline/sevenreadings_pipeline/sources/stubs.py` | not wired; ibn_kathir blocked on licensing |

App: verse-by-verse phone layout, side-by-side on wide screens, translation
chips, book/chapter picker with Protestant/Catholic/Tanakh order, readings
sheet with collapsible Markdown entries. No search UI, notes, or bookmarks yet
(the schema and `UserDb` exist for them).

## Setting up a session (AI side)

The maintainer will upload two things: the repo as `sevenreadings_tar.gz`
(a Termux `tar` of `~/sevenreadings`, so paths start with
`data/data/com.termux/files/home/`) and a ruff wheel or the `pipeline-wheels`
artifact from the `Tools for offline review` workflow.

```
mkdir -p /tmp/in && tar -xzf /mnt/user-data/uploads/sevenreadings_tar.gz -C /tmp/in
rm -rf /home/claude/sevenreadings && cp -r /tmp/in/data/data/com.termux/files/home/sevenreadings /home/claude/
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
- ruff: imports must be sorted (I001) and unused loop variables renamed (B007);
  line length 100; ruff measures display width, so Hebrew/Greek lines look
  longer than they count.
- Sources are renumbered at ingest to canonical ids (`versification.py`); the
  build prints every verse that has no counterpart in the reference
  translation, per book. Trust that report over memory: the Hebrew rule table
  was right first time; the Septuagint's was corrected three times from data.
- The Swete LXX digitisation advances chapter numbers one line early in ~90
  places; `parse_tokens` repairs that. Its Psalms are LXX-numbered throughout.
- Pages deploys only when all CI jobs pass on `main`; the content workflow
  re-triggers CI after pinning, because pushes made with the built-in token do
  not start workflows on their own.

## Where to go next

In rough order of value: Haydock (Catholic; pairs with a Douay-Rheims Bible),
Chrysostom (NPNF), the Jewish commentaries once Sefaria's per-text licenses are
settled, Byzantine Majority Text for the NT, search UI, notes/bookmarks,
Exodus 36-40 and Proverbs 24-31 LXX tables, Play Asset Delivery if the AAB
passes 200 MB. Each new source: verify the upstream and its license from the
actual repository, write the parser against a real sample, wire
`sources.toml`, fixtures, tests, then the `lock → build → push` loop.
