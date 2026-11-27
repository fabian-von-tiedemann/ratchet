# D-2026-11-25-prompt-per-tool: a picker by coding agent and one prompt to paste on the landing page

- Date: 2026-11-25
- Decided by: Ratchet's maintainer
- Kind: decision (D)
- Replaces: none
- Amends: D-2026-11-24-landing-page-pass (the word cap of the page and the elements of the picker)
- Ends: none

## Question

Put to the maintainer by the control room on 2026-11-25, in Swedish, after both reviewers had passed the head `de6c8ef` of the pull request that adds this file. As the control room passed it on, with its own elision:

> Under "Start here" får sajten en väljare per agent: Claude Code, Codex, Gemini CLI, Cursor, GitHub Copilot och "Other". Under väljaren står en prompt att klistra in, som `generate.py` skriver med den släppta versionen. För det lättas tre saker i sidans test:
> 1. **Ordgränsen** går från under 780 till under 1100 ord. Sidan har nu 1096.
> 2. **Sidan får ha en väljare:** ett `<fieldset>` med sex radioknappar och deras etiketter. Den kräver inget skript, inget formulär och ingen knapp, och fungerar med bara CSS.
> 3. **Hämtkommandot står två gånger:** bland de tre kommandona och i prompten. Båda skrivs från samma version.
>
> Föreslås inte: en kopieringsknapp, eftersom den kräver ett inline-skript. Ett klick markerar i stället hela prompten.
>
> **A. Ja på alla tre (rekommenderas).**
> **B. Ja, men håll ordgränsen**, så kortar jag sidan i stället.
> **C. Ja, och lägg till kopieringsknappen** som en fjärde lättnad, med ett test som bara tillåter just det skriptet.
>
> […]

Translation: Under "Start here" the site gets a picker by agent: Claude Code, Codex, Gemini CLI, Cursor, GitHub Copilot and "Other". Under the picker stands a prompt to paste, which `generate.py` writes with the released version. For it, three things in the page's test are loosened: 1. The word cap goes from under 780 to under 1100 words. The page now has 1096. 2. The page may hold a picker: a `<fieldset>` with six radio buttons and their labels. It needs no script, no form and no button, and works with CSS alone. 3. The fetch command stands twice: among the three commands and in the prompt. Both are written from the same version. Not proposed: a copy button, since it needs an inline script. One click selects the whole prompt instead. A. Yes to all three (recommended). B. Yes, but keep the word cap, and I shorten the page instead. C. Yes, and add the copy button as a fourth loosening, with a test that allows exactly that script.

## Answer

> ok på dina reks

Translation: ok on your recommendations. The control room reads it as A: yes to all three loosenings, and no copy button.

## What follows

Decided:

- `checks/test_pages.py` may hold the page to under 1100 words outside its CSS where it held it to under 780, and may allow `<fieldset>`, `<legend>`, `<label>` with `for`, and `<input>` with `type`, `name` and `checked`, as the one picker and nowhere else. An `<input>` is `type="radio"` and `name="tool"`. Nothing else of a form is allowed: no `<form>`, no `<button>`, no other kind of input and no script.
- The prompt is one, the same for every coding agent, and stands in `generate.py` as `PROMPT`. Its tag is the newest version with a date in `CHANGELOG.md`, the one the command in `README.md` fetches, so the pull request of a release moves it, and `generate.py --check` fails on a prompt edited by hand.
- What differs by coding agent is one line: where to paste the prompt, and the file that agent reads. The test ties each file to `INSTRUCTION_FILES` in `checks/init.py`: a line says `init.py` sees the file only while it is in that list, and the line of Cursor says `init.py` does not see `.cursor/rules` only while it is not.
- The page says of no coding agent that Ratchet was tried in it. It says that Ratchet builds itself with Claude Code and Codex, and that it has not been tried in the others.
- The first screen, the story and the values, the principles and the figure stand as they were.
