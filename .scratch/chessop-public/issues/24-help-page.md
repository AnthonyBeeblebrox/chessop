# 24: Help page

**What to build:** `/help`, titled "How chessop works", in both modes: a list of sections at the top, then one anchored section each for how a round works, the verdict (`#verdict`), "Not X this time", Score (`#score`), change since your last day, as White and as Black, known/learning/never passed, this session, the sparkline, the openings table, move colours and rating band. The Known section quotes the running sure threshold and the session section the running target range. On progress, each figure's label is a dotted-underline link to its section. On play, the corner links gain "help", and after a round a small line under the verdict reads "what does this mean? · what is the Score?". A closing line points to the repository for questions (the contact address is added in hosted mode by ticket 34). No popovers, no walkthrough. Port from branch `prototype/help`, variant B; its copy is the starting draft. Wording follows the glossary. (Spec §9.)

**Blocked by:** 19

**Status:** done

- [x] `/help` is served in local mode with every listed section and anchor
- [x] The quoted sure threshold and target range change when the running parameters change
- [x] Each progress label listed in the spec links to its help section
- [x] The play page has the help corner link and the two post-round links
- [x] The copy uses the glossary's terms and none of its Avoid words

## Comments

- The repository address the closing line links to is not given by the spec or any ticket; it is one constant, `REPOSITORY` in `src/chessop/app.py`, set to `https://github.com/afillion0/chessop` as a guess. Correct it there once the public repository exists (runbook owner step).
- The target range is the `TARGET` constant (displayed only, not a setting), shared by progress and help.
