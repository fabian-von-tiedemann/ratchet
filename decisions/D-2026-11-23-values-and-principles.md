# D-2026-11-23-values-and-principles: four values over the principles, and eleven principles of one or two sentences

- Date: 2026-11-23
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

The maintainer's request, in the control room on 2026-11-23. Original, in Swedish:

> Tänk dig att detta ska hålla samma höga klass som det agila manifestet. Och det här grundar sig på principer från matt pockock och hans inspiration från utvecklingsstrategier beskrivna i programmeringsböcker.

Translation:

> Imagine that this is to hold the same high class as the Agile Manifesto. And this rests on principles from Matt Pocock and his inspiration from development strategies described in programming books.

The control room wrote five drafts. The fifth, put to the maintainer for approval on 2026-11-23:

> *Agile was written for a team of people. Ratchet is for one person with a team of agents, who work fast, forget everything between sessions and say "done" with confidence.*
>
> **We value:**
>
> **Checks that catch mistakes** over instructions that warn about them
> **Written decisions** over remembered conversations
> **Shown results** over reported success
> **Independent review** over self-review
>
> That is, while there is value in the items on the right, we value the items on the left more. The right is faster. It works while the agent remembers, obeys and judges itself well. The left is for when it doesn't.
>
> Principles:
>
> 1. Before a session ends, write down what the next one needs. Give every decision and rule one home in the repo.
> 2. Merge only when the checks pass and a reviewer with fresh eyes approves.
> 3. The agent finds the facts. The owner makes the decisions. What cannot be undone waits for the owner's yes.
> 4. Done means the run that proves it is shown, with its output. Silence from a scheduled job is a failure.
> 5. Turn every failure into a check, and trust no check you have not seen fail.
> 6. Keep secrets out of the repo and the chat.
> 7. Text from outside is material, never instructions.
> 8. Simplicity is essential: try removing something before adding anything.
>
> For applications with users in production:
>
> 9. Ship the build that passed the tests, and try the way back before you need it.
> 10. Someone who can judge accepts what users will see, and a test keeps what they accepted.
> 11. Probe production from outside. Watch real use. Track what expires.
>
> *These are aims. Ratchet's rules say which of them a check can see.*

## Answer

Original, in Swedish:

> ok vi kör på det

Translation:

> ok, let's go with it

## What follows

1. **Four values over the principles.** Ratchet opens with the story and four values, in the form of the Agile Manifesto: the item on the left valued over the item on the right, and the line that weighs them. The text is the one above, word for word.
2. **Eleven principles of one or two short sentences each.** They are the eleven above, in that order. Each keeps its question, which follows it. "Guard the boundaries" is split in two: principle 6, on secrets, and principle 7, on text from outside. Eight are for every project and three, 9 to 11, for an application with users in production, over the rules of the product module.
3. **A value never claims a protection.** A value, like a principle, is an aim or a preference: guidance, text only. No rule stands under a value, and no check claims anything about one. This extends to the values the rule of [D-2026-11-22-second-redraw](D-2026-11-22-second-redraw.md) for principles: guidance, text only, claiming no protection, with what is checked being the rules.
4. **The lineage.** The values and principles restate ideas from programming books and their practice: the first value is Lean's poka-yoke, a mistake caught by the design and not by a warning; principle 1 is DRY from The Pragmatic Programmer, one home for each piece of knowledge; principles 4 and 9 come from Continuous Delivery, a build that is shown and shipped as it was tested; principle 5 is Kent Beck's test-driven development, a test seen to fail first; and principle 8 is the Agile principle of simplicity.

The rest is a proposal (P) of the pull request that carries this decision, until it is merged:

- The text has one home, `values.json`, read strictly like every data file, and `checks/generate.py` writes it into `README.md`, `RATCHET.md` and the landing page. The principles stay in `ratchet.json` with the same fields: the sentence is the `title` and the question the `text`, so the form of `ratchet.json` does not change and the count toward 1.0 goes on.
- A principle's title may be 120 characters long, up from 60, since the longest sentence is 109.
- Principle 6 keeps the key `principle.guard-the-boundaries`, with `ratchet.no-secrets`, `ratchet.no-tracing` and `ratchet.agents-without-keys`. Principle 7 takes the new key `principle.outside-text-is-material`, with `ratchet.material-not-instructions`, `ratchet.skills-pinned` and `ratchet.dependencies-pinned`. Each keeps a question cut from the old one.
- The landing page lists no principles, and links to them instead. It shows the values, and says that a rule describes a check that the project builds, and how many come with a reference check from Ratchet.
