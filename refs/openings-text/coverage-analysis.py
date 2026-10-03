#!/usr/bin/env python3
"""Coverage of the Wikibooks "Chess Opening Theory" book over the chess-openings TSV
and the play-loop repertoire (prototype/play-loop/tree.json).

Ticket 14 (.scratch/chessop/issues/14-lichess-opening-explanations.md).
Findings: docs/research/opening-explanations.md.

Method
- Titles are built exactly as lila does (ui/opening/src/wiki.ts): per ply
  "<n>. <SAN>" for White and "<n>...<SAN>" for Black, SAN stripped of "+!#?",
  joined by "/", prefixed "Chess Opening Theory/". Lila also skips paths longer
  than 30 plies or 234 characters; we record that separately.
- Existence is decided offline from wikibooks-api-allpages-Chess_Opening_Theory.json
  (list=allpages, apprefix, nonredirects + redirects). Redirect targets are
  resolved with `redirects=1` in batches of 50.
- Wikitext of every real page is fetched with prop=revisions in batches of 50
  (52 requests) and cached in wikibooks-Chess_Opening_Theory-pages.json.gz.
  "Prose" = the wikitext with templates, tables, refs, headings, markup and the
  sections lila hides (Theory table, All possible replies / Black's moves,
  External links, References) removed, whitespace collapsed.
- Lichess-style extracts (prop=extracts, HTML, whole page: the API serves ONE
  per request) are fetched serially (1 req/s) for every matched repertoire
  node and a seeded random sample of matched TSV lines, run through a Python
  port of lila's transformWikiHtml (ui/lib/src/wikiBooks.ts), and their text
  length is compared with the local prose measure.
All requests are serial, send a descriptive User-Agent and maxlag=5
(https://www.mediawiki.org/wiki/API:Etiquette).
"""
import csv, glob, gzip, json, os, random, re, statistics, sys, time, html
import urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
UA = "chessop-research/0.1 (afillion0@gmail.com; local research script; ticket 14)"
API = "https://en.wikibooks.org/w/api.php"
PREFIX = "Chess Opening Theory/"
SLEEP = 0.5
EXTRACT_SAMPLE = 60
random.seed(0)


