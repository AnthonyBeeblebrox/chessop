"""Hosted mode (public spec §1): what `chessop serve --hosted` adds to the app.

The CLI builds one `Hosted` from the `CHESSOP_*` environment and hands it to the app factory,
which takes from here the three things that differ from local mode: `CookieLearners` (whose
session a request is for), `router` (the hosted-only routes) and `site` (what the base template
shows on every hosted page).

A visitor is an **anonymous learner** (public spec §3): a learner in the store, created when
they start their first round, save settings or opt an opening in or out, never by a page view.
One cookie holds a random token; the store keeps its hash in a session, 12 months from its last
use. A learner's session in the process loads at their first request and is dropped after 30
minutes with no socket and no request (public spec §4). What their settings share with other
learners' (`chessop.shared`) is built off the event loop when no learner has it yet; the
default settings' is built at the start, so a new learner waits on no build.

Signing in, with Lichess or by email (public spec §5, ADR 0008), points the same cookie, its
token changed, at the learner of an **account**, who adopts the browser's anonymous learner.
Signing out changes it again, to nothing: the browser has no learner. Deleting the account
deletes its learner and every session pointing to them: every browser signed in to it has none.

Past 30 new anonymous learners an hour from one client, the next visitor is a **throwaway
learner** (public spec §6): in memory only, every default, no cookie, gone when its socket closes.
It plays, told with every round that nothing is saved, and its settings and progress pages say so
instead of saving. And at 300 live sessions the site is full: no new session begins.

Your data (public spec §10) downloads everything stored about the browser's learner, and forgets
an anonymous learner: deleted with their history, the cookie cleared. The legal notice names
only the host; the privacy notice names the controller and holds the audience statistics'
opt-out, which every hosted page's counting script reads (public spec §10, §12).
"""

import hashlib
import secrets
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, replace
from urllib.parse import parse_qsl, quote

from fastapi import APIRouter, Request, WebSocket
from fastapi.requests import HTTPConnection
from fastapi.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from chessop import limits
from chessop.backup import OffSite
from chessop.choices import load
from chessop.export import export, filename
from chessop.lichess import CALLBACK, LichessSignIn
from chessop.memory import DAY, MINUTE, Params
from chessop.repertoire import Settings
from chessop.session import Drill, Session
from chessop.shared import Shared
from chessop.signin import CHANGE, CONFIRM, EmailSignIn, address, local
from chessop.store import Account, LearnerStore, Store

COOKIE = "chessop"
COOKIE_LIFE = 365 * DAY  # from its last use, noted at most once a day
IDLE = 30 * MINUTE  # a learner session with no socket and no request this long is dropped
# Where the owner's Ko-fi page is (runbook), so correct it here if its address differs.
KOFI = "https://ko-fi.com/chessop"
CONTACT = "contact@chessop.fr"  # where the owner answers about the site (public spec §10)
# Who the privacy notice names as controller (GDPR art. 13): the owner fills their first and
# last name in before launch (runbook).
CONTROLLER = "Anthony Fillion"
# The pitch (public spec §11): the home page's title, and every hosted page's description and
# link preview. The README leads with the same words; everything else says "drill" (CONTEXT.md).
PITCH_TITLE = "chessop: grind chess openings"
PITCH = (
    "Grind chess openings against the moves people at your rating really play, drawn from"
    " Lichess games. Free, no sign-up."
)
INDEXED = ("/", "/help")  # the pages search engines may index; every other carries `noindex`
# The link preview's image, 1200 by 630, the same on every page; the owner replaces the
# placeholder with the real one before launch (runbook).
PREVIEW = "/static/preview.png"
ROBOTS = "User-agent: *\nAllow: /\n"


@dataclass(frozen=True)
class Host:
    """The host the legal notice names, the publisher staying anonymous (LCEN art. 1-1 II)."""

    name: str
    address: str
    phone: str


HOST = Host("OVH SAS", "2 rue Kellermann, 59100 Roubaix, France", "+33 9 72 10 10 07")
BROWSER_ONLY = (
    "Your progress is kept on this browser only: clearing its cookies, or playing on another"
    " device, starts over."
)
THROWAWAY = (
    "Too many new visitors from your network: this round won't be saved. Try again later or"
    " sign in."
)
_OWED = "chessop_set_cookie"  # where a request's scope state holds the cookie its answer sets


