"""The installable app: the web app manifest, the service worker and the offline page (public spec
§8), served in both modes; these run the app factory as local mode runs it.

What the service worker does in a browser (the shell cached, page loads going to the network, the
offline page when one fails, Try again reloading) is verified by hand against `prototype/mobile`.
"""

import json
import re
import struct
from importlib import metadata

import pytest
from fastapi.testclient import TestClient

from chessop.app import create_app
from chessop.graph import Graph


def test_the_manifest_installs_chessop_full_screen_from_the_root(graph: Graph) -> None:
    with TestClient(create_app(graph)) as client:
        response = client.get("/manifest.webmanifest")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/manifest+json")
    manifest = response.json()
    assert manifest["name"] == "chessop — drill your openings"
    assert manifest["short_name"] == "chessop"
    assert manifest["start_url"] == "/"
    assert manifest["scope"] == "/"
    assert manifest["display"] == "standalone"
    assert manifest["orientation"] == "any"
    assert manifest["background_color"] == "#161512"
    assert manifest["theme_color"] == "#161512"


def png_size(data: bytes) -> tuple[int, int]:
    """The width and height of a PNG, from its header."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "a PNG"
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def test_the_manifest_offers_192_and_512_px_icons_and_a_maskable_512_each_served(
    graph: Graph,
) -> None:
    with TestClient(create_app(graph)) as client:
        icons = client.get("/manifest.webmanifest").json()["icons"]
        assert [(i["sizes"], i["type"], i.get("purpose", "any")) for i in icons] == [
            ("192x192", "image/png", "any"),
            ("512x512", "image/png", "any"),
            ("512x512", "image/png", "maskable"),
        ]
        for icon in icons:
            response = client.get(icon["src"])
            assert response.status_code == 200, icon["src"]
            assert response.headers["content-type"] == "image/png"
            width, height = png_size(response.content)
            assert f"{width}x{height}" == icon["sizes"], icon["src"]
        # Its own art, full-bleed and drawn inside the circle a mask may cut to.
        assert icons[2]["src"] not in (icons[0]["src"], icons[1]["src"])


def head(page: str) -> str:
    """The page's document head."""
    found = re.search(r"<head>(.*?)</head>", page, re.S)
    assert found, "a document head"
    return found.group(1)


@pytest.mark.parametrize("path", ["/", "/play", "/progress", "/settings", "/help"])
def test_every_page_links_the_manifest_and_the_apple_touch_icon(graph: Graph, path: str) -> None:
    with TestClient(create_app(graph)) as client:
        page = client.get(path).text
        icon = re.search(r'<link rel="apple-touch-icon" href="([^"]+)">', head(page))
        assert icon, "an Apple touch icon"
        touch = client.get(icon.group(1))
    assert '<link rel="manifest" href="/manifest.webmanifest">' in head(page)
    assert '<meta name="theme-color" content="#161512">' in head(page)
    assert '<meta name="apple-mobile-web-app-capable" content="yes">' in head(page)
    assert touch.status_code == 200
    assert png_size(touch.content) == (180, 180)


def test_the_play_page_registers_the_worker_for_the_whole_site(graph: Graph) -> None:
    with TestClient(create_app(graph)) as client:
        scripts = re.findall(r'<script[^>]*src="([^"]+)"', client.get("/").text)
        sources = "".join(client.get(src).text for src in scripts)
    # Registered from the root, its scope is the whole site: the progress, settings and help
    # pages, which carry no script, still get the offline page.
    assert "navigator.serviceWorker.register('/sw.js')" in sources


def test_the_service_worker_is_served_at_the_root_under_a_cache_named_for_the_release(
    graph: Graph,
) -> None:
    with TestClient(create_app(graph)) as client:
        response = client.get("/sw.js")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/javascript")
    assert response.headers["cache-control"] == "no-cache"  # a new release is picked up at once
    assert "Service-Worker-Allowed" not in response.headers  # its own path gives the root scope
    cache = re.search(r"const CACHE = \"([^\"]+)\";", response.text)
    assert cache, "the cache name"
    assert f"-{metadata.version('chessop')}-" in cache.group(1)


def shell(worker: str) -> list[str]:
    """The paths the service worker caches."""
    found = re.search(r"const SHELL = (\[.*?\]);", worker, re.S)
    assert found, "the shell"
    return json.loads(found.group(1))


def test_the_worker_caches_only_static_shell_files_each_served(graph: Graph) -> None:
    with TestClient(create_app(graph)) as client:
        paths = shell(client.get("/sw.js").text)
        assert all(path.startswith("/static/") for path in paths), paths  # no page, no socket
        for path in paths:
            assert client.get(path).status_code == 200, path
    assert {
        "/static/chessground/chessground.min.js",
        "/static/chessground/chessground.cburnett.css",  # the pieces
        "/static/play.css",
        "/static/play.js",
        *(f"/static/sound/{n}.mp3" for n in ("Move", "Capture", "Check", "Victory", "Defeat")),
    } <= set(paths)


def test_the_offline_page_is_cached_and_says_chessop_needs_a_connection(graph: Graph) -> None:
    with TestClient(create_app(graph)) as client:
        worker = client.get("/sw.js").text
        offline = re.search(r"const OFFLINE = \"([^\"]+)\";", worker)
        assert offline, "the offline page"
        assert offline.group(1) in shell(worker)
        page = client.get(offline.group(1))
    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    text = " ".join(re.sub(r"<[^>]+>", " ", page.text).split())
    assert "chessop needs a connection: every move is checked by the server" in text
    again = r'<button[^>]*onclick="location.reload\(\)"[^>]*>Try again</button>'
    assert re.search(again, page.text)
