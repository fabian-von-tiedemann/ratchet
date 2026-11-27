# D-2026-11-23-adopt-mode-no-copied-row: adopt mode writes no copied row

- Date: 2026-11-23
- Decided by: Ratchet's maintainer
- Kind: decision (D)
- Replaces: none
- Amends: D-2026-11-22-second-redraw (the floor of adopt mode in step 9b)
- Ends: none

## Question

Background. Step 9b of [D-2026-11-22-second-redraw](D-2026-11-22-second-redraw.md) gave `checks/init.py` an adopt mode for a repo that already has an instruction file of its own, which "writes only `register.json`, with one copied row". The copied row is `ratchet.register-on-top`, the floor that made the register check pass. The adoption report of a real project on 0.11 showed that the row is false where the project's own instruction file governs: a register that holds rules by reference neither lists every rule in force nor takes precedence. The control room put the choices from that report to the maintainer in its chat on 2026-11-23. Choice 3, original, in Swedish:

> 3. **Skriv inte `register-on-top` i adopt-läget.** Den raden säger något som inte är sant när projektets egen fil gäller. Kontrollen går igenom utan den. **Mitt råd: ja.**

Translation:

> 3. **Do not write `register-on-top` in adopt mode.** That row says something that is not true when the project's own file governs. The check passes without it. **My recommendation: yes.**

## Answer

Original, in Swedish, 2026-11-23:

> ja på dina råd

Translation:

> yes to your recommendations

## What follows

- Adopt mode in `checks/init.py` writes no copied row. Its first run writes nothing, and prints the rows by reference and their marker lines.
- `register.json` is written only with the rows the project chooses, named with `--adopt <key>`, once for each rule whose marker line the project has put in its own file, and only if the register passes `check_register.py`. `check_register.py` is not loosened: a register that adopts nothing still fails.
- This replaces "one copied row" as the floor of adopt mode in step 9b of [D-2026-11-22-second-redraw](D-2026-11-22-second-redraw.md). That decision stands as written otherwise, and is not edited.
- The pull request that adds `checks/run_pinned.py` carries the change, and `CHANGELOG.md` and `checks/README.md` name this decision.
