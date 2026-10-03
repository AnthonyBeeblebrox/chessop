"""The explanation file: Wikibooks *Chess Opening Theory* text per position, loaded at start.

A separate file from the graph file so the licences never mix: the text is CC BY-SA 4.0, trimmed
(spec §3.3). On disk it is JSON, gzip-compressed or not:

    {"licence": {"name": "...", "url": "...", "notice": "..."}, "version": "...",
     "pages": [{id, title, url, lead, text}, ...],
     "positions": {"<epd>": <page id>, ...}}

The position map is shared by every band; a position with no page has no entry.
"""

import gzip
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import chess


@dataclass(frozen=True)
class Page:
    id: int
    title: str
    url: str
    lead: str
    text: str


@dataclass(frozen=True)
class Explanations:
    version: str
    pages: list[Page]
    positions: dict[str, int]
    by_id: dict[int, Page] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "by_id", {p.id: p for p in self.pages})

    def page_at(self, epd: str) -> Page | None:
        page_id = self.positions.get(epd)
        return None if page_id is None else self.by_id[page_id]

    def for_path(self, path: list[str]) -> dict[str, Any] | None:
        """The explanation of the position `path` (UCI from the start) ends on: its own page, else
        the nearest position with a page walking back along the path, named in SAN as
        `borrowed_from`; None when no position after the start has a page."""
        board = chess.Board()
        sans, epds = [], []
        for uci in path:
            move = chess.Move.from_uci(uci)
            sans.append(board.san(move))
            board.push(move)
            epds.append(board.epd())
        for ply in range(len(path), 0, -1):
            page = self.page_at(epds[ply - 1])
            if page is not None:
                return {
                    "lead": page.lead,
                    "text": page.text,
                    "title": page.title,
                    "url": page.url,
                    "borrowed_from": None if ply == len(path) else line_text(sans[:ply]),
                }
        return None


def line_text(sans: list[str]) -> str:
    """Moves from the start as `1.e4 c5 2.Nf3`."""
    return " ".join(f"{i // 2 + 1}.{san}" if i % 2 == 0 else san for i, san in enumerate(sans))


def explanations_path(graph_path: Path) -> Path:
    """The explanation file beside a graph file: `x.graph.json.gz` -> `x.explanations.json.gz`."""
    name = graph_path.name
    if ".graph." in name:
        return graph_path.with_name(name.replace(".graph.", ".explanations.", 1))
    return graph_path.with_name(name + ".explanations.json.gz")


def load_explanations(path: Path) -> Explanations:
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    doc = json.loads(raw)
    pages = [Page(p["id"], p["title"], p["url"], p["lead"], p["text"]) for p in doc["pages"]]
    return Explanations(doc["version"], pages, dict(doc["positions"]))
