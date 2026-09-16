# Day-to-day workflow (Termux)

Everything the maintainer runs, with the nuances that matter. Assumes
`~/sevenreadings` is the clone, `gh` is authenticated, and
`git config --global pull.rebase true` is set.

## Applying a patch from the AI

```
cd ~/sevenreadings
git apply -p1 ~/storage/downloads/<name>.patch
git add -A && git commit -m "<message>" && git pull && git push
```

- **Every patch has a unique name** (a tag or date in the file name; the
  AI's hard rule, `AGENTS.md`). If a download lands as `<name>-1.patch`, an
  older file of that name is already in the folder and is the wrong one:
  `ls -lt ~/storage/downloads/<name>*` shows which is newest, and a new
  file's header reads `--- ... 1970-01-01`. A patch that says "No such
  file or directory" for a file it should create was the stale download.
- Commit **before** `git pull`; with rebase pulls, a dirty tree refuses to pull.
- `git pull` is required before nearly every push: the content bot commits
  `app/content.lock` to `main` after each content release.
- If `git apply` reports `patch does not apply` on `pipeline/sources.toml`,
  the AI's copy of the pins is stale. Apply the rest of the patch by excluding
  that file (`git apply -p1 --exclude=pipeline/sources.toml …`) and make the
  toml edit by hand or with the Python snippet the AI provides.
- Patches are all-or-nothing: on failure nothing was applied.

## Adding or updating a source: the whole loop

Every step in one place. The AI's patch leaves `sha256 = "TODO"` (and, for
GitLab upstreams, `COMMIT` in the url); nothing builds until both are real.

```
cd ~/sevenreadings/pipeline
# 1. Commit-pinned upstreams: put the commit in the url first.
gh api repos/<owner>/<repo>/commits/master --jq .sha                      # GitHub
curl -s https://gitlab.com/api/v4/projects/<owner>%2F<repo>/repository/branches/master | jq -r .commit.id   # GitLab
sed -i "s/COMMIT/<that sha>/g" sources.toml
# 2. Record the hash. --write edits sources.toml (every entry sharing the url).
python -m sevenreadings_pipeline.cli lock --write <source>
# 3. Build with the reference translation, read the report.
python -m sevenreadings_pipeline.cli build --version dev --only web,<source> --out dist/sevenreadings.sqlite
# 4. Settle numbering from data, then push.
python -m sevenreadings_pipeline.cli probe --db dist/sevenreadings.sqlite --translation <source> --books Exod,Job
```

Step 2 without `--write` only prints the hash; the old way was
`sed -i '/<unique part of the url>/{n;s/TODO/<hash>/}' sources.toml`.
Entries that share one archive (douay and haydock) need one `lock --write`;
entries with a `urls = [...]` list (matthew_henry, chrysostom) get every
element written by one `lock --write`. Sources pinned by `commit` with no
url (rashi, ibn_ezra: Hugging Face) have nothing to lock; the commit is the
pin. Newer: https://huggingface.co/Sefaria/database_export/commits/main.

**A build with an unpinned source stops at that source and leaves a partial
database.** Everything that followed it in `--only` is missing, and `probe`
on that file prints `0/N` for every chapter. That is not a numbering
problem; go back to step 2.

`probe` prints, per chapter, the source's own verse count against the
reference's, only where they differ; it is how numbering schemes get settled.
It compares chapter N with chapter N, so for Psalms in LXX/Vulgate numbering
(Douay 17 is English 18) most lines are noise: read the build report's
"verses with no counterpart" lines for those instead.

Pushing anything under `pipeline/` (or the content schema) runs the Content
release workflow, which publishes `content-v<date>-<sha>`, pins it, and
re-runs CI so Pages deploys the new content. No manual step.

## Inspecting an upstream (when the AI asks)

The download cache is `pipeline/.cache/<16-hex>_<last URL segment>`, so
match on the commit or file name, not the repo name:

```
Z=$(ls .cache/*<commit-or-file>*.zip)
unzip -l "$Z" | head
unzip -p "$Z" '<member path>' | head -c 6000
gh api repos/<owner>/<repo>/contents/<dir> --jq '.[].name'
gh api -H "Accept: application/vnd.github.raw" repos/<owner>/<repo>/contents/<file> | head -20
```

When several files need grepping, extract once into scratch space and work
there. Never `/tmp`: Termux has no writable `/tmp`, so the extraction fails
and everything chained after it fails with it.

```
mkdir -p ~/scratch && rm -rf ~/scratch/src && unzip -q -o "$Z" '<glob>' -d ~/scratch/src
cd ~/scratch/src/*/
grep -a -l '<pattern>' *.html | head
```

## CI, logs, Pages

```
gh run list --limit 5
gh run watch
gh run view --log-failed            # or download the run's logs from the web UI and upload the zip to the AI
```

CI = `ci.yml` (analyze, tests, ruff, web + Linux smoke build, Pages deploy on
`main` when everything passes). `build.yml` builds all six targets on demand
or weekly. `release.yml` publishes app binaries on a `v*` tag.

