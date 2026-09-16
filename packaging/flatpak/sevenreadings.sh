#!/bin/sh
# /app/bin/sevenreadings: the Flutter bundle must be launched from its own
# directory layout (binary, lib/, data/ side by side).
exec /app/lib/sevenreadings/sevenreadings "$@"
