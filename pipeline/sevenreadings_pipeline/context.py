from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures"


@dataclass(slots=True)
class BuildContext:
    conn: sqlite3.Connection
    version: str
    sample: bool
    fixtures: Path = FIXTURES_DIR

    def log(self, msg: str) -> None:
        print(f"  {msg}")
