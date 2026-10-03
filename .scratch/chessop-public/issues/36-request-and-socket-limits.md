# 36: Request and socket limits

**What to build:** One abusive client cannot exhaust the box. A limits module of in-memory counters, hosted only, using the injected clock, lost on restart, dropping counters once their window passes. The client is its IPv4 address or IPv6 /64 prefix from the forwarded header; IPs are never logged. HTTP requests on non-static routes: 120 per minute per IP. Settings saves: 10 per minute per learner. Data downloads: 5 per hour per learner. A 429 carries `Retry-After` and a plain page "Slow down: try again in N seconds." `/healthz` and static files are exempt. WebSocket messages: 5 per second with a burst of 20 and 1 KB maximum per connection, closing with code 1008 past it. Open sockets: 10 per learner and 40 per IP, the new socket refused past it. (Spec §6.)

**Blocked by:** 28, 33

**Status:** done

- [x] Each HTTP limit answers 429 with `Retry-After` and the plain page once passed, and recovers when the window passes (injected clock)
- [x] `/healthz` and static files are never limited
- [x] A socket sending too fast or a message over 1 KB is closed with 1008
- [x] The 11th socket of a learner and the 41st of an IP are refused
- [x] Two IPv6 addresses in one /64 count as one client
- [x] None of the limits applies in local mode
