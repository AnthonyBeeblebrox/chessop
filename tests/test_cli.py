import io
import json
import socket
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from chessop.build import user_agent
from chessop.choices import load
from chessop.cli import (
    bind,
    data_dir,
    explanations_for,
    graph_for,
    hosted_settings,
    main,
    parse_args,
    serving,
)
from chessop.graph import FIXTURE_SNAPSHOT, PACKAGED_SNAPSHOT, load_graph
from chessop.store import Store
from conftest import Endpoint
from graphs import epd_after


def test_bare_chessop_plays_locally_on_8000_with_the_packaged_snapshot() -> None:
    args = parse_args([])
    assert (args.host, args.port, args.snapshot) == ("127.0.0.1", None, PACKAGED_SNAPSHOT)
    assert args.open_browser


def test_serve_binds_another_interface_and_snapshot() -> None:
    args = parse_args(["serve", "--host", "0.0.0.0", "--port", "9000", "--snapshot", "g.json"])
    assert (args.host, args.port, args.snapshot) == ("0.0.0.0", 9000, Path("g.json"))
    assert not args.open_browser


def test_bind_falls_back_to_a_free_port_when_the_default_is_taken() -> None:
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        busy = taken.getsockname()[1]
        with bind("127.0.0.1", None, default_port=busy) as sock:
            port = sock.getsockname()[1]
    assert port != busy


def test_bind_uses_the_default_port_when_free() -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        free = probe.getsockname()[1]
    with bind("127.0.0.1", None, default_port=free) as sock:
        assert sock.getsockname()[1] == free


def test_options_given_before_serve_are_kept() -> None:
    args = parse_args(["--snapshot", "g.json", "--port", "9000", "serve"])
    assert (args.port, args.snapshot) == (9000, Path("g.json"))
    assert not args.open_browser


def test_build_snapshot_takes_a_month_and_the_developer_switches() -> None:
    args = parse_args(["build-snapshot", "--month", "2026-08", "--max-games", "500"])
    assert (args.command, args.month, args.max_games) == ("build-snapshot", "2026-08", 500)
    assert args.book is None and args.out is None and args.dump is None


def test_build_snapshot_refuses_a_malformed_month() -> None:
    with pytest.raises(SystemExit):
        parse_args(["build-snapshot", "--month", "2026-13"])


def test_the_data_dir_is_the_flag_else_the_environment_else_the_xdg_default() -> None:
    home = Path.home()
    env = {"CHESSOP_DATA_DIR": "/env/dir"}
    assert data_dir(Path("/flag/dir"), env) == Path("/flag/dir")
    assert data_dir(None, env) == Path("/env/dir")
    assert data_dir(None, {}) == home / ".local" / "share" / "chessop"
    assert data_dir(None, {"XDG_DATA_HOME": "/xdg"}) == Path("/xdg/chessop")


def test_data_dir_is_accepted_before_or_after_serve() -> None:
    assert parse_args([]).data_dir is None
    assert parse_args(["--data-dir", "d", "serve"]).data_dir == Path("d")
    assert parse_args(["serve", "--data-dir", "d"]).data_dir == Path("d")


def test_the_explanation_file_beside_the_snapshot_is_loaded_when_its_version_matches() -> None:
    version = load_graph(FIXTURE_SNAPSHOT).version
    explanations = explanations_for(FIXTURE_SNAPSHOT, version)
    assert explanations is not None
    page = explanations.page_at(epd_after("e4", "c5"))
    assert page is not None and page.title == "Chess Opening Theory/1. e4/1...c5"
    assert explanations_for(FIXTURE_SNAPSHOT, "another/version") is None
    assert explanations_for(Path("nowhere.graph.json"), version) is None


def test_the_wikibooks_user_agent_names_the_app_and_a_contact() -> None:
    assert user_agent("me@example.org").startswith("chessop/0.1.0 (me@example.org) Python-urllib/")
    assert "@" in user_agent(None)


