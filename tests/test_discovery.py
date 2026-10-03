"""Discovery (public spec §11): the pitch, the link previews, what search engines may index, and
the README. Driven through the app as a browser or a crawler would; a forged `Host` stands in
for a request that names another site than the configured base URL."""

import re
from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient

from chessop.app import create_app
from chessop.repertoire import START
from test_hosted import Site, play_a_round
from test_wire import E4_E5

PITCH_TITLE = "chessop: grind chess openings"
PITCH = (
    "Grind chess openings against the moves people at your rating really play, drawn from"
    " Lichess games. Free, no sign-up."
)
FORGED = {"host": "evil.example"}


def head(page: str) -> str:
    """The page's `<head>`."""
    return page[: page.index("</head>")]


def meta(page: str, attribute: str, name: str) -> list[str]:
    """The contents of the head's `<meta {attribute}="{name}">` tags."""
    return re.findall(rf'<meta {attribute}="{re.escape(name)}" content="([^"]*)">', head(page))


def canonical(page: str) -> list[str]:
    """The addresses of the head's canonical links."""
    return re.findall(r'<link rel="canonical" href="([^"]*)">', head(page))


def title(page: str) -> str:
    """The page's title."""
    found = re.search(r"<title>(.*?)</title>", page, re.S)
    assert found is not None
    return found.group(1)


def test_the_hosted_home_page_carries_the_pitch_and_its_preview_from_the_base_url(
    tmp_path: Path,
) -> None:
    with Site(tmp_path).browser() as browser:
        page = browser.get("/", headers=FORGED).text
    assert title(page) == PITCH_TITLE
    assert meta(page, "name", "description") == [PITCH]
    assert canonical(page) == ["https://chessop.example/"]
    assert meta(page, "property", "og:title") == [PITCH_TITLE]
    assert meta(page, "property", "og:description") == [PITCH]
    assert meta(page, "property", "og:url") == ["https://chessop.example/"]
    assert meta(page, "property", "og:type") == ["website"]
    assert meta(page, "property", "og:image") == ["https://chessop.example/static/preview.png"]
    assert meta(page, "name", "twitter:card") == ["summary_large_image"]
    assert meta(page, "name", "robots") == []
    assert "evil.example" not in page


def test_the_hosted_help_page_keeps_its_title_with_the_pitch_and_its_canonical_address(
    tmp_path: Path,
) -> None:
    with Site(tmp_path).browser() as browser:
        page = browser.get("/help", headers=FORGED).text
    assert title(page) == "How chessop works"
    assert meta(page, "name", "description") == [PITCH]
    assert canonical(page) == ["https://chessop.example/help"]
    assert meta(page, "property", "og:title") == ["How chessop works"]
    assert meta(page, "property", "og:url") == ["https://chessop.example/help"]
    assert meta(page, "property", "og:image") == ["https://chessop.example/static/preview.png"]
    assert meta(page, "name", "robots") == []
    assert "evil.example" not in page


# Every other page a hosted browser can open, with or without a learner or an account.
PRIVATE = (
    "/play",
    "/progress",
    "/settings",
    "/settings/reset",
    "/progress/position/" + quote(START, safe=""),
    "/signin",
    "/data",
    "/data/forget",
    "/legal",
    "/privacy",
)


def test_every_other_hosted_page_carries_noindex_and_no_canonical_address(
    tmp_path: Path,
) -> None:
    with Site(tmp_path).browser() as browser:
        play_a_round(browser)  # a learner, so that the pages for one show
        for path in PRIVATE:
            response = browser.get(path, headers=FORGED)
            assert response.status_code == 200, path
            page = response.text
            assert meta(page, "name", "robots") == ["noindex"], path
            assert canonical(page) == [], path
            assert title(page) != PITCH_TITLE, path
            assert "evil.example" not in page, path


def test_the_hosted_robots_txt_allows_crawling_and_names_no_sitemap(tmp_path: Path) -> None:
    with Site(tmp_path).browser() as browser:
        response = browser.get("/robots.txt", headers=FORGED)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    lines = response.text.splitlines()
    assert "User-agent: *" in lines and "Allow: /" in lines
    assert not any(line.startswith("Disallow: /") for line in lines)
    assert "sitemap" not in response.text.lower()
    assert "set-cookie" not in response.headers


def test_the_preview_image_is_one_1200_by_630_png(tmp_path: Path) -> None:
    with Site(tmp_path).browser() as browser:
        response = browser.get("/static/preview.png")
    assert response.status_code == 200
    png = response.content
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and png[12:16] == b"IHDR"
    assert int.from_bytes(png[16:20]) == 1200 and int.from_bytes(png[20:24]) == 630


def test_local_pages_have_no_preview_no_indexing_tags_and_no_robots_txt() -> None:
    with TestClient(create_app(E4_E5)) as browser:
        for path in ("/", "/play", "/help", "/progress", "/settings"):
            page = browser.get(path).text
            for tag in ('property="og:', 'name="twitter:', 'rel="canonical"', 'name="robots"'):
                assert tag not in page, (path, tag)
            assert 'name="description"' not in page, path
        assert title(browser.get("/").text) == "chessop"
        assert title(browser.get("/help").text) == "How chessop works"
        assert browser.get("/robots.txt").status_code == 404


ROOT = Path(__file__).parent.parent


def test_the_readme_leads_with_the_pitch_then_running_then_hosting_with_the_licence_last() -> None:
    readme = (ROOT / "README.md").read_text()
    lead = readme[: readme.index("\n## ")]
    assert PITCH in re.sub(r"\s+", " ", lead)
    assert "https://chessop.fr" in lead
    assert re.search(r"!\[[^\]]*\]\([^)]+\.png\)", lead)  # the screenshot's slot
    headings = re.findall(r"^## (.+)$", readme, re.M)
    assert headings[0] == "Run it yourself"
    assert headings[1] == "Hosting your own"
    assert headings[-1].startswith("Licen")
    hosting = readme[readme.index("## Hosting your own") :]
    hosting = hosting[: hosting.index("\n## ")]
    assert "serve --hosted" in hosting and "deploy/" in hosting
    assert "no support" in hosting.lower()
    assert "badge" not in readme.lower() and "shields.io" not in readme


def test_grind_is_said_in_the_pitch_only() -> None:
    files = [ROOT / "README.md", ROOT / "docs" / "operating.md"] + [
        path
        for path in (ROOT / "src" / "chessop").rglob("*")
        if path.suffix in {".py", ".html", ".js", ".css", ".json", ".webmanifest"}
    ]
    for path in files:
        text = path.read_text(errors="ignore")
        for found in re.finditer(r"grind", text, re.I):
            said = text[found.start() : found.end() + 15]
            assert said.lower() == "grind chess openings", path
