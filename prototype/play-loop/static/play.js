// PROTOTYPE (ticket 10): three variants of one fast round on the real four-message socket.
//   A "Bare board": nothing but the board; reveal as arrows; miss = red pulse + arrows, auto-next; success auto-next.
//   B "Ledger": board + running move ledger with the accepted set as chips after every learner move; miss stays on
//               screen until Space/click; pass kind (counted/sure/relearning) and forced-exploration shown as chips.
//   C "Pure recall" (WINNER): no mid-round reveal; at round end the solution is drawn as arrows on the board, a verdict strip
//               under the board names the played move and the main moves, and Space starts the next round. Forced exploration
//               is announced in the banner. Big banner names the side and the opening.
import { Chessground } from '/static/chessground/chessground.min.js';

const VARIANTS = { A: 'Bare board', B: 'Ledger', C: 'Pure recall' };
const params = new URLSearchParams(location.search);
const variant = VARIANTS[params.get('variant')] ? params.get('variant') : 'C';   // C won (learner's reaction, 2026-09-12)
const ANIM = Number(params.get('anim') ?? 100);
const DEMO = params.get('demo');            // screenshot hooks: demo=pass plays a main move, demo=miss a wrong one; hold=1 stops auto-next
const HOLD = params.get('hold') === '1';

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
const showStats = (s) => { if (s) document.getElementById('vstats').textContent =
  `${s.rounds} rounds · ${s.rate == null ? '-' : Math.round(s.rate * 100) + '%'} · seen ${s.positions_seen}/${s.positions_total} · need ${s.mean_need}`; };

// ---------- shared plumbing: socket + board ----------
const ws = new WebSocket(`ws://${location.host}/ws`);
const send = (o) => ws.send(JSON.stringify(o));
let cg, side, tMove = 0;
const sq = (uci) => [uci.slice(0, 2), uci.slice(2, 4)];
const toDests = (d) => new Map(Object.entries(d));
function mountBoard(el, onMove) {
  cg = Chessground(el, { animation: { duration: ANIM }, movable: { free: false, showDests: true, events: { after: (o, d) => { tMove = performance.now(); onMove(o, d); } } },
    draggable: { showGhost: true }, premovable: { enabled: false }, drawable: { enabled: false } });
}
function showPosition(m, lastUci) {
  cg.set({ fen: m.fen, turnColor: side, orientation: side, lastMove: lastUci ? sq(lastUci) : undefined,
    movable: { color: side, dests: toDests(m.dests || {}) } });
}
const arrows = (moves, brush) => moves.map(x => ({ orig: sq(x.uci)[0], dest: sq(x.uci)[1], brush }));

// ---------- variants ----------
const app = document.getElementById('app');
const V = {};

V.A = () => {
  app.className = 'A';
  app.innerHTML = `<div class="board" id="b"></div><div class="corner"><span class="badge" id="side"></span><span class="dim" id="name"></span></div><div class="toast" id="toast"></div>`;
  const $ = (id) => document.getElementById(id);
  const boardEl = $('b');
  mountBoard(boardEl, (o, d) => send({ type: 'move', from: o, to: d }));
  const toast = (t, ms = 1200) => { $('toast').textContent = t; $('toast').classList.add('show'); setTimeout(() => $('toast').classList.remove('show'), ms); };
  const forcedNote = (m) => { if (m.forced) toast(`not ${m.forced} this time`); };
  return {
    onRound(m) { boardEl.classList.remove('glow-bad', 'glow-ok'); $('side').className = 'badge ' + side; $('side').textContent = side.toUpperCase(); $('name').textContent = m.opening;
      showPosition(m, null); cg.setAutoShapes([]); forcedNote(m); },
    onMoved(m) {
      if (m.verdict === 'miss') return;
      showPosition(m, m.reply?.uci); $('name').textContent = m.opening;
      cg.setAutoShapes(arrows(m.revealed, 'green'));   // main moves of the position just left, drawn instantly
      forcedNote(m);
    },
    onOver(m) {
      showStats(m.stats);
      if (m.outcome === 'miss') {
        cg.set({ fen: m.fen, lastMove: sq(m.missed.uci), movable: { color: undefined } });
        cg.setAutoShapes([...arrows(m.reveal, 'green'), { orig: sq(m.missed.uci)[0], dest: sq(m.missed.uci)[1], brush: 'red' }]);
        boardEl.classList.add('glow-bad');
        if (!HOLD) setTimeout(() => send({ type: 'next' }), 900);   // auto-restart: the miss is glimpsed, not studied
      } else {
        boardEl.classList.add('glow-ok');
        if (!HOLD) setTimeout(() => send({ type: 'next' }), 250);
      }
    },
  };
};

