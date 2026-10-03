"""The `chessop` command."""

import argparse
import errno
import os
import re
import socket
import sys
import threading
import time
import webbrowser
from collections.abc import Mapping
from pathlib import Path

import uvicorn

from chessop.app import create_app
from chessop.backup import FOLDER
from chessop.choices import load
from chessop.explanations import Explanations, explanations_path, load_explanations
from chessop.graph import DEFAULT_BAND, PACKAGED_SNAPSHOT, Graph, load_graph
from chessop.hosted import Hosted, MissingVariables
from chessop.limits import FRAME_BYTES
from chessop.mail import ConsoleMailer, Courier, MailError, Message, TemMailer
from chessop.maintain import run as run_maintenance
from chessop.stats import report
from chessop.store import FILENAME, Store

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
UVICORN_FRAME_BYTES = 16 * 1024 * 1024  # uvicorn's own largest socket message: local mode's


def _add_options(parser: argparse.ArgumentParser, *, defaults: bool) -> None:
    """The options shared by `chessop` and `chessop serve`, accepted before or after `serve`.

    Only the top-level parser sets defaults, so the subcommand never overwrites a value given first.
    """

    def default(value: object) -> object:
        return value if defaults else argparse.SUPPRESS

    parser.add_argument("--host", default=default(DEFAULT_HOST), help="interface to bind")
    parser.add_argument(
        "--port", type=int, default=default(None), help=f"port (default {DEFAULT_PORT} or free)"
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=default(PACKAGED_SNAPSHOT),
        help="graph file to drill from (default: the one shipped in the package)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=default(None),
        help="data directory (default $CHESSOP_DATA_DIR, else the XDG data dir)",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="chessop", description="Drill chess openings.")
    _add_options(parser, defaults=True)
    parser.set_defaults(open_browser=True, hosted=False)
    commands = parser.add_subparsers(dest="command")
    serve = commands.add_parser("serve", help="serve without opening a browser, e.g. for the LAN")
    _add_options(serve, defaults=False)
    serve.add_argument(
        "--hosted",
        action="store_true",
        help="serve the public site: many learners, configured by the CHESSOP_* environment",
    )
    serve.set_defaults(open_browser=False)
    build = commands.add_parser(
        "build-snapshot",
        help="build the graph and explanation files from one month of the Lichess dump",
    )
    build.add_argument("--month", required=True, type=_month, help="dump month, YYYY-MM")
    build.add_argument("--max-games", type=int, help="stop after this many games read (dev runs)")
    build.add_argument("--book", type=Path, help="directory of the chess-openings TSV files")
    build.add_argument(
        "--out", type=Path, help="graph file to write; the explanation file goes beside it"
    )
    build.add_argument("--dump", help="local .pgn.zst or URL instead of the month's Lichess URL")
    build.add_argument(
        "--wikitext",
        type=Path,
        help="saved Wikibooks pages ({title: {wikitext}} JSON) instead of the Wikibooks API",
    )
    build.add_argument(
        "--contact", help="contact for the Wikibooks User-Agent (default: the package's author)"
    )
    notify = commands.add_parser(
        "notify-owner",
        help="mail standard input to the owner, configured like serve --hosted",
    )
    notify.add_argument("--subject", required=True, help="the message's subject")
    stats = commands.add_parser(
        "stats", help="print how much the site is used, read from the data directory's database"
    )
    nightly = commands.add_parser(
        "maintain",
        help="the nightly upkeep: usage aggregate, account warnings, purges, backup; configured"
        " like serve --hosted",
    )
    for command in (stats, nightly):
        command.add_argument(
            "--data-dir", type=Path, default=argparse.SUPPRESS, help="data directory, as for serve"
        )
    return parser.parse_args(argv)


def _month(value: str) -> str:
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
        raise argparse.ArgumentTypeError(f"not a YYYY-MM month: {value}")
    return value


def data_dir(flag: Path | None, environ: Mapping[str, str]) -> Path:
    """`--data-dir`, else `CHESSOP_DATA_DIR`, else `chessop` in the XDG data dir."""
    if flag is not None:
        return flag
    if env := environ.get("CHESSOP_DATA_DIR"):
        return Path(env)
    xdg = environ.get("XDG_DATA_HOME")
    return (Path(xdg) if xdg else Path.home() / ".local" / "share") / "chessop"


def bind(host: str, port: int | None, default_port: int = DEFAULT_PORT) -> socket.socket:
    """A listening socket on `port`, or on `default_port` falling back to a free one."""
    family, kind, proto, _, _ = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)[0]
    sock = socket.socket(family, kind, proto)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, default_port if port is None else port))
    except OSError as e:
        if port is not None or e.errno != errno.EADDRINUSE:
            sock.close()
            raise
        sock.bind((host, 0))
    sock.listen(128)
    return sock


def explanations_for(graph_path: Path, version: str) -> Explanations | None:
    """The explanation file beside the graph file, when there is one of the same version."""
    path = explanations_path(graph_path)
    if not path.exists():
        print(f"chessop: no explanation file at {path}, rounds end without one", flush=True)
        return None
    explanations = load_explanations(path)
    if explanations.version != version:
        print(
            f"chessop: {path} is version {explanations.version}, not {version}: ignored",
            flush=True,
        )
        return None
    return explanations


FALLBACK_BANDS = (DEFAULT_BAND,)


