# Privacy answers, per store

The facts these answers rest on, all checkable in the code:

- The app makes no network requests. Its only outbound link is the Support
  screen's payment page, which opens in the system browser and exists only
  in direct-download builds (`SR_DISTRIBUTION=direct`); store builds
  compile it out.
- No account, no sign-in, no analytics, no crash reporting, no ads, no
  advertising identifiers, no third-party SDKs that talk to a network.
- Bookmarks, notes and settings live in a database on the device and are
  never transmitted. Deleting the app deletes them.
- The narrator uses the platform's own text-to-speech service on the
  device (Android TTS engine, AVSpeechSynthesizer, Windows voices).
- The web version at https://sevenreadings.org/ is static files on GitHub
  Pages; GitHub's servers see the requests that fetch them, under GitHub's
  privacy statement. The site itself sets no cookies and loads nothing
  from anywhere else.

The published policy is `store/privacy-policy.md`, served at
https://sevenreadings.org/privacy/ (`app/web/privacy/index.html`, the
same text). Both stores require that URL.

## Google Play, Data safety

- Does your app collect or share any of the required user data types? **No.**
- Is all of the user data collected by your app encrypted in transit? n/a (none collected).
- Do you provide a way for users to request that their data is deleted? n/a (none collected; uninstalling removes local data).
- Privacy policy URL: https://sevenreadings.org/privacy/
- App access: all functionality is available without special access; no login.
- Ads: **No ads.**
- Content rating questionnaire: reference/educational app; contains religious texts; no user-generated content shared, no violence, no purchases.
- Target audience: 13+ (not designed for children).

## App Store Connect, App Privacy

- Do you or your third-party partners collect data from this app? **No, we do not collect data from this app.** (This yields the "Data Not Collected" label.)
- Privacy Policy URL: https://sevenreadings.org/privacy/
- Age rating: 4+ (no objectionable content; religious/educational text).
- Export compliance: uses no encryption beyond what the OS provides (answer "No" to "Does your app use encryption?", or "Yes, exempt" if the form insists: HTTPS is not used at all).
- Content rights: all texts are public domain or openly licensed; notices in the app.

## Microsoft Partner Center

- Privacy policy URL: https://sevenreadings.org/privacy/
- Age ratings (IARC questionnaire): reference app, no user interaction, no purchases.
- App declarations: none (no accessibility claims, no dependencies on non-Microsoft drivers).
- Category: Books & reference.