Site: https://sevenreadings.org/ — the Pages custom domain (Settings >
Pages), DNS at the registrar (four A and four AAAA records on the apex to
GitHub Pages' addresses, `www` a CNAME to `joey-fuentes.github.io`),
`app/web/CNAME` in the build, `--base-href "/"` in ci.yml; sevenreadings.com
is a registrar-level 301 to it. The site is a PWA: `tools/web-sw.py` writes
its service worker after every build, so after a deploy a browser that has
the old cache shows the new build on its second load (the worker updates
in the background); to see it at once, clear the site's data in the
browser.

## The first-launch checklist on a device

`app/integration_test/app_test.dart` is the checklist a person did by hand
on 2026-09-15 (launch and content copy, Genesis 1 with the chips, a verse's
readings, bookmark and note, search, a second launch with both still
there). With a Flutter toolchain and a connected device, emulator or
simulator:

```
cd app
flutter test integration_test -d <device>                   # the checks only
flutter drive --driver=test_driver/integration_test.dart \
  --target=integration_test/app_test.dart -d <device>       # checks + screenshots
```

`flutter drive` writes `app/screenshots/*.png` (gitignored) and the launch
timings to `app/build/integration_response_data.json`; `flutter test` runs
the same assertions but drops the screenshots, because nothing on the host
receives them. `bash tools/checklist.sh <device>` is the drive plus the
check that ten screenshots and both timings came out (under
`xvfb-run -a -s "-screen 0 1280x800x24"` for a headless Linux run). The
maintainer has no Flutter locally, so in practice this runs in CI, below.

## The checklist in CI (screenshots.yml)

`screenshots.yml` runs the same `flutter drive` (`tools/checklist.sh`) on
an Android emulator (API 34, Pixel 6; about nine minutes: boot 40 s, debug
APK 4 min, the test 27 s), on the Linux build under Xvfb, and on headless
Chrome (which then also builds the site and proves it works offline),
with the pinned release content, on demand, every Monday, and on every
`v*` tag. The newest successful run's screenshots are published by the
next site deploy at https://sevenreadings.org/screenshots/ (T4).
Not on pushes. A job is green only if ten screenshots and both launch
timings came out of its run; the script checks and says so.

```
gh workflow run screenshots.yml                       # release content
gh workflow run screenshots.yml -f content=sample     # fixture content, faster
gh run watch
gh run download -n screenshots-android -D ~/storage/downloads/screenshots-android
gh run download -n screenshots-linux -D ~/storage/downloads/screenshots-linux
gh run download -n screenshots-web -D ~/storage/downloads/screenshots-web
```

Each artifact holds the ten PNGs and `integration_response_data.json`
(`first_launch_ms` with the content copy, `second_launch_ms` without, and
`view`, the window size in dp, which says whether the phone or the
side-by-side layout was exercised); the Android one adds `logcat.txt`. A
red run gets its log zip uploaded to the AI like any other; the
screenshots travel with it, since they are written before the failure is
reported. When a run has passed, its numbers go into `docs/plan.md`
(section 2, State) and anything it found into `AGENTS.md`.

## Releasing

A release is a `v*` tag: `git tag v0.1.0 && git push origin v0.1.0` runs
`release.yml` (every target's artifacts on the GitHub release, unsigned
until S1) and `screenshots.yml` (the checklist on every target with the
release content). Per store, once the accounts exist, the console steps go
here. Today:

- **Flathub** (`packaging/flatpak/`): after tagging, run
  `gh workflow run flatpak-sources.yml -f tag=v0.1.0`; it regenerates
  `org.sevenreadings.SevenReadings.yml` (built from source at that tag,
  offline, by `flatpak-flutter`) and commits it with `flutter-sdk-*.json`,
  `pubspec-sources.json` and `setup-flutter.sh`. Set the same version and
  date in the metainfo's `<releases>`, run `screenshots.yml` and confirm
  the `flatpak` job is green (Flathub's own builder, sandboxed, and their
  three lints), then open a PR to https://github.com/flathub/flathub (a
  branch off `new-pr` on a fork; the generated manifest and files,
  `flathub.json`, the desktop file, the metainfo, the icon files, the
  launcher). Re-run `flatpak-sources.yml` whenever dependencies, Flutter
  or the content release change. After acceptance, Flathub's bot opens an
  update PR per release
  from the manifest's `x-checker-data`. The metainfo's screenshots point at
  the site's copies; make sure the last `screenshots.yml` run was with the
  release content (the Monday run, or a dispatch without the sample
  input) before submitting, or the store shows fixture texts.

## Dependabot

Merge GitHub Actions bumps when CI is green. Dart-group bumps get a look
first; one of them moved sqlite3 to 3.x, which was fine, but a future one
could change drift codegen. The limit of 5 open PRs per ecosystem means more
appear after you merge.

## Starting an AI session

Upload two files, then paste the prompt below. Nothing else is needed to
begin; CI log zips and screenshots follow as the work produces them.

1. The repo: `rm -rf ~/sevenreadings.tar.gz && tar -czvf ~/sevenreadings.tar.gz ~/sevenreadings`
   (arrives as `sevenreadings_tar.gz`; includes `pipeline/.cache`, which
   the AI uses instead of the network).
