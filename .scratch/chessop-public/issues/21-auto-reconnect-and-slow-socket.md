# 21: Auto-reconnect and slow-socket hint

**What to build:** When the socket drops, the play page locks the board, shows a "Reconnecting…" banner over the verdict area and reconnects by itself: after 1 s, 2 s, 5 s, then every 10 s, and at once when the tab becomes visible or the browser reports it is online. The new socket gets a fresh round and one line says "Connection was lost; that round wasn't counted". A closed socket abandons the round on the server: nothing written, no miss charged. After 1 s with no reply to a move the page shows "waiting for the server…"; after about 10 s of silence it closes the socket and reconnects. A close with code 1008 or 1013 is not retried and keeps the manual "connection lost, reload" state. No application heartbeat. (Spec §7, G5.)

**Blocked by:** None (can start immediately)

**Status:** done

- [x] A socket closed mid-round writes no round, record or miss (wire test)
- [x] The page reconnects with the stated backoff and on visibility/online events, and starts a fresh round
- [x] The banner, the "wasn't counted" line and the "waiting for the server…" hint appear as described (verified by hand)
- [x] Close codes 1008 and 1013 do not trigger a retry
