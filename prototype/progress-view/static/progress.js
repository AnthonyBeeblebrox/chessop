// PROTOTYPE (ticket 19): three variants of the progress view over one /data payload.
//   A "Ledger":   openings table (score, W/B split, known/learning/never bar, opt-in toggle, reset) with each opening
//                 unfolding into its branches as move strings; every learner move is a chip coloured by recall; click = detail drawer.
//                 Score history is a sparkline in the header.
//   B "Explorer": board-first. The graph is walked like an analysis board: the main moves from the shown position as rows
//                 (popularity, aggregate recall below), breadcrumbs, a weakest-positions list; detail panel on the right.
//                 No history graph, no table.
//   C "Wall":     heatmap. Every learner position is one cell inside its opening's block, ordered by ply, coloured by recall;
//                 grey = never passed. Full-width score history chart on top. Click = modal detail.
import { Chessground } from '/cg/chessground.min.js';

const VARIANTS = { A: 'Ledger', B: 'Explorer', C: 'Wall' };
const params = new URLSearchParams(location.search);
const variant = VARIANTS[params.get('variant')] ? params.get('variant') : 'A';

// ---------- switcher (not part of the design) ----------
const keys = Object.keys(VARIANTS);
const go = (k) => { params.set('variant', k); location.search = params.toString(); };
document.getElementById('vlabel').textContent = `${variant} (${VARIANTS[variant]})`;
document.getElementById('prev').onclick = () => go(keys[(keys.indexOf(variant) + keys.length - 1) % keys.length]);
document.getElementById('next').onclick = () => go(keys[(keys.indexOf(variant) + 1) % keys.length]);
window.addEventListener('keydown', (e) => {
  if (e.target.matches('input,textarea,[contenteditable]')) return;
  if (e.key === 'ArrowLeft') document.getElementById('prev').click();
  if (e.key === 'ArrowRight') document.getElementById('next').click();
});