def test_the_stored_band_is_loaded_else_1500_plus_when_the_snapshot_lacks_it() -> None:
    store = Store.in_memory()
    assert graph_for(FIXTURE_SNAPSHOT, load(store.implicit()).settings.band).band == "1500+"
    store.implicit().set_setting("band", "1500-1800")
    assert graph_for(FIXTURE_SNAPSHOT, load(store.implicit()).settings.band).band == "1500-1800"
    store.implicit().set_setting("band", "2100+")
    assert graph_for(FIXTURE_SNAPSHOT, load(store.implicit()).settings.band).band == "1500+"


def test_a_snapshot_without_the_default_band_exits_naming_the_bands_tried(tmp_path: Path) -> None:
    doc = json.loads(FIXTURE_SNAPSHOT.read_text())
    del doc["bands"]["1500+"]
    path = tmp_path / "closed.graph.json"
    path.write_text(json.dumps(doc))
    assert graph_for(path, "1500-1800").band == "1500-1800"
    with pytest.raises(SystemExit, match=r"holds none of the bands 1800\+, 1500\+"):
        graph_for(path, "1800+")


HOSTED_ENV = {
    "CHESSOP_BASE_URL": "http://localhost:8000",
    "CHESSOP_MAIL_FROM": "login@chessop.example",
    "CHESSOP_OWNER_EMAIL": "owner@chessop.example",
}


def test_serve_hosted_with_variables_missing_exits_naming_every_one(tmp_path: Path) -> None:
    argv = ["serve", "--hosted", "--data-dir", str(tmp_path)]
    with pytest.raises(SystemExit) as stopped:
        main(argv, {})
    assert stopped.value.code not in (0, None)
    for name in ("CHESSOP_BASE_URL", "CHESSOP_MAIL_FROM", "CHESSOP_OWNER_EMAIL"):
        assert name in str(stopped.value.code)
    # On an https base URL the mail key is required too (public spec G2).
    with pytest.raises(SystemExit) as stopped:
        main(argv, {"CHESSOP_BASE_URL": "https://chessop.example", "CHESSOP_MAIL_FROM": "a@b.c"})
    message = str(stopped.value.code)
    for name in ("CHESSOP_OWNER_EMAIL", "CHESSOP_TEM_SECRET_KEY", "CHESSOP_TEM_PROJECT_ID"):
        assert name in message
    assert "CHESSOP_BASE_URL" not in message and "CHESSOP_MAIL_FROM" not in message
    assert not (tmp_path / "chessop.sqlite").exists()  # nothing half-started


def test_the_base_url_alone_never_turns_hosted_mode_on() -> None:
    assert not parse_args([]).hosted and not parse_args(["serve"]).hosted
    assert hosted_settings(parse_args(["serve"]), HOSTED_ENV) is None
    hosted = hosted_settings(parse_args(["serve", "--hosted"]), HOSTED_ENV)
    assert hosted is not None and hosted.base_url == "http://localhost:8000"


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_serve_hosted_starts_on_the_fixed_port_with_no_browser_and_no_access_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    args = parse_args(
        ["serve", "--hosted", "--snapshot", str(FIXTURE_SNAPSHOT), "--data-dir", str(tmp_path)]
    )
    assert not args.open_browser and args.host == "127.0.0.1"
    port = free_port()
    monkeypatch.setattr("chessop.cli.DEFAULT_PORT", port)
    server, sock, _ = serving(args, HOSTED_ENV)
    with sock:
        assert sock.getsockname() == ("127.0.0.1", port)
        config = server.config
        assert not config.access_log
        assert config.proxy_headers and config.forwarded_allow_ips == "127.0.0.1"
        assert config.ws_max_size == 64 * 1024  # no huge socket message is read whole
        app: Any = config.app
        with TestClient(app, base_url="http://localhost:8000") as browser:
            assert "<footer" in browser.get("/").text  # the hosted site
        # The port is fixed: taken, hosted mode does not look for a free one.
        with pytest.raises(OSError):
            serving(args, HOSTED_ENV)


