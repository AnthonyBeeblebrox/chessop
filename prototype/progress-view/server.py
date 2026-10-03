"""PROTOTYPE (ticket 19): three variants of the progress view on one throwaway route.

Run:  uv run python server.py      then open http://localhost:8011/prototype/progress?variant=A
Data: the play-loop prototype's tree.json (2013-01 dump, 1800+, 0.2 %, top-3) pooled by EPD into the
position graph of ADR 0006, plus THREE WEEKS OF SIMULATED HISTORY under ADR 0001's memory model, so the
page has something to show. Nothing persists; the memory lives in the process. Not the app.
"""
import json, math, random, time
from collections import defaultdict
import chess
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

random.seed(19)
TREE = json.load(open("../play-loop/tree.json"))
NODES = TREE["nodes"]
GAMES = TREE["games"]
DAY = 86400.0
NOW = time.time()

# ---- pool the trie into a position graph (ADR 0006) --------------------------------------------
POS = {}                      # epd -> position dict
for n in NODES:
    p = POS.setdefault(n["epd"], {"epd": n["epd"], "fen": n["fen"], "ply": n["ply"], "count": 0, "nodes": [], "exact": None, "eco": ""})
    p["count"] += n["count"]; p["nodes"].append(n)
    if n["named_here"]: p["exact"] = n["name"]; p["eco"] = n["eco"]
EDGES = defaultdict(lambda: defaultdict(int))   # parent epd -> child epd -> pooled count
for n in NODES:
    for c in n["children"]:
        EDGES[n["epd"]][NODES[c]["epd"]] += NODES[c]["count"]
PLIST = sorted(POS.values(), key=lambda p: (p["ply"], -p["count"]))
for i, p in enumerate(PLIST):
    p["id"] = i
    best = max(p["nodes"], key=lambda n: n["count"])            # canonical order = most popular trie node
    p["canonical"] = best["path"]; p["orders"] = len(p["nodes"])
    p["colour"] = "white" if " w " in p["fen"] else "black"       # side to move = the learner colour that owns the record
    p["moves"] = []
    for cepd, cnt in sorted(EDGES[p["epd"]].items(), key=lambda kv: -kv[1]):
        child = POS[cepd]; tn = next(n for n in child["nodes"] if n["parent"] is not None and NODES[n["parent"]]["epd"] == p["epd"])
        p["moves"].append({"san": tn["san"], "uci": tn["uci"], "to": None, "pop": cnt / p["count"], "cepd": cepd})
    p["parents"] = []
for p in PLIST:
    for m in p["moves"]: m["to"] = POS[m["cepd"]]["id"]; POS[m["cepd"]]["parents"].append(p["id"])
BYID = {p["id"]: p for p in PLIST}
# names: exact where the book names the position, else inherited along the canonical order (progress view rule)
def inherit(p):
    if p["exact"]: return p["exact"], p["eco"], True
    for k in range(len(p["canonical"]) - 1, -1, -1):
        for q in PLIST:
            if q["exact"] and q["canonical"] == p["canonical"][:k]: return q["exact"], q["eco"], False
    return "Start position", "", False
for p in PLIST:
    p["name"], p["eco"], p["exact_name"] = inherit(p)
    p["family"] = p["name"].split(":")[0] if p["ply"] >= 2 else "First moves"
    p["leaf"] = not p["moves"]
LEARNER = [p for p in PLIST if not p["leaf"]]        # every position with main moves is drilled for its side to move

# ---- explanations (ticket 15): one real page from refs/, placeholders elsewhere -----------------
NAJ = json.load(open("../../refs/openings-text/wikibooks-api-sample-najdorf-extract-plaintext.json"))["query"]["pages"][0]["extract"]
def title_of(order):
    parts = []
    for i, san in enumerate(order): parts.append(f"{i//2+1}._{san}" if i % 2 == 0 else f"{i//2+1}...{san}")
    return "Chess_Opening_Theory/" + "/".join(parts)
def explanation(p):
    if p["canonical"] == ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6"]:
        paras = [x.strip() for x in NAJ.split("\n") if x.strip() and not x.startswith("==")]
        return {"title": title_of(p["canonical"]), "lead": paras[0], "body": paras[1:], "borrowed": None, "real": True}
    src = p if p["exact_name"] else next((q for q in reversed(PLIST) if q["exact"] and p["canonical"][:len(q["canonical"])] == q["canonical"] and len(q["canonical"]) < len(p["canonical"])), None)
    lead = f"[placeholder lead] The {p['name']} arises after {line_str(p['canonical'])}. The real snapshot ships the Wikibooks 'Chess Opening Theory' page for this position, trimmed to prose."
    body = ["[placeholder body] Second paragraph: plans for both sides.", "[placeholder body] Third paragraph: the main continuations and what they aim at."]
    return {"title": title_of(src["canonical"] if src else p["canonical"]), "lead": lead, "body": body,
            "borrowed": (line_str(src["canonical"]) if src and src is not p else None), "real": False}
