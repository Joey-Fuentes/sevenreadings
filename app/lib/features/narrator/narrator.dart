import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';

/// What the narrator is doing, for the widgets that show it.
enum NarratorStatus { idle, speaking, paused, failed }

/// One thing to read aloud: a chapter's verses or a single reading.
class NarratorChunk {
  const NarratorChunk(this.text, {this.verseId});

  final String text;

  /// The verse this chunk is, when reading a chapter; null for a reading.
  final int? verseId;
}

/// Reads text aloud with the system voice (`flutter_tts`), one chunk at a
/// time, so the chunk being spoken is always known and can be highlighted
/// on every platform, including the ones whose voices report no word
/// progress. Pause stops the voice and resume restarts the current chunk:
/// the one behaviour every platform's engine can honour.
///
/// Speeds are the app's (1.0 = normal); the plugin's scale differs per
/// platform and is mapped in [_pluginRate].
class Narrator extends ChangeNotifier {
  Narrator({FlutterTts? tts}) : _tts = tts ?? FlutterTts();

  static const speeds = [0.75, 1.0, 1.25, 1.5];

  final FlutterTts _tts;
  bool _configured = false;
  int _generation = 0;

  NarratorStatus status = NarratorStatus.idle;

  /// What is being read, for the player bar: "Genesis 1", "Matthew Henry".
  String title = '';
  List<NarratorChunk> _chunks = const [];
  int _index = 0;
  double speed = 1.0;

  /// Why nothing can be spoken here, when that is the case.
  String? unavailable;

  /// The chunk being spoken (or paused on).
  NarratorChunk? get current {
    if (_index >= _chunks.length) return null;
    return _chunks[_index];
  }

  int get index => _index;
  int get total => _chunks.length;
  bool get active => status != NarratorStatus.idle;

  Future<void> _configure() async {
    if (_configured) return;
    _configured = true;
    await _tts.awaitSpeakCompletion(true);
    try {
      await _tts.setLanguage('en-US');
    } catch (_) {
      // The engine picks its default; the language is a preference.
    }
  }

  double _pluginRate(double s) => kIsWeb ? s : s * 0.5;

  /// Reads [chunks] from [from], under [title].
  Future<void> read(
    String title,
    List<NarratorChunk> chunks, {
    int from = 0,
  }) async {
    debugPrint('narrator: read "$title", ${chunks.length} chunks');
    await stop();
    this.title = title;
    _chunks = chunks;
    _index = chunks.isEmpty ? 0 : from.clamp(0, chunks.length - 1).toInt();
    if (chunks.isEmpty) return;
    await _speakFrom(_index);
  }

  Future<void> _speakFrom(int start) async {
    final generation = ++_generation;
    status = NarratorStatus.speaking;
    unavailable = null;
    notifyListeners();
    debugPrint('narrator: speaking from $start');
    try {
      await _configure();
      await _tts.setSpeechRate(_pluginRate(speed));
      for (var i = start; i < _chunks.length; i++) {
        if (generation != _generation) return;
        _index = i;
        notifyListeners();
        final result = await _tts.speak(_chunks[i].text);
        if (generation != _generation) return;
        // 1 is success where the engine reports one; other platforms
        // return nothing and completed the await.
        if (result is int && result != 1) {
          unavailable = 'No voice is available on this device.';
          break;
        }
      }
    } catch (e) {
      // MissingPluginException on a platform without the plugin, or the
      // engine refusing: the bar says so instead of the app crashing.
      unavailable = 'No voice is available on this device.';
      debugPrint('narrator: $e');
    }
    if (generation != _generation) return;
    // Failure keeps the bar on screen with its message until Stop.
    status = unavailable == null ? NarratorStatus.idle : NarratorStatus.failed;
    notifyListeners();
  }

  Future<void> pause() async {
    if (status != NarratorStatus.speaking) return;
    _generation++;
    status = NarratorStatus.paused;
    notifyListeners();
    try {
      await _tts.stop();
    } catch (_) {
      // Already silent, or no engine here: nothing to undo.
    }
  }

  Future<void> resume() async {
    if (status == NarratorStatus.speaking || !active) return;
    await _speakFrom(_index);
  }

  Future<void> stop() async {
    if (!active) return;
    _generation++;
    status = NarratorStatus.idle;
    notifyListeners();
    try {
      await _tts.stop();
    } catch (_) {
      // Already silent, or no engine here: nothing to undo.
    }
  }

  /// Sets the speed; a chunk being spoken restarts at the new speed.
  Future<void> setSpeed(double s) async {
    speed = s;
    notifyListeners();
    if (status == NarratorStatus.speaking) {
      _generation++;
      try {
        await _tts.stop();
      } catch (_) {
        // Already silent, or no engine here: nothing to undo.
      }
      await _speakFrom(_index);
    }
  }

  @override
  void dispose() {
    _generation++;
    _tts.stop().ignore();
    super.dispose();
  }
}
