# D-2026-11-25-prompt-per-tool: a picker by coding agent and one prompt to paste on the landing page

- Date: 2026-11-25
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

A proposal (P) until the maintainer answers. The question as the pull request that adds this file puts it, for the control room to pass on. The control room replaces it with the question exactly as it put it, in its language, before the merge:

> Under "Start here" the landing page gets a picker by coding agent, Claude Code, Codex, Gemini CLI, Cursor, GitHub Copilot and "Other", over one prompt to paste, which `generate.py` writes with the released tag. Three things in the page's test are loosened for it, and need your decision. I recommend yes to all three:
> 1. The word cap is raised from under 780 to under 1100 words. The page now has 1096, the prompt and the picker among them.
> 2. The page may hold one picker: a `<fieldset>` with a `<legend>`, six radio inputs and their labels. An input is a radio of the picker and nothing else. There is no script, no form and no button, and the picker works with CSS only.
> 3. The command that fetches Ratchet stands twice on the page: as before in the three commands, and as a line of the prompt. `generate.py` writes both from the same version.
>
> Not proposed: a copy button. It would need an inline script. One click selects the whole prompt instead, with CSS.

## Answer

To be filled in on approval.

## What follows

Proposals (P) until the pull request is merged:

- `checks/test_pages.py` may hold the page to under 1100 words outside its CSS where it held it to under 780, and may allow `<fieldset>`, `<legend>`, `<label>` with `for`, and `<input>` with `type`, `name` and `checked`, as the one picker and nowhere else. An `<input>` is `type="radio"` and `name="tool"`. Nothing else of a form is allowed: no `<form>`, no `<button>`, no other kind of input and no script.
- The prompt is one, the same for every coding agent, and stands in `generate.py` as `PROMPT`. Its tag is the newest version with a date in `CHANGELOG.md`, the one the command in `README.md` fetches, so the pull request of a release moves it, and `generate.py --check` fails on a prompt edited by hand.
- What differs by coding agent is one line: where to paste the prompt, and the file that agent reads. The test ties each file to `INSTRUCTION_FILES` in `checks/init.py`: a line says `init.py` sees the file only while it is in that list, and the line of Cursor says `init.py` does not see `.cursor/rules` only while it is not.
- The page says of no coding agent that Ratchet was tried in it. It says that Ratchet builds itself with Claude Code and Codex, and that it has not been tried in the others.
- The first screen, the story and the values, the principles and the figure stand as they were.
