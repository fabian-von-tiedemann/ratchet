# D-2026-11-16-register-only: 0.3 ships the register check alone

<!-- generated:status -->
Status: amended by D-2026-11-22-second-redraw (the core rules on decisions and on the glossary)
<!-- /generated:status -->

- Date: 2026-11-16
- Decided by: Ratchet's maintainer
- Kind: decision (D)
- Replaces: none
- Amends: D-2026-11-16-renumber (the second build set aside); D-2026-11-16-strict-forms (the strict line format of decisions and the glossary data set aside)
- Ends: none

## Question

Original, in Swedish:

> **Ett val till dig om Ratchet.** Mitt råd: publicera 0.3 med bara registerkontrollen, efter en liten rättning, och lägg kontrollerna för beslutsfiler och ordlista (0.4) åt sidan tills vi har ett bättre angreppssätt för dem.

Translation into English:

> **One choice for you about Ratchet.** My advice: publish 0.3 with the register check alone, after a small fix, and set the checks for decision files and the glossary (0.4) aside until we have a better approach for them.

## Answer

Original, in Swedish:

> ja ok

Translation into English:

> yes ok

## What follows

- 0.3 ships one reference check, for the register. Nothing that 0.3 promises leans on a later version.
- The checks for decision files and for the glossary were built and reviewed three times. The last review still found text that a reader does not see and the check accepts. They are set aside, and how to check them is an open question with the review's findings as its material.
- `ratchet.decision-as-file` and `ratchet.glossary` stay in the core as they are. Each names a check that a project builds. Ratchet ships no reference check for them.
- The small fix: every value that is written from a data file into a generated file is written as text, so that data cannot become hidden text. How is a technical choice, recorded in [D-2026-11-16-strict-forms](D-2026-11-16-strict-forms.md).
