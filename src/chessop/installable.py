"""The installable app (public spec §8): the web app manifest, and the service worker's static
shell and cache name. Served in both modes; no offline play, so pages are never cached."""

import hashlib
from importlib import metadata
from pathlib import Path
from typing import Any

# The page background (play.css's `--bg`, and the base template's theme colour), which the
# installed app opens on and colours its title bar with.
BACKGROUND = "#161512"

MANIFEST: dict[str, Any] = {
    "name": "chessop \N{EM DASH} drill your openings",
    "short_name": "chessop",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "orientation": "any",
    "background_color": BACKGROUND,
    "theme_color": BACKGROUND,
    "icons": [
        {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
        # Full-bleed, its art inside the central circle a mask may cut to.
        {
            "src": "/static/icons/icon-maskable-512.png",
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "maskable",
        },
    ],
}

# The page shown when a page load fails, itself part of the shell.
OFFLINE = "/static/offline.html"

# What the service worker caches: chessground's script and styles (the pieces are inside the
# cburnett styles), the five sounds, the pages' styles and script, the icon and the offline page.
# Nothing else is ever answered from its cache.
SHELL = (
    "/static/chessground/chessground.min.js",
    "/static/chessground/chessground.base.css",
    "/static/chessground/chessground.brown.css",
    "/static/chessground/chessground.cburnett.css",
    "/static/sound/Move.mp3",
    "/static/sound/Capture.mp3",
    "/static/sound/Check.mp3",
    "/static/sound/Victory.mp3",
    "/static/sound/Defeat.mp3",
    "/static/play.css",
    "/static/play.js",
    "/static/icons/icon-192.png",
    OFFLINE,
)


def cache_name(static: Path) -> str:
    """The service worker's cache, named for the release and the shell's contents under `static`
    (served at `/static`): a new release, or any change to a shell file, opens a new cache and
    the old one is deleted."""
    digest = hashlib.sha256()
    for path in SHELL:
        digest.update((static / path.removeprefix("/static/")).read_bytes())
    return f"chessop-{metadata.version('chessop')}-{digest.hexdigest()[:12]}"
