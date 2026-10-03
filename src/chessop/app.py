"""The web app: the play page, the one socket per tab, the settings page, the progress ledger,
the help page, `/healthz`, and the web app manifest and service worker that make it installable.

Every page and the socket act on the session of the current learner (`chessop.session`): saving
the settings, resetting all history, and the ledger's actions (opting an opening in or out,
resetting an opening or one position after a confirmation page) regenerate that learner's
repertoire in the running process (spec §4, §7).

Local mode and hosted mode (public spec §1) part in `create_app` only, at three seams: whose
session a request is for (`Learners`), the hosted-only router, and the base template's `site`.
"""

import json
import random
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import parse_qsl, quote

import chess
import chess.svg
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.requests import HTTPConnection
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from chessop import hosted as hosted_mode
from chessop.choices import (
    ANIMATION,
    BAND_NAMES,
    PARAMS_FIELDS,
    SETTINGS_FIELDS,
    form_values,
    hello,
    ignores_forced_rate,
    load,
    parse,
    save,
)
from chessop.clock import Clock
from chessop.explanations import Explanations
from chessop.graph import Edge, Graph
from chessop.hosted import Hosted
from chessop.installable import MANIFEST, OFFLINE, SHELL, cache_name
from chessop.lichess import HttpLichess, LichessClient, LichessSignIn
from chessop.limits import (
    FULL_CLOSE,
    Allowance,
    Full,
    Limits,
    PerClient,
    Unlimited,
    Unmetered,
    client_of,
    full,
    slow_down,
)
from chessop.mail import ConsoleMailer, Mailer
from chessop.memory import Params, half_life, recall
from chessop.play import ILLEGAL
from chessop.progress import (
    FIRST_MOVES,
    TARGET,
    LearnerPosition,
    Opening,
    Tally,
    duration,
    shade,
    sparkline,
    state_word,
    tally,
)
from chessop.repertoire import START, Settings, to_move
from chessop.score import change, percent
from chessop.session import (
    Drill,
    ImplicitLearner,
    Learners,
    Session,
    Tab,
)
from chessop.shared import EmptyRepertoire, SharedCache
from chessop.signin import EmailSignIn
from chessop.store import Store

HERE = Path(__file__).parent
# The public source repository the help page points to for questions (spec map: Source); the
# owner creates it on their GitHub (runbook), so correct it here if its address differs.
REPOSITORY = "https://github.com/AnthonyBeeblebrox/chessop"
# The in-session success rate aimed at, as the progress view and the help page quote it.
TARGET_RANGE = "\N{EN DASH}".join(f"{round(100 * t)}" for t in TARGET)