def graph_for(snapshot: Path, band: str) -> Graph:
    """The band the settings choose, else the first of `FALLBACK_BANDS` the snapshot holds."""
    for candidate in dict.fromkeys((band, *FALLBACK_BANDS)):
        try:
            graph = load_graph(snapshot, candidate)
        except KeyError:
            continue
        if candidate != band:
            print(f"chessop: {snapshot} holds no band {band}, drilling {candidate}", flush=True)
        return graph
    tried = ", ".join(dict.fromkeys((band, *FALLBACK_BANDS)))
    raise SystemExit(f"chessop: {snapshot} holds none of the bands {tried}")


def hosted_settings(args: argparse.Namespace, environ: Mapping[str, str]) -> Hosted | None:
    """The hosted site's settings from `environ` under `serve --hosted`, None otherwise: local
    mode, whatever the environment holds. A missing variable stops the start, each one named."""
    if not args.hosted:
        return None
    return hosted_or_exit(environ)


def hosted_or_exit(environ: Mapping[str, str]) -> Hosted:
    """The hosted site's settings in `environ`; a missing variable stops the command, each one
    named."""
    try:
        return Hosted.from_environ(environ)
    except MissingVariables as e:
        raise SystemExit(f"chessop: {e}") from None


def mailer_for(hosted: Hosted) -> TemMailer | ConsoleMailer:
    """Scaleway Transactional Email when the site has a mail key, else the console (public spec
    G2: an `https` base URL always has one)."""
    if hosted.tem_secret_key and hosted.tem_project_id:
        return TemMailer(hosted.tem_secret_key, hosted.tem_project_id, hosted.mail_from)
    return ConsoleMailer()


def notify_owner(subject: str, environ: Mapping[str, str]) -> None:
    """Mail standard input to the owner under `subject` (public spec §13), through the site's
    mailer; a message that did not go stops the command with a non-zero exit."""
    hosted = hosted_or_exit(environ)
    message = Message(to=hosted.owner_email, subject=subject, body=sys.stdin.read())
    try:
        mailer_for(hosted).deliver(message)
    except MailError as e:
        raise SystemExit(f"chessop: the owner was not mailed: {e}") from None


def print_stats(directory: Path, now: float) -> None:
    """Print the usage tables of the database in `directory` as they stand at `now` (public
    spec §12); with none there, say so and create none."""
    store = _existing(directory)
    try:
        print(report(store, now), end="")
    finally:
        store.close()


def maintain(directory: Path, hosted: Hosted, courier: Courier, now: float) -> None:
    """Run the nightly upkeep (`chessop.maintain`, public spec §13) at `now` on the database in
    `directory`, warning through `courier`; with no database there, say so and create none. A
    step that failed stops the command with a non-zero exit, once every step has run."""
    store = _existing(directory)
    try:
        succeeded = run_maintenance(
            store, courier, hosted.base_url, directory / FOLDER, hosted.backup, now
        )
    finally:
        store.close()
    if not succeeded:
        raise SystemExit(1)


def _existing(directory: Path) -> Store:
    """The store of the database in `directory`; with none there, the command stops."""
    if not (directory / FILENAME).exists():
        raise SystemExit(f"chessop: no database at {directory / FILENAME}")
    return Store.open(directory)


def serving(
    args: argparse.Namespace, environ: Mapping[str, str]
) -> tuple[uvicorn.Server, socket.socket, Graph]:
    """The server `args` and `environ` ask for, the socket it listens on and the graph it starts
    with.

    Local mode drills the band its one learner chose and falls back to a free port. Hosted mode
    (public spec §1) starts on the default band and its port is fixed. Neither writes an access
    log, and forwarded headers are trusted from `127.0.0.1` only. Hosted, the server reads no
    socket message past `FRAME_BYTES` (public spec §6): it closes the socket first."""
    hosted = hosted_settings(args, environ)
    store = Store.open(data_dir(args.data_dir, environ))
    if hosted is None:
        band, port = load(store.implicit()).settings.band, args.port
    else:
        band, port = DEFAULT_BAND, args.port or DEFAULT_PORT
    graph = graph_for(args.snapshot, band)
    explanations = explanations_for(args.snapshot, graph.version)
    sock = bind(args.host, port)
    app = create_app(
        graph,
        store=store,
        explanations=explanations,
        load_band=lambda band: load_graph(args.snapshot, band),
        hosted=hosted,
        mailer=None if hosted is None else mailer_for(hosted),
    )
    config = uvicorn.Config(
        app,
        log_level="warning",
        access_log=False,
        proxy_headers=True,
        forwarded_allow_ips="127.0.0.1",
        ws_max_size=UVICORN_FRAME_BYTES if hosted is None else FRAME_BYTES,
    )
    return uvicorn.Server(config), sock, graph


def main(argv: list[str] | None = None, environ: Mapping[str, str] = os.environ) -> None:
    args = parse_args(argv)
    if args.command == "build-snapshot":
        from chessop import build  # only here: the server never loads the build or zstandard

        build.main(args)
        return
    if args.command == "notify-owner":
        notify_owner(args.subject, environ)
        return
    if args.command == "stats":
        print_stats(data_dir(args.data_dir, environ), time.time())
        return
    if args.command == "maintain":
        hosted = hosted_or_exit(environ)
        maintain(data_dir(args.data_dir, environ), hosted, mailer_for(hosted), time.time())
        return
    server, sock, graph = serving(args, environ)
    port = sock.getsockname()[1]
    url_host = "127.0.0.1" if args.host in ("0.0.0.0", "::") else args.host
    if ":" in url_host:
        url_host = f"[{url_host}]"
    url = f"http://{url_host}:{port}/"
    print(f"chessop: {url}  ({graph.version}, band {graph.band})", flush=True)
    if args.open_browser:
        threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
    server.run(sockets=[sock])