# Where `chessop maintain` uploads the backup, in `OffSite`'s order: all of them, or none to
# skip the upload (public spec §1).
BACKUP_VARIABLES = (
    "CHESSOP_BACKUP_BUCKET",
    "CHESSOP_BACKUP_ACCESS_KEY",
    "CHESSOP_BACKUP_SECRET_KEY",
    "CHESSOP_BACKUP_RECIPIENT",
)


class MissingVariables(ValueError):
    """The environment lacks variables hosted mode requires: every one of them, in `names`."""

    def __init__(self, names: tuple[str, ...]) -> None:
        super().__init__(f"hosted mode needs {', '.join(names)}")
        self.names = names


@dataclass(frozen=True)
class Hosted:
    """The hosted site's settings (public spec §1). `base_url` is the site's public address,
    which no request's `Host` ever stands in for."""

    base_url: str
    mail_from: str
    owner_email: str
    tem_secret_key: str | None = None
    tem_project_id: str | None = None
    goatcounter_url: str | None = None
    backup: OffSite | None = None

    @classmethod
    def from_environ(cls, environ: Mapping[str, str]) -> "Hosted":
        """The settings in `environ`; `MissingVariables` naming every required one it lacks.
        The mail key is required on an `https` base URL only (public spec G2)."""

        def get(name: str) -> str:
            return environ.get(name, "").strip()

        base_url = get("CHESSOP_BASE_URL").rstrip("/")
        required = ["CHESSOP_BASE_URL", "CHESSOP_MAIL_FROM", "CHESSOP_OWNER_EMAIL"]
        if base_url.startswith("https:"):
            required += ["CHESSOP_TEM_SECRET_KEY", "CHESSOP_TEM_PROJECT_ID"]
        backup = any(get(name) for name in BACKUP_VARIABLES)
        if backup:
            required += BACKUP_VARIABLES
        missing = tuple(name for name in required if not get(name))
        if missing:
            raise MissingVariables(missing)
        return cls(
            base_url=base_url,
            mail_from=get("CHESSOP_MAIL_FROM"),
            owner_email=get("CHESSOP_OWNER_EMAIL"),
            tem_secret_key=get("CHESSOP_TEM_SECRET_KEY") or None,
            tem_project_id=get("CHESSOP_TEM_PROJECT_ID") or None,
            goatcounter_url=get("CHESSOP_GOATCOUNTER_URL").rstrip("/") or None,
            backup=OffSite(*(get(name) for name in BACKUP_VARIABLES)) if backup else None,
        )

    @property
    def secure(self) -> bool:
        """Whether the cookie is for `https` only: not on an `http` base URL (development)."""
        return not self.base_url.startswith("http:")


