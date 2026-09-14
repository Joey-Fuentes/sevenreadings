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

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
