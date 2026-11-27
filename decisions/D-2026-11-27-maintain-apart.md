# D-2026-11-27-maintain-apart: keep Ratchet's own maintenance apart from what an adopter runs, and fetch only what an adopter needs

- Date: 2026-11-27
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

The maintainer asked, in Swedish, what it means that a check stops a merge, whether Ratchet's own maintenance should be kept more clearly apart, and whether Ratchet should rather be an npm package, since most people do not care about the code that runs and develops Ratchet. The control room answered the first question, then put this to the maintainer:

> **Mina råd:**
> 1. **Flytta underhållet till `maintain/`**, som en egen PR med granskad plan, efter det som ligger i kön nu. *Mitt råd: ja.*
> 2. **Hämta bara det projekt behöver** genom att låta mallen och `init.py` hämta enbart `checks/`, `templates/` och `ratchet.json`. *Mitt råd: ja, direkt efter punkt 1.*
> 3. **Ett paket på PyPI eller npm**: ta upp frågan efter 1.0, om användare ber om det. *Mitt råd: vänta.*
>
> Svara till exempel **"ja på dina råd"**. Jag lägger då in punkt 1 och 2 i ordningen före receptet för utvärderingen av skills.

Translation:
1. Move the maintenance to `maintain/`, as a PR of its own with a reviewed plan, after what is in the queue now. *My advice: yes.*
2. Fetch only what a project needs, by letting the template and `init.py` fetch only `checks/`, `templates/` and `ratchet.json`. *My advice: yes, right after point 1.*
3. A package on PyPI or npm: take the question up after 1.0, if users ask for it. *My advice: wait.*

Answer, for example, "yes to your advice". I will then put points 1 and 2 into the order, before the recipe for the evaluation of skills.

Before the advice, the control room gave its reasons. An adopter checks out the whole repo at a pinned commit, so scripts it never runs, such as `release.py`, `watch_sources.py` and `form_age.py`, come along. A package registry would add an account, a publishing token and a new chain to trust, where today the adopter runs exactly the commit it pinned. Ratchet is Python with no dependencies, so an npm package would need both Node and Python.

## Answer

> ja på dina råd. lets do it

Translation: yes to your advice. Let's do it.

## What follows

- **Point 1.** The scripts that only Ratchet's own maintenance runs move out of `checks/` into `maintain/`: `generate.py`, `from_base.py`, `released_text.py`, `release.py`, `watch_sources.py` and `form_age.py`. What an adopter runs stays in `checks/`, so the paths an adopter's workflow uses do not change. The PR changes what judges it, so `base` is red and the maintainer merges it as an administrator.
- **Point 2.** The template's checkouts of Ratchet and the clone the docs give place in `.ratchet/` only what an adopter's commands use, still at the pinned commit.
- **Point 3.** No package is published before 1.0.
- The order of the work: points 1 and 2, then the recipe of D-2026-11-26-skills-eval, then #71 and the secret scan.