// ---------- shared plumbing ----------
let D;                                  // the /data payload
const pct = (x, d = 1) => x == null ? '–' : (100 * x).toFixed(d) + ' %';
const P = (id) => D.positions[id];
const colour = (rec) => rec == null ? 'transparent' : rec.never ? 'var(--never)' : rec.relearn ? 'var(--bad)' : rec.R >= 0.9 ? 'var(--ok)' : rec.R >= 0.5 ? 'var(--mid)' : '#c0603a';
const label = (rec) => rec.never ? 'never passed' : rec.relearn ? 'relearning' : rec.known ? 'known' : 'learning';
const days = (x) => x < 1 / 24 ? `${Math.round(x * 1440)} min` : x < 1 ? `${Math.round(x * 24)} h` : `${x.toFixed(1)} d`;
const toast = (t) => { const el = document.getElementById('toast'); el.textContent = t; el.classList.add('show'); setTimeout(() => el.classList.remove('show'), 2500); };
async function load() { D = await (await fetch('/data')).json(); }
async function act(what, arg) {
  const r = await (await fetch(`/act/${what}/${encodeURIComponent(arg)}`, { method: 'POST' })).json();
  if (r.toast) { toast(r.toast); return false; }
  D = r; return true;
}
function stats() {
  document.getElementById('vstats').textContent = `${D.counts.learner} learner positions · ${D.counts.rounds} simulated rounds · ${D.band}`;
  document.getElementById('navscore').textContent = `Score ${pct(D.score.all)}`;
}
function miniBoard(el, p) { Chessground(el, { fen: p.fen, viewOnly: true, coordinates: false, orientation: p.colour, drawable: { enabled: false } }); }
function lineHtml(order, upto) { return order.map((s, i) => (i % 2 === 0 ? `${i / 2 + 1}.` : '') + s).join(' '); }
function sessionLine() {
  const s = D.session, rate = s.rounds ? s.success / s.rounds : null;
  const cls = rate == null ? '' : rate < s.target[0] ? 'style="color:var(--mid)"' : rate > s.target[1] ? 'style="color:var(--acc)"' : 'style="color:var(--ok)"';
  return `<span ${cls}>${s.success}/${s.rounds} rounds</span> this session (${pct(rate, 0)}, target 80–90 %)`;
}
// the one shared piece: what a position's detail says. Layout differs per variant; the content is the decision.
function detailHtml(p, opts = {}) {
  const r = p.rec, e = p.explanation;
  const nums = r == null ? `<div class="dim">A leaf: the branch ends here, nothing to recall.</div>` : `
    <div class="rbig" style="color:${colour(r)}">${r.never ? '—' : pct(r.R, 0)} <span style="font-size:.45em;font-weight:500;color:var(--dim)">${label(r)}</span></div>
    <div class="nums">
      <span class="k">recall estimate</span><b>${r.never ? 'none yet' : pct(r.R)}</b>
      <span class="k">half-life</span><b>${r.never ? '–' : r.h_hours < 48 ? Math.round(r.h_hours) + ' h' : (r.h_hours / 24).toFixed(1) + ' d'}</b>
      <span class="k">passes / misses</span><b>${r.s} / ${r.f}${r.relearn ? ' <span class="dim">(relearning pass owed)</span>' : ''}</b>
      <span class="k">last pass</span><b>${r.never ? 'never' : days(r.last_days) + ' ago'}</b>
      <span class="k">reached by</span><b>${pct(p.share, 2)} of games${p.orders > 1 ? ` · ${p.orders} move orders` : ''}</b>
    </div>`;
  return `
    <h3><span class="badge ${p.colour}">${p.colour === 'white' ? 'W' : 'B'}</span> ${p.name}${p.exact ? '' : ' <span class="dim">(inherited)</span>'}</h3>
    <div class="sub">${p.eco ? p.eco + ' · ' : ''}${lineHtml(p.canonical) || 'start position'}</div>
    <div class="mini" id="mini-${p.id}"></div>
    ${nums}
    ${r == null ? '' : `<div class="dim" style="font-size:.85em">main moves</div><div class="moves">${p.moves.map(m => `<span class="chip" data-go="${m.to}" style="border-bottom:3px solid ${colour(P(m.to).rec)}">${m.san} <span class="dim">${Math.round(m.pop * 100)}%</span></span>`).join('')}</div>`}
    <div class="expl">
      ${e.borrowed ? `<div class="borrowed">No page of its own: showing the text for ${e.borrowed}</div>` : ''}
      <div>${e.lead}</div>
      <div class="more" data-more>more ▾</div>
      <div class="body" hidden>${e.body.map(x => `<p>${x}</p>`).join('')}</div>
      <div class="foot">From Wikibooks, <a href="https://en.wikibooks.org/wiki/${e.title}" target="_blank">Chess Opening Theory</a>, CC BY-SA 4.0, trimmed.</div>
    </div>
    ${r == null ? '' : `<div class="acts"><button class="btn go" data-drill="${p.id}">Drill from here</button><button class="btn danger" data-reset="${p.id}">Reset this position</button></div>`}`;
}
function wireDetail(root, p, onGo) {
  const mini = root.querySelector(`#mini-${p.id}`); if (mini) miniBoard(mini, p);
  root.querySelectorAll('[data-more]').forEach(el => el.onclick = () => { const b = el.nextElementSibling; b.hidden = !b.hidden; el.textContent = b.hidden ? 'more ▾' : 'less ▴'; });
  root.querySelectorAll('[data-go]').forEach(el => el.onclick = () => onGo(Number(el.dataset.go)));
  root.querySelectorAll('[data-drill]').forEach(el => el.onclick = () => act('drill', el.dataset.drill));
  root.querySelectorAll('[data-reset]').forEach(el => el.onclick = async () => { if (confirm(`Forget everything about ${p.name} (${lineHtml(p.canonical)})?`)) { await act('reset_position', el.dataset.reset); render(); onGo(p.id); } });
}
function sparkline(h, w = 220, ht = 44) {
  const xs = h.map((x, i) => i), lo = 0.5, hi = 1;
  const pt = (i, v) => `${(i / (h.length - 1)) * w},${ht - ((v - lo) / (hi - lo)) * ht}`;
  return `<svg width="${w}" height="${ht}" style="overflow:visible"><polyline fill="none" stroke="var(--acc)" stroke-width="2" points="${h.map((x, i) => pt(i, x.score)).join(' ')}"/>
    <circle r="3" fill="var(--acc)" cx="${w}" cy="${ht - ((h.at(-1).score - lo) / (hi - lo)) * ht}"/><text x="0" y="${ht + 12}" fill="var(--dim)" font-size="10">${h[0].day.slice(5)}</text><text x="${w}" y="${ht + 12}" fill="var(--dim)" font-size="10" text-anchor="end">today</text></svg>`;
}
function chart(h, w = 900, ht = 150) {
  const padL = 36, padB = 18, lo = 0.4, hi = 1, iw = w - padL, ih = ht - padB;
  const x = (i) => padL + (i / (h.length - 1)) * iw, y = (v) => ih - ((v - lo) / (hi - lo)) * ih;
  const line = (k, col) => `<polyline fill="none" stroke="${col}" stroke-width="2" points="${h.map((p, i) => `${x(i)},${y(p[k])}`).join(' ')}"/>`;
  const grid = [0.5, 0.75, 1].map(v => `<line x1="${padL}" x2="${w}" y1="${y(v)}" y2="${y(v)}" stroke="#333"/><text x="0" y="${y(v) + 4}" fill="var(--dim)" font-size="11">${v * 100} %</text>`).join('');
  const bars = h.map((p, i) => `<rect x="${x(i) - 3}" y="${ih - p.rate * 40}" width="6" height="${p.rate * 40}" fill="#444" opacity=".8"><title>${p.day}: ${p.rounds} rounds, ${pct(p.rate, 0)} success</title></rect>`).join('');
  const labels = h.map((p, i) => i % 3 === 0 ? `<text x="${x(i)}" y="${ht}" fill="var(--dim)" font-size="10" text-anchor="middle">${p.day.slice(5)}</text>` : '').join('');
  return `<svg viewBox="0 0 ${w} ${ht}" class="chart" preserveAspectRatio="none">${grid}${bars}${line('white', '#ddd')}${line('black', '#777')}${line('score', 'var(--acc)')}${labels}
    <text x="${w}" y="12" fill="var(--acc)" font-size="11" text-anchor="end">score · <tspan fill="#ddd">white</tspan> · <tspan fill="#777">black</tspan> · <tspan fill="#666">▮ rounds/day, success</tspan></text></svg>`;
}
const legend = () => `<div class="legend"><span><i style="background:var(--ok)"></i>known (≥90 %)</span><span><i style="background:var(--mid)"></i>learning</span><span><i style="background:#c0603a"></i>fading (&lt;50 %)</span><span><i style="background:var(--bad)"></i>relearning after a miss</span><span><i style="background:var(--never)"></i>never passed</span></div>`;

