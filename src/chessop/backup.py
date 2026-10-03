"""The nightly backup (public spec §13, §14): the last two steps of `chessop maintain`.

`take` copies the database through SQLite's backup API, never as a file, into the data
directory's backups folder, one file a UTC day, and keeps the 14 most recent there. `upload`
encrypts that day's copy with `age` to the owner's public key (whose private half never is on
the VPS) and puts it in a Scaleway Object Storage bucket in Paris, with a key that may only
write objects there; the bucket's lifecycle rule expires them after 30 days, which keeps the
promise that deleted data leaves the backups within 30 days. With no bucket configured (the
`CHESSOP_BACKUP_*` variables unset) the upload is skipped and says so.
"""

import hashlib
import hmac
import re
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote, urlsplit

import pyrage

from chessop.clock import utc_day
from chessop.store import Store

FOLDER = "backups"  # in the data directory
KEEP = 14  # local backups, one a UTC day
_NAME = re.compile(r"chessop-\d{4}-\d{2}-\d{2}\.sqlite")
# Scaleway Object Storage in its Paris region, spoken to as S3 is.
ENDPOINT = "https://s3.fr-par.scw.cloud"
REGION = "fr-par"
SERVICE = "s3"
TIMEOUT = 60.0  # seconds the upload waits on the bucket at any one point
_CHUNK = 1 << 20


@dataclass(frozen=True)
class OffSite:
    """Where the backup goes off the VPS (`CHESSOP_BACKUP_*`): encrypted with `age` to
    `recipient`, the owner's public key, and put in `bucket` with a key that may only write
    objects there."""

    bucket: str
    access_key: str
    secret_key: str = field(repr=False)
    recipient: str


class UploadError(Exception):
    """A backup that did not reach the bucket."""


def filename(now: float) -> str:
    """The name of the backup taken at `now`: one a UTC day, a later one replacing it."""
    return f"chessop-{utc_day(now)}.sqlite"


def take(store: Store, folder: Path, now: float) -> str:
    """Back the database up into `folder` as `filename(now)`, then keep only the `KEEP` most recent
    backups there: what was done, counted."""
    folder.mkdir(exist_ok=True)
    target = folder / filename(now)
    partial = target.with_name(f"{target.name}.partial")
    partial.unlink(missing_ok=True)
    store.back_up(partial)
    partial.replace(target)  # a backup that failed halfway never stands as one
    kept = sorted(path for path in folder.iterdir() if _NAME.fullmatch(path.name))
    for old in kept[:-KEEP]:
        old.unlink()
    return f"wrote {target.name}, {min(len(kept), KEEP)} kept, {len(kept[:-KEEP])} removed"


def upload(folder: Path, now: float, off_site: OffSite | None) -> str:
    """Encrypt the backup `take` left in `folder` at `now` to the owner's key and put it in the
    bucket, the local backup left as it was; with no bucket configured, skip it: what was done.
    `UploadError` when it did not go."""
    if off_site is None:
        return "skipped, the CHESSOP_BACKUP_* variables are unset"
    local = folder / filename(now)
    if not local.exists():
        raise UploadError(f"no backup {local.name} to upload")
    recipient = pyrage.x25519.Recipient.from_str(off_site.recipient)
    with tempfile.TemporaryDirectory(prefix="chessop-backup-") as scratch:
        encrypted = Path(scratch) / f"{local.name}.age"
        pyrage.encrypt_file(str(local), str(encrypted), [recipient])
        size = encrypted.stat().st_size
        _put(off_site, encrypted)
    return f"uploaded {encrypted.name}, {size} bytes"


def _put(off_site: OffSite, path: Path) -> None:
    """Put the file at `path` in the bucket under its own name."""
    digest = hashlib.sha256()
    with path.open("rb") as body:
        while chunk := body.read(_CHUNK):
            digest.update(chunk)
    url = f"{ENDPOINT}/{off_site.bucket}/{quote(path.name)}"
    headers = sign(
        "PUT",
        url,
        {},
        payload_hash=digest.hexdigest(),
        access_key=off_site.access_key,
        secret_key=off_site.secret_key,
        region=REGION,
        now=time.time(),
    )
    headers |= {
        "Content-Length": str(path.stat().st_size),
        "Content-Type": "application/octet-stream",
    }
    with path.open("rb") as body:
        request = urllib.request.Request(url, data=body, headers=headers, method="PUT")
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT):
                pass
        except urllib.error.HTTPError as e:
            raise UploadError(f"the bucket answered {e.code} {e.reason}") from None
        except (urllib.error.URLError, OSError) as e:
            raise UploadError(f"the bucket could not be reached: {e}") from None


def sign(
    method: str,
    url: str,
    headers: Mapping[str, str],
    *,
    payload_hash: str,
    access_key: str,
    secret_key: str,
    region: str,
    now: float,
) -> dict[str, str]:
    """`headers` and the ones an S3 request to `url` (its path already percent-encoded, no
    query) needs to be accepted at `now`, signed with AWS Signature Version 4: `Host`,
    `x-amz-date`, `x-amz-content-sha256` (the body's `payload_hash`) and `Authorization`."""
    when = datetime.fromtimestamp(now, UTC)
    amz_date, day = when.strftime("%Y%m%dT%H%M%SZ"), when.strftime("%Y%m%d")
    parts = urlsplit(url)
    signed = {
        **headers,
        "Host": parts.netloc,
        "x-amz-date": amz_date,
        "x-amz-content-sha256": payload_hash,
    }
    canonical = {name.lower(): " ".join(value.split()) for name, value in signed.items()}
    names = ";".join(sorted(canonical))
    request = "\n".join(
        [
            method,
            parts.path or "/",
            "",  # no query string
            *(f"{name}:{canonical[name]}" for name in sorted(canonical)),
            "",
            names,
            payload_hash,
        ]
    )
    scope = f"{day}/{region}/{SERVICE}/aws4_request"
    to_sign = "\n".join(
        ["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(request.encode()).hexdigest()]
    )
    key = f"AWS4{secret_key}".encode()
    for part in (day, region, SERVICE, "aws4_request"):
        key = hmac.digest(key, part.encode(), "sha256")
    signature = hmac.new(key, to_sign.encode(), "sha256").hexdigest()
    signed["Authorization"] = (
        f"AWS4-HMAC-SHA256 Credential={access_key}/{scope},"
        f"SignedHeaders={names},Signature={signature}"
    )
    return signed
