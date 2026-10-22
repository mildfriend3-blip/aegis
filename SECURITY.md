# Security Policy

## Scope

AEGIS is a **defensive measurement tool**. It runs contained text payloads against a
local, simulated agent. By default it contacts no external system, uses no real
credential, and the "secret" it protects is an inert sentinel string. The live-model
adapter (`--target openai`) is opt-in and requires you to supply your own endpoint.

Because of that, the security surface of AEGIS itself is small. The realistic issues
are:

- a payload or harness bug that causes an unintended network call;
- a defence that silently fails open (blocks nothing while reporting success);
- an attack in the catalogue that, if copied, would be misused against a system the
  reader is not authorised to test.

## Reporting a vulnerability

Please do not open a public issue for a security problem. Report it privately to the
maintainer at the email address on the repository profile, with:

- a description and the impact;
- steps to reproduce, ideally a minimal input;
- the version or commit you tested.

You will get an acknowledgement within a few days. Confirmed issues are fixed and
credited in `CHANGELOG.md` unless you ask to stay anonymous.

## Responsible use

The attacks in `aegis/attacks/payloads.py` are for testing **your own** agents, in a
sandbox, or under a bug-bounty programme's rules. Do not point them at systems you do
not own or have written permission to test.