// ---------- variants ----------
const app = document.getElementById('app');
const V = {};
let sel = null;                          // selected position id, kept across re-renders

V.A = () => {
  app.className = 'A';
  let open = new Set(['French Defense']);
  const draw = () => {
    const h = D.history, last = D.last_score;
    app.innerHTML = `
      <div class="head">
        <div><div class="score">${pct(D.score.all)}</div><div class="lbl">score · ${pct(D.score.all - last, 1).replace(' %', '')} since ${D.last_day.slice(5)}</div></div>
        <div class="split"><div class="kv"><span class="lbl">as White</span><b>${pct(D.score.white)}</b></div><div class="kv"><span class="lbl">as Black</span><b>${pct(D.score.black)}</b></div></div>
        <div class="kv"><span class="lbl">known / learning / never</span><b>${D.counts.known} / ${D.counts.learner - D.counts.known - D.counts.never} / <span style="color:var(--dim)">${D.counts.never}</span></b></div>
        <div class="kv"><span class="lbl">this session</span><b style="font-size:1em">${sessionLine()}</b></div>
        ${sparkline(h)}
      </div>
      <div>
        <table><thead><tr><th>Opening</th><th>ECO</th><th class="num">positions</th><th style="width:22%">known / learning / never</th><th class="num">score</th><th class="num">W</th><th class="num">B</th><th></th></tr></thead>
        <tbody>${D.openings.map(o => {
          const learning = o.positions - o.known - o.never;
          return `<tr class="op ${o.opted_in ? '' : 'out'}" data-f="${o.family}"><td>${open.has(o.family) ? '▾' : '▸'} ${o.family}</td><td class="dim">${o.eco}</td><td class="num">${o.positions}</td>
            <td><div class="bar"><i style="width:${100 * o.known / o.positions}%;background:var(--ok)"></i><i style="width:${100 * learning / o.positions}%;background:var(--mid)"></i></div></td>
            <td class="num"><b>${pct(o.score, 0)}</b></td><td class="num dim">${pct(o.white, 0)}</td><td class="num dim">${pct(o.black, 0)}</td>
            <td><label class="tog"><input type="checkbox" data-opt="${o.family}" ${o.opted_in ? 'checked' : ''}> in</label> <button class="btn danger" style="padding:.15em .5em;font-size:.8em" data-resetop="${o.family}">reset</button></td></tr>` +
            (open.has(o.family) ? `<tr class="lines"><td colspan="8">${branches(o.family)}</td></tr>` : '');
        }).join('')}</tbody></table>
        <div style="margin-top:10px">${legend()}</div>
      </div>
      <div class="side detail" id="detail">${sel == null ? '<div class="empty">Click a move to see the position.</div>' : detailHtml(P(sel))}</div>`;
    app.querySelectorAll('tr.op').forEach(tr => tr.onclick = (e) => { if (e.target.closest('label,button')) return; const f = tr.dataset.f; open.has(f) ? open.delete(f) : open.add(f); draw(); });
    app.querySelectorAll('[data-opt]').forEach(cb => cb.onchange = async () => { await act(cb.checked ? 'optin' : 'optout', cb.dataset.opt); draw(); });
    app.querySelectorAll('[data-resetop]').forEach(b => b.onclick = async () => { if (confirm(`Forget everything about the ${b.dataset.resetop}?`)) { await act('reset_opening', b.dataset.resetop); draw(); } });
    app.querySelectorAll('.mv[data-id]').forEach(el => el.onclick = () => { sel = Number(el.dataset.id); draw(); });
    if (sel != null) wireDetail(app.querySelector('#detail'), P(sel), (id) => { sel = id; draw(); });
    stats();
  };
  // branches of an opening: every leaf whose canonical order runs through the family, shown as its canonical order
  const branches = (f) => {
    const leaves = D.positions.filter(p => p.leaf && (p.family === f || (f === 'First moves' && p.ply <= 1)));
    const byOrder = D.positions.reduce((m, p) => (m[p.canonical.join(' ')] = p, m), {});
    return leaves.map(l => `<div class="line">${l.canonical.map((s, i) => { const p = byOrder[l.canonical.slice(0, i).join(' ')]; const learner = p && !p.leaf && p.family === l.family || (p && i <= 1 && f === 'First moves');
      const mv = (i % 2 === 0 ? `${i / 2 + 1}.` : '') + s;
      return p && !p.leaf ? `<span class="mv ${p.id === sel ? 'sel' : ''}" data-id="${p.id}" style="border-bottom-color:${colour(p.rec)}" title="${p.name}: ${p.rec.never ? 'never passed' : pct(p.rec.R, 0)}">${mv}</span>` : `<span class="mv opp">${mv}</span>`; }).join('')}
      <span class="nm">${l.name}</span></div>`).join('');
  };
  draw();
};

