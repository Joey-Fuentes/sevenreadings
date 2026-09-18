# Plan: stores, testing, donations, chat, narrator

Written 2026-09-15 after the first full build of all targets and the first
install on a device. Five goals, each broken into spikes small enough to
finish in one session and judge honestly. Every spike names what it proves,
how, and (where the goal could cost money or fail on principle) when to
abandon it. Read `AGENTS.md` first for the project's constraints; the
short version: the maintainer works on a phone, CI is the only machine
with Flutter, and nothing may cost money or be closed source.

Division of labour, stated once: CI configuration, tests, screenshots,
signing steps, the app code — the AI can do all of it and verify most of it
through CI artifacts. Store accounts, certificates, tax forms, policy
reviews, and pressing "publish" are the maintainer's; each is marked
**(maintainer)** below.

## 1. Stores: one tag publishes everywhere

Goal: pushing a `v*` tag builds, signs, tests and submits every target
without further steps; a person's involvement is limited to approving a
release in each store's console, and to the one-time setup.

### Accounts and one-time setup

| store | account (maintainer) | cost | what CI needs as secrets |
|-------|----------------------|------|--------------------------|
| Google Play | Play Console developer account | $25 once | upload keystore + passwords; a Play Console service-account JSON with release rights |
| Apple App Store (iOS) and Mac App Store | Apple Developer Program | $99/year | App Store Connect API key (issuer, key id, .p8); distribution certificate and provisioning profiles (or fastlane match with a private repo) |
| macOS outside the store (notarized DMG) | same Apple account | included | Developer ID Application certificate + notarytool credentials |
| Microsoft Store | Partner Center individual account | ~$19 once | Partner Center tenant/client/secret for the `msstore` CLI; an MSIX signing certificate (Store-signed on submission) |
| Linux | none: the `.flatpak` bundle on each release is the channel; Flathub deferred (S3 state) | free | none |
| Web | GitHub Pages (already live) | free | none |

Nothing else costs money. If the maintainer chooses not to pay for the
Apple program, iOS and macOS stop at "unsigned artifact" and the rest of
this plan is unaffected.

### Per-target pipeline (what `release.yml` will do)

- **Android**: `flutter build appbundle` signed with the keystore from
  secrets (`app/android/key.properties` written at build time, never
  committed); upload to Play's internal testing track via the Play
  Developer API (fastlane `supply` or an equivalent action); promotion to
  production is a console click (maintainer). Also the direct-install APK
  as a release asset, `--split-per-abi`.
- **iOS**: `flutter build ipa` with the export options for App Store
  distribution; upload to TestFlight with the App Store Connect API key;
  submission to review is a console click (maintainer).
- **macOS**: two outputs. A notarized DMG for direct download (Developer ID
  signing + `notarytool` in the workflow, where the comment in `build.yml`
  marks the spot). Optionally the Mac App Store through the same App Store
  Connect route as iOS.
- **Windows**: package as MSIX (the `msix` pub package), submit with the
  `msstore` CLI to a Partner Center product; also a plain zip as a release
  asset for people who do not use the Store. Code signing outside the Store
  is optional (SmartScreen warns without it) and costs money, so: Store
  route only, plus unsigned zip.
- **Linux**: the tar.gz as a release asset (exists), plus Flathub: a
  manifest repo `org.sevenreadings.sevenreadings` submitted to Flathub once;
  after that, Flathub's bot opens an update PR per release (maintainer
  merges). Flatpak manifest lives in this repo under `packaging/flatpak/`
  and is what the Flathub repo points at.
- **Web**: Pages (exists). Add a PWA manifest and service-worker caching of
  the content database so the site installs and works offline; that is a
  small change and belongs before any store work because it is free.

### Before any of it: the platform folders and an icon

Every item below edits files under `app/android`, `app/web`, `app/linux`
and the rest, and until 2026-09-15 those folders did not exist in git:
nine `flutter create` steps regenerated them from the template on every
build. `bootstrap.yml` (run once, by hand) creates all six, sets the
application id `org.sevenreadings.SevenReadings` (see `AGENTS.md`,
"Identity") and commits them; the create steps are gone since. Nothing in the
tree is an app icon either; every target ships Flutter's placeholder,
which neither Flathub nor the stores accept. Since 2026-09-15 there is
one: `tools/icons.py` draws seven bookmark ribbons on the app's brown and
writes every platform's icon set from that (Android legacy and adaptive,
iOS, macOS, Windows `.ico`, PWA and favicon, SVG and PNGs under
`packaging/icon/` for Linux and Flatpak); CI fails if a committed icon
drifts from the script. A first draft for the maintainer to keep or
replace: a different design is a change to one function in that script.

### Spikes

