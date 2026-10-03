"""The explanation file from Wikibooks *Chess Opening Theory*, for `build-snapshot` only.

Spec §3.2 step 6 and §3.3; ADR 0003's ticket 15 amendment; the trimming follows Lichess's
`transformWikiHtml` (`docs/research/opening-explanations.md` §1b). Every stored position of every
band is looked up under the title its book line spells, then under its canonical order in each
band; the first title whose page has prose is the position's page. Wikibooks' list of titles is read
first so only titles that exist are asked for, 50 to a request, in series.
"""

import gzip
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import chess

from chessop.explanations import Explanations, Page
from chessop.graph import Graph

API_URL = "https://en.wikibooks.org/w/api.php"
PAGE_URL = "https://en.wikibooks.org/wiki/"
PREFIX = "Chess Opening Theory/"
MAX_PLIES = 30
BATCH = 50
LEAD_CAP = 400  # characters
PAUSE = 0.5  # seconds between two requests
RETRIED_STATUSES = frozenset({429, 502, 503, 504})  # HTTP: rate-limited or unavailable
UNAVAILABLE_WAIT = 30.0  # seconds, when such a status names no Retry-After
MAXLAG_WAIT = 5.0  # seconds, when a maxlag error names no Retry-After
LICENCE = {
    "name": "Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)",
    "url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "notice": (
        'The pages below are text from the Wikibooks book "Chess Opening Theory"'
        " (https://en.wikibooks.org/wiki/Chess_Opening_Theory) by its contributors, listed in"
        " the history of each page at its url. Licensed under CC BY-SA 4.0. The text was"
        " trimmed: the position template, the move heading, theory tables, lists of replies,"
        " references, external links and link markup were removed. Fair-use quotations remain"
        " under their own terms. This file is CC BY-SA 4.0 data, separate from the program."
    ),
}


# Titles


def title_for(sans: list[str]) -> str | None:
    """The Wikibooks title for the moves `sans`, as Lichess builds it; None past 30 plies or at the
    start."""
    if not sans or len(sans) > MAX_PLIES:
        return None
    parts = [f"{i // 2 + 1}{'. ' if i % 2 == 0 else '...'}{san}" for i, san in enumerate(sans)]
    return PREFIX + re.sub(r"[+#!?]", "", "/".join(parts))


def _sans(uci_line: Iterable[str]) -> list[str]:
    board, sans = chess.Board(), []
    for uci in uci_line:
        move = chess.Move.from_uci(uci)
        sans.append(board.san(move))
        board.push(move)
    return sans


def page_url(title: str) -> str:
    return PAGE_URL + urllib.parse.quote(title.replace(" ", "_"), safe="/:'(),")


# Sources of wikitext


class Source(Protocol):
    def titles(self) -> set[str]:
        """Every title under the Chess Opening Theory prefix, pages and redirects."""
        ...

    def fetch(self, titles: list[str]) -> dict[str, tuple[str, str]]:
        """Asked title -> (the page's title after redirects, its wikitext), for pages found."""
        ...


@dataclass
class SavedPages:
    """Wikitext saved earlier (ticket 14's pull of Chess Opening Theory): offline builds, tests."""

    pages: dict[str, str]
    redirects: dict[str, str] = field(default_factory=dict)

    @classmethod
    def read(cls, path: Path) -> "SavedPages":
        """`{title: {"wikitext": ...}}`, gzip-compressed or not."""
        raw = path.read_bytes()
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return cls({title: page["wikitext"] for title, page in json.loads(raw).items()})

    def titles(self) -> set[str]:
        return {t for t in (*self.pages, *self.redirects) if t.startswith(PREFIX)}

    def fetch(self, titles: list[str]) -> dict[str, tuple[str, str]]:
        found = {}
        for title in titles:
            target = self.redirects.get(title, title)
            if target in self.pages:
                found[title] = (target, self.pages[target])
        return found