class CookieLearners:
    """Hosted mode's learners (`chessop.session.Learners`): the one the browser's cookie points
    to. Each drills the snapshot at the band they chose, with the server's `params`."""

    def __init__(
        self,
        hosted: Hosted,
        store: Store,
        drill: Drill,
        params: Params,
        limiting: limits.Limits,
    ) -> None:
        self._hosted = hosted
        self._limits = limiting
        self._store = store
        self._drill = drill
        self._params = params
        self._live: dict[int, Session] = {}  # by learner id
        # Whom a browser with no learner is shown: every default, nothing recorded, never stored.
        # A client that has had all its new learners is shown one that says so.
        self._memory = Store.in_memory()
        now = drill.clock()
        # What the default settings share, warmed here, at the start: every new learner's.
        self._default = default = drill.shared.warm(Settings())
        self._nobody = self._session(self._memory.create_learner(now), default, anonymous=True)
        self._turned_away = self._session(
            self._memory.create_learner(now), default, unsaved=THROWAWAY
        )
        self._throwaway: set[Session] = set()  # the throwaway learners' sessions, one a socket

    async def visiting(self, conn: HTTPConnection) -> Session:
        session = await self.known(conn)
        if session is None:
            self._begin()
            spent = self._limits.spent(limits.client_of(conn))
            session = self._turned_away if spent else self._nobody
        return session

    async def playing(self, conn: HTTPConnection) -> Session:
        session = await self.known(conn)
        if session is None:
            self._begin()
            now = self._drill.clock()
            if not self._limits.new_learner(limits.client_of(conn)):
                if conn.scope["type"] != "websocket":  # a save: refused, nothing to keep
                    return self._turned_away
                session = self._session(
                    self._memory.create_learner(now), self._default, unsaved=THROWAWAY
                )
                self._throwaway.add(session)
                return session
            learner = self._store.create_learner(now)
            token = secrets.token_urlsafe(32)
            self._store.start_session(_hash(token), learner.id, now, now + COOKIE_LIFE)
            self._owe(conn, token)
            session = self._live[learner.id] = self._session(learner, self._default, anonymous=True)
        return session

    def account(self, conn: HTTPConnection) -> Account | None:
        """The account the connection's browser is signed in to, None when it is signed in to
        none."""
        token = conn.cookies.get(COOKIE)
        found = self._store.session(_hash(token), self._drill.clock()) if token else None
        return None if found is None else self._store.account_of(found[0])

    async def sign_in(self, conn: HTTPConnection, kind: str, identity: str, name: str) -> None:
        """Sign the connection's browser in to the account of that identity, created when no
        learner has it, and shown as `name` from now on. Its anonymous learner, if it has one,
        is adopted (`Store.adopt`): their history joins the account's and they are deleted. The
        cookie's token changes. The account's learner is noted as seen, which clears a warning
        that the account is about to be deleted (public spec §10)."""
        now = self._drill.clock()
        store = self._store
        old = conn.cookies.get(COOKIE)
        found = store.session(_hash(old), now) if old else None
        account = store.account(kind, identity)
        if account is None:
            learner_id = store.create_learner(now).id
            store.create_account(learner_id, kind, identity, name, now)
        else:
            learner_id = account.learner_id
            if account.name != name:
                store.rename_account(learner_id, name)
        if found is not None and found[0] != learner_id and store.account_of(found[0]) is None:
            anonymous = found[0]
            store.adopt(anonymous, learner_id, now)
            # Neither learner is what a running session holds of them any more.
            stale = [self._live.pop(i) for i in (anonymous, learner_id) if i in self._live]
            for session in stale:
                await session.retire()
        store.learner(learner_id).seen(now)  # a sign-in is a request: no warning stands
        store.count_sign_in(now)
        if old:
            store.end_session(_hash(old))
        token = secrets.token_urlsafe(32)
        store.start_session(_hash(token), learner_id, now, now + COOKIE_LIFE)
        self._owe(conn, token)

    async def sign_out(self, conn: HTTPConnection) -> None:
        """End the session of the connection's cookie and clear the cookie: the browser has no
        learner. The learner's open tabs are closed, so that none of this browser's goes on
        playing as them; those of a browser still signed in reconnect."""
        token = conn.cookies.get(COOKIE)
        found = self._store.session(_hash(token), self._drill.clock()) if token else None
        if token:
            self._store.end_session(_hash(token))
        self._owe(conn, "", life=0)
        if found is not None and found[0] in self._live:
            await self._live[found[0]].retire()

    async def delete(self, conn: HTTPConnection) -> None:
        """Delete the account the connection's browser is signed in to (`Store.delete_learner`):
        its learner, history, identity and every session, so that every browser signed in to
        it has no learner from its next request. This one's cookie is cleared and the learner's
        open tabs, on every device, are closed."""
        signed = self.account(conn)
        if signed is None:  # an anonymous learner is forgotten instead (`forget`)
            return
        await self._delete(conn, signed.learner_id)

    async def forget(self, conn: HTTPConnection) -> None:
        """Delete the anonymous learner the connection's browser holds and everything of theirs
        (public spec §10), close their open tabs and clear the cookie: the browser has no
        learner. A signed-in learner's is the account's deletion (`delete`)."""
        session = await self.forgettable(conn)
        if session is not None:
            await self._delete(conn, session.learner.id)

    async def forgettable(self, conn: HTTPConnection) -> Session | None:
        """The session of the anonymous learner the connection's browser holds, None when it
        holds none or is signed in."""
        session = await self.known(conn)
        return session if session is None or self.account(conn) is None else None

    async def _delete(self, conn: HTTPConnection, learner_id: int) -> None:
        session = self._live.pop(learner_id, None)
        # Nothing is awaited from here until `retire` has stopped every tab's round, so none
        # commits for the deleted learner.
        self._store.delete_learner(learner_id, self._drill.clock())
        self._owe(conn, "", life=0)
        if session is not None:
            await session.retire()

    async def export(self, conn: HTTPConnection) -> tuple[str, AsyncIterator[str]] | None:
        """The name and the pieces of the file of everything stored about the learner the
        connection's browser holds (`chessop.export`), None when it holds none."""
        session = await self.known(conn)
        if session is None:
            return None
        now = self._drill.clock()
        learner = session.learner
        return filename(learner, now), export(learner, self.account(conn), now)

    def holds(self, email: str) -> bool:
        """Whether an account is keyed by the address `email`."""
        return self._store.account("email", email) is not None

    def change_email(self, learner_id: int, email: str) -> bool:
        """Make `email` the address of the learner's email account, unless another account
        holds it: whether it changed. Their sessions stay signed in."""
        return self._store.change_email(learner_id, email)

    def handshake(self, sock: WebSocket) -> list[tuple[bytes, bytes]]:
        cookie = sock.scope.get("state", {}).get(_OWED)
        return [] if cookie is None else [(b"set-cookie", cookie)]

    def leaving(self, session: Session) -> None:
        if session in self._throwaway:  # gone with its socket
            self._throwaway.discard(session)
            # Counted in the memory store's own aggregate, which no one reads.
            self._memory.delete_learner(session.learner.id, self._drill.clock())

    async def known(self, conn: HTTPConnection) -> Session | None:
        """The session of the learner the connection's cookie points to, None when it points
        to none: a browser that never played has no learner, and asking makes none. Either way,
        the sessions idle for too long are dropped.

        A session about to begin on settings no learner has built waits for their build, off
        the event loop, and the cookie is then looked up again: nothing read before the wait
        is trusted after it."""
        while True:
            found = self._known(conn)
            if not isinstance(found, Settings):
                return found
            await self._drill.shared.get(found)

    def _known(self, conn: HTTPConnection) -> Session | Settings | None:
        """`known`, with nothing awaited: the settings still to build when the session cannot
        begin without."""
        now = self._drill.clock()
        for learner_id, session in list(self._live.items()):
            if not session.tabs and now - session.active >= IDLE:
                del self._live[learner_id]
                self._store.unload(learner_id)
        token = conn.cookies.get(COOKIE)
        found = self._store.session(_hash(token), now) if token else None
        if token is None or found is None:
            return None
        learner_id, last_used = found
        if now - last_used >= DAY:  # the 12 months slide, a day at a time
            self._store.extend_session(_hash(token), now, now + COOKIE_LIFE)
            self._owe(conn, token)
        if learner_id not in self._live:
            self._begin()
            learner = self._store.learner(learner_id)
            settings = load(learner).settings
            shared = self._drill.shared.ready(settings)
            if shared is None:
                return settings
            self._live[learner_id] = self._session(
                learner, shared, anonymous=self._store.account_of(learner_id) is None
            )
        session = self._live[learner_id]
        session.touch(now)
        return session

    def _begin(self) -> None:
        """A session is about to begin for a browser that has none running: `limits.Full` when
        the site has all it may (public spec §6). Called once the idle ones are dropped."""
        if len(self._live) + len(self._throwaway) >= limits.LIVE_SESSIONS:
            raise limits.Full

    def _session(
        self,
        learner: LearnerStore,
        shared: Shared,
        anonymous: bool = False,
        unsaved: str | None = None,
    ) -> Session:
        """The learner's session over `shared`, what their settings share: its band is the one
        drilled, the default when the snapshot lacks theirs (public spec §2)."""
        choices = replace(load(learner), settings=shared.repertoire.settings, params=self._params)
        return Session(
            self._drill,
            learner,
            shared,
            choices,
            sets_params=False,
            after_first_round=BROWSER_ONLY if anonymous else None,
            unsaved=unsaved,
        )

    def _owe(self, conn: HTTPConnection, token: str, life: float = COOKIE_LIFE) -> None:
        """Have the answer to `conn` set the cookie to `token`, for another 12 months unless
        `life` says otherwise: none clears it."""
        attributes = [f"{COOKIE}={token}", "HttpOnly", f"Max-Age={int(life)}", "Path=/"]
        attributes.append("SameSite=Lax")
        if self._hosted.secure:
            attributes.append("Secure")
        conn.scope.setdefault("state", {})[_OWED] = "; ".join(attributes).encode()


