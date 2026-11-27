# D-2026-11-27-no-sparse-fetch: drop the sparse fetch, and take up a GitHub Action after 1.0

- Date: 2026-11-27
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Earlier the same day, [D-2026-11-27-maintain-apart](D-2026-11-27-maintain-apart.md) decided to move Ratchet's own maintenance into `maintain/`, and then to let an adopter fetch only what it needs. The control room explained that a sparse checkout leaves out files but still downloads the whole pinned history, since `run_pinned.py` reads the check from git's objects. The maintainer then asked, in Swedish:

> fattar inte, är det här enligt best practise?

Translation: I don't get it, is this best practice?

The control room answered that pinning to an exact commit is best practice, and so is the split into `maintain/`, but that a sparse checkout is not. It is an uncommon trick that solves a problem that hardly exists, since `.ratchet/` is a tool folder that is not committed, as `node_modules` is. It then put this:

> **Mitt råd:**
> 1. **Behåll PR 1**, flytten till `maintain/`. Den byggs nu. *Mitt råd: ja.*
> 2. **Stryk PR 2**, den glesa hämtningen. *Mitt råd: stryk den.* Vinsten är liten, och den lägger till ett ovanligt trick. Beslutet från i dag ändras då i den punkten, och jag skriver ändringen i beslutsfilen.
> 3. **En GitHub Action i stället för klonen i CI**: ta frågan efter 1.0, tillsammans med frågan om ett paket. *Mitt råd: vänta.*
>
> Svara till exempel **"ja på dina råd"**.

Translation:
1. Keep PR 1, the move to `maintain/`. It is being built now. *My advice: yes.*
2. Drop PR 2, the sparse fetch. *My advice: drop it.* The gain is small, and it adds an uncommon trick. Today's decision then changes on that point, and I write the change in the decision file.
3. A GitHub Action in place of the clone in CI: take the question up after 1.0, together with the question of a package. *My advice: wait.*

Answer, for example, "yes to your advice".

## Answer

> ja på dina råd

Translation: yes to your advice.

## What follows

- Point 2 of D-2026-11-27-maintain-apart is withdrawn. The template and the docs keep fetching the whole repo at the pinned commit.
- Point 1 of that decision stands: the move to `maintain/`.
- Whether an adopter's CI uses Ratchet as a GitHub Action, pinned by commit, is taken up after 1.0 with the question of a package.
