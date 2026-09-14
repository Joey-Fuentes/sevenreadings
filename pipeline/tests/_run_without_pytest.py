"""Run the test suite without pytest (sandboxes without network).

Supports the fixtures the suite uses: `tmp_path`, `capsys`, and
`pytest.raises`. Prefer real pytest whenever it can be installed.
"""

from __future__ import annotations

import contextlib
import io
import pathlib
import re
import sys
import tempfile
import traceback
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

pytest = types.ModuleType("pytest")


@contextlib.contextmanager
def _raises(exc, match=None):
    try:
        yield
    except exc as e:
        assert match is None or re.search(match, str(e)), str(e)
    else:
        raise AssertionError(f"did not raise {exc.__name__}")


pytest.raises = _raises
sys.modules.setdefault("pytest", pytest)


class _Capsys:
    def __init__(self) -> None:
        self.buf = io.StringIO()

    def readouterr(self):
        return types.SimpleNamespace(out=self.buf.getvalue(), err="")


def main() -> int:
    failed = 0
    total = 0
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        mod = __import__(f"tests.{path.stem}", fromlist=["x"])
        for name in dir(mod):
            if not name.startswith("test_"):
                continue
            fn = getattr(mod, name)
            args = fn.__code__.co_varnames[: fn.__code__.co_argcount]
            kwargs = {}
            if "tmp_path" in args:
                kwargs["tmp_path"] = pathlib.Path(tempfile.mkdtemp())
            cap = _Capsys() if "capsys" in args else None
            if cap is not None:
                kwargs["capsys"] = cap
            total += 1
            try:
                with contextlib.redirect_stdout(cap.buf if cap else io.StringIO()):
                    fn(**kwargs)
            except Exception:
                failed += 1
                print(f"FAIL {path.stem}::{name}")
                traceback.print_exc()
    print(f"{total - failed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
