# D-2026-11-24-faster-suite: run the suite once in each pass, and the suite on a released copy in a job of its own

- Date: 2026-11-24
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Put to the maintainer in the control room on 2026-11-24, after a measurement of this repo's CI. The job `own` of `.github/workflows/checks.yml` ran `python3 -m unittest discover -s checks -v` and then `python3 checks/expected_tests.py`, which runs the same discover with strictly more checks, and each took 6.6 to 9.6 minutes. Inside each pass, `test_released_text.ReleaseSteps` ran `expected_tests.py` on a released copy of the repo, so the full suite ran again: 260 of 527 seconds locally, about 49%. The job `base` runs one more pass. The options were: 1, remove the plain `unittest discover` step from `own`; 2, move the run of the full suite on a released copy out of the suite, into a step or a job of its own that runs once on each pull request and push to `main` and that the job `checks` needs; 3, a further change beyond those two. The question, verbatim, in Swedish:

> A. Gör 1 och 2 (rekommenderas) / B. Bara 1 / C. 1, 2 och 3 direkt

Translation:

> A. Do 1 and 2 (recommended) / B. Only 1 / C. 1, 2 and 3 at once

## Answer

> Ja på rek

Translation:

> Yes to the recommendation

That is option A.

## What follows

- The job `own` runs the suite once, with `checks/expected_tests.py`, which is its suite step. The step that ran `unittest discover` before it is removed: every test it ran, `expected_tests.py` runs too, and checks that each one ran and passed.
- The run of `expected_tests.py` on a released copy of the repo moves out of `ReleaseSteps` into `released_copy_case` in `checks/test_released_text.py`, a test that discover does not collect. It takes the same release steps, with every assertion they made, and then runs the full suite in the copy. The job `released` runs it once on each pull request and each push to `main`, and the job `checks`, the one the ruleset on `main` requires, needs `released` and is red unless it passed. The release workflow runs it before it tags, as it ran inside its suite before.
- This loosens nothing. Every assertion of the old test still runs on every pull request and every push to `main`, and is still required for the merge through the job `checks`. A test fails when `checks` does not need `released`, or when `released` no longer runs the suite on the copy. The ruleset on `main` still requires only the job `checks`, so no setting of the host changes.
- Like every change to the workflow, the pull request that makes this change cannot be judged by the base branch's checks: its job `checks` is red by design, and the maintainer reads it and merges it as an administrator.
