# Security

Report a security fault in Ratchet privately, through GitHub's private vulnerability reporting, and never in a public issue.

## How to report

1. Open the repo's [Security tab](https://github.com/fabian-von-tiedemann/ratchet/security) and choose **Report a vulnerability**.
2. Say what the fault is, the version or commit it is in, and the steps that show it. Leave out every name and internal detail of your own project, as [CONTRIBUTING.md](CONTRIBUTING.md#if-you-are-an-agent) says.
3. Only the maintainer sees the report, and answers you in it.

## What counts

A security fault is a check, template or workflow that can leak a secret, run code it should not, or need more permissions than it says. A check that misses a fault someone hid from it on purpose is outside its claim, since every check's threat model is mistakes and drift ([checks/README.md](checks/README.md#the-threat-model)), and goes in a normal issue.

## Which versions get fixes

| Version | Gets the fix |
|---|---|
| The latest release | Yes, in a new version released at once. |
| An older release | No. Upgrade, as [UPGRADING.md](UPGRADING.md) says. A published tag is never moved. |