class WikibooksApi:
    """The MediaWiki action API of English Wikibooks, one request at a time (API etiquette:
    in series, `maxlag=5`, a descriptive User-Agent with contact)."""

    RETRIES = 8

    def __init__(
        self,
        user_agent: str,
        *,
        urlopen: Callable[..., Any] = urllib.request.urlopen,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.user_agent = user_agent
        self.urlopen = urlopen
        self.sleep = sleep
        self.requests = 0

    def titles(self) -> set[str]:
        out: set[str] = set()
        params: dict[str, str] = {
            "list": "allpages",
            "apprefix": PREFIX,
            "apfilterredir": "all",
            "aplimit": "max",
        }
        while True:
            doc = self._query(params)
            out.update(p["title"] for p in doc["query"]["allpages"])
            if "continue" not in doc:
                return out
            params = {**params, **doc["continue"]}

    def fetch(self, titles: list[str]) -> dict[str, tuple[str, str]]:
        found: dict[str, tuple[str, str]] = {}
        for start in range(0, len(titles), BATCH):
            batch = titles[start : start + BATCH]
            params: dict[str, str] = {
                "prop": "revisions",
                "rvprop": "content",
                "rvslots": "main",
                "titles": "|".join(batch),
                "redirects": "1",
            }
            renamed: dict[str, str] = {}
            contents: dict[str, str] = {}
            while True:
                doc = self._query(params)
                query = doc.get("query", {})
                for step in (*query.get("normalized", ()), *query.get("redirects", ())):
                    renamed[step["from"]] = step["to"]
                for page in query.get("pages", ()):
                    revisions = page.get("revisions")
                    if revisions:
                        contents[page["title"]] = revisions[0]["slots"]["main"]["content"]
                if "continue" not in doc:
                    break
                params = {**params, **doc["continue"]}
            for title in batch:
                target, seen = title, {title}
                while target in renamed and renamed[target] not in seen:
                    target = renamed[target]
                    seen.add(target)
                if target in contents:
                    found[title] = (target, contents[target])
        return found

    def _query(self, params: Mapping[str, str]) -> dict[str, Any]:
        body = urllib.parse.urlencode(
            {"action": "query", **params, "maxlag": "5", "format": "json", "formatversion": "2"}
        ).encode()
        for _ in range(self.RETRIES):
            if self.requests:
                self.sleep(PAUSE)
            self.requests += 1
            request = urllib.request.Request(
                API_URL, data=body, headers={"User-Agent": self.user_agent}
            )
            try:
                with self.urlopen(request, timeout=120) as response:
                    doc = json.loads(response.read())
                    retry_after = response.headers.get("Retry-After")
            except urllib.error.HTTPError as e:
                if e.code not in RETRIED_STATUSES:
                    raise
                self.sleep(_seconds(e.headers.get("Retry-After"), default=UNAVAILABLE_WAIT))
                continue
            if doc.get("error", {}).get("code") == "maxlag":
                self.sleep(_seconds(retry_after, default=MAXLAG_WAIT))
                continue
            if "error" in doc:
                raise RuntimeError(f"Wikibooks API error: {doc['error']}")
            return doc
        raise RuntimeError("Wikibooks API: still lagging or unavailable after retries")


def _seconds(retry_after: str | None, *, default: float) -> float:
    """A `Retry-After` header given in seconds, else `default` (an HTTP date is not followed)."""
    try:
        return float(retry_after) if retry_after else default
    except ValueError:
        return default


# The converter


@dataclass(frozen=True)
class Converted:
    lead: str
    text: str


HIDDEN = re.compile(
    r"^(theory table|all possible .*|(black's |white's )?(replies|responses)|external links"
    r"|references|footnotes|notes|bibliography|see also)$",
    re.I,
)
HEADING = re.compile(r"^(=+)\s*(.*?)\s*=+\s*$")
CONVENTIONS = "When contributing to this Wikibook, please follow the Conventions for organization."
# The evaluation symbols of `{{Chess/not|...}}` and `{{chesspunc|...}}`.
NOTATION = {
    "+": "⩲",
    "++": "±",
    "+++": "+\u2212",  # minus sign
    "=": "=",
    "-": "⩱",
    "--": "∓",
    "---": "\u2212+",
    "unclear": "∞",
    "∞": "∞",
    "only": "□",
    "equal": "=",
    "compensation": "=/∞",
}


def _template(inner: str) -> str:
    """What an inline template shows in the prose; every other template is dropped."""
    name, *args = [a.strip() for a in inner.split("|")]
    name = name.lower().replace("_", " ")
    if name in ("w", "wikipedia-inline") and args:
        return args[-1]
    if name in ("chess/not", "chesspunc") and args:
        return NOTATION.get(args[0], "")
    return ""


def _strip_templates(s: str) -> str:
    """Templates replaced innermost first by what they show inline (mostly nothing)."""
    stack: list[list[str]] = [[]]
    i = 0
    while i < len(s):
        if s.startswith("{{", i):
            stack.append([])
            i += 2
        elif s.startswith("}}", i) and len(stack) > 1:
            inner = "".join(stack.pop())
            stack[-1].append(_template(inner))
            i += 2
        else:
            stack[-1].append(s[i])
            i += 1
    while len(stack) > 1:  # an unclosed template runs to the end of the page: dropped
        stack.pop()
    return "".join(stack[0])


def _strip_tables(s: str) -> str:
    out, depth = [], 0
    for line in s.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("{|"):
            depth += 1
        elif depth and stripped.startswith("|}"):
            depth -= 1
        elif not depth:
            out.append(line)
    return "\n".join(out)


def _link(match: re.Match[str]) -> str:
    target, _, label = match.group(1).partition("|")
    prefix, colon, rest = target.strip().partition(":")
    wikipedia = colon and prefix.lower() in ("w", "wikipedia")
    if colon and not wikipedia:  # files and their captions, categories, other languages
        return ""
    if label:
        return label
    return rest if wikipedia else target.strip().rstrip("/").rsplit("/", 1)[-1]


def _inline(s: str) -> str:
    s = re.sub(r"\[\[([^\[\]]*)\]\]", _link, s)
    s = re.sub(r"\[https?://\S+\s*([^\]]*)\]", r"\1", s)
    s = s.replace("'''", "").replace("''", "")
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]*>", "", s)
    s = html.unescape(s).replace(CONVENTIONS, "")
    return re.sub(r"\s+", " ", s).strip()


