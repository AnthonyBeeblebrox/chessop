# Abuse and limits on the hosted site

Type: grilling
Status: resolved
Blocked by: 
Map: [chessop in public](../map.md)

## Question

The magic-link email limits are already set (Sign-in with Lichess and email), and the client IP is trusted from Caddy's `X-Forwarded-For` (Switching chessop serve into hosted mode). Decide the rest:
- which routes and WebSocket messages get rate limits, with what limits per IP or per learner, and what a limited visitor sees;
- a cap on anonymous learners created per IP, since one is created at each first round without a cookie (From one learner to many);
- whether anonymous learners with only a round or two are purged sooner than the 12 months set in Legal pages and data rights;
- where the limits live: in-process counters in chessop, Caddy, or fail2ban reading journald. Limit state is lost on restart unless stored.

## Answer

Grilled 2026-09-30. No ADR (every number is easy to reverse); no glossary change (the throwaway learner is a limit's fallback, not a domain concept). Code facts from "From one learner to many": a learner session holds ~3 MB for 30 idle minutes, a new settings key costs 200–400 ms (repertoire + ledger, LRU 16), band graphs are bounded at 8.

- **Purpose**: protect the €4.49 box (memory, CPU, disk; TEM already capped by Sign-in with Lichess and email). No anti-scraping or anti-bot work; the legal notice's "no misuse" line stays a legal lever only.
- **Where**: in-process counters in one `limits` module, active only under `--hosted`, in memory, lost on restart (accepted). Not Caddy (third-party plugin, custom build) nor fail2ban (would need IPs in logs, ruled out by Legal pages and data rights).
- **Client identity**: the IP from `X-Forwarded-For` (trusted from 127.0.0.1 only); IPv4 address, or IPv6 /64 prefix. Counters are dropped once their window passes.
- **Live sessions**: at most 300 server-wide (~900 MB), constant in code. Past it a new session is refused with "chessop is full right now, try again in a few minutes"; running sessions are unaffected. The Latency fog may revisit the number.
- **New anonymous learners**: at most 30 per IP per hour (loose for classrooms and CGNAT). Past it, `current_learner` hands out a **throwaway learner**: in memory, default settings (band 1500+), never written to SQLite, no cookie, gone when its socket closes, counted in the 300. Play works; a notice says "Too many new visitors from your network: this round won't be saved. Try again later or sign in." Settings and progress pages show the notice instead of saving. Sign-in still works within the email limits.
- **Quick purge**: an anonymous learner with fewer than 5 rounds and no request for 30 days is deleted, by the same daily job as the 12-month purge. The privacy notice's anonymous-retention line gains that clause. Accounts unaffected.
- **WebSocket**: per connection 5 messages/s, burst 20, 1 KB max message; a breach closes with code 1008 and the page shows its "connection lost, reload" state. At most 10 open sockets per learner and 40 per IP; beyond, the new socket is refused.
- **HTTP**: 120 requests/min per IP on all non-static routes; 10 settings saves/min per learner; 5 `/data` downloads/hour per learner. A limit answers 429 with `Retry-After` and a plain page "Slow down: try again in N seconds." `/healthz` and static files are exempt. Email limits unchanged.
- **Handed on**: the quick-purge job → Deploying and operating fog; whether 300 sessions and the round-end lock hold together → Latency fog.