def line_str(order):
    out = []
    for i, san in enumerate(order): out.append((f"{i//2+1}." if i % 2 == 0 else "") + san)
    return " ".join(out) or "start"

# ---- ADR 0001 memory model ----------------------------------------------------------------------
H0, H_MIN, H_MAX = DAY, 900.0, 9 * 30 * DAY
SURE, FLOOR = 0.9, 0.1
class Record:
    def __init__(self): self.s = 0; self.f = 0; self.last = None; self.relearn = False; self.reveals = 0
    def halflife(self): return min(H_MAX, max(H_MIN, H0 * 2 ** (self.s - self.f)))
    def recall(self, now): return 0.0 if self.last is None else 2 ** (-(now - self.last) / self.halflife())
    def need(self, now): return max(FLOOR, 1 - self.recall(now))
    def on_pass(self, now):
        if self.relearn: self.relearn = False; self.last = now; return "relearning"
        if self.recall(now) >= SURE: self.last = now; return "sure"
        self.s += 1; self.last = now; return "counted"
    def on_miss(self): self.f += 1; self.relearn = True; self.reveals += 1
records = defaultdict(Record)     # position id -> Record (colour is inside the EPD, ADR 0006)
round_log = []
opted_out = set()

def scoped(): return [p for p in LEARNER if p["family"] not in opted_out]
def score(ps, now):
    tot = sum(p["count"] for p in ps)
    return None if not tot else sum(p["count"] * records[p["id"]].recall(now) for p in ps) / tot
def mean_need_below(pid, now, memo):
    if pid in memo: return memo[pid]
    p = BYID[pid]; xs = []
    def walk(i, w):
        q = BYID[i]
        if not q["leaf"]: xs.append((w, records[i].need(now)))
        for m in q["moves"]: walk(m["to"], w * m["pop"])
    walk(pid, 1.0)
    v = sum(w * n for w, n in xs) / (sum(w for w, _ in xs) or 1) if xs else FLOOR
    memo[pid] = v; return v

# ---- simulated learner: three weeks of sessions -------------------------------------------------
FAMILY_SKILL = defaultdict(lambda: random.uniform(0.35, 0.8))
FAMILY_SKILL.update({"Sicilian Defense": 0.85, "Ruy Lopez": 0.8, "French Defense": 0.45, "Queen's Gambit Declined": 0.7, "First moves": 0.97, "King's Indian Defense": 0.3})
def p_know(p, rec): return min(0.97, FAMILY_SKILL[p["family"]] * 0.94 ** max(0, p["ply"] - 2) + 0.12 * rec.reveals)
def play_round(now):
    memo = {}
    needs = {c: sum(p["count"] * records[p["id"]].need(now) for p in LEARNER if p["colour"] == c) for c in ("white", "black")}
    side = "white" if random.random() < max(0.2, min(0.8, needs["white"] / (sum(needs.values()) or 1))) else "black"
    p = PLIST[0]; path = []; outcome = "success"; ended = p["id"]
    while not p["leaf"]:
        if p["colour"] == side:
            rec = records[p["id"]]
            if random.random() < p_know(p, rec):
                rec.on_pass(now); m = random.choices(p["moves"], [x["pop"] for x in p["moves"]])[0]
            else:
                rec.on_miss(); outcome = "miss"; ended = p["id"]; path.append("??"); break
        else:
            m = random.choices(p["moves"], [max(1e-6, x["pop"] * mean_need_below(x["to"], now, memo) + 0.3 * random.gauss(0, 1)) for x in p["moves"]])[0]
        path.append(m["san"]); p = BYID[m["to"]]; ended = p["id"]
    round_log.append({"t": now, "side": side, "path": path, "outcome": outcome, "ended": ended})
history = []
DAYS = 21
for d in range(DAYS):
    if d in (9, 10, 16): continue                                   # days off, so the decay shows
    day_start = NOW - (DAYS - d) * DAY + 3600 * 19
    t = day_start; n = random.randint(25, 70); before = len(round_log)
    for _ in range(n): play_round(t); t += random.uniform(8, 25)
    todays = round_log[before:]
    history.append({"day": time.strftime("%Y-%m-%d", time.localtime(day_start)), "score": score(scoped(), t),
                    "white": score([p for p in scoped() if p["colour"] == "white"], t), "black": score([p for p in scoped() if p["colour"] == "black"], t),
                    "rounds": len(todays), "rate": sum(r["outcome"] == "success" for r in todays) / len(todays)})
