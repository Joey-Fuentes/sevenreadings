#!/usr/bin/env python3
"""Prove the built site installs and works offline (docs/plan.md, S3).

    pip install selenium
    python tools/web-offline-check.py app/build/web [screenshots-dir]

Serves the build directory, opens it in headless Chrome (chromedriver
from $CHROMEWEBDRIVER, as on GitHub's runners), waits for the app to show
Genesis 1 (the reader puts the chapter in the tab title, which is the one
thing a canvas-rendered app exposes to a browser test), waits for our
service worker to control the page, then cuts the network with the
DevTools protocol and reloads: the page must load from the worker's cache
and the reader must show Genesis 1 again from the browser's own copy of
the texts. Writes web-offline.png beside the checklist's screenshots.
"""

from __future__ import annotations

import http.server
import os
import socketserver
import sys
import threading
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service

PORT = 8765
TITLE = "Genesis 1"


def serve(root: Path) -> socketserver.TCPServer:
    handler = type(
        "Quiet",
        (http.server.SimpleHTTPRequestHandler,),
        {
            "log_message": lambda *a, **k: None,
            "__init__": lambda self, *a, **k: http.server.SimpleHTTPRequestHandler.__init__(
                self, *a, directory=str(root), **k
            ),
        },
    )
    server = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def wait(driver, what: str, condition, timeout: float) -> None:
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        try:
            if condition():
                print(f"ok: {what} ({time.monotonic() - started:.1f}s)")
                return
        except Exception:  # noqa: BLE001 - the page may be mid-reload
            pass
        time.sleep(0.5)
    raise SystemExit(f"FAIL: {what} not within {timeout:.0f}s; title={driver.title!r}")


def main(argv: list[str]) -> int:
    root = Path(argv[0]).resolve()
    shots = Path(argv[1]).resolve() if len(argv) > 1 else None
    server = serve(root)
    url = f"http://127.0.0.1:{PORT}/"
    options = webdriver.ChromeOptions()
    for flag in ("--headless=new", "--window-size=1280,800", "--no-sandbox"):
        options.add_argument(flag)
    chromedriver = os.environ.get("CHROMEWEBDRIVER")
    service = Service(f"{chromedriver}/chromedriver") if chromedriver else Service()
    driver = webdriver.Chrome(options=options, service=service)
    try:
        driver.get(url)
        wait(driver, "the reader online", lambda: TITLE in driver.title, 240)
        wait(
            driver,
            "the service worker controls the page",
            lambda: driver.execute_script(
                "return !!(navigator.serviceWorker && navigator.serviceWorker.controller)"
            ),
            60,
        )
        manifest = driver.execute_script(
            "return fetch('manifest.json').then(r => r.ok && r.json()).then(m => m && m.name)"
        )
        if manifest != "Seven Readings":
            raise SystemExit(f"FAIL: manifest.json unexpected: {manifest!r}")
        print("ok: manifest.json")
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd(
            "Network.emulateNetworkConditions",
            {"offline": True, "latency": 0, "downloadThroughput": 0, "uploadThroughput": 0},
        )
        driver.get(url)
        wait(driver, "the reader offline, after a reload", lambda: TITLE in driver.title, 120)
        if shots:
            shots.mkdir(parents=True, exist_ok=True)
            driver.save_screenshot(str(shots / "web-offline.png"))
            print(f"screenshot: {shots / 'web-offline.png'}")
        print("PASS: installable (manifest, service worker) and works offline")
        return 0
    finally:
        driver.quit()
        server.shutdown()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
