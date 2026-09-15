import 'package:flutter/material.dart';
import 'package:sr_core/sr_core.dart';
import 'package:sr_data/sr_data.dart';

import '../search/search_screen.dart';
import '../support/support_links.dart';
import '../support/support_screen.dart';

/// Everything the reader has bookmarked or written, newest first. Tapping
/// an item pops with a [SearchTarget] so the reader opens that verse.
class NotesScreen extends StatefulWidget {
  const NotesScreen({super.key, required this.user});

  final UserDb user;

  @override
  State<NotesScreen> createState() => _NotesScreenState();
}

class _Items {
  const _Items(this.bookmarks, this.notes);

  final List<Bookmark> bookmarks;
  final List<Note> notes;
}

class _NotesScreenState extends State<NotesScreen> {
  late Future<_Items> _items = _load();

  Future<_Items> _load() async {
    const timeout = Duration(seconds: 4);
    final bookmarks = await widget.user.allBookmarks().get().timeout(timeout);
    final notes = await widget.user.allNotes().get().timeout(timeout);
    return _Items(bookmarks, notes);
  }

  // A block, not an arrow: see _ReadingsSheetState._refresh.
  void _refresh() {
    setState(() {
      _items = _load();
    });
  }

  Future<void> _deleteNote(Note note) async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete this note?'),
        content: Text(firstLine(note.body)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Keep'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (yes != true) return;
    await widget.user.deleteNote(note.id);
    _refresh();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Bookmarks & notes'),
        bottom: showsSupportLinks ? const SupportBar() : null,
      ),
      body: FutureBuilder<_Items>(
        future: _items,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Center(child: Text('${snapshot.error}'));
          }
          final data = snapshot.data;
          if (data == null) {
            return const Center(child: CircularProgressIndicator());
          }
          if (data.bookmarks.isEmpty && data.notes.isEmpty) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  'Nothing yet. Tap a verse, then the bookmark or the '
                  'note icon.',
                  style: theme.textTheme.bodySmall,
                  textAlign: TextAlign.center,
                ),
              ),
            );
          }
          return ListView(
            children: [
              if (data.bookmarks.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                  child: Text('Bookmarks', style: theme.textTheme.titleMedium),
                ),
              for (final b in data.bookmarks)
                ListTile(
                  leading: const Icon(Icons.bookmark),
                  title: Text(VerseRef.fromId(b.verseId).label),
                  subtitle: b.label == null ? null : Text(b.label!),
                  trailing: IconButton(
                    icon: const Icon(Icons.close),
                    tooltip: 'Remove bookmark',
                    onPressed: () async {
                      await widget.user.deleteBookmark(b.id);
                      _refresh();
                    },
                  ),
                  onTap: () => Navigator.pop(
                    context,
                    SearchTarget(b.verseId, showReadings: true),
                  ),
                ),
              if (data.notes.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                  child: Text('Notes', style: theme.textTheme.titleMedium),
                ),
              for (final n in data.notes)
                ListTile(
                  leading: const Icon(Icons.notes),
                  title: Text(VerseRef.fromId(n.startVerseId).label),
                  subtitle: Text(
                    firstLine(n.body),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  trailing: IconButton(
                    icon: const Icon(Icons.delete_outline),
                    tooltip: 'Delete note',
                    onPressed: () => _deleteNote(n),
                  ),
                  onTap: () => Navigator.pop(
                    context,
                    SearchTarget(n.startVerseId, showReadings: true),
                  ),
                ),
              const SizedBox(height: 24),
            ],
          );
        },
      ),
    );
  }
}

/// The first non-empty line of a note, for lists and confirmations.
String firstLine(String body) {
  for (final line in body.split('\n')) {
    final t = line.trim();
    if (t.isNotEmpty) return t;
  }
  return '';
}

/// A dialog to write or edit a note. Resolves to the trimmed text, or null
/// when cancelled.
Future<String?> noteDialog(BuildContext context, {String initial = ''}) {
  return showDialog<String>(
    context: context,
    builder: (_) => _NoteDialog(initial: initial),
  );
}

/// Owns its text controller, so it is disposed with the dialog's widgets
/// after the closing animation. Disposing it when showDialog returned, as
/// this did before, hit the still-animating TextField ("used after being
/// disposed"; the emulator checklist, 2026-09-15).
class _NoteDialog extends StatefulWidget {
  const _NoteDialog({required this.initial});

  final String initial;

  @override
  State<_NoteDialog> createState() => _NoteDialogState();
}

class _NoteDialogState extends State<_NoteDialog> {
  late final _controller = TextEditingController(text: widget.initial);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.initial.isEmpty ? 'New note' : 'Edit note'),
      content: TextField(
        controller: _controller,
        autofocus: true,
        minLines: 3,
        maxLines: 8,
        textCapitalization: TextCapitalization.sentences,
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(context, _controller.text.trim()),
          child: const Text('Save'),
        ),
      ],
    );
  }
}