class SetCookie:
    """Middleware: the cookie `CookieLearners` owes a page request goes out with its answer,
    whatever response the route made. (A socket's goes out with its acceptance.)"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def sending(message: Message) -> None:
            cookie = scope.get("state", {}).get(_OWED)
            if message["type"] == "http.response.start" and cookie is not None:
                message = {**message, "headers": [*message["headers"], (b"set-cookie", cookie)]}
            await send(message)

        await self.app(scope, receive, sending)


def router(
    learners: CookieLearners,
    email: EmailSignIn,
    lichess: LichessSignIn,
    templates: Jinja2Templates,
    limiting: limits.Limits,
) -> APIRouter:
    """The routes only the hosted site has (public spec §1): here Lichess and email sign-in, the
    account page with its change of address and deletion, and sign-out (public spec §5), Your
    data, the legal notice and the privacy notice (public spec §10), and `robots.txt` (public
    spec §11). Downloads of a learner's data count against `limiting` (public spec §6)."""
    routes = APIRouter()

    def ask_page(request: Request, back: str, refused: str | None = None) -> HTMLResponse:
        """The sign-in page, saying why the last try was `refused` when one was."""
        return templates.TemplateResponse(
            request,
            "signin.html",
            {"next": back, "refused": refused},
            status_code=400 if refused else 200,
        )

    def inbox_page(
        request: Request, email: str, binding: str, back: str, wrong: bool = False
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "inbox.html",
            {"email": email, "binding": binding, "next": back, "wrong": wrong},
            status_code=400 if wrong else 200,
        )

    def confirm_page(request: Request, token: str, back: str, good: bool) -> HTMLResponse:
        # The address holds the token: it must not travel on as a referrer.
        return templates.TemplateResponse(
            request,
            "confirm.html",
            {"token": token, "next": back, "good": good, "action": CONFIRM},
            headers={"Referrer-Policy": "no-referrer"},
        )

    @routes.get("/signin", response_class=HTMLResponse)
    def ask(request: Request) -> HTMLResponse:
        return ask_page(request, local(request.query_params.get("next")))

    @routes.post("/signin", response_class=HTMLResponse)
    async def send(request: Request) -> HTMLResponse:
        """Mail the link and the code. The answer is the same whatever the address, and whether
        or not a message went."""
        form = await _form(request)
        back = local(form.get("next"))
        email_address = address(form.get("email", ""))
        if email_address is None:
            return ask_page(request, back, refused="That is not an email address.")
        # A resend comes with the page's binding, and so keeps its count of tries.
        binding = form.get("binding", "")[:200] or secrets.token_urlsafe(32)
        email.request(email_address, binding, limits.client_of(request), back)
        return inbox_page(request, email_address, binding, back)

    @routes.post("/signin/code", response_class=HTMLResponse)
    async def by_code(request: Request) -> Response:
        form = await _form(request)
        back, binding = local(form.get("next")), form.get("binding", "")
        proved = email.by_code(binding, form.get("code", ""))
        if proved is None:
            return inbox_page(request, form.get("email", ""), binding, back, wrong=True)
        await learners.sign_in(request, "email", proved, proved)
        return RedirectResponse(back, status_code=303)

    @routes.get(CONFIRM, response_class=HTMLResponse)
    def landing(request: Request) -> HTMLResponse:
        """Where the mailed link leads: a button. Opening it signs no one in and spends
        nothing, so a mail scanner fetching the link does no harm."""
        token = request.query_params.get("token", "")
        back = local(request.query_params.get("next"))
        return confirm_page(request, token, back, email.link_is_good(token))

    @routes.post(CONFIRM, response_class=HTMLResponse)
    async def confirm(request: Request) -> Response:
        form = await _form(request)
        back = local(form.get("next"))
        proved = email.by_link(form.get("token", ""))
        if proved is None:
            return confirm_page(request, "", back, good=False)
        await learners.sign_in(request, "email", proved, proved)
        return RedirectResponse(back, status_code=303)

    @routes.post("/signin/lichess")
    async def to_lichess(request: Request) -> Response:
        """Send the browser to Lichess, to come back to `CALLBACK`."""
        back = local((await _form(request)).get("next"))
        return RedirectResponse(
            lichess.begin(back, request.cookies.get(COOKIE, "")), status_code=303
        )

    @routes.get(CALLBACK, response_class=HTMLResponse)
    async def from_lichess(request: Request) -> Response:
        """Where Lichess sends the browser back, with a code when its holder agreed."""
        query = request.query_params
        pending = lichess.spend(query.get("state", ""), request.cookies.get(COOKIE, ""))
        if pending is None:
            return ask_page(request, "/", refused="That sign-in was not started here. Try again.")
        code = query.get("code")
        # Lichess is over the network: asked off the event loop.
        proved = await run_in_threadpool(lichess.identity, pending, code) if code else None
        if proved is None:
            return ask_page(
                request, pending.back, refused="Lichess did not sign you in. Try again."
            )
        await learners.sign_in(request, "lichess", proved.id, proved.username)
        return RedirectResponse(pending.back, status_code=303)

    def account_page(
        request: Request, signed: Account, sent: str | None = None, refused: str | None = None
    ) -> HTMLResponse:
        """The account page, saying where a change link was `sent`, or why a change of address
        was `refused`."""
        return templates.TemplateResponse(
            request,
            "account.html",
            {"account": signed, "sent": sent, "refused": refused},
            status_code=400 if refused else 200,
        )

    def change_page(
        request: Request,
        token: str = "",
        good: bool = False,
        changed: str | None = None,
        taken: str | None = None,
    ) -> HTMLResponse:
        """The page the change link opens: its button while the link is `good`, the address it
        `changed` the account to, the address it found `taken`, or that it no longer works."""
        # The address holds the token: it must not travel on as a referrer.
        return templates.TemplateResponse(
            request,
            "change_email.html",
            {"token": token, "good": good, "changed": changed, "taken": taken, "action": CHANGE},
            headers={"Referrer-Policy": "no-referrer"},
        )

    to_sign_in = "/signin?next=%2Faccount"

    @routes.get("/account", response_class=HTMLResponse)
    def account(request: Request) -> Response:
        signed = learners.account(request)
        if signed is None:
            return RedirectResponse(to_sign_in, status_code=303)
        return account_page(request, signed)

    @routes.post("/account/email", response_class=HTMLResponse)
    async def change_email(request: Request) -> Response:
        """Mail the new address a link that makes the change. Refused, with nothing mailed,
        when another account holds the address."""
        signed = learners.account(request)
        if signed is None:
            return RedirectResponse(to_sign_in, status_code=303)
        if signed.kind != "email":  # a Lichess account has no address to change
            return Response(status_code=404)
        new = address((await _form(request)).get("email", ""))
        if new is None:
            return account_page(request, signed, refused="That is not an email address.")
        if new == signed.identity:
            return account_page(request, signed, refused="That is already your address.")
        if learners.holds(new):
            return account_page(request, signed, refused="Another account uses that address.")
        email.request_change(signed.learner_id, new, limits.client_of(request))
        return account_page(request, signed, sent=new)

    @routes.get(CHANGE, response_class=HTMLResponse)
    def change_landing(request: Request) -> HTMLResponse:
        """Where the change link leads: a button. Opening it changes nothing."""
        token = request.query_params.get("token", "")
        return change_page(request, token, good=email.change_link_is_good(token))

    @routes.post(CHANGE, response_class=HTMLResponse)
    async def change_confirm(request: Request) -> HTMLResponse:
        """The change link's button: the address it proves becomes its account's."""
        proved = email.by_change_link((await _form(request)).get("token", ""))
        if proved is None:
            return change_page(request)
        learner_id, new = proved
        if not learners.change_email(learner_id, new):  # taken since the link was mailed
            return change_page(request, taken=new)
        return change_page(request, changed=new)

    @routes.get("/account/delete", response_class=HTMLResponse)
    def ask_delete(request: Request) -> Response:
        """The confirmation "Delete my account" leads to. Asking deletes nothing."""
        signed = learners.account(request)
        if signed is None:
            return RedirectResponse(to_sign_in, status_code=303)
        return templates.TemplateResponse(request, "delete_account.html", {"account": signed})

    @routes.post("/account/delete")
    async def delete(request: Request) -> Response:
        """The confirmation's button: the account is deleted at once, on every device."""
        await learners.delete(request)
        return RedirectResponse("/", status_code=303)

    @routes.get("/data", response_class=HTMLResponse)
    async def your_data(request: Request) -> HTMLResponse:
        """Your data (public spec §10): the download, and the way to delete it all. Visiting
        makes no learner."""
        held = await learners.known(request) is not None
        signed = learners.account(request)
        return templates.TemplateResponse(
            request, "data.html", {"held": held, "account": signed, "contact": CONTACT}
        )

    @routes.get("/data/download")
    async def download(request: Request) -> Response:
        """The file of everything stored about the learner, generated as it is sent."""
        session = await learners.known(request)
        if session is None:  # nothing is stored
            return RedirectResponse("/data", status_code=303)
        wait = limiting.download(session.learner.id)
        if wait is not None:
            return limits.slow_down(wait)
        made = await learners.export(request)
        assert made is not None  # the browser holds a learner
        name, pieces = made
        return StreamingResponse(
            pieces,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{name}"',
                "Cache-Control": "no-store",
                "X-Robots-Tag": "noindex",
            },
        )

    @routes.get("/data/forget", response_class=HTMLResponse)
    async def ask_forget(request: Request) -> Response:
        """The confirmation "Forget this browser's history" leads to. Asking deletes nothing."""
        if await learners.forgettable(request) is None:
            return RedirectResponse("/data", status_code=303)
        return templates.TemplateResponse(request, "forget.html")

    @routes.post("/data/forget")
    async def forget(request: Request) -> Response:
        """The confirmation's button: the anonymous learner is deleted at once."""
        await learners.forget(request)
        return RedirectResponse("/data", status_code=303)

    @routes.get("/legal", response_class=HTMLResponse)
    def legal(request: Request) -> HTMLResponse:
        """The legal notice (public spec §10): the host, the contact and the terms."""
        return templates.TemplateResponse(request, "legal.html", {"host": HOST})

    @routes.get("/privacy", response_class=HTMLResponse)
    def privacy(request: Request) -> HTMLResponse:
        """The privacy notice (public spec §10), with the audience statistics' opt-out."""
        return templates.TemplateResponse(request, "privacy.html", {"controller": CONTROLLER})

    @routes.post("/signout")
    async def sign_out(request: Request) -> Response:
        if learners.account(request) is not None:  # an anonymous learner stays the browser's
            await learners.sign_out(request)
        return RedirectResponse("/", status_code=303)

    @routes.get("/robots.txt", response_class=PlainTextResponse)
    def robots() -> str:
        """Crawlers may crawl everything (public spec §11): the pages not to index say so
        themselves. No sitemap."""
        return ROBOTS

    return routes