2. The tools, if the AI's sandbox turns out to lack ruff or pytest (it says
   so on its first command): `gh workflow run tools.yml`, wait for it, then
   `gh run download -D ~/storage/downloads` and upload the
   `pipeline-wheels-*` zip. Without it the AI can still run the tests
   (`tests/_run_without_pytest.py`) but not lint.

The prompt:

```
You are picking up the sevenreadings project. I have uploaded the repo as a
Termux tarball (sevenreadings_tar.gz; paths inside start with
data/data/com.termux/files/home/). Unpack it and read AGENTS.md first, in
full; it is the handoff and states the constraints: I work on an Android
phone in Termux with no Flutter, you work in a sandbox with no network, and
CI is the only machine that runs Flutter. Then read docs/plan.md, which is
the roadmap for everything app-side, and the Known gaps section of
AGENTS.md, which lists every deferral.

How we work:
- You deliver changes as unified diff patches against my tree (docs/workflow.md
  and AGENTS.md, "How changes are delivered"); I apply them with
  git apply -p1, run what you tell me, and paste the output or upload the
  CI log zip. Give me copy-pastable commands every time. Every patch file
  gets a name never used before, and you diff against the tree I have,
  not a scratch copy (the two hard rules in AGENTS.md).
- Verify before claiming: run the pipeline's ruff and tests on the tree
  before every patch; for Dart, state that CI is the check and read its
  logs when I upload them. Never say something works that has not run.
- Every fact about a source's layout or license comes from reading the
  real thing (the cached upstream files in pipeline/.cache, or something I
  paste), not from memory.
- No /tmp anywhere. No new dependency, model, service or text that costs
  money or is not open source; if a goal cannot be met that way, say so and
  record it.
- Do not quietly defer. Anything you decide not to do goes into the Known
  gaps section of AGENTS.md in the same patch, with its state and what
  would resolve it. Anything you finish updates the relevant doc in the
  same patch (AGENTS.md tables, docs/plan.md spike results, notices).
- Keep the documentation true: when you change behaviour, change the docs
  that describe it.

The task for this session: <state it, or: "start on docs/plan.md, order
item 1 (the integration test and the Android emulator screenshots), and
continue down the order as each item is verified">.

Begin by unpacking the repo, running the pipeline's tests, and telling me
in a few lines what state you found and what you will do first.
```

## Giving the AI what it needs

Repo: make the archive, then upload `~/sevenreadings.tar.gz` (it arrives as
`sevenreadings_tar.gz`; that is fine).

```
rm -rf ~/sevenreadings.tar.gz && tar -czvf ~/sevenreadings.tar.gz ~/sevenreadings
```

That includes `pipeline/.cache`, the fetched upstreams (about 200 MB), which
lets the AI read real upstream files offline. When only the code matters,
the same without the cache is a couple of megabytes:

```
rm -rf ~/sevenreadings.tar.gz && tar --exclude=sevenreadings/pipeline/.cache -czvf ~/sevenreadings.tar.gz -C ~ sevenreadings
```

- Tools: run `gh workflow run tools.yml`, then `gh run download -D ~/storage/downloads`
  and upload the `pipeline-wheels-*` zip (ruff + pytest + httpx, matching CI).
- CI failures: the run's log zip (`gh run view --log-failed` is the short
  form; the zip has everything).
- Anything about an upstream's layout: the `unzip -p` / `gh api` output above,
  or a small Python snippet the AI writes that prints the relevant part to a
  file under `~/storage/downloads` for upload.

## Odds and ends

- `pkg install ruff` in Termux lets you run `ruff format . && ruff check --fix .`
  in `pipeline/` before pushing, which catches the two classes of failure
  CI has ever raised on Python.
- There is no `/tmp` in Termux. Scratch files go under `~/scratch`; anything
  the AI hands over that mentions `/tmp` is a bug in the handover, not in the
  phone.
- `python -m sevenreadings_pipeline.cli sources` lists sources and their
  license status; `blocked` ones are skipped by builds.
- The web app persists the content database in the browser after first load;
  Pages has a soft 100 GB/month bandwidth limit, so it is a demo host, not a
  distribution channel.

## Dart dependencies

`pubspec.lock` is committed and owned by the "Dart lockfile" workflow (first
run 2026-09-15, Flutter 3.47.4). A
change to any pubspec.yaml regenerates it on the pinned Flutter and commits
it; to take newer versions on purpose, run the workflow by hand with
`upgrade` (`gh workflow run lockfile.yml -f upgrade=true`). Nobody needs a
machine with Flutter for this. If a transitive release breaks CI before the
lockfile has caught up, the pattern is a dated `dependency_overrides` entry
in the root `pubspec.yaml` with its removal condition written beside it.
The workflow's log also shows (`git status --short`) that drift codegen
modifies `app/analysis_options.yaml` and `packages/sr_data/analysis_options.yaml`
on the runner; those changes are not committed, and what they are has not
yet been looked at.
