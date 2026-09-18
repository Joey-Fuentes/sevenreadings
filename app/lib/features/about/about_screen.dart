import 'package:flutter/material.dart';
import 'package:sr_data/sr_data.dart';

import '../reader/markdown_text.dart';
import '../support/support_screen.dart';

/// The screen's list, for the integration test to scroll to the notices.
const Key aboutListKey = Key('about-list');

/// One block of the notices document: a `# heading` or a paragraph.
class NoticeBlock {
  const NoticeBlock(this.text, {required this.isHeading});

  final String text;
  final bool isHeading;
}

/// Splits the notices Markdown the pipeline stores in `meta.notices` into
/// headings and paragraphs. Hard line breaks inside a paragraph are joined,
/// since the source files are wrapped for editors, not phones.
List<NoticeBlock> parseNotices(String notices) {
  final out = <NoticeBlock>[];
  for (final raw in notices.split(RegExp(r'\n\s*\n'))) {
    final block = raw.trim().replaceAll('`', '');
    if (block.isEmpty) continue;
    if (block.startsWith('#')) {
      final text = block.replaceFirst(RegExp(r'^#+\s*'), '');
      out.add(NoticeBlock(text, isHeading: true));
    } else {
      final text = block.replaceAll(RegExp(r'\s*\n\s*'), ' ');
      out.add(NoticeBlock(text, isHeading: false));
    }
  }
  return out;
}

class _About {
  const _About(this.version, this.notices, this.translations, this.sources);

  final String version;
  final String notices;
  final List<Translation> translations;
  final List<Source> sources;
}

/// What is bundled, under which license, with each source's own notice.
/// Everything shown comes from the content database, so it always matches
/// the texts actually shipped.
class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key, required this.db});

  final ContentDb db;

  Future<_About> _load() async {
    final version = await db.metaValue('content_version').getSingleOrNull();
    final notices = await db.metaValue('notices').getSingleOrNull();
    final translations = await db.allTranslations().get();
    final sources = await db.allSources().get();
    return _About(version ?? '', notices ?? '', translations, sources);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: const Text('About the texts'),
        bottom: SupportBar.ifShown,
      ),
      body: FutureBuilder<_About>(
        future: _load(),
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Center(child: Text('${snapshot.error}'));
          }
          final data = snapshot.data;
          if (data == null) {
            return const Center(child: CircularProgressIndicator());
          }
          return ListView(
            key: aboutListKey,
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            children: [
              Text(
                'Content ${data.version}. Every text below is public domain '
                'or under a license that allows redistribution; the notices '
                'give the terms and the attribution each requires.',
                style: theme.textTheme.bodyMedium,
              ),
              if (SupportBar.shown)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.favorite_outline),
                  title: const Text('Support this project'),
                  subtitle: const Text('Free, no ads; a gift keeps it so'),
                  onTap: () => Navigator.of(context).push<void>(
                    MaterialPageRoute(builder: (_) => const SupportScreen()),
                  ),
                ),
              const SizedBox(height: 16),
              Text('Bibles', style: theme.textTheme.titleMedium),
              for (final t in data.translations)
                _Entry(
                  title: '${t.name} (${t.abbreviation})',
                  detail: t.license,
                  link: t.sourceUrl,
                ),
              const SizedBox(height: 16),
              Text('Readings', style: theme.textTheme.titleMedium),
              for (final s in data.sources)
                _Entry(
                  title: '${s.author}: ${s.title}',
                  detail: s.license,
                  link: s.sourceUrl,
                ),
              const SizedBox(height: 16),
              Text('Notices', style: theme.textTheme.titleMedium),
              for (final block in parseNotices(data.notices))
                if (block.isHeading)
                  Padding(
                    padding: const EdgeInsets.only(top: 16, bottom: 4),
                    child: Text(block.text, style: theme.textTheme.titleSmall),
                  )
                else
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text.rich(
                      TextSpan(
                        children: markdownSpans(
                          block.text,
                          theme.textTheme.bodySmall,
                        ),
                      ),
                    ),
                  ),
            ],
          );
        },
      ),
    );
  }
}

class _Entry extends StatelessWidget {
  const _Entry({
    required this.title,
    required this.detail,
    required this.link,
  });

  final String title;
  final String detail;
  final String link;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: theme.textTheme.bodyLarge),
          Text(detail, style: theme.textTheme.bodySmall),
          if (link.isNotEmpty)
            SelectableText(link, style: theme.textTheme.bodySmall),
        ],
      ),
    );
  }
}
