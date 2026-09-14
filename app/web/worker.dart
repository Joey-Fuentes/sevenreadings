// Compiled by tools/web-assets.sh into web/drift_worker.js.
// Do not import Flutter here; this runs in a web worker.
import 'package:drift/wasm.dart';

void main() => WasmDatabase.workerMainForOpen();
