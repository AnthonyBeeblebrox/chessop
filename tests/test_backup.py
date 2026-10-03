"""The nightly backup (public spec §13, §14): the last two steps of `chessop maintain`, backup
and upload. The site is driven as a browser would, then the command is run on its data directory
at a chosen time, the off-site bucket an HTTP stub standing in for Scaleway Object Storage; the
backups folder, the restored database and the object handed to the bucket are looked at."""

import hashlib
import re
import shutil
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pyrage
import pytest

from chessop.backup import OffSite, sign
from chessop.cli import main, maintain
from chessop.store import FILENAME, Store
from test_cli import HOSTED_ENV
from test_hosted import DAY, HOSTED, NOW, Site
from test_maintain import Post, play_rounds, run

IDENTITY = pyrage.x25519.Identity.generate()  # the owner's age key, kept off the VPS
OFF_SITE = OffSite(
    bucket="chessop-backups",
    access_key="SCWBACKUPACCESSKEY",
    secret_key="backup-secret-key",
    recipient=str(IDENTITY.to_public()),
)
BACKED_UP = replace(HOSTED, backup=OFF_SITE)


@dataclass
class Put:
    """One object the bucket was handed."""

    path: str
    headers: dict[str, str]
    body: bytes


@dataclass
class Bucket:
    """Scaleway Object Storage, stubbed: the objects put in it, oldest first. It answers
    `status` to each."""

    received: list[Put] = field(default_factory=list)
    status: int = 200


@pytest.fixture
def bucket(monkeypatch: pytest.MonkeyPatch) -> Iterator[Bucket]:
    """Scaleway Object Storage, stubbed, where every backup uploaded from now on goes."""
    stub = Bucket()

    class Handler(BaseHTTPRequestHandler):
        def do_PUT(self) -> None:
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            headers = {name.lower(): value for name, value in self.headers.items()}
            stub.received.append(Put(self.path, headers, body))
            self.send_response(stub.status)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    monkeypatch.setattr("chessop.backup.ENDPOINT", f"http://127.0.0.1:{server.server_address[1]}")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield stub
    finally:
        server.shutdown()
        server.server_close()


def test_a_request_is_signed_as_in_the_aws_signature_v4_worked_example() -> None:
    # "Example: PUT Object" in Amazon S3's "Signature Calculations for the Authorization
    # Header: Transferring Payload in a Single Chunk (AWS Signature Version 4)".
    headers = sign(
        "PUT",
        "https://examplebucket.s3.amazonaws.com/test%24file.text",
        {
            "Date": "Fri, 24 May 2013 00:00:00 GMT",
            "x-amz-storage-class": "REDUCED_REDUNDANCY",
        },
        payload_hash="44ce7dd67c959e0d3524ffac1771dfbba87d2b6b4b4e99e42034a8b803f8b072",
        access_key="AKIAIOSFODNN7EXAMPLE",
        secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="us-east-1",
        now=1_369_353_600.0,  # 2013-05-24T00:00:00Z
    )
    assert headers["Authorization"] == (
        "AWS4-HMAC-SHA256 Credential=AKIAIOSFODNN7EXAMPLE/20130524/us-east-1/s3/aws4_request,"
        "SignedHeaders=date;host;x-amz-content-sha256;x-amz-date;x-amz-storage-class,"
        "Signature=98ad721746da40c64f1a55b78f14c238d841ea1380cd77a1b5971af0ece108bd"
    )
    assert headers["x-amz-date"] == "20130524T000000Z"


def backups(site: Site) -> list[str]:
    """The backups folder's files, oldest first."""
    return sorted(path.name for path in (site.data_dir / "backups").iterdir())


def test_maintain_leaves_a_restorable_backup_of_the_live_database(tmp_path: Path) -> None:
    site = Site(tmp_path / "live")
    with site.browser() as browser:
        play_rounds(browser, 5)  # the rounds still in the live database's write-ahead log
    site.clock.now = NOW + DAY  # 2027-01-16
    run(site)
    assert backups(site) == ["chessop-2027-01-16.sqlite"]
    restored = tmp_path / "restored"
    restored.mkdir()
    shutil.copy(site.data_dir / "backups" / "chessop-2027-01-16.sqlite", restored / FILENAME)
    assert Site(restored).learners() == 1
    store = Store.open(restored)
    try:
        (day,) = (day for day in store.usage_days() if day.rounds)
        assert day.rounds == 5
    finally:
        store.close()