def create_app(
    graph: Graph,
    rng: random.Random | None = None,
    settings: Settings | None = None,
    store: Store | None = None,
    params: Params | None = None,
    explanations: Explanations | None = None,
    load_band: Callable[[str], Graph] | None = None,
    clock: Clock = time.time,
    hosted: Hosted | None = None,
    mailer: Mailer | None = None,
    lichess: LichessClient | None = None,
) -> FastAPI:
    """The app over `graph`; without a `store` nothing outlives the process, without
    `explanations` no round carries one. Without `load_band` the band cannot change: only
    `graph`'s band is offered. Every moment a page or a round reads comes from `clock`.

    Without `hosted` this is local mode: one implicit learner, whose `settings` and `params`
    default to the stored ones. With it, hosted mode: a learner per browser cookie, each with
    their own stored settings, and `params` (the defaults when None) for all of them; its mail
    goes through `mailer`, and is printed to the console without one; it reaches Lichess through
    `lichess`, the real one without one."""
    store = store or Store.in_memory()
    bands = (graph.bands or (graph.band,)) if load_band is not None else (graph.band,)
    # What learners with the same settings share (public spec §4); each start warms its own.
    shared = SharedCache(graph, load_band)
    drill = Drill(rng or random.Random(), explanations, shared, clock)
    app = FastAPI()
    app.state.shared = shared
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")

    learners: Learners
    limits: Limits | Unlimited
    if hosted is None:
        limits = Unlimited()
        learner = store.implicit()
        choices = load(learner)
        choices = replace(
            choices,
            settings=replace(settings or choices.settings, band=graph.band),
            params=params or choices.params,
        )
        app.state.session = Session(drill, learner, shared.warm(choices.settings), choices)
        learners = ImplicitLearner(app.state.session)

        def site(request: Request) -> hosted_mode.Site | None:
            return None  # local mode's pages carry nothing of the site's

    else:
        limits = hosted_limits = Limits(clock)
        cookie_learners = hosted_mode.CookieLearners(
            hosted, store, drill, params or Params(), hosted_limits
        )
        learners = cookie_learners
        app.add_middleware(hosted_mode.SetCookie)
        app.add_middleware(PerClient, limits=hosted_limits)

        def site(request: Request) -> hosted_mode.Site | None:
            account = cookie_learners.account(request)
            name = None if account is None else account.name
            return hosted_mode.site(hosted, REPOSITORY, name, request)

    templates = Jinja2Templates(
        directory=HERE / "templates", context_processors=[lambda request: {"site": site(request)}]
    )
    if hosted is not None:
        email = EmailSignIn(hosted.base_url, store, mailer or ConsoleMailer(), clock)
        by_lichess = LichessSignIn(hosted.base_url, lichess or HttpLichess(), clock)
        app.include_router(
            hosted_mode.router(cookie_learners, email, by_lichess, templates, hosted_limits)
        )

    @app.exception_handler(Full)
    async def site_is_full(request: Request, refusal: Full) -> Response:
        """A page for a learner with no running session, asked of a full site (public spec G5)."""
        return full()

    # On the event loop, like every other write: a visit notes when the learner was last seen.
    async def visiting(conn: HTTPConnection) -> Session:
        return await learners.visiting(conn)

    Visiting = Annotated[Session, Depends(visiting)]

    @app.get("/", response_class=HTMLResponse)
    @app.get("/play", response_class=HTMLResponse)
    def play(request: Request, session: Visiting) -> HTMLResponse:
        # The page starts with the persisted sound and animation (spec §11 defaults).
        return templates.TemplateResponse(
            request,
            "play.html",
            {
                "sound": bool(session.learner.setting("sound", True)),
                "animation_ms": session.learner.setting("animation_ms", 100),
            },
        )

    def settings_page(
        request: Request,
        session: Session,
        values: dict[str, str],
        errors: dict[str, str] | None = None,
        notice: str | None = None,
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "settings.html",
            {
                "values": values,
                "errors": errors or {},
                "notice": notice or session.unsaved,
                "fields": SETTINGS_FIELDS,
                # The memory model's are shown to the learner whose they are to set.
                "params_fields": PARAMS_FIELDS if session.sets_params else (),
                "animation": ANIMATION,
                "band_names": BAND_NAMES,
                "bands": bands,  # the ones the snapshot holds: the others are listed, not offered
                "band": session.graph.band,
                "version": session.graph.version,  # recorded as `snapshot_version` at start
                "storage_cutoff": session.graph.storage_cutoff,
                "forced_rate_ignored": ignores_forced_rate(session.choices),
                # Local mode's learner's day is the machine's: no time zone to edit (ADR 0002).
                "timezone_field": session.learner.follows_timezone,
            },
            status_code=400 if errors else 200,
        )

    @app.get("/settings", response_class=HTMLResponse)
    def show_settings(request: Request, session: Visiting) -> HTMLResponse:
        notice = {"saved": "Saved.", "reset": "All history reset."}.get(
            request.query_params.get("done", "")
        )
        return settings_page(
            request, session, form_values(session.current_choices()), notice=notice
        )

    @app.post("/settings", response_class=HTMLResponse)
    async def save_settings(request: Request, session: Visiting) -> Response:
        form = dict(parse_qsl((await request.body()).decode(), keep_blank_values=True))
        parsed = parse(
            form,
            session.current_choices(),
            session.graph.storage_cutoff,
            bands,
            sets_params=session.sets_params,
        )
        if isinstance(parsed, dict):
            return settings_page(request, session, form, parsed)
        session = await learners.playing(request)  # a save makes the learner (public spec G1)
        if session.unsaved:  # a throwaway learner: told so instead of saved (public spec §6)
            return settings_page(request, session, form)
        wait = limits.save(session.learner.id)
        if wait is not None:
            return slow_down(wait)
        try:
            await session.regenerate(parsed)
        except EmptyRepertoire as e:
            return settings_page(request, session, form, {"": f"Not saved: {e}"})
        save(session.learner, parsed, sets_params=session.sets_params)
        return RedirectResponse("/settings?done=saved", status_code=303)

    def confirm_page(
        request: Request, what: str, deleted: str, action: str, back: str
    ) -> HTMLResponse:
        """The confirmation a reset asks for: its form posts `confirm=yes` to `action`."""
        return templates.TemplateResponse(
            request,
            "reset.html",
            {"what": what, "deleted": deleted, "action": action, "back": back},
        )

    @app.get("/settings/reset", response_class=HTMLResponse)
    def confirm_reset(request: Request) -> HTMLResponse:
        return confirm_page(
            request,
            "all history",
            "Every position record is deleted: every position goes back to never passed and"
            " the Score to 0.",
            "/settings/reset",
            "/settings",
        )

    @app.post("/settings/reset")
    async def reset_all(request: Request, session: Visiting) -> Response:
        # Every need changed: the steering starts over.
        await session.regenerate(session.choices, session.learner.reset_all)
        return RedirectResponse("/settings?done=reset", status_code=303)

    @app.get("/progress", response_class=HTMLResponse)
    def progress(request: Request, session: Visiting) -> HTMLResponse:
        return ledger_page(request, session)

    def ledger_page(
        request: Request, session: Session, refused: str | None = None, status_code: int = 200
    ) -> HTMLResponse:
        now = clock()
        shape = session.ledger()
        learner, choices, repertoire = session.learner, session.choices, session.repertoire
        record, params = learner.record, choices.params
        head = tally(repertoire.learner_counts, record, now, params)
        context: dict[str, Any] = {
            "head": _numbers(head),
            "never_list": None,
            "sure": round(100 * params.sure),
            "target": TARGET_RANGE,
            "refused": refused,
            "notice": session.unsaved or session.tell("progress"),
        }
        last = learner.last_day_before(learner.day(now))
        context["since"] = (
            None if last is None else {"day": last[0], "delta": change(head.score or 0.0, last[1])}
        )
        successes, rounds = learner.successes_since(session.start)
        rate = successes / rounds if rounds else None
        context["session"] = {
            "successes": successes,
            "rounds": rounds,
            "rate": None if rate is None else round(100 * rate),
            "outside": rate is not None and not TARGET[0] <= rate <= TARGET[1],
        }
        daily = [row["score"] for row in learner.daily_scores()]
        context["spark"] = {"points": sparkline(daily, 160, 32), "days": len(daily)}

        if request.query_params.get("never") == "1":
            never = sorted(
                (
                    (count, epd)
                    for epd, count, _ in repertoire.learner_counts
                    if record(epd).last_pass is None
                ),
                key=lambda item: (-item[0], item[1]),
            )
            context["never_list"] = [
                {
                    "href": _href(epd),
                    "moves": shape.moves(epd) or "the start",
                    "name": shape.naming(epd).name,
                    "side": to_move(epd),
                    "share": 100 * count / session.graph.games,
                }
                for count, epd in never
            ]
        else:

            def row(
                name: str | None, eco: str, positions: tuple[LearnerPosition, ...]
            ) -> dict[str, Any]:
                return {
                    "name": name,
                    "eco": eco,
                    "positions": len(positions),
                    **_numbers(tally(positions, record, now, params)),
                }

            context["openings"] = [
                {
                    **row(o.name, o.eco, o.positions),
                    "out": o.name != FIRST_MOVES and o.name in choices.settings.opted_out,
                    "toggle": None if o.name == FIRST_MOVES else _opening_href(o.name, "toggle"),
                    "reset": _opening_href(o.name, "reset"),
                    "lines": [
                        {
                            **row(line.name, line.eco, line.positions),
                            "branches": [
                                [
                                    {"text": c.text}
                                    if c.epd is None
                                    else {
                                        "text": c.text,
                                        "href": _href(c.epd),
                                        "shade": shade(record(c.epd), now, params),
                                    }
                                    for c in branch
                                ]
                                for branch in line.branches
                            ],
                        }
                        for line in o.lines
                    ],
                }
                for o in shape.openings
            ]
        return templates.TemplateResponse(
            request, "progress.html", context, status_code=status_code
        )

    def opening(session: Session, name: str) -> Opening:
        """The opening of that name in the session's ledger, 404 when it lists none."""
        found = next((o for o in session.ledger().openings if o.name == name), None)
        if found is None:
            raise HTTPException(status_code=404, detail="no such opening in the ledger")
        return found

    @app.post("/progress/opening/{name:path}/toggle", response_class=HTMLResponse)
    async def toggle_opening(request: Request, session: Visiting, name: str) -> Response:
        """Opt the opening out, or back in: a settings write, then regeneration (spec §10.3)."""
        if opening(session, name).name == FIRST_MOVES:
            raise HTTPException(status_code=404, detail="the first moves are not an opening")
        session = await learners.playing(request)  # a toggle makes the learner (public spec G1)
        if session.unsaved:  # a throwaway learner: told so instead of saved (public spec §6)
            return ledger_page(request, session)
        wait = limits.save(session.learner.id)  # it is a settings save
        if wait is not None:
            return slow_down(wait)
        choices = session.choices
        opted_out = choices.settings.opted_out ^ {name}
        new = replace(choices, settings=replace(choices.settings, opted_out=opted_out))
        try:
            await session.regenerate(new)
        except EmptyRepertoire as e:
            return ledger_page(request, session, refused=f"Not changed: {e}", status_code=400)
        session.learner.set_setting("opted_out", sorted(opted_out))
        return RedirectResponse("/progress", status_code=303)

    @app.post("/progress/opening/{name:path}/reset", response_class=HTMLResponse)
    async def reset_opening(request: Request, session: Visiting, name: str) -> Response:
        """Confirm, then delete the records of the opening's learner positions (spec §7)."""
        found = opening(session, name)
        if not await confirmed(request):
            return confirm_page(
                request,
                f"the {found.name}" if found.name != FIRST_MOVES else "the first moves",
                f"The records of its {len(found.positions)} positions are deleted: they go back"
                " to never passed.",
                _opening_href(found.name, "reset"),
                "/progress",
            )
        epds = [epd for epd, _, _ in found.positions]
        # The steering starts over.
        await session.regenerate(session.choices, lambda: session.learner.reset(epds))
        return RedirectResponse("/progress", status_code=303)

    @app.get("/progress/position/{epd:path}", response_class=HTMLResponse)
    def position_page(request: Request, session: Visiting, epd: str) -> HTMLResponse:
        shape = session.ledger()
        rep = shape.repertoire
        if epd not in rep.positions:
            raise HTTPException(status_code=404, detail="no such position in the repertoire")
        now = clock()
        graph = session.graph
        record, params = session.learner.record, session.choices.params
        position = graph.positions[epd]
        naming = shape.naming(epd)
        side = to_move(epd)
        board = chess.Board(f"{epd} 0 1")
        numbers = None
        if epd in rep.learner_positions:
            r = record(epd)
            numbers = {
                "state": state_word(r, now, params),
                "shade": shade(r, now, params),
                "recall": percent(recall(r, now, params)),
                "half_life": duration(half_life(r, params)),
                "passes": r.passes,
                "misses": r.misses,
                "relearn": r.relearn,
                "since": None if r.last_pass is None else duration(now - r.last_pass),
            }

        def chip(edge: Edge) -> dict[str, Any]:
            child = edge.child_epd
            stub = rep.is_stub(edge)
            return {
                "san": edge.san,
                "share": round(100 * edge.count / position.count),
                "stub": stub,
                "href": None if stub else _href(child),
                "shade": (
                    shade(record(child), now, params) if child in rep.learner_positions else None
                ),
            }

        explanation = (
            None if explanations is None else explanations.for_path(list(position.canonical))
        )
        if explanation is not None:
            explanation = {
                **explanation,
                "lead": explanation["lead"].split("\n\n"),
                "text": explanation["text"].split("\n\n"),
                "more": explanation["text"] != explanation["lead"],
            }
        context = {
            "side": side,
            "board": chess.svg.board(
                board, orientation=chess.WHITE if side == "white" else chess.BLACK, size=360
            ),
            "name": naming.name,
            "exact": naming.exact,
            "first_moves": FIRST_MOVES,
            "eco": naming.eco,
            "moves": shape.moves(epd),
            "numbers": numbers,
            "share": 100 * position.count / graph.games,
            "orders": shape.move_orders(epd),
            "chips": [chip(e) for e in rep.main_moves(epd)],
            "explanation": explanation,
            "sure": round(100 * params.sure),
            "reset": f"{_href(epd)}/reset",
        }
        return templates.TemplateResponse(request, "position.html", context)

    @app.post("/progress/position/{epd:path}/reset", response_class=HTMLResponse)
    async def reset_position(request: Request, session: Visiting, epd: str) -> Response:
        """Confirm, then delete the position's record (spec §7)."""
        shape = session.ledger()
        if epd not in shape.repertoire.learner_positions:
            raise HTTPException(status_code=404, detail="no such learner position in the ledger")
        if not await confirmed(request):
            return confirm_page(
                request,
                "this position",
                f"The record of {shape.moves(epd) or 'the start position'} ({to_move(epd)} to"
                " move) is deleted: it goes back to never passed.",
                f"{_href(epd)}/reset",
                _href(epd),
            )
        # The steering starts over.
        await session.regenerate(session.choices, lambda: session.learner.reset([epd]))
        return RedirectResponse(_href(epd), status_code=303)

    @app.get("/help", response_class=HTMLResponse)
    def help_page(request: Request, session: Visiting) -> HTMLResponse:
        """How chessop works, quoting the running sure threshold and target range (public spec
        §9)."""
        return templates.TemplateResponse(
            request,
            "help.html",
            {
                "sure": round(100 * session.choices.params.sure),
                "target": TARGET_RANGE,
                "repository": REPOSITORY,
            },
        )

    @app.api_route("/healthz", methods=["GET", "HEAD"], response_class=PlainTextResponse)
    def healthz() -> PlainTextResponse:
        """What the uptime check (which may send HEAD) and the deploy script poll: 200 only
        when the database answers and the snapshot is loaded (public spec §12)."""
        if not store.answers():
            return PlainTextResponse("the database does not answer", status_code=503)
        if START not in graph.positions:
            return PlainTextResponse("no snapshot is loaded", status_code=503)
        return PlainTextResponse("ok")

    @app.get("/manifest.webmanifest")
    def manifest() -> JSONResponse:
        """The web app manifest that lets chessop install to a home screen (public spec §8)."""
        return JSONResponse(MANIFEST, media_type="application/manifest+json")

    service_worker_script = templates.get_template("sw.js").render(
        cache=cache_name(HERE / "static"), shell=SHELL, offline=OFFLINE
    )

    @app.get("/sw.js")
    def service_worker() -> Response:
        """The service worker, at the root so its scope is the whole site (public spec §8)."""
        return Response(
            service_worker_script,
            media_type="text/javascript",
            headers={"Cache-Control": "no-cache"},
        )

    @app.websocket("/ws")
    async def ws(sock: WebSocket) -> None:
        # Past a cap the socket is refused (public spec §6), before a learner is made for it.
        client = client_of(sock)
        if not limits.admits(client):
            await sock.close(code=1008)
            return
        try:
            session = await learners.playing(sock)
        except Full:
            await sock.close(code=FULL_CLOSE)
            return
        try:
            allowance = limits.socket(client, None if session.unsaved else session.learner.id)
            if allowance is None:
                await sock.close(code=1008)
                return
            try:
                await sock.accept(headers=learners.handshake(sock))
                await converse(sock, session, allowance)
            finally:
                allowance.close()
        finally:
            learners.leaving(session)

    async def converse(sock: WebSocket, session: Session, allowance: Allowance | Unmetered) -> None:
        """The accepted socket's tab, from its first round until it closes."""
        tab = await session.open_tab(sock)
        try:
            while True:
                message = await sock.receive()
                received = time.perf_counter()
                if message["type"] == "websocket.disconnect":
                    break
                text = message.get("text")
                size = len(text.encode()) if text is not None else len(message["bytes"])
                if not allowance.message(size):  # too fast or too big (public spec §6)
                    await sock.close(code=1008)
                    break
                try:
                    msg = None if text is None else json.loads(text)
                except ValueError:
                    msg = None
                if not isinstance(msg, dict):
                    continue
                async with tab.lock:
                    if tab not in session.tabs:  # the session let go of it
                        break
                    await handle(session, tab, msg, received)
        except WebSocketDisconnect:
            pass
        finally:
            session.close_tab(tab)

    async def handle(session: Session, tab: Tab, msg: dict, received: float) -> None:
        """Answer `msg`, received on `tab`'s socket at `received` (`time.perf_counter`)."""
        kind = msg.get("type")
        if kind == "next":
            tab.round = session.new_round()
            await tab.sock.send_json(session.start_message(tab, first=False))
        elif kind == "move":
            frm, to = msg.get("from"), msg.get("to")
            if isinstance(frm, str) and isinstance(to, str) and tab.round is not None:
                replies = session.move(tab.round, frm, to)
                # The server's handling of the move, from its receipt to its replies ready, round
                # end commit included: what the load-test script measures (public spec §7).
                handled_ms = round(1000 * (time.perf_counter() - received), 3)
                replies = [
                    {**r, "handled_ms": handled_ms} if r["type"] == "moved" else r for r in replies
                ]
            else:
                replies = [ILLEGAL]
            for reply in replies:
                await tab.sock.send_json(reply)
        elif kind == "sound" and isinstance(msg.get("on"), bool):
            # The `m` key on the play page: persisted, answered with nothing.
            session.learner.set_setting("sound", msg["on"])
        elif kind == "hello":
            # Sent when the socket opens (public spec G6). Answered with nothing.
            hello(session.learner, msg.get("tz"))

    return app


async def confirmed(request: Request) -> bool:
    """Whether the posted form is the confirmation page's own."""
    return dict(parse_qsl((await request.body()).decode())).get("confirm") == "yes"


def _opening_href(name: str, action: str) -> str:
    """Where an opening's toggle or reset form posts: the name URL-encoded, slashes included."""
    return f"/progress/opening/{quote(name, safe='')}/{action}"


def _href(epd: str) -> str:
    """The position page's address: the EPD URL-encoded, slashes and spaces included."""
    return f"/progress/position/{quote(epd, safe='')}"


def _numbers(t: Tally) -> dict[str, Any]:
    """A row's numbers as the ledger shows them: scores in percent, None shown as a dash."""
    return {
        "score": None if t.score is None else percent(t.score),
        "white": None if t.white is None else percent(t.white),
        "black": None if t.black is None else percent(t.black),
        "known": t.known,
        "learning": t.learning,
        "never": t.never,
        "total": t.known + t.learning + t.never,
    }
