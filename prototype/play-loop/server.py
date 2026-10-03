"""PROTOTYPE (ticket 10): one fast round over the four messages of ADR 0004.

Run:  uv run python server.py      then open http://localhost:8010/prototype/play?variant=A
State lives in memory and dies with the process. Not the app.
"""
import json, math, random, time
from collections import defaultdict
import chess
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

TREE = json.load(open("tree.json"))
NODES = TREE["nodes"]
LEARNER_PLY_PARITY = {"white": 0, "black": 1}   # learner moves at nodes whose ply parity = this

# ---- ADR 0001 memory model, defaults --------------------------------------------------------
H0, H_MIN, H_MAX = 86400.0, 900.0, 9 * 30 * 86400.0
SURE, FLOOR, C_EXPLORE, ALPHA, FORCED, SIDE_FLOOR = 0.9, 0.1, 1.0, 1.0, 0.1, 0.2
FORCED_RATE = lambda: FORCED   # read at call time so /forced/<p> takes effect
SPEED = 1.0   # prototype knob: clock multiplier so a 10-minute session can show forgetting (set via /speed)

class Record:
    def __init__(self): self.s = 0; self.f = 0; self.last = None; self.relearn = False
    def halflife(self): return min(H_MAX, max(H_MIN, H0 * 2 ** (self.s - self.f)))
    def recall(self, now):
        if self.last is None: return 0.0
        return 2 ** (-((now - self.last) * SPEED) / self.halflife())
    def need(self, now): return max(FLOOR, 1 - self.recall(now))
    def on_pass(self, now):
        r = self.recall(now)
        if self.relearn: self.relearn = False; self.last = now; return "relearning"
        if r >= SURE: self.last = now; return "sure"
        self.s += 1; self.last = now; return "counted"
    def on_miss(self): self.f += 1; self.relearn = True

records = defaultdict(Record)          # (epd, colour) -> Record
faced = defaultdict(int)               # (node id) -> times the learner has faced this opponent move
round_log = []

def learner_nodes_below(nid, colour):
    """Learner positions (nodes where the learner is to move) in the subtree of nid, with popularity weights."""
    out = []
    def walk(i, w):
        n = NODES[i]
        if n["children"] and n["ply"] % 2 == LEARNER_PLY_PARITY[colour]:
            out.append((n, w))
        for c in n["children"]: walk(c, w * NODES[c]["pop"])
    walk(nid, 1.0)
    return out

def mean_need(nid, colour, now):
    xs = learner_nodes_below(nid, colour)
    if not xs: return FLOOR
    tot = sum(w for _, w in xs)
    return sum(w * records[(n["epd"], colour)].need(now) for n, w in xs) / tot

def draw_side(now):
    needs = {c: sum(w * records[(n["epd"], c)].need(now) for n, w in learner_nodes_below(0, c)) for c in ("white", "black")}
    tot = sum(needs.values()) or 1
    p_white = max(SIDE_FLOOR, min(1 - SIDE_FLOOR, needs["white"] / tot))
    return ("white" if random.random() < p_white else "black"), needs

def opponent_pick(nid, colour, now):
    cands = NODES[nid]["children"]
    weights = []
    for c in cands:
        base = NODES[c]["pop"] ** ALPHA * mean_need(c, colour, now)
        gumbel = -math.log(-math.log(random.random()))
        bonus = C_EXPLORE / math.sqrt(1 + faced[c]) * gumbel
        weights.append(max(1e-6, base + bonus))
    pick = random.choices(cands, weights)[0]
    faced[pick] += 1
    return pick, [(NODES[c]["san"], round(w, 3)) for c, w in zip(cands, weights)]

def dests(board):
    d = defaultdict(list)
    for m in board.legal_moves: d[chess.square_name(m.from_square)].append(chess.square_name(m.to_square))
    return d

def moves_of(nid): return [{"san": NODES[c]["san"], "uci": NODES[c]["uci"], "pop": round(NODES[c]["pop"], 2)} for c in NODES[nid]["children"]]

