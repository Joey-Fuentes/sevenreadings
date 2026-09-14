from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import db, fetch, registry
from .context import BuildContext


def cmd_sources(_: argparse.Namespace) -> int:
    for sid, cfg in registry.load_config().items():
        print(f"{sid:14} {cfg['kind']:15} {cfg['license_status']:8} {cfg['license']}")
    return 0


def cmd_lock(args: argparse.Namespace) -> int:
    cfg = registry.load_config()[args.source]
    if "url" not in cfg:
        print(f"{args.source} is pinned by git commit, not a URL; set `commit` by hand.")
        return 1
    try:
        fetch.fetch(cfg["url"], None)
    except SystemExit as e:  # fetch prints the hash when unpinned
        print(e)
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    out = Path(args.out).resolve()
    if args.sample:
        config = registry.SAMPLE_SOURCES
    else:
        config = registry.load_config()
    if args.only and args.only != "all":
        wanted = set(args.only.split(","))
        missing = wanted - set(config)
        if missing:
            raise SystemExit(f"unknown sources: {sorted(missing)}")
        config = {k: v for k, v in config.items() if k in wanted}

    conn = db.create(out)
    ctx = BuildContext(conn=conn, version=args.version, sample=args.sample)
    built: list[str] = []
    print(f"Building {out} (version {args.version}{', sample' if args.sample else ''})")
    for sid, cfg in config.items():
        if cfg.get("license_status") == "blocked":
            print(f"  {sid}: skipped (license_status = blocked)")
            continue
        source = registry.make(sid, cfg)
        try:
            source.build(ctx)
        except NotImplementedError as e:
            if args.strict:
                raise
            print(f"  {sid}: skipped (not wired)\n{e}", file=sys.stderr)
            continue
        built.append(sid)
    manifest = db.finalize(conn, out, args.version, built)
    print(f"Done: {manifest['counts']}")
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    """Per chapter: how many verses the translation has in its own numbering
    versus the reference's numbering. Prints only chapters that differ."""
    import sqlite3

    from .refs import BY_OSIS, decode

    conn = sqlite3.connect(args.db)
    for osis in args.books.split(","):
        book = BY_OSIS[osis]
        native: dict[int, int] = {}
        rows = conn.execute(
            "SELECT verse_id, native_ref FROM verses WHERE translation_id=? AND verse_id/1000000=?",
            (args.translation, book.id),
        ).fetchall()
        for vid, ref in rows:
            _, c, v = decode(vid)
            for part in ref.split(", ") if ref else [f"{c}:{v}"]:
                if ":" in part and part.split(":")[0].isdigit():
                    nc, nv = (int(x) for x in part.split(":"))
                    native[nc] = max(native.get(nc, 0), nv)
        english = dict(
            conn.execute(
                "SELECT verse_id/1000%1000, MAX(verse_id%1000) FROM verses "
                "WHERE translation_id=? AND verse_id/1000000=? GROUP BY 1",
                (args.reference, book.id),
            ).fetchall()
        )
        diffs = [
            f"{c}: {native.get(c, 0)}/{english.get(c, 0)}"
            for c in sorted(set(native) | set(english))
            if native.get(c) != english.get(c)
        ]
        print(f"{osis}: {'  '.join(diffs) if diffs else 'all chapters match'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="srp", description="sevenreadings content pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("sources", help="list configured sources").set_defaults(fn=cmd_sources)

    lock = sub.add_parser("lock", help="print the SHA-256 of a source's upstream file")
    lock.add_argument("source")
    lock.set_defaults(fn=cmd_lock)

    build = sub.add_parser("build", help="build the content database")
    build.add_argument("--out", required=True, help="output .sqlite path")
    build.add_argument("--version", required=True, help="content version, e.g. 0.1.0")
    build.add_argument("--only", help="comma-separated source ids")
    build.add_argument("--sample", action="store_true", help="fixtures only, no network")
    build.add_argument("--strict", action="store_true", help="fail on sources that are not wired")
    build.set_defaults(fn=cmd_build)

    probe = sub.add_parser("probe", help="compare a translation's chapter lengths with a reference")
    probe.add_argument("--db", required=True)
    probe.add_argument("--translation", required=True)
    probe.add_argument("--reference", default="web")
    probe.add_argument("--books", required=True, help="comma-separated OSIS ids, e.g. Exod,Lev")
    probe.set_defaults(fn=cmd_probe)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
