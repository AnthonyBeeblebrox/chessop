# 37: Full site and throwaway learner

**What to build:** When 300 learner sessions are live, a new session is refused with "chessop is full right now, try again in a few minutes": a page request gets 503 with that sentence and a socket is closed with code 1013; running sessions are unaffected. When an IP has created 30 anonymous learners in the last hour, the next would-be learner becomes a throwaway learner: in memory, default settings, never written to the store, no cookie, gone when its socket closes, counted in the 300. Play works, with the notice "Too many new visitors from your network: this round won't be saved. Try again later or sign in." Settings and progress show the notice instead of saving. Sign-in still works. (Spec §6, G5.)

**Blocked by:** 36

**Status:** done

- [x] At the session ceiling a new visitor gets the 503 page or a 1013 close, and an existing session keeps playing
- [x] The 31st new learner from one IP in an hour plays a full round, receives the notice, gets no cookie and leaves nothing in the store
- [x] A throwaway learner's settings save and progress view show the notice
- [x] A throwaway learner can still sign in
- [x] The cap also covers learners created by a settings save
