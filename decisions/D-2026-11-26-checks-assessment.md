# D-2026-11-26-checks-assessment: fix two faults, simplify `checks/`, and stop hunting disguised markers

- Date: 2026-11-26
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

The maintainer asked, in Swedish, whether the code of all the checks could be reviewed, since it felt like a lot of code, and whether it could be made simpler, better and safer. A Codex session (gpt-6.1-sol), from another model family than the author of the code and in a fresh context, assessed `checks/` at `3e07781` and wrote a memo. The memo is the control room's material, not part of this repo. The control room then put this to the maintainer, in Swedish, quoted from the proposals on. The summary of the memo before them is left out:

> **Mina förslag:**
> 1. **Rätta de två säkerhetsfelen först.** Det är skärpningar, inga uppmjukningar. Planen granskas först och sedan två granskare. *Mitt råd: ja, före allt annat utom #180, som redan byggs.*
> 2. **Gör de tre förenklingarna med lägst risk:** en gemensam versionsjämförelse, gemensamma testhjälpare och parametriserade tester för landningssidan. *Mitt råd: ja, efter punkt 1.*
> 3. **Ta bort jakten på förklädda markörer** och behåll den exakta markörsyntaxen. Det mjukar upp en kontroll, så det kräver ett beslut som listar de fall som inte längre stoppas. *Mitt råd: ja. Det är utanför hotmodellen, och det är kod som användarna kör.*
> 4. **Generera hela landningssidan från en mall, och ta bort kontrollen av orelaterade länkar i trädet.** Båda kräver beslut, och båda gäller bara vårt eget underhåll. *Mitt råd: vänta. Sidan får fria tyglar i designarbetet med Fable, och en strikt mall krockar med det.*
> 5. **Gemensam git-körning och gemensam skyddad läsning.** *Mitt råd: ja, men sist. Risken är medelhög, eftersom olika skript har olika regler för git och sökvägar med avsikt.*
>
> Svara till exempel **"ja på dina råd"**. Då lägger jag in det i ordningen: #180 som pågår, sedan säkerhetsfelen, förenklingarna, beslutet om markörerna, receptet och därefter #71 och hemlighetsskanningen.

Translation:
1. Fix the two safety faults first. Both are tightenings, not loosenings. The plan is reviewed first, and then two reviewers review the build. *My advice: yes, before everything else except #180, which is already being built.*
   - The copy command that `run_pinned.py` prints follows a link at its temporary file `.new`, and so can write outside the project.
   - `generate.py` hangs when `ratchet.json` is a FIFO.
2. Make the three simplifications with the lowest risk: one shared comparison of versions, shared test helpers, and parameterized tests of the landing page. *My advice: yes, after point 1.*
3. Remove the hunt for disguised markers, and keep the exact marker syntax. This loosens a check, so it needs a decision that lists the cases no longer refused. *My advice: yes. It is outside the threat model, and it is code that adopters run.*
4. Generate the whole landing page from a template, and remove the refusal of unrelated links in the tree. Both need a decision, and both concern only this repo's own maintenance. *My advice: wait. The page has free rein in the design work with Fable, and a strict template would clash with that.*
5. A shared way of running git, and a shared guarded reader. *My advice: yes, but last. The risk is medium, since different scripts follow different rules for git and paths on purpose.*

Answer, for example, "yes to your advice", and I will put it into the order: #180, which is in progress, then the safety faults, the simplifications, the decision on markers, the recipe, and after that #71 and the secret scan.

## Answer

> ja på dina råd

Translation: yes, on your advice.

## What follows

- **Points 1, 2 and 5** are done in that order. None of them loosens a check, and each tightening keeps every case that passes or fails today.
- **Point 3 is decided here.** `check_register.py` keeps the exact form of a marker line, and so keeps refusing a marker that is missing, misspelled, or names another key or sha256. It may stop recognizing markers disguised with lookalike Unicode letters or other spellings, and partial-adoption phrases written in another shape. The pull request that does it cites this decision. It lists each fixture and case that no longer fails, and updates the claim in `checks/README.md` to match.
- **Point 4 waits.** The landing page stays as it is, and so does the refusal of unrelated links in the tree.
- The order of the work is: #180, then points 1, 2 and 3, then the recipe, then #71 and the secret scan. Point 5 comes after #71.