V.B = () => {
  app.className = 'B';
  app.innerHTML = `<div class="board" id="b"></div><div class="side">
    <div class="head"><span class="badge" id="side"></span><span class="name" id="name"></span><span class="dim" id="ply"></span></div>
    <div class="ledger" id="ledger"></div>
    <button class="nextbtn" id="nextbtn" hidden>Next round <kbd>space</kbd></button>
    <div class="strip" id="strip"></div></div>`;
  const $ = (id) => document.getElementById(id);
  mountBoard($('b'), (o, d) => send({ type: 'move', from: o, to: d }));
  let plyNo = 0, waiting = false;
  const label = (n) => (n % 2 ? `${(n + 1) / 2}.` : `${n / 2}...`);
  const row = (cls, num, move, rest = '') => { const r = document.createElement('div'); r.className = 'row ' + cls;
    r.innerHTML = `<span class="dim">${num}</span><span>${move}</span><span>${rest}</span>`; $('ledger').appendChild(r); r.scrollIntoView({ block: 'nearest' }); return r; };
  const chips = (m, played, forced) => m.revealed.map(x => `<span class="chip ${x.san === played ? 'played' : ''} ${x.san === forced ? 'forced' : ''}">${x.san}${x.san === forced ? ' ✕' : ''}</span>`).join('');
  const oppRow = (m) => { plyNo++; row('opp', label(plyNo), m.reply.san, `<span class="kind">opponent</span>`); };
  const restart = () => { if (!waiting) return; waiting = false; $('nextbtn').hidden = true; send({ type: 'next' }); };
  $('nextbtn').onclick = restart;
  window.addEventListener('keydown', (e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); restart(); } });
  const head = (m) => { $('name').textContent = m.opening; $('ply').textContent = `ply ${m.ply}${m.relearning ? ' · relearning' : ''}${m.forced ? ` · forced: not ${m.forced}` : ''}`; };
  return {
    onRound(m) { $('ledger').innerHTML = ''; plyNo = 0; $('side').className = 'badge ' + side; $('side').textContent = `you are ${side}`; head(m); showPosition(m, null);
      if (m.path.length) { plyNo = 1; row('opp', '1.', m.path[0], `<span class="kind">opponent</span>`); } },
    onMoved(m) {
      plyNo++;
      if (m.verdict === 'miss') { row('miss', label(plyNo), `<span class="chip missed">${m.played.san}</span>`, chips(m, null, m.forced)); return; }
      row('', label(plyNo), m.played.san, chips(m, m.played.san, m.forced) + `<span class="kind">${m.pass_kind}</span>`);
      if (m.reply) { oppRow(m); showPosition(m, m.reply.uci); head(m); }
    },
    onOver(m) {
      showStats(m.stats);
      $('strip').textContent = `session: ${m.stats.rounds} rounds, ${Math.round((m.stats.rate ?? 0) * 100)}% success, ${m.stats.relearning} positions relearning`;
      if (m.outcome === 'miss') cg.set({ fen: m.fen, lastMove: sq(m.missed.uci), movable: { color: undefined } });
      else row('done', '', `line complete · ${m.path.length} plies`, m.opening);
      waiting = true; $('nextbtn').hidden = false;
    },
  };
};