class Round:
    def __init__(self):
        now = time.time()
        self.side, needs = draw_side(now)
        self.nid = 0; self.board = chess.Board(); self.path = []; self.forced = None
        self.before = {}
        self.needs = needs
        self.start = now
        if self.side == "black": self.opponent_moves()      # opponent opens
        self.prepare_learner_turn()

    def opponent_moves(self):
        pick, weights = opponent_pick(self.nid, self.side, time.time())
        self.nid = pick; self.board.push_san(NODES[pick]["san"]); self.path.append(NODES[pick]["san"])
        self.last_weights = weights
        return pick

    def prepare_learner_turn(self):
        n = NODES[self.nid]; self.forced = None
        acc = list(n["children"])
        if len(acc) >= 2 and random.random() < FORCED_RATE():
            now = time.time()
            needs = sorted((mean_need(c, self.side, now), c) for c in acc)
            if needs[0][0] < needs[1][0]:            # a tie means no move is better known: nothing to force
                best = needs[0][1]; acc.remove(best); self.forced = NODES[best]["san"]
        self.accepted = acc
        rec = records[(n["epd"], self.side)]
        self.before[n["epd"]] = {"s": rec.s, "f": rec.f, "R": round(rec.recall(time.time()), 2), "relearn": rec.relearn}

    def position_msg(self):
        n = NODES[self.nid]; rec = records[(n["epd"], self.side)]
        return {"fen": self.board.fen(), "dests": dests(self.board), "ply": n["ply"], "opening": n["name"], "eco": n["eco"],
                "forced": self.forced, "forced_uci": next((NODES[c]["uci"] for c in n["children"] if NODES[c]["san"] == self.forced), None),
                "relearning": rec.relearn, "recall": round(rec.recall(time.time()), 2),
                "path": list(self.path)}

    def round_msg(self):
        return {"type": "round", "side": self.side, "orientation": self.side,
                "side_need": {k: round(v, 2) for k, v in self.needs.items()}, **self.position_msg()}

    def learner_move(self, frm, to):
        """Returns list of messages to send."""
        t0 = time.perf_counter(); now = time.time()
        mv = chess.Move.from_uci(frm + to)
        if self.board.piece_at(mv.from_square) and self.board.piece_at(mv.from_square).piece_type == chess.PAWN and chess.square_rank(mv.to_square) in (0, 7):
            mv = chess.Move.from_uci(frm + to + "q")
        if mv not in self.board.legal_moves: return [{"type": "error", "text": "illegal"}]
        san = self.board.san(mv)
        left = NODES[self.nid]; rec = records[(left["epd"], self.side)]
        revealed = moves_of(self.nid)
        hit = next((c for c in self.accepted if NODES[c]["san"] == san), None)
        if hit is None and san == self.forced:       # the discarded move: round ends, neither pass nor miss
            self.board.push(mv); self.path.append(san)
            return [{"type": "moved", "verdict": "forced", "played": {"san": san, "uci": mv.uci()}, "revealed": revealed,
                     "forced": self.forced, "reply": None, "fen": self.board.fen(), "dests": {}, "ms": round((time.perf_counter()-t0)*1000, 2)},
                    self.over("forced", revealed, {"san": san, "uci": mv.uci()})]
        if hit is None:
            rec.on_miss()
            self.board.push(mv); self.path.append(san)
            out = [{"type": "moved", "verdict": "miss", "played": {"san": san, "uci": mv.uci()}, "revealed": revealed,
                    "forced": self.forced, "reply": None, "fen": self.board.fen(), "dests": {}, "ms": round((time.perf_counter()-t0)*1000, 2)}]
            out.append(self.over("miss", revealed, {"san": san, "uci": mv.uci()}))
            return out
        kind = rec.on_pass(now)
        self.nid = hit; self.board.push(mv); self.path.append(san)
        reply = None; over = None
        if NODES[self.nid]["children"]:
            pick = self.opponent_moves()
            reply = {"san": NODES[pick]["san"], "uci": NODES[pick]["uci"]}
            if NODES[self.nid]["children"]: self.prepare_learner_turn()
            else: over = self.over("success", moves_of(NODES[pick]["parent"]), None)
        else:
            over = self.over("success", revealed, None)
        msg = {"type": "moved", "verdict": "pass", "pass_kind": kind, "played": {"san": san, "uci": mv.uci()},
               "revealed": revealed, "reply": reply, "opponent_weights": getattr(self, "last_weights", None),
               "ms": round((time.perf_counter()-t0)*1000, 2), **self.position_msg()}
        if over: msg["dests"] = {}
        return [msg] + ([over] if over else [])

    def over(self, outcome, reveal, missed):
        entry = {"t": round(time.time(), 1), "side": self.side, "path": self.path, "outcome": outcome, "ply": len(self.path),
                 "before": self.before, "seconds": round(time.time() - self.start, 1)}
        round_log.append(entry)
        return {"type": "round_over", "outcome": outcome, "reveal": reveal, "missed": missed, "path": list(self.path),
                "opening": NODES[self.nid]["name"], "fen": self.board.fen(), "stats": stats()}

def stats():
    now = time.time(); n = len(round_log)
    ok = sum(1 for r in round_log if r["outcome"] == "success")
    seen = {k: r for k, r in records.items() if r.last is not None or r.f}
    return {"rounds": n, "success": ok, "rate": round(ok / n, 2) if n else None,
            "positions_seen": len(seen), "positions_total": sum(1 for c in ("white", "black") for _ in learner_nodes_below(0, c)),
            "known": sum(1 for r in seen.values() if r.s >= 3),
            "relearning": sum(1 for r in seen.values() if r.relearn),
            "mean_need": round(sum(mean_need(0, c, now) for c in ("white", "black")) / 2, 2)}

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/prototype/play")
def play(): return FileResponse("static/play.html")

@app.get("/state")
def state():
    now = time.time()
    recs = sorted(({"epd": k[0], "colour": k[1], "s": r.s, "f": r.f, "R": round(r.recall(now), 2), "need": round(r.need(now), 2),
                    "h_hours": round(r.halflife() / 3600, 1), "relearn": r.relearn} for k, r in records.items()), key=lambda x: -x["need"])
    return JSONResponse({"stats": stats(), "records": recs, "log": round_log[-50:]})

@app.get("/forced/{x}")
def forced_rate(x: float):
    global FORCED; FORCED = x; return {"forced": FORCED}

@app.get("/speed/{x}")
def speed(x: float):
    global SPEED; SPEED = x; return {"speed": SPEED}

@app.websocket("/ws")
async def ws(sock: WebSocket):
    await sock.accept()
    rnd = Round(); await sock.send_json(rnd.round_msg())
    try:
        while True:
            msg = await sock.receive_json()
            if msg.get("type") == "next":
                rnd = Round(); await sock.send_json(rnd.round_msg())
            elif msg.get("type") == "move":
                for m in rnd.learner_move(msg["from"], msg["to"]): await sock.send_json(m)
    except WebSocketDisconnect:
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8010, log_level="warning")