- **S1. Signing without secrets in git**: write the secret-to-file steps for
  Android and the Apple certificate import for macOS runners, with the
  workflow refusing to run the signing steps when secrets are absent (so
  forks and canaries still build unsigned). Proof: a dispatch run with no
  secrets builds unsigned as today; a run with secrets produces a signed
  AAB (`apksigner verify` in the log) and a notarized DMG (`spctl -a -vv`
  in the log). Needs: the maintainer to create the keystore and, if
  paying, the Apple certificates.
- **S2. Upload steps**: Play internal track, TestFlight, `msstore` submit,
  each behind "secrets present". Proof: the artifact appears in the
  console. Needs: the accounts.
- **S3. Flathub manifest** and a PWA manifest: both free, both provable in
  CI (`flatpak-builder` in a job; Lighthouse's installability check).
- **S3, PWA (2026-09-16): done**; the `web` job's offline proof passed:
  reader up, service worker in control, network cut, reload, reader back.
  On a phone: Chrome, Install app, airplane mode, open again. `app/web/`:
  `manifest.json` (name, icons incl. maskable, standalone, root scope),
  our `flutter_bootstrap.js` (keeps a loading line on screen through the
  white phase; Flutter's own service worker is gone from the template),
  `index.html` registering `sw.js`, which `tools/web-sw.py` writes after
  every build from the files the build actually produced: everything but
  the content database is precached (about 20 MB; the database lives in
  the browser's storage once loaded, so the app is complete offline after
  one visit), a new build is a new cache and old ones are dropped. The
  app's first screen says what the wait is (native too: the copy). Proof
  is the `web` job (T3 web, above), not Lighthouse: its PWA category was
  removed in Lighthouse 12. The Pages bandwidth note stands: a demo host.
- **S3, Flatpak, tarball route (2026-09-16): proven in CI end to end.**
  Fifth run green: Flathub's builder, their manifest, metainfo and repo
  lints, install, and the sandboxed first launch in 2011 ms with Genesis
  1 rendered on the virtual display. Not the manifest to submit (below).
  `packaging/flatpak/`: the manifest Flathub receives (freedesktop 26.08,
  no network permission, the Linux release tarball as the app module with
  `x-checker-data` on the latest GitHub release), a launcher, the desktop
  file, the AppStream metainfo (screenshots from the site, the Stripe link
  as the donation URL) and the icon from `packaging/icon/`. The `flatpak`
  job in `screenshots.yml` builds the Linux bundle, runs Flathub's linter
  on the manifest and the metainfo, builds the Flatpak from that bundle
  through the same manifest (a tool since retired swapped the archive
  for the directory), lints the build, and launches it in the
  sandbox under Xvfb (`tools/flatpak-smoke.sh`: the content database
  appears in the sandbox's data directory, a window titled Seven Readings
  exists, an X screenshot is kept as `screenshots-flatpak`). Second run
  (2026-09-16): manifest and metainfo pass Flathub's linter, the build
  exports; the built-app lint wanted the screenshots mirrored the way
  Flathub's build does it. Researched in Flathub's docs (2026-09-16):
  mirroring needs `--mirror-screenshots-url` *and*
  `--compose-url-policy=full`, its evidence is the `screenshots/x86_64`
  ref of the exported OSTree repo, and the check Flathub runs is `repo`,
  not `builddir`; both errors are "never granted" exceptions, so the build
  is the fix, and the job now runs Flathub's own builder with those flags.
  The same research changed the submission plan: Flathub requires
  source-available apps to be built from source, and since offline
  Flutter builds exist (`flatpak-flutter`: a pinned Flutter SDK module, a
  generated offline pub cache, `flutter build linux --no-pub`), a prebuilt
  tarball is expected to be refused for a new Flutter app. The tarball
  manifest is what CI proves today; the manifest to submit is the
  source build, the next patch, proven the same way. The metainfo, icons,
  permissions and launch smoke carry over unchanged. Fourth run
  (2026-09-16), with that recipe plus a session bus for the sandboxed
  builder: manifest, metainfo and repo lints pass, the Flatpak installs,
  and the app launched in the sandbox on the virtual display with Genesis
  1 rendered (the X screenshot shows it); the smoke's own check for the
  copied database looked for the wrong file name, fixed. The Linux
  window is titled "Seven Readings" since. Submission is the maintainer's
  (docs/workflow.md, "Releasing") and needs the first tag; the tarball
  route is the one CI proves, and if Flathub's review asks for a build
  from source inside the sandbox, that is a second manifest and a new
  entry here, not a silent change.
- **S3, Flatpak, source route (2026-09-16): proven in CI end to end**, in
  Flathub's sandbox with no network: the vendored Flutter SDK built, the
  offline `pub get` resolved the workspace, drift's codegen ran (42 s, on
  the bare Dart VM, see below), SQLite compiled from its amalgamation by
  `package:sqlite3`'s own hook, `flutter build linux` succeeded, install,
  Flathub's manifest, metainfo and repo lints passed (the only warning:
  runtime 26.08 available, the LLVM extension not having it yet), and the
  app launched in the sandbox in 1011 ms with the release content, six
  translations side by side, Hebrew right to left. The manifest to submit
  is `packaging/flatpak/org.sevenreadings.SevenReadings.yml` as the
  generator writes it; the tarball manifest is gone (git history has it).
  **Flathub itself: not submitted, by decision (2026-09-16).** A first PR
  (flathub/flathub#10252) was closed by their bot for a missing
  checklist; reading the checklist and the requirements it points at
  changed the plan. Their Generative AI policy requires disclosing
  AI-generated code and packaging with its extent, lets reviewers reject
  on that extent alone, and forbids AI-written PR descriptions, commit
  messages and review replies; their development-history requirement
  generally refuses apps that have existed only briefly. This project is
  two days old and nearly all of it, this manifest included, was written
  with an AI. So the Linux channel is the `.flatpak` bundle the `flatpak`
  job now builds and attaches to every tagged release (installable with
  one command, runtime from Flathub); the store waits for history and
  users, and for a submission written entirely by the maintainer
  (docs/workflow.md, "Releasing"). How it got here:
  `packaging/flatpak/flatpak-flutter.template.yml` is the manifest as
  written by hand: freedesktop 25.08 with the `llvm21` SDK extension
  (Flutter's Linux build needs clang, the base SDK has none, and the
  extension has no 26.08 branch yet), no network permission, and one
  module that builds the app from source inside the sandbox: the repo at
  a pinned commit or tag, Flutter at tag 3.47.4, `flutter pub get
  --offline` for the workspace, drift's codegen, `flutter build linux
  --release --no-pub`, the content database and its manifest as
  checksummed files from the content release (from `app/content.lock`).
  `flatpak-sources.yml` renders it (`tools/flatpak-template.py`), runs
  `flatpak-flutter` (MIT; Flathub's de-facto tool for Flutter apps, which
  replaces the Flutter source with an offline SDK module and vendors the
  pub cache, under `generated/`) and commits the generated
  `org.sevenreadings.SevenReadings.yml` and its files. The `flatpak` job then builds that manifest with Flathub's
  builder under `--sandbox` (no network), lints it three ways, and
  launches it. The tarball manifest is kept as
  `org.sevenreadings.SevenReadings.tarball.yml`, proven but not
  submittable. Two facts the first runs settle, both researched to the
  edge of what is documented: whether `flatpak-flutter` copes with a pub
  workspace whose lock file is at the root rather than next to
  `app/pubspec.yaml` (runs 1 and 2 said no to both `--app-pubspec` forms;
  reading the tool's code settled it: those flags name directories that
  must hold a `pubspec.lock`, and with no flags it reads the root's, the
  workspace's only lock, which names every member's packages), and
  whether it vendors the
  prebuilt SQLite that `sqlite3` 3.6.0's build hooks download. Run 3
  generated everything and the sandboxed build got as far as the tool's
  own patch for `sqlite3`'s hook, written for another version, which did
  not apply to 3.6.0 (the very thing the wger project warns about). The
  answer is in `package:sqlite3`'s own documentation, not in anyone's
  registry: the `source: source` user-define compiles SQLite from its
  amalgamation with the package's compile-time options (FTS5 included).
  The sandbox build appends that to the workspace pubspec and the
  manifest supplies the amalgamation (the current one on sqlite.org at
  generation time, pinned with its checksum in the rendered manifest; the
  exact 3.53.3 that 3.6.0 bundles is not on the download page and parity
  is not needed) as a checksummed source; a `foreign.json` beside the
  template keeps the tool's registry entry out. Every other platform keeps
  the prebuilt library. `flathub.json` limits Flathub's builds to x86_64
  for now. Then codegen: `dart run build_runner build` blocked silently in
  the sandbox, run after run (ten minutes, no output even verbose). A
  ladder proved `dart --version` and `dart pub get --offline` answer within
  a second; a process dump proved `dart run` was one process in a futex
  wait with no files open and no children, i.e. its command-line layer
  blocking at start-up before touching the project; a home inside the
  sandbox and telemetry off (`CI=true`) changed nothing. Running the bare
  VM on build_runner's entrypoint (`dart --disable-dart-dev --packages=…`)
  did the same work in 42 s, and that is what the manifest does. Why
  `dart run`'s layer blocks in this nested sandbox is not known; it is
  written down in `AGENTS.md` as a trap, not solved.
- **S1 (2026-09-17): written, Android provable now, Apple waits for the
  account.** `build.yml` reads the secrets named in docs/workflow.md
  ("Signing") and builds unsigned without them: Android writes
  `key.properties` and the keystore from `ANDROID_KEYSTORE_*`, and a step
  after the build prints the certificate of the APK and the AAB
  (`apksigner`, `keytool`) and fails if it is the debug key while secrets
  exist, or not the debug key while they do not (that half ran on the next
  build: pending). macOS imports a Developer ID `.p12` into a temporary
  keychain (`.github/actions/apple-keychain`), signs frameworks then app
  with the hardened runtime and `Release.entitlements`, makes a DMG, signs
  it, notarizes it with the App Store Connect API key, staples and checks
  it with `spctl`. iOS uses only the API key: `flutter build ios
  --config-only`, then `xcodebuild archive` and `-exportArchive` with
  `-allowProvisioningUpdates` and the key, `app/ios/ExportOptions.plist`
  (`app-store-connect`, automatic signing, team id from a secret), which
  is Apple's cloud signing and creates the managed distribution
  certificate; Developer ID cannot be cloud-managed (Apple bug
  FB16835802), which is why macOS needs the `.p12`. The Apple steps have
  not run: no account yet. Their proof, when it exists, is the first
  signed run's log (notarytool "Accepted", `spctl` "accepted", the
  `.ipa`); until then they are code written against the documentation,
  and any failure there is a new entry here, not a surprise.
- **S4. Store listings as code**: `fastlane/metadata`-style directories
  with descriptions, keywords, privacy answers, and the screenshots from
  section 2, so a listing is reproducible from the repo.

Order: S3 first (no cost, no gate), S1, S2, S4. Documented output: this
file's tables kept current, and `docs/workflow.md` gains a "Releasing"
section with the tag command and the console clicks per store.

## 2. Testing: every target runs, and shows it

Goal: on every push, and on every tag, each target is launched on an
emulator, simulator or headless desktop, walked through the first-launch
checklist, and screenshotted; the screenshots are artifacts a person can
open, and later the store listings.

The checklist (the one a person did by hand on Android, 2026-09-15):
launch and first content copy/import; Genesis 1 with the Bible chips; a
verse's readings with the seven traditions; a search; a bookmark and a
note; restart with both still there and an instant second launch.

- **T1. Integration test**: `app/integration_test/app_test.dart` using
  `integration_test` and `IntegrationTestWidgetsFlutterBinding.takeScreenshot`,
  driving the checklist against the sample content (fast) and the release
  content (the real first-launch copy). Runs anywhere `flutter test
  integration_test` runs.
- **T2. Android emulator in CI**: `reactivecircus/android-emulator-runner`
  (API 34, x86_64, no snapshot), `flutter test integration_test` on it,
  screenshots to `screenshots-android`. This is the highest-value one: it
  is where a phone-shaped bug shows.
- **T3. iOS simulator** on the macOS runner (`xcrun simctl boot`, then the
  same test); **macOS** app on the same runner; **Windows** on the Windows
  runner (has a desktop session); **Linux** under `xvfb-run`; **Web** with
  `flutter drive -d chrome` (chromedriver, headless).
- **T4. Publish the screenshots**: one job collects `screenshots-*` into a
  contact-sheet HTML on Pages under `/screenshots/`, so the state of every
  target is one URL away, dated. Store-ready framed versions come from the
  same files later (S4).

Abandon conditions: none; all of this is free and standard. Risk: emulator
jobs are slow (10-20 minutes) and occasionally flaky; run them on tags and
weekly, and on demand, not on every push.

### State

- **T1 and T2: done, 2026-09-15, proven on sample content.** Fifth run of
  `screenshots.yml` green: `app/integration_test/app_test.dart` walked the
  whole checklist on an API 34 Pixel 6 emulator and the `screenshots-android`
  artifact holds the PNGs (eight then; nine since D1, ten since N1), `integration_response_data.json` and the
  device log. Measured: first launch to Genesis 1 with its verses, content
  copy included, 2922 ms; second launch 168 ms (the copy skipped, both
  databases reopened; the bookmark and note back). Sixth run, release
  content (the pinned 167 MB database): first launch 4999 ms, second
  157 ms; the screenshots show the real texts, and the search rankings
  match what the offline build predicted. The job takes 8-9 minutes:
  emulator boot 40 s, debug APK build about 4 minutes, the test 27 s.
  Debug build, so the copy on a release build will be somewhat faster;
  the number to beat is five seconds with a spinner.
- What the runs found on the way, all fixed in the tree: two debug-only
  assertions in the app that the release APK on the phone never showed
  (`setState` with an arrow returning the reload Future, in the readings
  sheet and the notes screen; the note dialog disposing its text
  controller while still animating out), and on the CI side the
  emulator-runner executing each `script` line in its own shell, which
  let a job pass having run nothing (now one command plus a step that
  fails unless eight screenshots and both timings exist). Test-side
  lessons are in `AGENTS.md`: lazy lists need scrolling before a finder
  can see below the fold; one `testWidgets`, because the binding resets
  the Android screenshot surface between tests.
- What differs from the spike as written: `flutter test integration_test`
  runs the checks but has nowhere to put screenshot bytes, so `flutter
  drive` with `app/test_driver/integration_test.dart` is what saves them
  (and the timings); and "restart" is a second app instance in the same
  process after the first is unmounted and `SevenReadingsApp.dispose`
  has closed both databases, not a process restart. Triggers: on demand,
  Mondays at 06:00 UTC, every `v*` tag; never on plain pushes.
- **T3, web (2026-09-16): done.** Green on sample content: the checklist
  on headless Chrome (first launch 2390 ms, 1600x881 dp, the column
  layout), then the offline proof, then the page on the site. A `web` job in
  `screenshots.yml`: the runner's chromedriver drives a headless Chrome,
  `tools/checklist.sh chrome` runs the same test through `flutter drive
  -d web-server` (screenshots by WebDriver, the plugin path), artifact
  `screenshots-web`. The same job then builds the release site with the
  service worker and runs `tools/web-offline-check.py` (Selenium): the
  reader must come up, the worker must control the page, and after the
  network is cut with the DevTools protocol a reload must bring the
  reader back; it writes `web-offline.png` beside the ten.
- **T3, Windows, macOS, iOS simulator (2026-09-17): written, not yet
  run.** Three more jobs in `screenshots.yml`, the same script and test:
  `windows` on the hosted Windows runner (it has an interactive desktop;
  Git Bash runs `tools/checklist.sh windows`), `macos` on the hosted
  macOS runner (`checklist.sh macos`; the debug app runs in the app
  sandbox, whose profile already allows the VM service's local server),
  and `ios` on the same runner image: the newest available iPhone
  simulator is booted by udid and `checklist.sh <udid>` drives it, with
  the plugin's screenshots as on Android and the simulator's log kept.
  Artifacts `screenshots-windows`, `screenshots-macos`, `screenshots-ios`;
  the site's page picks them up by name. For the desktop pair the macOS
  window was set to 1280x720 in `MainMenu.xib` (Windows already was), so
  all three desktops show the same side-by-side layout. Two things only
  the first run can tell: whether `flutter drive -d windows` gets a
  window on the hosted runner (it is documented to have a desktop
  session, and this is the first time this project asks for one), and
  the simulator's first-launch time with the release content, which is
  the number the App Store screenshots will show. The display name was
  also corrected to "Seven Readings" where the platform folders still
  said `sevenreadings` (Android label, iOS and macOS bundle display
  names, the Windows window title and version resource). First run
  (2026-09-17, sample content): the four existing jobs green (Android
  2175/151 ms, Linux 2113/279, web 2701/796, Flatpak); the three new ones
  red before the test started, each on the runner, not the app: on
  Windows the pipeline's sample build died printing a Greek file name
  through cp1252 (`PYTHONUTF8=1` on that step now), on macOS and the iOS
  simulator the script hit bash 3.2's empty-array bug under `set -u`
  (the script now uses the portable form). The simulator itself booted
  (iPhone Air, iOS 26 on the macOS 26 runner image; `bootstatus` ended
  with "Data Migration Failed", which the next run will show to matter
  or not). Second run (2026-09-17, sample content): six of seven green.
  **iOS simulator: done**, iPhone Air on iOS 26, 420x912 dp, first launch
  7079 ms (a simulator running a debug build on the hosted Mac; the
  number to read is the phone's), second 152 ms, ten plugin screenshots
  of the phone layout. **Windows: done**, first launch 1771 ms, second
  160 ms, ten screenshots; the hosted desktop is small, so the 1280x720
  window was clamped to 1028x681 dp, still the side-by-side layout. The
  other four held (Android 2768/216, Linux 2298/302, web 2621/749,
  Flatpak). **macOS: red at the fourth step**, with three screenshots
  and a first launch of 3097 ms at 1024x642 dp (clamped, as on Windows).
  The test tapped Genesis 1:1 right after leaving the Support screen,
  and on macOS (and iOS) the page transition slides the reader in from
  the left while absorbing pointers: the tap landed a third of a screen
  left of the verse, mid-slide, and was absorbed. The test now pops a
  screen and waits until it is gone from the tree (`goBack`), at all
  three places it goes back; the other targets' fade transitions had
  hidden the race. Third run (sample): all seven green, macOS 4070/268.
- **T3: done on every target, 2026-09-17**, release content (the pinned
  167 MB database, debug builds): Android emulator 6285 / 186 ms; iPhone
  Air simulator 4480 / 151; macOS 5333 / 218 at 1024x642; Windows 3900 /
  177 at 1028x681; Linux 2588 / 312 at 1280x720; web 8589 / 2190 at
  1600x881 (the database streamed into the browser, then the offline
  proof); Flatpak launched in the sandbox. Ten screenshots each, on
  https://sevenreadings.org/screenshots/ after the next deploy. Section 2
  is complete; the store-ready framed versions are S4.
- **T4 (2026-09-16): done**, https://sevenreadings.org/screenshots/ shows
  android, linux and web, ten each, with their launch timings, and the
  offline proof's screenshot. Its first deploy published an empty page
  (a wrong `gh` call, swallowed); the script now fails rather than do
  that. CI's smoke job puts
  the newest successful screenshots run's artifacts on the site
  (`tools/site-screenshots.sh`, `tools/screenshots-page.py`):
  https://sevenreadings.org/screenshots/ is the contact sheet, and
  `screenshots/<target>/screenshots/<name>.png` are stable addresses the
  Flatpak metainfo can cite. Artifacts expire after 30 days, so the weekly
  run keeps it current; with none available the site still deploys.
- **T3, Linux (2026-09-15): done.** Second run green on sample content:
  first launch 2461 ms, second 253 ms, eight screenshots of the 1280x720
  side-by-side layout (three columns, the sheet constrained to 640 px,
  search, About), the Android job green in the same run (2331 / 198 ms),
  so the programmatic scroll holds on both. The columns showed one thing
  the phone layout hides, a title row labelled "0"; fixed. How it got
  here:
  A `linux` job in `screenshots.yml` runs the same test on the Linux build
  under Xvfb (1280x800, software GL) and uploads `screenshots-linux`. Same
  checklist, same driver; two differences. The desktop window is 1280x720
  dp, so the reader shows the side-by-side columns, a different code path
  from the phone layout the emulator exercises, and the test records the
  view size it saw (`view` in the report). And desktop has no
  integration_test screenshot plugin, so the test renders the app from a
  `RepaintBoundary` at its root to PNG and puts the bytes on the same
  report list the driver already writes; Android, iOS and web keep the
  plugin. The guard moved into `tools/checklist.sh`, which every target's
  job calls with its device id. First run, sample content: the embedder
  renders under Xvfb, the rendered screenshots are right (three columns,
  the sheet, the dialog), first launch 2028 ms, taps and text entry work;
  then fifty synthetic drags on the readings sheet moved nothing, where
  the same drags scroll on the emulator. Not investigated: the test now
  scrolls lists programmatically (`scrollTo`, the list's `ScrollPosition`
  jumped until the item is on stage), on every target, and the Android
  job re-proves that path. Windows (a desktop session on the runner),
  macOS, the iOS simulator and web (chromedriver) are one job each from
  here; each is a first run, not a copy, until it has passed.

## 3. Donations

Goal: a "Support this project" screen, reachable from About, that lets a
person give money, on every target, in the way each store allows.

The one fact that decides the rules **(maintainer)**: is the recipient an
individual (you) or a registered nonprofit? The stores treat those
differently, and their policies have been changing (external payment links
in the US after 2025; the EU's DMA); the exact text has to be re-read at
submission time, so this section states the design and the constraints,
not a claim about today's rules.

- **Apple (iOS, Mac App Store)**: money to the developer inside the app goes
  through StoreKit as consumable in-app purchases ("tip jar" of, say, $2/$5/$10;
  Apple keeps its commission). Registered nonprofits may take donations
  through the web without IAP. Links out to external payment are permitted
  in some regions since 2025 and not in others. Design for IAP as the
  in-app path.
- **Google Play**: in-app purchases of digital goods must use Play Billing;
  tips to the developer are treated as that. Donations to registered
  nonprofits may use other means. A plain link to a donation page that
  unlocks nothing is common but sits in a grey area of the Payments policy;
  do not rely on it for the Play build.
- **Microsoft Store**: in-app purchases go through Microsoft commerce;
  donation links to external pages are generally tolerated for open-source
  apps; verify at submission.
- **Web, Linux (tarball and Flathub), Windows zip, direct macOS DMG**: no
  store rules. External links: GitHub Sponsors, Liberapay, Ko-fi, or a
  Stripe payment link — the maintainer chooses the accounts; all are free
  to set up.

Design: one screen, two mechanisms behind a per-platform switch. Store
builds use the `in_app_purchase` plugin (StoreKit on Apple, Play Billing on
Android) with three consumable products, no restore, no entitlement — a tip
changes nothing in the app, which is what keeps it honest and keeps the
review simple. Non-store builds show the external links. The About screen
says where the money goes. No analytics, no accounts, no tracking; the app
stays local-only.

Spikes:
- **D1. The screen with external links only**, on all targets. Free,
  reviewable in CI screenshots. Ships on web and the non-store desktop
  builds immediately.
- **D2. IAP on Android**: products created in Play Console (maintainer),
  `in_app_purchase` wired, tested on the internal track. Needs the Play
  account.
- **D3. IAP on iOS/macOS**: same with App Store Connect. Needs the Apple
  program.
- **D4. Legal and tax note** in `docs/`: what receiving money as an
  individual means where the maintainer lives is not something this
  project can answer; it is written down as a question the maintainer must
  settle before D2/D3 go live.

### State

- **D1 (2026-09-15): done, proven on the emulator and under Xvfb** (both
  green with nine screenshots; step 02 (03 since N1) is the Support screen, the band is
  in every later one). `app/lib/features/support/`: a band
  under the title row of every app bar, full width and centred, "Support
  Seven Readings" with a heart, on screen at all times (the maintainer's
  ask: the most obvious thing in the app), plus an entry at the top of
  About; both open the Support screen: one link for now, a Stripe
  Payment Link (customer chooses the amount; card, Apple Pay and Google Pay
  on Stripe's hosted page), opened with `url_launcher` and shown as text
  too. The build flag `SR_DISTRIBUTION` (see `AGENTS.md`) hides the entry
  in `play`, `appstore` and `msstore` builds, where tips must be in-app
  purchases (D2, D3); every workflow sets the flag per artifact and the
  checklist runs are `direct`, so the band is in every screenshot and
  step 02 is the screen itself. The Stripe "buy button" embed and its publishable
  key are for an HTML page, not the app; they can go on a landing page.
- **D4, the fact as of 2026-09-15:** the maintainer intends a nonprofit
  but none is formed, so the recipient is an individual: gifts are that
  person's income where they live, donors deduct nothing, and the app's
  wording says "gift" and "support", never "donation" or anything
  suggesting a deduction. When a nonprofit exists and Apple and Google
  have approved it, the Stripe link may go into the store builds too
  (Apple's nonprofit fundraising rule) at Stripe's fee instead of the
  stores' 15-30 %; until then the store path is D2/D3. What forming one
  means where the maintainer lives is still the question this project
  cannot answer.

## 4. Local LLM chat

Goal: "Ask about this passage" — a chat that runs entirely on the device,
grounded in the seven readings the app already has, on every target,
fully open source, at no cost to anyone. **Abandon if any part of the path
requires paying, or a closed model, or a service.**

What exists, all free and open:
- **Web**: WebLLM (MLC, Apache-2.0) runs models in the browser over WebGPU.
  Reachable from Flutter web through `dart:js_interop`. WebGPU works in
  Chrome and Edge on desktop and Android; Firefox and Safari are partial.
- **Native (Android, iOS, macOS, Windows, Linux)**: llama.cpp (MIT) through
  a Flutter FFI binding (`llama_cpp_dart`, MIT, or similar); runs GGUF
  models on CPU with Metal/Vulkan acceleration where present.
- **Models under open licenses**: Qwen2.5-1.5B-Instruct (Apache-2.0),
  SmolLM2-1.7B-Instruct (Apache-2.0), OLMo-2-1B-Instruct (Apache-2.0),
  Phi-3.5-mini (MIT). Llama and Gemma are free to use but not open-source
  licenses, so they are out by the project's rule. Weights are 1-2 GB at
  4-bit; they are downloaded on demand, never bundled, and cached, with the
  size and the model's license shown before download and recorded in the
  About screen like any other text.

Grounding is the point: a 1.5B model knows little and invents freely, but
it can summarize and compare text it is given. The prompt carries the
verse, the readings on it (from the content database, by the same query the
sheet uses), and instructions to answer from those and cite them; the UI
labels the answer as generated and shows the readings it drew on.

Spikes, in order, each with a measurable outcome:
- **L1. Feasibility on the maintainer's phone browser** (nothing to
  install): a standalone HTML page on Pages that loads WebLLM with
  Qwen2.5-1.5B q4 and reports load time, memory, and tokens per second.
  Abandon web chat on phones if under ~3 tokens/s; keep desktop web if
  desktop is fine.
- **L2. llama.cpp on Linux in CI**: the FFI binding built into the Linux
  target, a 360M model (SmolLM2-360M) for the test, a headless run that
  answers one grounded question; the answer and speed in the log. Proves
  the native path without a device.
- **L3. Android on the phone**: the same binding in the APK, Qwen2.5-1.5B
  q4, tokens per second on the maintainer's phone. Abandon native chat on
  phones if under ~3 tokens/s; desktop still benefits.
- **L4. Grounded prompt over the content database**: FTS-backed retrieval,
  the prompt template, citation rendering, tested with sample content in
  the integration test (a fixed tiny model, deterministic sampling).
- **L5. Download and licensing UX**: model catalogue in `sources.toml`
  style, size and license before download, the About screen entry.

Windows and iOS follow from L2/L3 with the same binding; they are build
matrix entries, not new spikes.

## 5. Narrator

Goal: the app reads a chapter or a reading aloud, offline, on every target,
English first (there are no open voices worth using for Greek or Hebrew),
with the current verse highlighted as it is read.

Two open options, both free:
- **System voices** through `flutter_tts` (MIT plugin): Android and iOS/macOS
  system speech, Windows SAPI, Linux speech-dispatcher, web
  `speechSynthesis`. Zero download, voice quality and availability set by
  the OS; the plugin is open, the voices mostly are not.
- **Bundled open neural voices** through `sherpa-onnx` (Apache-2.0; has a
  Flutter plugin covering all six targets, web via WASM) running Piper
  voices (MIT engine; each voice's dataset license must be checked —
  LJSpeech-based voices are public domain, LibriTTS-based are CC BY 4.0,
  some are non-commercial and excluded). A voice is ~60 MB, downloaded on
  demand like a model.

Spikes:
- **N1. `flutter_tts` on all targets** with play/pause/speed and per-verse
  highlighting driven by the plugin's progress callbacks; proven in the
  integration tests by state, and by ear on the phone. Ships first.
- **N2. `sherpa-onnx` + one CC-BY-4.0 Piper voice** on Android and Linux;
  measure size, synthesis speed, and quality against N1; keep it as the
  "open voice" option if it is clearly better and fast enough, else stay
  on N1.
- **N3. Highlight sync** for N2 (chunk by verse, synthesize ahead).

### State

- **N1 (2026-09-15): done by state, both targets green with ten screenshots**
  (emulator: the engine accepted the chapter, the strip in its speaking
  state, verse 1 highlighted and scrolled to; Linux: the failed state with
  its message; first launch 3404 / 2412 ms, second 167 / 277 ms). By ear
  on the phone is still the maintainer's part. `app/lib/features/narrator/`:
  `Narrator` (a `ChangeNotifier` over `flutter_tts`) reads one chunk at a
  time — the verses of the chapter in the first English translation shown,
  from the highlighted verse if any, or a reading paragraph by paragraph —
  so the chunk being spoken is known on every platform, which is what the
  per-verse highlight is driven by (no engine's word callbacks needed).
  Pause stops the voice and resume restarts the chunk, the one contract
  every engine honours. "Listen" is the first icon in the reader's top
  bar; every reading in the sheet has a headphones button; `NarratorBar`
  at the bottom has play/pause, stop, "Genesis 1 · verse 3 of 31" and the
  speed (0.75-1.5×, remembered in `UserDb.settings`, the first use of that
  table). Navigation stops the voice. When the platform has no voice the
  strip says so and stays until Stop, so the state is testable: step 02 of
  the checklist taps Listen, asserts the strip with the chapter, and
  stops. Two facts found writing it: `flutter_tts` has no Linux
  implementation (speech-dispatcher, as this section assumed, is not a
  route it offers; recorded as a known gap, N2 is the way to a Linux
  voice); and the plugin's speed scale differs by platform (mapped in
  `Narrator._pluginRate`). By ear on the phone is the maintainer's part:
  a real voice, the highlight following it, pause and resume, the speed.
  The web run added a state: headless Chrome has no voices and "finishes"
  each utterance instantly, so a chapter ended and the strip vanished in
  milliseconds; now a finished reading keeps the strip ("Genesis 1 ·
  finished", play reads it again) until Stop, which is better behaviour
  on a phone too, and every terminal state is on screen for the test.

## Order of everything

1. T1-T2 (integration test, Android emulator screenshots): the foundation
   every other item is checked against. Done 2026-09-15 (section 2, State).
2. S3 (Flathub manifest, PWA) and D1 (donations screen, links only): free,
   ship on the free channels. All done 2026-09-16, with one decision:
   the Flatpak ships as a bundle on each release, not on the Flathub store,
   until the project has the history and the maintainer-written submission
   Flathub's policies require (section 1, S3 state; docs/workflow.md,
   "Releasing").
3. N1 (narrator with system voices). Done by state 2026-09-15 (section 5,
   State), by ear pending; item 2's PWA and Flatpak resume next.
4. T3 for the remaining targets (Windows, macOS, the iOS simulator), so
   every target the stores will see has been walked through in CI. In
   `screenshots.yml` since 2026-09-17; first runs pending (section 2,
   State).
5. Publishing, all of it, before any chat work (the maintainer's
   direction, 2026-09-17: "no chat feasibility spikes until the app is
   properly published across all supported platforms"): S1 signing as
   code, S4 listings as code, Windows packaged as MSIX, D2-D3 in-app tips
   behind `SR_DISTRIBUTION`, then S2 uploads and the store submissions as
   the accounts open. The maintainer's hardware for the parts CI cannot
   do: a Windows laptop, an iPad, an Android phone, and a 2018 Intel Mac
   mini on macOS Sequoia (Xcode 16 runs there, so it can sign, run the
   iOS simulator, and run the macOS app once, which the Mac App Store
   requires before a listing; Tahoe and later Xcodes need Apple silicon,
   so this Mac's ceiling is whatever the last Sequoia Xcode supports).
6. L1 and L2 (chat feasibility, web and Linux) — decide from the numbers.
7. L3-L5, N2-N3 if the spikes justified them.

Each finished spike updates this file: what was measured, what was decided.