V.C = () => {
  app.className = 'C';
  app.innerHTML = `<div class="banner"><span class="badge" id="side"></span><span class="name" id="name"></span><span class="forced" id="forced"></span></div>
    <div class="board"><div id="b"></div></div>
    <div class="verdict" id="verdict"></div>
    <div class="counter" id="counter"></div>`;
  const $ = (id) => document.getElementById(id);
  mountBoard($('b'), (o, d) => send({ type: 'move', from: o, to: d }));
  let waiting = false;
  const dismiss = () => { if (!waiting) return; waiting = false; $('verdict').className = 'verdict'; send({ type: 'next' }); };
  window.addEventListener('keydown', (e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); dismiss(); } });
  $('verdict').onclick = dismiss;
  const banner = (m) => { $('side').className = 'badge ' + side; $('side').textContent = side === 'white' ? '♔ WHITE' : '♚ BLACK'; $('name').textContent = m.opening;
    $('forced').textContent = m.forced ? `not ${m.forced} this time` : ''; };
    // the set-aside move is drawn yellow on the board before the learner moves (learner's request); nothing else is revealed mid-round
    const setAside = (m) => cg.setAutoShapes(m.forced_uci ? [{ orig: sq(m.forced_uci)[0], dest: sq(m.forced_uci)[1], brush: 'yellow' }] : []);
    return {
    onRound(m) { banner(m); showPosition(m, null); setAside(m); },
    onMoved(m) { if (m.verdict !== 'pass') return; showPosition(m, m.reply?.uci); banner(m); setAside(m); },
    onOver(m) {
      showStats(m.stats); $('counter').textContent = `${m.stats.success}/${m.stats.rounds}`;
      $('forced').textContent = '';
      cg.set({ fen: m.fen, lastMove: m.missed ? sq(m.missed.uci) : undefined, movable: { color: undefined } });
      const mains = m.reveal.map(x => x.san).join('  ·  ');
      if (m.outcome === 'miss') {
        cg.setAutoShapes([...arrows(m.reveal, 'green'), { orig: sq(m.missed.uci)[0], dest: sq(m.missed.uci)[1], brush: 'red' }]);
        $('verdict').innerHTML = `<span class="big">✗ ${m.missed.san}</span> main: ${mains} <span class="hint"><kbd>space</kbd> next round</span>`;
        $('verdict').className = 'verdict show bad';
      } else if (m.outcome === 'forced') {
        cg.setAutoShapes([...arrows(m.reveal.filter(x => x.san !== m.missed.san), 'green'), { orig: sq(m.missed.uci)[0], dest: sq(m.missed.uci)[1], brush: 'yellow' }]);
        $('verdict').innerHTML = `<span class="big">${m.missed.san} was set aside</span> this time: ${mains.replace(m.missed.san, '')} <span class="hint"><kbd>space</kbd> next round</span>`;
        $('verdict').className = 'verdict show warn';
      } else {
        cg.setAutoShapes(arrows(m.reveal, 'green'));
        $('verdict').innerHTML = `<span class="big">✓ ${m.path.length} plies</span> ${m.opening} <span class="hint"><kbd>space</kbd> next round</span>`;
        $('verdict').className = 'verdict show ok';
      }
      waiting = true;
    },
  };
};

// ---------- dispatch ----------
const v = V[variant]();
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.type === 'round') { side = m.side; v.onRound(m);
    if (DEMO) setTimeout(() => { let mv = side === 'white' ? 'e2e4' : ({ e4: 'e7e6', d4: 'd7d5', Nf3: 'g8f6' })[m.path[0]];
      if (DEMO === 'miss') mv = side === 'white' ? 'a2a3' : 'a7a6';
      cg.move(mv.slice(0, 2), mv.slice(2, 4)); send({ type: 'move', from: mv.slice(0, 2), to: mv.slice(2, 4) }); }, 300); }
  else if (m.type === 'moved') { m.rtt = Math.round(performance.now() - tMove); console.log('moved', m.verdict, m.played.san, 'server', m.ms, 'ms; drop→reply', m.rtt, 'ms'); v.onMoved(m); }
  else if (m.type === 'round_over') { console.log('round_over', m.outcome, m.path.join(' ')); v.onOver(m); }
};
