import 'package:flutter/material.dart';
import 'package:sr_core/sr_core.dart';

import 'narrator.dart';

/// The integration test finds the bar by this key.
const Key narratorBarKey = Key('narrator-bar');

/// The strip at the bottom of the reader while something is being read:
/// play/pause, stop, what and where, the speed. Hidden when idle.
class NarratorBar extends StatelessWidget {
  const NarratorBar({super.key, required this.narrator});

  final Narrator narrator;

  String _where() {
    final n = narrator;
    if (n.status == NarratorStatus.finished) {
      return '${n.title} \u00b7 finished';
    }
    final verseId = n.current?.verseId;
    if (verseId != null) {
      final ref = VerseRef.fromId(verseId);
      final label = ref.verse == 0 ? 'title' : 'verse ${ref.verse}';
      return '${n.title} \u00b7 $label of ${n.total}';
    }
    if (n.total > 1) return '${n.title} \u00b7 ${n.index + 1} of ${n.total}';
    return n.title;
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: narrator,
      builder: (context, _) {
        final theme = Theme.of(context);
        final n = narrator;
        if (!n.active) return const SizedBox.shrink();
        final speaking = n.status == NarratorStatus.speaking;
        final finished = n.status == NarratorStatus.finished;
        var playTooltip = finished ? 'Read again' : 'Resume';
        if (speaking) playTooltip = 'Pause';
        return Material(
          key: narratorBarKey,
          color: theme.colorScheme.surfaceContainerHighest,
          child: SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(8, 4, 8, 4),
              child: Row(
                children: [
                  IconButton(
                    icon: Icon(speaking ? Icons.pause : Icons.play_arrow),
                    tooltip: playTooltip,
                    onPressed: speaking ? n.pause : n.resume,
                  ),
                  IconButton(
                    icon: const Icon(Icons.stop),
                    tooltip: 'Stop',
                    onPressed: n.stop,
                  ),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          _where(),
                          style: theme.textTheme.bodyMedium,
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (n.unavailable != null)
                          Text(
                            n.unavailable!,
                            style: theme.textTheme.bodySmall,
                          ),
                      ],
                    ),
                  ),
                  DropdownButton<double>(
                    value: n.speed,
                    underline: const SizedBox.shrink(),
                    items: [
                      for (final s in Narrator.speeds)
                        DropdownMenuItem(value: s, child: Text('$s\u00d7')),
                    ],
                    onChanged: (s) {
                      if (s != null) n.setSpeed(s);
                    },
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
