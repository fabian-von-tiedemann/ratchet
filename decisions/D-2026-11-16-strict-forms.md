# D-2026-11-16-strict-forms: checks read data and strict forms, and refuse everything else

<!-- generated:status -->
Status: amended by D-2026-11-16-register-only (the strict line format of decisions and the glossary data set aside); amended by D-2026-11-17-latin-strict-utf8 (technical choice 4)
<!-- /generated:status -->

- Date: 2026-11-16
- Decided by: Ratchet's maintainer
- Kind: decision (D)

Names are left out of this file. Where the original names a reviewer, a model or another project, the name is replaced by a word in square brackets. Nothing else in the original is changed.

## Question

Original, in Swedish:

> **Ett val till dig om Ratchet:** [Granskaren] har underkänt kontrollerna två rundor i rad med samma slags fel. Mitt råd är att byta angreppssätt innan vi rättar mer, enligt Ratchets egen regel om två rundor.
>
> **Felklassen.** Kontrollerna försöker tolka vanlig Markdown, och Markdown kan skrivas på oändligt många sätt. Varje runda hittar ett nytt sätt att gömma en ändrad rad eller en förbjuden term:
>
> - **Runda 1:** indragningar och borttagna markörer.
> - **Runda 2:**
>   - en rubrik inuti en HTML-kommentar
>   - ett escapat lodstreck som flyttar kolumnerna
>   - ett kodblock med fyra backticks som stängs med tre
>   - en mallplatshållare som har radbrutits.
>
> Varje rättning stänger de fall som hittades, men inte klassen. Det är samma mönster som i [ett annat projekts] domare.
>
> **Det nya angreppssättet: ett strikt format som vägrar allt annat.** Kontrollerna ska inte förstå all Markdown. De ska kräva ett litet, exakt format och fälla allt som avviker:
>
> - **Registret:** ett projekts register blir en datafil, på samma sätt som Ratchets egna regler redan ligger i `ratchet.json`. Tabellen i Markdown genereras därifrån, och kontrollen jämför datarader exakt. Då finns inget att gömma i kommentarer eller kodblock.
> - **Beslutsfilerna och ordlistan:** de får ett strikt radformat. En rad som inte följer formatet fäller kontrollen, i stället för att tyst hoppas över.
> - **Testerna:** [granskarens] attacker från båda rundorna blir regressionstester. [Granskaren] får sedan en ny runda för att försöka bryta det strikta formatet.
>
> Det gör också Ratchet bättre som idé. "Vägra allt som inte uttryckligen är tillåtet" är just en spärrhake.
>
> Övriga fynd är små och rättas samtidigt. Det gäller versionssuffix, ett test som godtar fel kodägare och en motsägelse om maskinkontot.
>
> Svara "ja", så får [en modell] bygga om kontrollerna så. Tills dess publiceras varken 0.3 eller 0.4, eftersom registerkontrollen i båda har luckan.

Translation into English:

> **One choice for you about Ratchet:** [The reviewer] has rejected the checks two rounds in a row with the same kind of failure. My advice is to change the approach before we fix more, by Ratchet's own rule on two rounds.
>
> **The failure class.** The checks try to interpret ordinary Markdown, and Markdown can be written in endlessly many ways. Every round finds a new way to hide a changed row or a forbidden term:
>
> - **Round 1:** indentation and removed markers.
> - **Round 2:**
>   - a heading inside an HTML comment
>   - an escaped pipe that moves the columns
>   - a code block with four backticks that is closed with three
>   - a template placeholder that has been wrapped over several lines.
>
> Every fix closes the cases that were found, but not the class. It is the same pattern as in [another project's] judges.
>
> **The new approach: a strict form that refuses everything else.** The checks are not to understand all Markdown. They are to require a small, exact form and fail everything that departs from it:
>
> - **The register:** a project's register becomes a data file, in the same way that Ratchet's own rules already live in `ratchet.json`. The table in Markdown is generated from it, and the check compares rows of data exactly. Then there is nothing to hide in comments or code blocks.
> - **The decision files and the glossary:** they get a strict line format. A line that does not follow the format fails the check, instead of being silently skipped.
> - **The tests:** [the reviewer's] attacks from both rounds become regression tests. [The reviewer] then gets a new round to try to break the strict form.
>
> It also makes Ratchet better as an idea. "Refuse everything that is not expressly allowed" is exactly a ratchet.
>
> The other findings are small and are fixed at the same time. They are a version suffix, a test that accepts the wrong code owner and a contradiction about the machine account.
>
> Answer "ja", and [a model] will rebuild the checks that way. Until then neither 0.3 nor 0.4 is published, because the register check in both has the gap.

## Answer

Original, in Swedish:

> ja

Translation into English:

> yes

## What follows

The rule `repo.strict-forms` is in the register, with this decision as its source.

What stands in 0.3 is the register: a project's register is a data file, and the readable file is generated from it and compared with it exactly.

The strict line format for decision files and the data file for the glossary were built and reviewed, and are set aside: see [D-2026-11-16-register-only](D-2026-11-16-register-only.md).

Technical choices made by the control room within the owner's decision. The owner gave no answer on these. By `ratchet.five-choices` the control room makes technical choices and shows them in the PR.

1. The format of a register changes, and a register written for 0.2 is moved by hand. The steps are in the file MIGRATING.md in the root of the repo. The template for a Markdown register is removed, because a register is generated, not copied and edited.
2. A value in a data file is text, never Markdown. When it is written into a generated file, every ASCII punctuation mark gets a backslash, so that no value can become a link, an image, emphasis, HTML or a comment. The generator does not try to work out what Markdown would make of a value: an earlier form of this choice did, and a review got a comment past it twice.
3. The one form besides text is code. A part of a value between a pair of backticks is code, by the data's own rule, and is written as a code span. That covers what Ratchet's own rules need: file names, ids and commands inside a sentence.
4. Characters are taken by allowlist. A value is in the normal form NFC, and every character is a letter, a digit, a punctuation mark, a symbol or a plain space. Combining marks, format characters, other spaces, fillers and compatibility forms are refused. The cost is that scripts written with combining marks cannot be used in a value. This choice is replaced by [D-2026-11-17-latin-strict-utf8](D-2026-11-17-latin-strict-utf8.md), which is narrower: a value is written in Latin script, from one fixed list of characters.
