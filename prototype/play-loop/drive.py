"""Drive rounds through the socket: play the top main move (or a wrong move every 4th round) and print the flow."""
import json, random, statistics
from fastapi.testclient import TestClient
import chess
import server
random.seed(1)
client = TestClient(server.app)
ms = []
with client.websocket_connect("/ws") as ws:
    for i in range(12):
        m = ws.receive_json(); assert m["type"] == "round"
        print(f"\n== round {i}: {m['side']} ply{m['ply']} {m['opening']} need={m['side_need']} forced={m['forced']} relearn={m['relearning']}")
        wrong = (i % 4 == 3)
        while True:
            board = chess.Board(m["fen"])
            node = next(n for n in server.NODES if n["fen"] == m["fen"]) if not wrong else None
            if node and node["children"]:
                cands = [server.NODES[c] for c in node["children"]]
                pick = cands[0] if cands[0]["san"] != m["forced"] else cands[1]
                uci = pick["uci"]
            else:
                uci = next(x for x in board.legal_moves if board.san(x) not in [server.NODES[c]["san"] for c in (node or {"children": []})["children"]]).uci()
            ws.send_json({"type": "move", "from": uci[:2], "to": uci[2:4]})
            r = ws.receive_json(); ms.append(r["ms"])
            print(f"  {r['type']}: {r['verdict']} {r['played']['san']} kind={r.get('pass_kind')} revealed={[x['san'] for x in r['revealed']]} reply={r['reply'] and r['reply']['san']} {r['ms']}ms")
            if r["verdict"] == "miss" or not r.get("dests"):
                o = ws.receive_json(); assert o["type"] == "round_over", o
                print(f"  round_over {o['outcome']} path={' '.join(o['path'])} stats={o['stats']}"); break
            m = r
            wrong = False
        ws.send_json({"type": "next"})
print("\nserver ms: max", max(ms), "p95", sorted(ms)[int(len(ms)*.95)], "mean", round(statistics.mean(ms), 2))