def convert(wikitext: str) -> Converted | None:
    """The page's prose as plain paragraphs (sub-headings kept as their own paragraphs) and its
    lead, or None when no prose remains."""
    s = re.sub(r"<!--.*?-->", "", wikitext, flags=re.S)
    s = re.sub(r"__[A-Z]+__", "", s)  # magic words: __NOTOC__ and the like
    s = re.sub(r"<ref[^>]*/>", "", s, flags=re.I)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S | re.I)
    s = re.sub(r"<references[^>]*>(.*?</references>)?", "", s, flags=re.S | re.I)
    s = re.sub(r"<table.*?</table>", "", s, flags=re.S | re.I)
    s = _strip_tables(_strip_templates(s))
    s = re.sub(r"</?(blockquote|p|div)[^>]*>", "\n\n", s, flags=re.I)

    blocks: list[tuple[str, str]] = []  # ("heading" | "prose", text)
    lines: list[str] = []
    skip_level: int | None = None

    def flush() -> None:
        if lines and skip_level is None:
            text = _inline(" ".join(lines))
            if re.search(r"\w", text):
                blocks.append(("prose", text))
        lines.clear()

    for line in s.split("\n"):
        if heading := HEADING.match(line.strip()):
            flush()
            level, title = len(heading.group(1)), _inline(heading.group(2))
            if skip_level is not None and level <= skip_level:
                skip_level = None
            if skip_level is not None:
                continue
            if HIDDEN.match(title):
                skip_level = level
            elif any(kind == "prose" for kind, _ in blocks):  # the move heading comes first
                blocks.append(("heading", title))
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith(("|", "!")):
            flush()
            continue
        if stripped[0] in "*#:;":  # a list item is a paragraph of its own
            flush()
            lines.append(stripped.lstrip("*#:; "))
            flush()
            continue
        lines.append(stripped)
    flush()

    while blocks and blocks[-1][0] == "heading":  # a heading left with no prose under it
        blocks.pop()
    blocks = [b for i, b in enumerate(blocks) if b[0] == "prose" or blocks[i + 1][0] == "prose"]
    if not blocks:
        return None
    first = next((i for i, (kind, _) in enumerate(blocks) if kind == "heading"), len(blocks))
    lead = "\n\n".join(text for _, text in blocks[:first])  # the first block is prose
    return Converted(_cap(lead), "\n\n".join(text for _, text in blocks))


def _cap(lead: str) -> str:
    """At most `LEAD_CAP` characters, cut after a sentence when one ends in the second half, else
    at a word with an ellipsis."""
    if len(lead) <= LEAD_CAP:
        return lead
    head = lead[: LEAD_CAP + 1]
    sentence = max(head.rfind(end) for end in (". ", "! ", "? ", ".\n"))
    if sentence >= LEAD_CAP // 2:
        return head[: sentence + 1]
    return head[: LEAD_CAP - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


# The explanation file


def build_explanations(
    graphs: Mapping[str, Graph], version: str, source: Source, progress: bool = False
) -> Explanations:
    """Every stored position of every band mapped to its page, each page stored once."""
    candidates: dict[str, list[str]] = {}
    for graph in graphs.values():
        for position in graph.positions.values():
            titles = candidates.setdefault(position.epd, [])
            for line in (position.book_line, position.canonical):
                title = None if line is None else title_for(_sans(line))
                if title is not None and title not in titles:
                    titles.append(title)
    existing = source.titles()
    wanted = sorted({t for titles in candidates.values() for t in titles if t in existing})
    if progress:
        print(f"  explanations: {len(wanted):,} titles to fetch", flush=True)
    found = source.fetch(wanted)
    converted: dict[str, Converted | None] = {}
    for page_title, wikitext in found.values():
        if page_title not in converted:
            converted[page_title] = convert(wikitext)

    ids = {t: i for i, t in enumerate(sorted(t for t, c in converted.items() if c is not None))}
    pages = []
    for title, page_id in ids.items():
        c = converted[title]
        assert c is not None
        pages.append(Page(page_id, title, page_url(title), c.lead, c.text))
    positions = {}
    for epd, titles in candidates.items():
        for title in titles:
            hit = found.get(title)
            if hit is not None and hit[0] in ids:
                positions[epd] = ids[hit[0]]
                break
    return Explanations(version, pages, positions)


def write_explanation_file(explanations: Explanations, path: Path) -> None:
    doc = {
        "licence": LICENCE,
        "version": explanations.version,
        "pages": [
            {"id": p.id, "title": p.title, "url": p.url, "lead": p.lead, "text": p.text}
            for p in explanations.pages
        ],
        "positions": explanations.positions,
    }
    data = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode()
    path.write_bytes(gzip.compress(data, mtime=0))
