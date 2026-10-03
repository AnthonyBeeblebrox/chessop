// The play page. No chess logic here: drags are restricted to the server's `dests`, a drop sends
// `move`, and the page renders what comes back. Nothing is revealed until `round_over`.
import { Chessground } from '/static/chessground/chessground.min.js';

const $ = (id) => document.getElementById(id);
const sq = (uci) => [uci.slice(0, 2), uci.slice(2, 4)];
const arrow = (uci, brush) => ({ orig: sq(uci)[0], dest: sq(uci)[1], brush });

let side = 'white';
let playing = false;   // a round is in flight: its `round_over` has not come
let waiting = false;   // a round is over and the page waits for the learner to ask for the next one
let shown = null;      // the last position the server sent, to put back after an `error`
let since = null;      // the Score's change since the last round played, until this tab's first round ends

// The Score as a percentage with one decimal, and a change in it with its sign.
const pct = (x) => `${x.toFixed(1)} %`;
const signed = (x) => `${x < 0 ? '−' : '+'}${Math.abs(x).toFixed(1)}`;

// A local ISO date as the banner names it: "today", a weekday within the week, else the date.
function dayName(iso) {
  const day = new Date(`${iso}T00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const ago = Math.round((today - day) / 864e5);
  if (ago <= 0) return 'today';
  if (ago < 7) return day.toLocaleDateString(undefined, { weekday: 'short' });
  return day.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function showScore(value) {
  $('score').textContent = pct(value);
  $('since').textContent = since ? `(${signed(since.delta)} since ${dayName(since.day)})` : '';
}

// Sound and animation as persisted (spec §11); `m`, or the header's sound icon on a phone,
// toggles sound and tells the server.
let soundOn = document.body.dataset.sound === 'true';
function toggleSound() {
  soundOn = !soundOn;
  send({ type: 'sound', on: soundOn });
  $('sound').textContent = soundOn ? '🔊' : '🔇';
  $('sound').setAttribute('aria-pressed', String(soundOn));
}
$('sound').addEventListener('click', toggleSound);
const animationMs = Math.min(100, Math.max(0, Number(document.body.dataset.animationMs ?? 100)));

// Lichess's `sfx` set. The set's Error is a link to the non-free standard set, so a miss plays
// its Defeat. Each play restarts the one element of its sound.
const sounds = Object.fromEntries(['Move', 'Capture', 'Check', 'Victory', 'Defeat']
  .map((n) => [n, Object.assign(new Audio(`/static/sound/${n}.mp3`), { preload: 'auto' })]));
function playSound(name) {
  if (!soundOn) return;
  const a = sounds[name];
  a.currentTime = 0;
  a.play().catch(() => {});  // blocked until the page has had a user gesture: silence, no error
}
// A move's sounds as Lichess plays them, read off its SAN: Capture or Move, plus Check.
function moveSound(san) {
  playSound(san.includes('x') ? 'Capture' : 'Move');
  if (/[+#]/.test(san)) playSound('Check');
}
const REPLY_GAP_MS = 120;  // so the opponent's reply is heard as a second move
let replyGap = 0;          // the round-end sound waits for the last move's own

const cg = Chessground($('board'), {
  animation: { enabled: animationMs > 0, duration: animationMs },
  coordinatesOnSquares: true,  // every square names itself, e4 on e4
  movable: { free: false, showDests: true, events: { after: (from, to) => ask({ type: 'move', from, to }) } },
  premovable: { enabled: false },
  drawable: { enabled: false },
});

// Chessground keeps the board's place on the page until a scroll or a resize. On a phone the
// banner over the board grows when the opening name wraps, and the notice shows and hides, which
// moves the board without either: forget the place as chessground does then, or taps miss.
const boardMoved = new ResizeObserver(() => cg.state.dom.bounds.clear());
boardMoved.observe($('banner'));
boardMoved.observe($('notice'));

const lockBoard = () => cg.set({ movable: { color: undefined, dests: new Map() } });

function showPosition(m, lastUci) {
  shown = { m, lastUci };
  cg.set({
    fen: m.fen, turnColor: side, orientation: side,
    lastMove: lastUci ? sq(lastUci) : undefined,
    movable: { color: side, dests: new Map(Object.entries(m.dests)) },
  });
  // The one thing shown before the learner moves: the move set aside this turn, in yellow.
  cg.setAutoShapes(m.forced_uci ? [arrow(m.forced_uci, 'yellow')] : []);
}

function banner(m) {
  $('side').className = `badge ${side}`;
  $('side').textContent = side === 'white' ? '♔ WHITE' : '♚ BLACK';
  $('name').textContent = m.opening ?? '';
  $('forced').textContent = m.forced ? `not ${m.forced} this time` : '';
}

// Plain text as paragraphs, one per blank-line-separated block.
function paragraphs(el, text) {
  el.replaceChildren(...text.split('\n\n').map((t) => Object.assign(document.createElement('p'), { textContent: t })));
}

// The Explanation under the verdict strip: the lead, the full text behind "more" (it grows
// downward, the board above never moves), the borrowed-text label, and the licence footer.
function showExplanation(e) {
  $('explanation').hidden = !e;
  if (!e) return;
  $('borrowed').textContent = e.borrowed_from ? `No text of its own: the text for ${e.borrowed_from}` : '';
  $('borrowed').hidden = !e.borrowed_from;
  paragraphs($('lead'), e.lead);
  paragraphs($('full'), e.text);
  $('lead').hidden = false;
  $('full').hidden = true;
  $('more').hidden = e.text === e.lead;
  $('more').textContent = 'more';
  $('source').href = e.url;
  $('source').title = e.title;
}
$('more').addEventListener('click', () => {
  const open = $('full').hidden;
  $('full').hidden = !open;
  $('lead').hidden = open;
  $('more').textContent = open ? 'less' : 'more';
});

function onRound(m) {
  side = m.side;
  playing = true;
  if (m.side === 'black') playSound('Move');  // the opponent's first move is already on the board
  setWaiting(false);
  if (m.score_since) since = m.score_since;
  // The one-time snapshot notice stays up for this round only.
  $('notice').textContent = m.notice ?? '';
  $('notice').hidden = !m.notice;
  $('verdict').className = 'verdict';
  $('verdict').textContent = '';
  $('verdict-help').hidden = true;
  showExplanation(null);
  banner(m);
  showScore(m.score);
  showPosition(m, null);
}

function onMoved(m) {
  moveSound(m.played.san);
  replyGap = m.reply ? REPLY_GAP_MS : 0;
  if (m.reply) setTimeout(() => moveSound(m.reply.san), replyGap);
  if (Object.keys(m.dests).length === 0) {
    // The round is over: freeze the board on the last move, the reveal follows in `round_over`.
    const last = m.reply?.uci ?? m.played.uci;
    cg.set({ fen: m.fen, lastMove: sq(last) });
    lockBoard();
    return;
  }
  banner(m);
  showPosition(m, m.reply?.uci);
}

function onOver(m) {
  const { main, played } = m.reveal;
  $('forced').textContent = '';
  $('name').textContent = m.opening ?? '';
  // Each main move carries its rank by popularity (1 the most played), the set-aside one too.
  const ranked = (x, brush) => ({ ...arrow(x.uci, brush), label: { text: String(main.indexOf(x) + 1) } });
  const shapes = main.filter((x) => x.uci !== played?.uci).map((x) => ranked(x, 'green'));
  const setAside = main.find((x) => x.uci === played?.uci);
  if (setAside) shapes.push(ranked(setAside, 'yellow'));
  else if (played) shapes.push(arrow(played.uci, 'red'));
  cg.setAutoShapes(shapes);
  const mains = main.map((x) => x.san).join(' · ');
  const [big, rest, cls] =
    m.outcome === 'miss' ? [`✗ ${played.san}`, `main: ${mains}`, 'bad']
    : m.outcome === 'forced' ? [`${played.san} was set aside`, `main: ${mains}`, 'warn']
    : [`✓ ${m.plies} plies`, m.opening ?? '', 'ok'];
  const span = (className, text) => Object.assign(document.createElement('span'), { className, textContent: text });
  const hint = span('hint', ' next round');
  hint.prepend(Object.assign(document.createElement('kbd'), { textContent: 'space' }));
  const { value, delta } = m.score;
  const score = span('score', `· ${pct(value)}${delta === null ? '' : ` (${signed(delta)})`}`);
  $('verdict').replaceChildren(span('big', big), span('', rest ? `· ${rest}` : ''), score, hint);
  since = null;
  showScore(value);
  $('verdict').className = `verdict show ${cls}`;
  $('verdict-help').hidden = false;
  showExplanation(m.explanation);
  // Nothing extra on `forced`.
  if (m.outcome !== 'forced') setTimeout(() => playSound(m.outcome === 'success' ? 'Victory' : 'Defeat'), replyGap);
  playing = false;
  setWaiting(true);
  note = null;
  showStatus();
}

// The Next round button shows exactly while the page waits for it.
function setWaiting(on) {
  waiting = on;
  $('next').hidden = !on;
}

function next() {
  if (!waiting) return;
  setWaiting(false);
  ask({ type: 'next' });
}
window.addEventListener('keydown', (e) => {
  if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); next(); }
  else if (e.key === 'm' && !e.ctrlKey && !e.metaKey && !e.altKey) toggleSound();
});
$('verdict').addEventListener('click', next);
$('next').addEventListener('click', next);

function receive(m) {
  stopWaiting();
  if (m.type === 'round') {
    failures = 0;
    onRound(m);
    // After a drop, the fresh round says once that the cut one was not counted (spec §7).
    note = cutRound ? "Connection was lost; that round wasn't counted" : null;
    cutRound = false;
    showNote();
  }
  else if (m.type === 'moved') onMoved(m);
  else if (m.type === 'round_over') onOver(m);
  else if (m.type === 'error' && shown && !waiting) showPosition(shown.m, shown.lastUci);
}

// The socket (public spec §7). A dropped one abandons its round on the server; the page locks
// the board, says so over the verdict strip and opens a new socket by itself, which gets a fresh
// round: after 1 s, 2 s, 5 s, then every 10 s, and at once when the tab is shown again or the
// browser is back online. A close for the message rate (1008) or a full server (1013) is not
// retried: the learner reloads by hand. No heartbeat: a move left unanswered is what tells a dead
// socket, hinted after 1 s and given up after 10 s; a new socket gets as long to bring its round.
const URL_WS = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`;
const BACKOFF_MS = [1000, 2000, 5000, 10000];  // the last repeats
const HINT_MS = 1000;
const SILENCE_MS = 10000;
const NO_RETRY = new Set([1008, 1013]);

let ws = null;            // the open or opening socket; null while disconnected
let failures = 0;         // sockets in a row that brought no round
let retryTimer = null;    // the pending reconnect
let gaveUp = false;       // closed with a code that is not retried
let cutRound = false;     // a round was in flight when the socket dropped
let note = null;          // the line about the cut round, up until the fresh round ends
let statusKind = null;    // what the strip over the verdict shows: down, dead, slow, note or nothing
let hintTimer = null;     // shows "waiting for the server…" when the answer is late
let silenceTimer = null;  // gives the socket up when the answer never comes

// The strip over the verdict; no kind hides it.
function showStatus(kind = null, text = '') {
  const el = $('status');
  statusKind = kind;
  el.hidden = !kind;
  el.className = `status ${kind ?? ''}`;
  el.textContent = text;
  if (kind === 'dead') {
    const reload = Object.assign(document.createElement('button'), { type: 'button', textContent: 'reload' });
    reload.addEventListener('click', () => location.reload());
    el.append(' ', reload);
  }
}
const showNote = () => (note ? showStatus('note', note) : showStatus());

function send(o) {
  if (ws?.readyState !== WebSocket.OPEN) return false;
  ws.send(JSON.stringify(o));
  return true;
}

// Send a message the server answers, and wait for the answer.
function ask(o) {
  if (!send(o)) return;
  stopWaiting();
  hintTimer = setTimeout(() => showStatus('slow', 'waiting for the server…'), HINT_MS);
  silenceTimer = setTimeout(giveUp, SILENCE_MS);
}

// Something came (or the socket went): no answer is awaited any more.
function stopWaiting() {
  clearTimeout(hintTimer);
  clearTimeout(silenceTimer);
  hintTimer = silenceTimer = null;
  if (statusKind === 'slow') showNote();
}

function connect() {
  clearTimeout(retryTimer);
  retryTimer = null;
  const sock = new WebSocket(URL_WS);
  ws = sock;
  // The browser's time zone, which the server keeps only while the learner has none.
  sock.onopen = () => { if (sock === ws) send({ type: 'hello', tz: Intl.DateTimeFormat().resolvedOptions().timeZone }); };
  sock.onmessage = (e) => { if (sock === ws) receive(JSON.parse(e.data)); };
  sock.onclose = (e) => { if (sock === ws) lost(e.code); };
  silenceTimer = setTimeout(giveUp, SILENCE_MS);  // until its round comes
}

function lost(code) {
  ws = null;
  stopWaiting();
  cutRound ||= playing;
  playing = false;
  setWaiting(false);
  note = null;
  lockBoard();  // until a round comes
  if (NO_RETRY.has(code)) {
    gaveUp = true;
    showStatus('dead', code === 1013 ? 'chessop is full right now, try again in a few minutes.' : 'Connection lost.');
    return;
  }
  showStatus('down', 'Reconnecting…');
  retryTimer = setTimeout(connect, BACKOFF_MS[Math.min(failures, BACKOFF_MS.length - 1)]);
  failures += 1;
}

// Ten seconds without an answer: the socket is taken for dead, without waiting for a close
// handshake that may never come.
function giveUp() {
  const sock = ws;
  lost(null);
  sock?.close();
}

function reconnectNow() {
  if (ws || gaveUp) return;
  connect();
}
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') reconnectNow(); });
window.addEventListener('online', reconnectNow);

connect();

// The service worker, whose scope is the whole site; the other pages carry no script (public spec §8).
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