@dataclass(frozen=True)
class Site:
    """What the base template shows on every page of the hosted site (public spec §1, §10).
    `account` is the name of the account the browser is signed in to, None when it is signed in
    to none; `sign_in` is then where "Sign in" leads, to come back to the page shown."""

    footer: tuple[tuple[str, str], ...]  # each link's text and address, in order
    account: str | None
    sign_in: str
    # The page's public address and its link preview's image (public spec §11), both built
    # from the base URL; `canonical` is the address on an indexable page, None on the others,
    # which carry `noindex`. `title` is the pitch's title on the home page, None elsewhere.
    address: str
    image: str
    canonical: str | None
    title: str | None
    description: str = PITCH
    # Where the audience statistics count a page view (public spec §12), None when they are
    # not configured (public spec G3): then no page counts anything.
    count_url: str | None = None
    contact: str = CONTACT
    kofi: str = KOFI


def site(hosted: Hosted, source: str, account: str | None, request: Request) -> Site:
    """The `hosted` site's `site` value for a page answering `request`, shown to a browser
    signed in to `account`; `source` is where the code is published."""
    url = request.url
    if url.path.startswith("/signin"):  # the sign-in pages lead back where they were asked to
        back = local(request.query_params.get("next"))
    else:
        back = url.path + (f"?{url.query}" if url.query else "")
    address = hosted.base_url + url.path  # the request's path only: never its `Host`
    return Site(
        footer=(
            ("Legal notice", "/legal"),
            ("Privacy", "/privacy"),
            ("Your data", "/data"),
            ("Source", source),
            ("Ko-fi", KOFI),
        ),
        account=account,
        sign_in=f"/signin?next={quote(back, safe='')}",
        address=address,
        image=f"{hosted.base_url}{PREVIEW}",
        canonical=address if url.path in INDEXED else None,
        title=PITCH_TITLE if url.path == "/" else None,
        count_url=None if hosted.goatcounter_url is None else f"{hosted.goatcounter_url}/count",
    )


async def _form(request: Request) -> dict[str, str]:
    """The fields of the form the request posts."""
    return dict(parse_qsl((await request.body()).decode(), keep_blank_values=True))


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