# a short session "today", so the in-session rate has something to say
TODAY_START = NOW - 900
t = TODAY_START; before = len(round_log)
for _ in range(23): play_round(t); t += random.uniform(8, 25)
SESSION_FROM = before

# ---- the page's data --------------------------------------------------------------------------
def fam_stats(now):
    fams = defaultdict(list)
    for p in LEARNER: fams[p["family"]].append(p)
    out = []
    for f, ps in fams.items():
        recs = [records[p["id"]] for p in ps]
        ecos = sorted({p["eco"] for p in ps if p["eco"]})
        out.append({"family": f, "eco": (ecos[0] + ("–" + ecos[-1] if len(ecos) > 1 else "")) if ecos else "",
                    "positions": len(ps), "branches": sum(1 for p in ps if all(BYID[m["to"]]["leaf"] for m in p["moves"])),
                    "never": sum(1 for r in recs if r.last is None), "known": sum(1 for r in recs if r.s >= 3 and not r.relearn),
                    "relearning": sum(1 for r in recs if r.relearn),
                    "score": score(ps, now), "white": score([p for p in ps if p["colour"] == "white"], now), "black": score([p for p in ps if p["colour"] == "black"], now),
                    "share": sum(p["count"] for p in ps) / sum(q["count"] for q in LEARNER), "opted_in": f not in opted_out,
                    "max_ply": max(p["ply"] for p in ps)})
    return sorted(out, key=lambda x: -x["share"])
def pos_json(p, now):
    r = records[p["id"]]
    return {"id": p["id"], "epd": p["epd"], "fen": p["fen"], "ply": p["ply"], "colour": p["colour"], "name": p["name"], "eco": p["eco"],
            "exact": p["exact_name"], "family": p["family"], "canonical": p["canonical"], "line": line_str(p["canonical"]), "orders": p["orders"],
            "count": p["count"], "share": p["count"] / GAMES, "leaf": p["leaf"], "parents": p["parents"],
            "moves": [{"san": m["san"], "uci": m["uci"], "to": m["to"], "pop": round(m["pop"], 3)} for m in p["moves"]],
            "rec": None if p["leaf"] else {"s": r.s, "f": r.f, "R": r.recall(now), "h_hours": r.halflife() / 3600, "relearn": r.relearn,
                     "never": r.last is None, "last_days": None if r.last is None else (now - r.last) / DAY, "known": r.s >= 3 and not r.relearn},
            "explanation": explanation(p)}
def data():
    now = time.time(); sess = round_log[SESSION_FROM:]
    return {"now": now, "games": GAMES, "band": "1800+ (2013-01 sample; the real graph is ~4x this: 1,104 positions)",
            "score": {"all": score(scoped(), now), "white": score([p for p in scoped() if p["colour"] == "white"], now), "black": score([p for p in scoped() if p["colour"] == "black"], now)},
            "session": {"rounds": len(sess), "success": sum(r["outcome"] == "success" for r in sess), "target": [0.8, 0.9], "since_minutes": (now - TODAY_START) / 60},
            "last_score": history[-1]["score"], "last_day": history[-1]["day"], "history": history,
            "counts": {"positions": len(PLIST), "learner": len(LEARNER), "scoped": len(scoped()),
                       "never": sum(1 for p in LEARNER if records[p["id"]].last is None), "known": sum(1 for p in LEARNER if records[p["id"]].s >= 3 and not records[p["id"]].relearn),
                       "relearning": sum(1 for p in LEARNER if records[p["id"]].relearn), "rounds": len(round_log)},
            "openings": fam_stats(now), "positions": [pos_json(p, now) for p in PLIST], "opted_out": sorted(opted_out)}

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/cg", StaticFiles(directory="../play-loop/static/chessground"), name="cg")
@app.get("/prototype/progress")
def page(): return FileResponse("static/progress.html")
@app.get("/data")
def get_data(): return JSONResponse(data())
@app.post("/act/{what}/{arg}")
def act(what: str, arg: str):
    """Stubbed actions: they mutate the in-memory state so the page shows the consequence, nothing more."""
    if what == "reset_position": records.pop(int(arg), None)
    elif what == "reset_opening":
        for p in LEARNER:
            if p["family"] == arg: records.pop(p["id"], None)
    elif what == "optout": opted_out.add(arg)
    elif what == "optin": opted_out.discard(arg)
    elif what == "drill": return {"toast": f"would open the play page on a round starting from {line_str(BYID[int(arg)]['canonical'])} (not built)"}
    return data()

if __name__ == "__main__":
    print(f"{len(PLIST)} positions ({len(LEARNER)} learner), {sum(len(p['moves']) for p in PLIST)} edges, {len(round_log)} simulated rounds; http://localhost:8011/prototype/progress")
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8011, log_level="warning")
