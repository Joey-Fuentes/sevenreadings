# Store listings as code (docs/plan.md, S4)

Everything a store console asks for, kept here so a listing can be
reproduced, reviewed in a diff, and reused across stores. Nothing here is
uploaded automatically yet (that is S2, per store, behind secrets); today
the maintainer pastes from these files. Store builds are the ones built
with their store's `SR_DISTRIBUTION` (AGENTS.md, "Identity").

- `android/en-US/`: Play Console listing. `title.txt` (30 chars max),
  `short_description.txt` (80), `full_description.txt` (4000). The
  `fastlane supply` layout, so S2 can point a tool at it.
- `ios/en-US/`: App Store Connect. `name.txt` (30), `subtitle.txt` (30),
  `description.txt` (4000), `keywords.txt` (100, comma-separated),
  `promotional_text.txt` (170), `support_url.txt`, `marketing_url.txt`,
  `privacy_url.txt`. The `fastlane deliver` layout. `review-notes.txt` is
  what goes in the App Review notes box.
- `windows/en-US/`: Partner Center. `description.txt` (10000),
  `features.txt` (one per line, up to 20 of 200 chars), `search-terms.txt`
  (up to 7 of 30 chars).
- `privacy-policy.md`: the policy every store requires a URL for; served
  at https://sevenreadings.org/privacy/ (`app/web/privacy/index.html`
  carries the same text; change both together).
- `privacy-answers.md`: the answers to each store's data-safety, privacy
  and rating questionnaires, with the facts behind them.
- `captions.json`: one caption per checklist screenshot, used by
  `tools/store-screenshots.py` to frame the CI screenshots at the sizes
  each store accepts. The `store` job in `screenshots.yml` does that after
  every run and uploads `store-listing`: `play/phone/` (1080x1920),
  `play/tablet-10/` and `appstore/ipad-13/` (2048x2732, from the iPad
  simulator), `play/feature-graphic.png` (1024x500),
  `appstore/iphone-6.9/` (1260x2736), `appstore/mac/` (2560x1600),
  `msstore/desktop/` (1920x1080). Use a run with the release content, never
  the fixture texts.

Linux's listing is `packaging/flatpak/org.sevenreadings.SevenReadings.metainfo.xml`,
the AppStream form of the same words.