V.B = () => {
  app.className = 'B';
  let cur = sel ?? 0;
  const draw = () => {
    const p = P(cur);
    const crumbs = p.canonical.map((s, i) => { const q = D.positions.find(x => x.canonical.join(' ') === p.canonical.slice(0, i + 1).join(' ')); return `<span data-c="${q ? q.id : ''}" class="${q && q.id === cur ? 'cur' : ''}">${(i % 2 === 0 ? `${i / 2 + 1}.` : '')}${s}</span>`; });
    const agg = (id) => { const q = P(id); if (q.leaf) return null; const xs = []; const walk = (i, w) => { const z = P(i); if (!z.leaf) xs.push([w, z.rec.R]); z.moves.forEach(m => walk(m.to, w * m.pop)); }; walk(id, 1); return xs.reduce((a, [w, r]) => a + w * r, 0) / xs.reduce((a, [w]) => a + w, 0); };
    const weakest = D.positions.filter(q => q.rec && !q.rec.never).sort((a, b) => a.rec.R - b.rec.R).slice(0, 8);
    const never = D.positions.filter(q => q.rec && q.rec.never).sort((a, b) => b.count - a.count).slice(0, 6);
    app.innerHTML = `
      <div class="scoreline"><span>Score <b>${pct(D.score.all)}</b></span><span>White ${pct(D.score.white, 0)} · Black ${pct(D.score.black, 0)}</span><span>${sessionLine()}</span><span>${D.counts.never} positions never passed</span></div>
      <div class="boardcol"><div class="board" id="bigboard"></div>
        <div class="crumbs"><span data-c="0" class="${cur === 0 ? 'cur' : ''}">start</span> ${crumbs.join(' ')}</div>
        <div class="kbd">← up a move · click a move row to go down · <kbd>Esc</kbd> back to start</div></div>
      <div class="movesbox">
        <h4>${p.leaf ? 'branch ends here' : `${p.colour === 'white' ? 'White' : 'Black'} to move · ${p.moves.length} main move${p.moves.length > 1 ? 's' : ''} · ${p.colour === 'white' ? 'the learner’s' : 'the learner’s'} position`}</h4>
        ${p.moves.map(m => { const q = P(m.to); const a = agg(m.to); return `<div class="mrow" data-go="${m.to}" style="border-left-color:${colour(q.rec)}">
          <span class="san">${m.san}</span><span class="pop">${Math.round(m.pop * 100)} %</span>
          ${q.leaf ? `<span class="stub">${q.exact ? q.name : 'ends the branch'}</span>` : `<div><div class="dim" style="font-size:.8em">${q.name}${q.exact ? '' : ' <i>(inh.)</i>'} · ${Math.round(a * 100)} % known below</div><div class="agg"><i style="width:${100 * a}%"></i></div></div>`}
          <span class="num" style="color:${colour(q.rec)}">${q.rec == null ? '' : q.rec.never ? 'new' : pct(q.rec.R, 0)}</span></div>`; }).join('')}
        <div class="weak"><h4>weakest positions</h4>${weakest.map(q => `<div data-go="${q.id}"><span style="color:${colour(q.rec)}">${pct(q.rec.R, 0)}</span> <span class="badge ${q.colour}">${q.colour[0].toUpperCase()}</span> ${q.name} <span class="dim">${lineHtml(q.canonical)}</span></div>`).join('')}
        <h4 style="margin-top:1em">never passed, most played first</h4>${never.map(q => `<div data-go="${q.id}"><span class="badge ${q.colour}">${q.colour[0].toUpperCase()}</span> ${q.name} <span class="dim">${lineHtml(q.canonical)} · ${pct(q.share, 1)} of games</span></div>`).join('')}</div>
      </div>
      <div class="panel detail" id="detail">${detailHtml(p)}</div>`;
    Chessground(app.querySelector('#bigboard'), { fen: p.fen, viewOnly: true, orientation: p.colour, lastMove: undefined, drawable: { enabled: false } });
    app.querySelectorAll('[data-go]').forEach(el => el.onclick = () => { cur = sel = Number(el.dataset.go); draw(); });
    app.querySelectorAll('[data-c]').forEach(el => el.onclick = () => { if (el.dataset.c !== '') { cur = sel = Number(el.dataset.c); draw(); } });
    wireDetail(app.querySelector('#detail'), p, (id) => { cur = sel = id; draw(); });
    stats();
  };
  window.addEventListener('keydown', (e) => { if (e.key === 'Escape') { cur = sel = 0; draw(); } if (e.key === 'ArrowUp' && P(cur).parents.length) { cur = sel = P(cur).parents[0]; draw(); } });
  draw();
};

