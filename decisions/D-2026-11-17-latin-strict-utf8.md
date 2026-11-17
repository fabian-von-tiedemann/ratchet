# D-2026-11-17-latin-strict-utf8: data in Latin script, files in strict UTF-8, no name between two colons

- Date: 2026-11-17
- Decided by: Ratchet's maintainer
- Kind: decision (D)

Names are left out of this file. Where the original names a reviewer or a model, the name is replaced by a word in square brackets. Nothing else in the original is changed.

## Question

The question was the second of three choices in one message from the control room, with the advice "ja" (yes) to all three. The other two choices are about other things and are left out.

Original, in Swedish:

> 2. **Ge klartecken till Ratchet 0.3.** Där får data bara skrivas med latinsk skrift, filerna ska vara strikt UTF-8 och formen `:ord:` för emoji vägras. Det stänger de kantfall som [granskarens] femte runda hittade på en gång, så att vi slipper lappa dem ett i taget. Svara "ja". Då rättar [en modell], [granskaren] gör en kort kontroll och du publicerar 0.3 via en PR.

Translation into English:

> 2. **Give the go-ahead for Ratchet 0.3.** There, data may only be written in Latin script, the files must be strict UTF-8 and the form `:word:` for emoji is refused. That closes the edge cases that [the reviewer's] fifth round found, all at once, so that we do not have to patch them one at a time. Answer "ja". Then [a model] fixes it, [the reviewer] does a short check and you publish 0.3 through a PR.

## Answer

The answer was given to the whole message with its three choices.

Original, in Swedish:

> Ja

Translation into English:

> Yes

## What follows

The fifth review of the register check found five things. Each was a case at the edge of the rule "a letter, a digit, a punctuation mark, a symbol or a plain space", or of how a file is read. They are closed by making the rule narrower, not by one more exception each.

1. **Latin script.** A value holds Latin letters, digits, the plain space and marks from one fixed list. Everything else is refused. No character on the list is written right to left, is a digit of a right-to-left script or is a control for direction, so a punctuation mark or a symbol of such a script can no longer change the order two numbers are shown in.
2. **The list is code points in the check.** The check no longer asks the interpreter what kind of character it has. A letter that only a newer version of Unicode knows was accepted on one supported version of Python and refused on the other. Now it is refused on both.
3. **Strict UTF-8.** Every file a check reads is decoded as strict UTF-8. Bytes that are not UTF-8 fail the check, with the file and the byte named. Before, such a byte was read as the replacement character U+FFFD, and a generated file with a wrong byte compared equal to one that held U+FFFD. U+FFFD is not on the list either.
4. **No name between two colons.** A colon, one or more letters, digits, `_`, `+` or `-`, and a colon are refused in a value. A site that renders the file may replace such a name with a picture after Markdown is done, and the backslashes do not stop it.
5. **What the normal form NFKC is for.** The list holds no compatibility form. The text says that this shuts out compatibility forms, and no longer suggests that it shuts out characters that look alike.

The register is not changed. `repo.strict-forms` already says that a check fails on what it does not know.

Technical choices made within the owner's decision. The owner gave no answer on these. By `ratchet.five-choices` the control room makes technical choices and shows them in the PR.

1. Which characters are on the list. The letters are ASCII, Latin-1, Latin Extended-A and -B and Latin Extended Additional, without the compatibility forms and without four click letters that look like a pipe and an exclamation mark. The digits are `0` to `9`. The marks are the ASCII marks and sixteen marks outside ASCII: inverted marks, quotation marks, two dashes, and the signs for section, degree, middle dot, pound and euro. The list is in `checks/README.md`. A character is added only by a decision, because that loosens the check.
2. A name between two colons is refused in code too, not only in text. The rule then does not lean on how a site treats code.
3. The cost. A value cannot be written in another script. A symbol that is not on the list cannot be used. A time with seconds, such as 12:30:00, has digits between two colons and is written another way.
4. A person named with `@`, an issue named with `#` and the id of a commit are still accepted and written as text. Refusing them was not part of the question. What a site makes of them after Markdown is done is stated as not covered, with a fixture that shows what the check accepts.
5. The version and the date in a data file are ASCII digits. The pattern that read them took the digits of any script.
6. In a fixture that fails, a character outside ASCII stands as its JSON escape, so that the fixture shows which character it holds.
7. That a line made of the listed characters is shown in the order it is stored follows from the Unicode rules for mixing directions and from the direction class of each character, which a test reads on every supported version of Python. It has not been tried in a browser.
