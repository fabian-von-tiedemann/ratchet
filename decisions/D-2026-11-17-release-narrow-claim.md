# D-2026-11-17-release-narrow-claim: the release script claims to catch mistakes in normal operation

- Date: 2026-11-17
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

The question was put after the second review round of the approach in [D-2026-11-17-release-links](D-2026-11-17-release-links.md) was rejected, in [PR #9](https://github.com/fabian-von-tiedemann/ratchet/pull/9). Both rounds found an input under which a version merged into `main` could be left unreleased without a red run that names it: a changelog heading moved out of its form, then a graft in the checkout and a version spelled `00.4`. The recommendation was the one made for the check of expected tests in PR #12.

Original, in Swedish:

> **Mitt förslag, samma lösning som för #12:** kontrollen lovar bara att fånga misstag i normal drift. Det betyder en avbruten eller misslyckad körning, en publicering som fallerar och en ändringslogg som har redigerats. Den lovar inte att stå emot någon som manipulerar körningens git-data eller medvetet skriver ett avvikande versionsnummer. Det står uttryckligen i dokumentationen. Två enkla spärrar läggs ändå till, eftersom de kostar nästan ingenting:
> - Versionsnumret måste ha en strikt form, alltså inga inledande nollor.
> - Körningen vägrar om den lokala kopian innehåller grafts eller andra ersättningsobjekt.
>
> Det mindre felet med jämförelsen 0.9 → 0.10 rättas också.

Translation into English:

> **My proposal, the same solution as for #12:** the check promises only to catch mistakes in normal operation. That means a run that was cancelled or failed, a publication that fails, and a changelog that has been edited. It does not promise to stand against someone who manipulates the run's git data or deliberately writes a deviating version number. That is stated explicitly in the documentation. Two simple barriers are added anyway, because they cost almost nothing:
> - The version number must have a strict form, that is, no leading zeros.
> - The run refuses if the local copy contains grafts or other replacement objects.
>
> The smaller fault with the comparison 0.9 → 0.10 is fixed as well.

## Answer

Original, in Swedish:

> ja

Translation into English:

> yes

## What follows

- The release script promises only to catch mistakes in normal operation: a run that was cancelled or failed, a publication that fails, and a changelog that has been edited.
- It does not promise to stand against someone who manipulates the run's git data or deliberately writes a deviating version number. [checks/README.md](../checks/README.md#releasepy) says so explicitly.
- The version number must have a strict form, with no leading zeros.
- The run refuses if the checkout contains grafts or other replacement objects.
- The comparison of 0.9 with 0.10 is fixed.

Proposals (P) made within the decision, shown in PR #9. The owner gave no answer on these.

1. P: The strict form is `^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$`. It holds for every version the script reads: from `ratchet.json` in the checkout, from `ratchet.json` at each commit on `main`, from the tags (`v` and the version), and from the headings of the changelog. Anything else fails the run, and the message names the value and where it came from. Versions are compared only as pairs of integers.
2. P: "Grafts or other replacement objects" means `.git/info/grafts`, any ref under `refs/replace/`, a `.git/shallow` file, even an empty one, and a `.git/objects/info/alternates` file. The run refuses each before it reads any history. git still runs with `GIT_NO_REPLACE_OBJECTS=1` and `--no-replace-objects`, and now with `GIT_GRAFT_FILE` set to an empty file in a directory the script makes.
3. P: The fix of the comparison is a test of 0.9 then 0.10 on a real git history. It fails when the versions are compared as strings.
4. P: A message may now name a tag from an answer of the API. The script takes the token out of every message it prints.
5. P, not done here: `registry.py` could read `version` in `ratchet.json` with the same strict form, so that `generate.py` and `check_register.py` refuse `00.4` too. Today the release script refuses it, and the others accept it.
