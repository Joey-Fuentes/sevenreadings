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
| Flathub (Linux) | Flathub is free; a GitHub account | free | none in this repo: Flathub builds from a manifest in its own repo |
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

## Order of everything

1. T1-T2 (integration test, Android emulator screenshots): the foundation
   every other item is checked against.
2. S3 (Flathub manifest, PWA) and D1 (donations screen, links only): free,
   ship on the free channels.
3. N1 (narrator with system voices).
4. L1 and L2 (chat feasibility, web and Linux) — decide from the numbers.
5. T3-T4 (remaining targets' screenshots, the contact sheet).
6. S1-S2 and D2-D3 as the maintainer opens accounts; S4 with the
   screenshots.
7. L3-L5, N2-N3 if the spikes justified them.

Each finished spike updates this file: what was measured, what was decided.