def test_serve_without_hosted_is_local_mode_whatever_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    args = parse_args(["serve", "--snapshot", str(FIXTURE_SNAPSHOT), "--data-dir", str(tmp_path)])
    monkeypatch.setattr("chessop.cli.DEFAULT_PORT", free_port())
    server, sock, _ = serving(args, HOSTED_ENV)
    assert server.config.ws_max_size == 16 * 1024 * 1024  # uvicorn's own: no limit of ours
    app: Any = server.config.app
    with sock, TestClient(app) as browser:
        assert "<footer" not in browser.get("/").text


HTTPS_ENV = {
    **HOSTED_ENV,
    "CHESSOP_BASE_URL": "https://chessop.example",
    "CHESSOP_TEM_SECRET_KEY": "tem-secret-key",
    "CHESSOP_TEM_PROJECT_ID": "tem-project-id",
}


def test_serve_hosted_with_a_mail_key_mails_through_scaleway(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, endpoint: Endpoint
) -> None:
    monkeypatch.setattr("chessop.cli.DEFAULT_PORT", free_port())
    args = parse_args(
        ["serve", "--hosted", "--snapshot", str(FIXTURE_SNAPSHOT), "--data-dir", str(tmp_path)]
    )
    server, sock, _ = serving(args, HTTPS_ENV)
    app: Any = server.config.app
    with sock, TestClient(app, base_url="https://chessop.example") as browser:
        browser.post("/signin", data={"email": "ann@example.org", "next": "/"})
        assert endpoint.arrived.wait(5)
    (posted,) = endpoint.received
    assert posted.headers["x-auth-token"] == "tem-secret-key"
    assert posted.body["from"]["email"] == "login@chessop.example"
    assert posted.body["to"] == [{"email": "ann@example.org"}]


def notify_owner(
    monkeypatch: pytest.MonkeyPatch, environ: dict[str, str], body: str, subject: str = "Disk"
) -> None:
    """Run `chessop notify-owner --subject subject` with `body` on its standard input."""
    monkeypatch.setattr("sys.stdin", io.StringIO(body))
    main(["notify-owner", "--subject", subject], environ)


def test_notify_owner_mails_stdin_to_the_owner_under_the_subject(
    monkeypatch: pytest.MonkeyPatch, endpoint: Endpoint
) -> None:
    notify_owner(monkeypatch, HTTPS_ENV, "/dev/sda1 81% used\n", subject="chessop: disk at 81%")
    (posted,) = endpoint.received  # sent before the command returns
    assert posted.headers["x-auth-token"] == "tem-secret-key"
    assert posted.body["project_id"] == "tem-project-id"
    assert posted.body["from"]["email"] == "login@chessop.example"
    assert posted.body["to"] == [{"email": "owner@chessop.example"}]
    assert posted.body["subject"] == "chessop: disk at 81%"
    assert posted.body["text"] == "/dev/sda1 81% used\n"


def test_notify_owner_exits_non_zero_when_the_message_does_not_go(
    monkeypatch: pytest.MonkeyPatch, endpoint: Endpoint
) -> None:
    endpoint.status = 503
    with pytest.raises(SystemExit) as stopped:
        notify_owner(monkeypatch, HTTPS_ENV, "chessop.service failed\n")
    assert stopped.value.code not in (0, None) and "503" in str(stopped.value.code)
    assert len(endpoint.received) == 1


def test_notify_owner_on_http_with_no_mail_key_prints_the_message(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    notify_owner(monkeypatch, HOSTED_ENV, "chessop.service failed\n", subject="chessop failed")
    printed = capsys.readouterr().out
    assert "owner@chessop.example" in printed
    assert "Subject: chessop failed" in printed and "chessop.service failed" in printed


def test_notify_owner_reads_the_environment_serve_hosted_does() -> None:
    with pytest.raises(SystemExit) as stopped:
        main(["notify-owner", "--subject", "Disk"], {"CHESSOP_BASE_URL": "https://chessop.example"})
    message = str(stopped.value.code)
    for name in (
        "CHESSOP_MAIL_FROM",
        "CHESSOP_OWNER_EMAIL",
        "CHESSOP_TEM_SECRET_KEY",
        "CHESSOP_TEM_PROJECT_ID",
    ):
        assert name in message


def test_notify_owner_requires_a_subject() -> None:
    with pytest.raises(SystemExit):
        parse_args(["notify-owner"])