V.C = () => {
  app.className = 'C';
  let filt = 'both';
  const draw = () => {
    const fams = D.openings;
    app.innerHTML = `
      <div class="top">
        <div><div class="score">${pct(D.score.all)}</div><div class="delta">${(D.score.all - D.last_score >= 0 ? '+' : '') + (100 * (D.score.all - D.last_score)).toFixed(1)} since ${D.last_day.slice(5)}</div>
          <div class="split">White ${pct(D.score.white, 0)} · Black ${pct(D.score.black, 0)}</div><div class="split dim">${sessionLine()}</div></div>
        ${chart(D.history)}
      </div>
      <div class="filters">${legend()}<span style="margin-left:auto">show</span>
        ${['both', 'white', 'black'].map(k => `<label><input type="radio" name="f" value="${k}" ${filt === k ? 'checked' : ''}> ${k}</label>`).join('')}
        <span class="dim">· ${D.counts.never} never passed · ${D.counts.relearning} relearning</span></div>
      <div class="blocks">${fams.map(o => {
        const ps = D.positions.filter(p => p.family === o.family && !p.leaf).sort((a, b) => a.ply - b.ply || b.count - a.count);
        return `<div class="block ${o.opted_in ? '' : 'out'}"><h4><span>${o.family} <span class="dim" style="font-weight:400;font-size:.85em">${o.eco}</span></span><span>${pct(o.score, 0)}</span></h4>
          <div class="meta">${o.positions} positions to ply ${o.max_ply} · ${o.never} never passed · W ${pct(o.white, 0)} / B ${pct(o.black, 0)}
            · <a href="#" data-opt="${o.family}">${o.opted_in ? 'opt out' : 'opt in'}</a> · <a href="#" data-resetop="${o.family}" style="color:var(--bad)">reset</a></div>
          <div class="cells">${ps.map(p => `<div class="cell ${filt !== 'both' && p.colour !== filt ? 'hidden' : ''}" data-id="${p.id}" style="background:${colour(p.rec)};${p.colour === 'black' ? 'border:2px solid #000c' : ''}" title="${p.name} · ${lineHtml(p.canonical)} · ${p.rec.never ? 'never passed' : pct(p.rec.R, 0)}"></div>`).join('')}</div></div>`;
      }).join('')}</div>
      ${sel == null ? '' : `<div class="modal" id="modal"><span class="close">×</span><div class="box"><div class="detail" id="detail">${detailHtml(P(sel))}</div></div></div>`}`;
    app.querySelectorAll('input[name=f]').forEach(r => r.onchange = () => { filt = r.value; draw(); });
    app.querySelectorAll('.cell[data-id]').forEach(c => c.onclick = () => { sel = Number(c.dataset.id); draw(); });
    app.querySelectorAll('[data-opt]').forEach(a => a.onclick = async (e) => { e.preventDefault(); const o = D.openings.find(x => x.family === a.dataset.opt); await act(o.opted_in ? 'optout' : 'optin', a.dataset.opt); draw(); });
    app.querySelectorAll('[data-resetop]').forEach(a => a.onclick = async (e) => { e.preventDefault(); if (confirm(`Forget everything about the ${a.dataset.resetop}?`)) { await act('reset_opening', a.dataset.resetop); draw(); } });
    const modal = app.querySelector('#modal');
    if (modal) { modal.onclick = (e) => { if (e.target === modal || e.target.classList.contains('close')) { sel = null; draw(); } };
      wireDetail(modal, P(sel), (id) => { sel = id; draw(); }); }
    stats();
  };
  window.addEventListener('keydown', (e) => { if (e.key === 'Escape' && sel != null) { sel = null; draw(); } });
  draw();
};

// ---------- boot ----------
function render() { V[variant](); }
await load();
if (params.get('sel')) sel = Number(params.get('sel'));
render();