def test_only_the_14_most_recent_backups_are_kept(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    site = Site(tmp_path)
    for days in range(1, 17):  # 2027-01-16 to 2027-01-31
        site.clock.now = NOW + days * DAY
        run(site)
    assert "wrote chessop-2027-01-31.sqlite, 14 kept, 1 removed" in capsys.readouterr().out
    site.clock.now += 3600
    run(site)  # a second run in the day replaces its backup
    assert backups(site) == [f"chessop-2027-01-{day}.sqlite" for day in range(18, 32)]
    assert "wrote chessop-2027-01-31.sqlite, 14 kept, 0 removed" in capsys.readouterr().out


def test_the_backup_is_uploaded_encrypted_to_the_owners_age_key(
    tmp_path: Path, bucket: Bucket
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        play_rounds(browser, 5)
    site.clock.now = NOW + DAY  # 2027-01-16
    maintain(site.data_dir, BACKED_UP, Post(), site.clock.now)
    (put,) = bucket.received
    assert put.path == "/chessop-backups/chessop-2027-01-16.sqlite.age"
    assert put.body.startswith(b"age-encryption.org/v1\n")
    local = site.data_dir / "backups" / "chessop-2027-01-16.sqlite"
    assert pyrage.decrypt(put.body, [IDENTITY]) == local.read_bytes()
    # Signed at the real time, which the bucket checks, not the run's.
    assert re.match(
        r"AWS4-HMAC-SHA256 Credential=SCWBACKUPACCESSKEY/\d{8}/fr-par/s3/aws4_request,",
        put.headers["authorization"],
    )
    assert put.headers["x-amz-content-sha256"] == hashlib.sha256(put.body).hexdigest()


def test_a_failed_upload_exits_non_zero_and_leaves_the_local_backup(
    tmp_path: Path, bucket: Bucket, capsys: pytest.CaptureFixture[str]
) -> None:
    bucket.status = 403
    site = Site(tmp_path)
    site.clock.now = NOW + DAY
    with pytest.raises(SystemExit) as stopped:
        maintain(site.data_dir, BACKED_UP, Post(), site.clock.now)
    assert stopped.value.code not in (0, None)
    assert len(bucket.received) == 1
    assert backups(site) == ["chessop-2027-01-16.sqlite"]
    captured = capsys.readouterr()
    assert "upload failed" in captured.err and "403" in captured.err
    assert OFF_SITE.secret_key not in captured.out + captured.err


def test_an_unreachable_bucket_exits_non_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("chessop.backup.ENDPOINT", "http://127.0.0.1:9")
    site = Site(tmp_path)
    with pytest.raises(SystemExit):
        maintain(site.data_dir, BACKED_UP, Post(), site.clock.now)
    assert "could not be reached" in capsys.readouterr().err
    assert backups(site) == ["chessop-2027-01-15.sqlite"]


BACKUP_ENV = {
    "CHESSOP_BACKUP_BUCKET": OFF_SITE.bucket,
    "CHESSOP_BACKUP_ACCESS_KEY": OFF_SITE.access_key,
    "CHESSOP_BACKUP_SECRET_KEY": OFF_SITE.secret_key,
    "CHESSOP_BACKUP_RECIPIENT": OFF_SITE.recipient,
}


def test_with_the_backup_variables_unset_the_upload_is_skipped_and_maintain_exits_zero(
    tmp_path: Path, bucket: Bucket, capsys: pytest.CaptureFixture[str]
) -> None:
    Site(tmp_path)
    main(["maintain", "--data-dir", str(tmp_path)], HOSTED_ENV)  # no SystemExit: exit zero
    out = capsys.readouterr().out
    assert "chessop maintain: upload: skipped" in out and "CHESSOP_BACKUP_" in out
    assert bucket.received == []
    assert len(list((tmp_path / "backups").iterdir())) == 1  # the local backup is still taken


def test_with_the_backup_variables_set_maintain_uploads_the_backup(
    tmp_path: Path, bucket: Bucket
) -> None:
    Site(tmp_path)
    main(["maintain", "--data-dir", str(tmp_path)], {**HOSTED_ENV, **BACKUP_ENV})
    (put,) = bucket.received
    assert put.path.startswith("/chessop-backups/chessop-") and put.path.endswith(".sqlite.age")
    assert pyrage.decrypt(put.body, [IDENTITY]).startswith(b"SQLite format 3\0")


def test_some_backup_variables_but_not_all_stop_maintain_naming_the_missing_ones(
    tmp_path: Path, bucket: Bucket
) -> None:
    Site(tmp_path)
    environ = {**HOSTED_ENV, **BACKUP_ENV}
    del environ["CHESSOP_BACKUP_SECRET_KEY"], environ["CHESSOP_BACKUP_RECIPIENT"]
    with pytest.raises(SystemExit) as stopped:
        main(["maintain", "--data-dir", str(tmp_path)], environ)
    assert "CHESSOP_BACKUP_SECRET_KEY, CHESSOP_BACKUP_RECIPIENT" in str(stopped.value.code)
    assert bucket.received == []
