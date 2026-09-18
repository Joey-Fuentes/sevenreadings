import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import 'support_links.dart';
import 'tips.dart';

/// The band under the title row of every app bar, in builds that may show
/// outside payment links (see [showsSupportLinks]) and in store builds
/// once the store has answered with tips to sell ([TipStore.available]):
/// full width, centred, on screen at all times. The most visible thing in
/// the app, by design.
class SupportBar extends StatelessWidget implements PreferredSizeWidget {
  const SupportBar({super.key});

  static const double height = 44;

  /// Whether any screen shows the band right now. The app rebuilds from
  /// the root when [TipStore] changes, so app bars built with [ifShown]
  /// follow it.
  static bool get shown => showsSupportLinks || TipStore.instance.available;

  static PreferredSizeWidget? get ifShown => shown ? const SupportBar() : null;

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
/// may show outside payment links, or the store's tips in store builds.
/// Each link opens in the browser; the address is shown too, so it can be
/// copied when no browser opens.
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
          if (usesStoreTips) const _Tips(),
          if (showsSupportLinks)
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

/// The store's tips: one button per product with the store's own price,
/// the purchase through the store's sheet, and the outcome in a line.
class _Tips extends StatelessWidget {
  const _Tips();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final store = TipStore.instance;
    return ListenableBuilder(
      listenable: store,
      builder: (context, _) {
        final busy = store.status == TipStatus.purchasing;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (store.status == TipStatus.loading)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 12),
                child: LinearProgressIndicator(),
              ),
            if (store.status == TipStatus.unavailable)
              Text(
                'Tips are not available from the store right now.',
                style: theme.textTheme.bodyMedium,
              ),
            for (final product in store.products)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: FilledButton(
                  onPressed: busy ? null : () => store.buy(product),
                  child: Text(
                    '${tipProducts[product.id] ?? product.title}'
                    '  \u00b7  ${product.price}',
                  ),
                ),
              ),
            if (busy)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 8),
                child: LinearProgressIndicator(),
              ),
            if (store.message != null)
              Padding(
                padding: const EdgeInsets.only(top: 4, bottom: 12),
                child: Text(store.message!, style: theme.textTheme.bodyMedium),
              ),
            if (store.products.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: Text(
                  'Paid through the store, which keeps its share. A tip '
                  'buys nothing extra: the app stays complete for everyone.',
                  style: theme.textTheme.bodySmall,
                ),
              ),
          ],
        );
      },
    );
  }
}
