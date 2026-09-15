/// The ways to support the project, opened from the Support screen in
/// builds that may show them. Editing this list is the whole of a change
/// to what is offered. Wording rule (docs/plan.md, D1 and D4): the project
/// is one person, not a registered charity, so nothing here says
/// "donation" or suggests a deduction.
class SupportLink {
  const SupportLink({
    required this.label,
    required this.url,
    required this.note,
  });

  final String label;
  final String url;
  final String note;
}

const supportLinks = [
  SupportLink(
    label: 'Give once, any amount',
    url: 'https://buy.stripe.com/4gMcN5flk4MVfyG8oR1ck00',
    note: 'Card, Apple Pay or Google Pay, through Stripe.',
  ),
];

const _env = 'SR_DISTRIBUTION';

/// How this build is distributed, from `--dart-define=SR_DISTRIBUTION=`:
/// `direct` (release assets and plain `flutter run`), `web`, `flathub`,
/// `play`, `appstore`, `msstore`. The stores require in-app purchases for
/// tips and forbid links to outside payment, so those builds never show
/// the Support screen; in-app tips there are docs/plan.md D2 and D3.
const distribution = String.fromEnvironment(_env, defaultValue: 'direct');

const storeDistributions = {'play', 'appstore', 'msstore'};

bool get showsSupportLinks => !storeDistributions.contains(distribution);
