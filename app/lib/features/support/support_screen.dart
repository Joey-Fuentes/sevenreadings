import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import 'support_links.dart';

/// The band under the title row of every app bar, in builds that may show
/// outside payment links (see [showsSupportLinks]): full width, centred,
/// on screen at all times. The most visible thing in the app, by design.
class SupportBar extends StatelessWidget implements PreferredSizeWidget {
  const SupportBar({super.key});

  static const double height = 44;

  @override
  Size get preferredSize => const Size.fromHeight(height);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = theme.colorScheme.onTertiaryContainer;
    return Material(
      color: theme.colorScheme.tertiaryContainer,
      child: InkWell(
        onTap: () => Navigator.of(context).push<void>(
          MaterialPageRoute(builder: (_) => const SupportScreen()),
        ),
        child: SizedBox(
          height: height,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.favorite, color: color),
              const SizedBox(width: 8),
              Text(
                'Support Seven Readings',
                style: theme.textTheme.titleSmall?.copyWith(color: color),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// The links, reached from the [SupportBar] and from About in builds that
/// may show outside payment links. Each link opens in the browser; the
/// address is shown too, so it can be copied when no browser opens.
class SupportScreen extends StatelessWidget {
  const SupportScreen({super.key});

  Future<void> _open(BuildContext context, SupportLink link) async {
    // Desktop and mobile hand the address to the browser; web opens a tab.
    const external = LaunchMode.externalApplication;
    final mode = kIsWeb ? LaunchMode.platformDefault : external;
    final ok = await launchUrl(Uri.parse(link.url), mode: mode);
    if (ok || !context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Could not open a browser for ${link.url}')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Support')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          Text(
            'Seven Readings is free, with no ads, no accounts and no '
            'tracking, and it stays that way. If it is worth something '
            'to you, a gift of any size goes into the hours that build '
            'it: new texts, better numbering, every platform.',
            style: theme.textTheme.bodyLarge,
          ),
          const SizedBox(height: 20),
          for (final link in supportLinks) ...[
            FilledButton.icon(
              onPressed: () => _open(context, link),
              icon: const Icon(Icons.open_in_new),
              label: Text(link.label),
            ),
            Padding(
              padding: const EdgeInsets.only(top: 6, bottom: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(link.note, style: theme.textTheme.bodySmall),
                  SelectableText(link.url, style: theme.textTheme.bodySmall),
                ],
              ),
            ),
          ],
          Text(
            'Gifts go to the person who makes the app, not to a registered '
            'charity, and are not tax-deductible.',
            style: theme.textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}
