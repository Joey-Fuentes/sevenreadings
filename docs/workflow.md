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
Entries that share one archive (douay and haydock) need one `lock --write`.

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

Site: `https://<owner>.github.io/sevenreadings/`. Hard-refresh after a deploy.

## Dependabot

Merge GitHub Actions bumps when CI is green. Dart-group bumps get a look
first; one of them moved sqlite3 to 3.x, which was fine, but a future one
could change drift codegen. The limit of 5 open PRs per ecosystem means more
appear after you merge.

## Giving the AI what it needs

- Repo: `cd ~ && tar -czf ~/storage/downloads/sevenreadings_tar.gz sevenreadings`
  then upload the file. (Excluding `pipeline/.cache` keeps it small:
  `tar --exclude=sevenreadings/pipeline/.cache -czf …`.)
- Tools: run `gh workflow run tools.yml`, then `gh run download -D ~/storage/downloads`
  and upload the `pipeline-wheels-*` zip (ruff + pytest + httpx, matching CI).
- CI failures: the run's log zip.
- Anything about an upstream's layout: the `unzip -p` / `gh api` output above.

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