def api(params, sleep=SLEEP):
    params = dict(params, format="json", formatversion=2, maxlag=5)
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(API, data=data, headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            if "error" in d and d["error"].get("code") == "maxlag":
                time.sleep(5); continue
            time.sleep(sleep)
            return d
        except Exception as e:  # noqa
            print("retry", attempt, e, file=sys.stderr); time.sleep(5 * (attempt + 1))
    raise SystemExit("API failure")


def batches(xs, n=50):
    xs = list(xs)
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


# ---------- title mapping (lila ui/opening/src/wiki.ts) ----------
def title_for(sans):
    parts = []
    for i, san in enumerate(sans, start=1):
        n = (i + 1) // 2
        parts.append(f"{n}. {san}" if i % 2 == 1 else f"{n}...{san}")
    path = "/".join(parts)
    path = re.sub(r"[+!#?]", "", path)
    return PREFIX + path, (len(parts) > 30 or len(path) > 255 - 21)


def sans_from_pgn(pgn):
    return [t for t in pgn.split() if not t.endswith(".")]


# ---------- prose stripping ----------
HIDDEN_SECTIONS = re.compile(
    r"^=+\s*(Theory table|All possible (Black|White)'?s moves|All possible replies|External links|References|See also|Notes)\s*=+\s*$",
    re.I | re.M)


def strip_templates(s):
    out, depth, i = [], 0, 0
    while i < len(s):
        if s.startswith("{{", i): depth += 1; i += 2; continue
        if s.startswith("}}", i) and depth: depth -= 1; i += 2; continue
        if depth == 0: out.append(s[i])
        i += 1
    return "".join(out)


def prose(wikitext):
    s = re.sub(r"<!--.*?-->", "", wikitext, flags=re.S)
    s = re.sub(r"<ref[^>/]*/>", "", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = strip_templates(s)
    s = re.sub(r"\{\|.*?\|\}", "", s, flags=re.S)  # tables
    # drop hidden sections: from a hidden heading to the next heading of same-or-higher level
    lines, keep, skip_level = s.split("\n"), [], None
    for ln in lines:
        m = re.match(r"^(=+)\s*(.*?)\s*=+\s*$", ln)
        if m:
            level = len(m.group(1))
            if skip_level is not None and level <= skip_level: skip_level = None
            if HIDDEN_SECTIONS.match(ln): skip_level = level; continue
            continue  # headings themselves are not prose
        if skip_level is None: keep.append(ln)
    s = "\n".join(keep)
    s = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\[\[([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\[https?://\S+\s*([^\]]*)\]", r"\1", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("'''", "").replace("''", "")
    s = re.sub(r"^[*#:;]+\s*", "", s, flags=re.M)
    s = s.replace("When contributing to this Wikibook, please follow the Conventions for organization.", "")
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------- lila transformWikiHtml port ----------
def transform_wiki_html(h):
    h = h.replace("When contributing to this Wikibook, please follow the Conventions for organization.", "")
    h = re.sub(r'<h2 data-mw-anchor="External_links">External links</h2>.*?(?=<h[1-6]|$)', "", h, flags=re.S)
    h = re.sub(r'<h3 data-mw-anchor="All_possible_replies">All possible replies</h3>.*?(?=<h[1-6]|$)', "", h, flags=re.S)
    h = re.sub(r"<h2 data-mw-anchor=\"All_possible_Black's_moves\" data-mw-fallback-anchor=\"All_possible_Black\.27s_moves\">All possible Black's moves</h2>.*?(?=<h[1-6]|$)", "", h, flags=re.S)
    h = re.sub(r'<h2 data-mw-anchor="Theory_table">Theory table</h2>.*?(?=<h[1-6]|$)', "", h, flags=re.S)
    h = re.sub(r"<p>(<br />|\s)*</p>", "", h)
    h = re.sub(r"<h1.+</h1>", "", h)
    return h


def html_text(h):
    t = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def q(xs):
    xs = sorted(xs)
    if not xs: return "n/a"
    p = lambda f: xs[min(len(xs) - 1, int(f * len(xs)))]
    return f"min {xs[0]}, q1 {p(.25)}, median {p(.5)}, q3 {p(.75)}, max {xs[-1]}, mean {statistics.mean(xs):.0f}"


def main():
    inv = json.load(open(os.path.join(HERE, "wikibooks-api-allpages-Chess_Opening_Theory.json")))
    pages, redirs = set(inv["nonredirects"]), set(inv["redirects"])

    # ---- inputs
    tsv = []
    for f in sorted(glob.glob(os.path.join(ROOT, "refs/lichess/chess-openings-[a-e].tsv"))):
        for row in csv.DictReader(open(f), delimiter="\t"):
            tsv.append(row)
    tree = json.load(open(os.path.join(ROOT, "prototype/play-loop/tree.json")))["nodes"]
    tree = [n for n in tree if n["path"]]  # drop the start position (its page is the book's main page)

    # ---- redirect targets (batches of 50)
    cache_r = os.path.join(HERE, "wikibooks-api-redirect-targets.json")
    if os.path.exists(cache_r):
        target = json.load(open(cache_r))
    else:
        target, n = {}, 0
        for b in batches(sorted(redirs)):
            d = api({"action": "query", "titles": "|".join(b), "redirects": 1, "prop": "info"}); n += 1
            for r in d["query"].get("redirects", []): target[r["from"]] = r["to"]
        print("redirect-target requests:", n)
        json.dump(target, open(cache_r, "w"), indent=0)

    def status(sans):
        t, too_long = title_for(sans)
        if t in pages: return "page", t, too_long
        if t in redirs:
            to = target.get(t)
            return ("redirect->page" if to in pages else "redirect->missing"), to or t, too_long
        return "missing", t, too_long

    # ---- wikitext of every real page (batches of 50)
    cache_w = os.path.join(HERE, "wikibooks-Chess_Opening_Theory-pages.json.gz")
    if os.path.exists(cache_w):
        wt = json.load(gzip.open(cache_w, "rt"))
    else:
        wt, n = {}, 0
        for b in batches(sorted(pages)):
            d = api({"action": "query", "titles": "|".join(b), "prop": "revisions|info",
                     "rvprop": "content|timestamp|size", "rvslots": "main"}); n += 1
            for p in d["query"]["pages"]:
                if "revisions" in p:
                    r = p["revisions"][0]
                    wt[p["title"]] = {"timestamp": r["timestamp"], "size": r.get("size"),
                                      "wikitext": r["slots"]["main"]["content"]}
        print("wikitext requests:", n, "pages:", len(wt))
        json.dump(wt, gzip.open(cache_w, "wt"), indent=0)

    pr = {t: prose(v["wikitext"]) for t, v in wt.items()}
    plen = {t: len(p) for t, p in pr.items()}

    # ---- classify
    rows_tsv, rows_tree = [], []
    for r in tsv:
        st, t, tl = status(sans_from_pgn(r["pgn"]))
        rows_tsv.append({"eco": r["eco"], "name": r["name"], "pgn": r["pgn"], "plies": len(sans_from_pgn(r["pgn"])),
                         "status": st, "title": t, "lila_skips": tl, "prose_chars": plen.get(t, 0)})
    for n in tree:
        st, t, tl = status(n["path"])
        rows_tree.append({"id": n["id"], "ply": n["ply"], "path": " ".join(n["path"]), "name": n["name"],
                          "named_here": n["named_here"], "status": st, "title": t, "lila_skips": tl,
                          "prose_chars": plen.get(t, 0)})

    # ---- Lichess-style extracts (one page per request)
    cache_e = os.path.join(HERE, "wikibooks-api-extracts-sample.json.gz")
    want = sorted({r["title"] for r in rows_tree if r["status"].endswith("page")})
    tsv_titles = sorted({r["title"] for r in rows_tsv if r["status"].endswith("page")})
    sample = random.sample(tsv_titles, min(EXTRACT_SAMPLE, len(tsv_titles)))
    want_all = sorted(set(want) | set(sample))
    ex = json.load(gzip.open(cache_e, "rt")) if os.path.exists(cache_e) else {}
    n = 0
    for t in want_all:
        if t in ex: continue
        d = api({"action": "query", "titles": t, "redirects": 1, "prop": "extracts", "exlimit": 1}); n += 1
        p = d["query"]["pages"][0]
        ex[t] = p.get("extract", "") if not p.get("missing") else ""
        if n % 50 == 0: json.dump(ex, gzip.open(cache_e, "wt"))
    print("extract requests:", n)
    json.dump(ex, gzip.open(cache_e, "wt"))
    exlen = {t: len(html_text(transform_wiki_html(h)).replace("Read more on WikiBooks", "")) for t, h in ex.items()}

    # ---- write per-row tables
    with open(os.path.join(HERE, "coverage-lines.tsv"), "w") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_tsv[0].keys()), delimiter="\t"); w.writeheader(); w.writerows(rows_tsv)
    with open(os.path.join(HERE, "coverage-tree.tsv"), "w") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_tree[0].keys()), delimiter="\t"); w.writeheader(); w.writerows(rows_tree)

    # ---- report
    out = []
    P = out.append
    P("# Wikibooks 'Chess Opening Theory' coverage (generated by refs/openings-text/coverage-analysis.py)")
    P(f"inventory: {len(pages)} pages + {len(redirs)} redirects under '{PREFIX}' (list=allpages); "
      f"{sum(1 for v in target.values() if v in pages)} redirects point at a page, "
      f"{sum(1 for t in redirs if target.get(t) not in pages)} at a missing page or unresolved")
    P(f"wikitext fetched for {len(wt)} pages; page bytes: {q([v['size'] for v in wt.values()])}")
    P(f"prose chars per page (all {len(pr)} pages): {q(list(plen.values()))}")
    for thr in (1, 100, 200, 500, 1000, 2000):
        P(f"  pages with prose >= {thr} chars: {sum(1 for v in plen.values() if v >= thr)}")
    depth = {}
    for t in pages:
        d = t[len(PREFIX):].count("/") + 1
        depth[d] = depth.get(d, 0) + 1
    P("pages by ply: " + ", ".join(f"{k}:{v}" for k, v in sorted(depth.items())))
    last = [v["timestamp"][:4] for v in wt.values()]
    P("last-edit year of pages: " + ", ".join(f"{y}:{last.count(y)}" for y in sorted(set(last))))

    def summarise(label, rows, thr=(200, 500)):
        P("")
        P(f"## {label}: {len(rows)} rows")
        for st in ("page", "redirect->page", "redirect->missing", "missing"):
            P(f"  {st}: {sum(1 for r in rows if r['status'] == st)}")
        hit = [r for r in rows if r["status"].endswith("page")]
        P(f"  any page (direct or via redirect): {len(hit)} ({100*len(hit)/len(rows):.1f}%)")
        for th in thr:
            k = sum(1 for r in hit if r["prose_chars"] >= th)
            P(f"  with prose >= {th} chars: {k} ({100*k/len(rows):.1f}% of rows)")
        P(f"  prose chars of the pages hit: {q([r['prose_chars'] for r in hit])}")
        P(f"  rows lila would skip (>30 plies or long title): {sum(1 for r in rows if r['lila_skips'])}")
        byply = {}
        for r in rows:
            k = r["plies"] if "plies" in r else r["ply"]
            a = byply.setdefault(k, [0, 0, 0]); a[0] += 1
            if r["status"].endswith("page"): a[1] += 1
            if r["prose_chars"] >= 200: a[2] += 1
        P("  by ply (rows/any page/prose>=200): " + ", ".join(f"{k}:{a[0]}/{a[1]}/{a[2]}" for k, a in sorted(byply.items())))

    summarise("chess-openings TSV lines", rows_tsv)
    byeco = {}
    for r in rows_tsv:
        a = byeco.setdefault(r["eco"][0], [0, 0]); a[0] += 1
        if r["prose_chars"] >= 200: a[1] += 1
    P("  by ECO volume (rows/prose>=200): " + ", ".join(f"{k}:{a[0]}/{a[1]}" for k, a in sorted(byeco.items())))
    summarise("repertoire tree.json nodes (excluding the start position)", rows_tree)
    named = [r for r in rows_tree if r["named_here"]]
    P(f"  named nodes: {len(named)}, of which any page {sum(1 for r in named if r['status'].endswith('page'))}, prose>=200 {sum(1 for r in named if r['prose_chars']>=200)}")
    leaves = {r["id"] for r in rows_tree} - {n["parent"] for n in tree if n["parent"] is not None}
    lv = [r for r in rows_tree if r["id"] in leaves]
    P(f"  leaf nodes: {len(lv)}, any page {sum(1 for r in lv if r['status'].endswith('page'))}, prose>=200 {sum(1 for r in lv if r['prose_chars']>=200)}")
    P("  nodes without a page whose parent has one (prose>=200): " + str(sum(
        1 for r in rows_tree if not r["status"].endswith("page") and any(
            p["id"] == [n for n in tree if n["id"] == r["id"]][0]["parent"] and p["prose_chars"] >= 200 for p in rows_tree))))
    # ancestor fallback: nearest ancestor-or-self with prose >= 200
    byid = {n["id"]: n for n in tree}
    rowsid = {r["id"]: r for r in rows_tree}
    def nearest(nid):
        while nid is not None and nid in rowsid:
            if rowsid[nid]["prose_chars"] >= 200: return nid
            nid = byid[nid]["parent"]
        return None
    P(f"  nodes with prose>=200 at self or an ancestor: {sum(1 for r in rows_tree if nearest(r['id']) is not None)} of {len(rows_tree)}")

    P("")
    P(f"## Lichess-style extracts (whole-page HTML, transformWikiHtml applied): {len(ex)} pages fetched")
    P(f"  repertoire pages: {len(want)}; TSV sample: {len(sample)} (seed 0)")
    both = [(exlen[t], plen.get(t, 0)) for t in ex]
    P(f"  extract text chars: {q([a for a, b in both])}")
    P(f"  local prose chars for the same pages: {q([b for a, b in both])}")
    P(f"  pages where extract is empty: {sum(1 for a, b in both if a == 0)}; extract < 200 chars: {sum(1 for a, b in both if a < 200)}; local prose < 200 for same pages: {sum(1 for a, b in both if b < 200)}")
    agree = sum(1 for a, b in both if (a >= 200) == (b >= 200))
    P(f"  agreement of the >=200 verdict between extract and local measure: {agree}/{len(both)}")
    if both:
        ratio = [a / b for a, b in both if b]
        P(f"  extract/local length ratio: {q([round(r, 2) for r in ratio])}")
    P("")
    P("## Repertoire nodes: status per node (ply, path, name, status, prose chars, extract chars)")
    for r in rows_tree:
        P(f"  {r['ply']:2d} {r['path']:<45} {r['name'][:38]:<38} {r['status']:<17} {r['prose_chars']:6d} {exlen.get(r['title'], -1):6d}")
    P("")
    P("## TSV lines: 20 missing examples at plies <= 6")
    for r in [r for r in rows_tsv if r["status"] == "missing" and r["plies"] <= 6][:20]:
        P(f"  {r['eco']} {r['name']} | {r['pgn']}")
    txt = "\n".join(out)
    open(os.path.join(HERE, "coverage-stats.txt"), "w").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
