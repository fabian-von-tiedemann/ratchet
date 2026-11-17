# D-2026-11-17-auto-merge: the agents' account turns on auto-merge, and the code owner's approval merges

- Date: 2026-11-17
- Decided by: Ratchet's maintainer
- Kind: decision (D)

The mark `[...]` shows where this file leaves out part of a message. Nothing else in the original is changed.

## Question

The question came in two messages. The first put the arrangement as the first of three points. The second put it again, after the maintainer asked whether it was a sound way to work, and asked for the setting.

From the first message, original in Swedish:

> **Mitt förslag: du gör en enda sak, "Approve", och resten sker av sig självt.**
>
> 1. **Automatisk merge.** Du slår på det en gång: Settings → General → Pull Requests → **Allow auto-merge**. Den inställningen kan jag inte ändra, eftersom kontot inte är admin. Sedan slår jag på auto-merge för varje PR jag öppnar. När du godkänner, och CI är grönt, slås PR:en ihop direkt.

Translation into English:

> **My proposal: you do one thing, "Approve", and the rest happens by itself.**
>
> 1. **Automatic merge.** You turn it on once: Settings → General → Pull Requests → **Allow auto-merge**. I cannot change that setting, because the account is not an admin. Then I turn on auto-merge for every PR I open. When you approve, and CI is green, the PR is merged at once.

From the second message, original in Swedish:

> Om du tycker att det låter rätt: slå på **Allow auto-merge** och skriv "på". Då slår jag på auto-merge för PR #7, öppnar en separat PR för release-arbetsflödet och sammanfattningen överst i varje PR, och lägger in arbetssättet i dina instruktionsfiler så att nästa session gör likadant.

Translation into English:

> If you think that sounds right: turn on **Allow auto-merge** and write "på" (on). Then I turn on auto-merge for PR #7, open a separate PR for the release workflow and the summary at the top of every PR, and put the way of working into your instruction files so that the next session does the same.

## Answer

Original, in Swedish:

> på

Translation into English:

> on

## What follows

- The repository allows auto-merge. The agents' account turns it on for the pull requests it opens. A pull request is merged only when the job `checks` is green and the code owner has approved its latest push, so what is merged is exactly what the code owner approved.
- `repo.agents-own-account` changes: the account may turn on auto-merge, and it still never approves a pull request and never merges one by hand. It was first used on the pull request for 0.3, which GitHub merged in the name of the agents' account after the code owner approved. The rule stays text only: an account with write access is still able to merge by hand once the requirements are met.
- Every pull request from the agents' account starts with a short section that says what the code owner approves, so that the approval can be given from a phone.
