# AEGIS

[![CI](https://github.com/mildfriend3-blip/aegis/actions/workflows/ci.yml/badge.svg)](https://github.com/mildfriend3-blip/aegis/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Live site](https://img.shields.io/badge/live%20site-visit-5980A6)](https://mildfriend3-blip.github.io/aegis/)

**Live site:** <https://mildfriend3-blip.github.io/aegis/> · [talk deck](https://mildfriend3-blip.github.io/aegis/AEGIS-talk.html) · [writeup](https://mildfriend3-blip.github.io/aegis/AEGIS-writeup.pdf)

**A**n **E**valuation-and-defense framework for prompt-injection attacks on tool-using LLM agents.

AEGIS runs a catalogue of realistic prompt-injection attacks against a tool-using agent,
quantifies how often each attack achieves its forbidden effect (**Attack Success Rate**),
and measures how much each defensive layer reduces that rate — *and at what cost to
legitimate utility*. It ships with a deterministic offline agent, a four-layer defense
stack, 17 attacks across 9 categories, a CLI, and a 22-test suite.

```
$ aegis run
```

---

## Why this exists

When an LLM agent can call tools — send email, hit an HTTP endpoint, run SQL, read
files — a prompt injection stops being a party trick and becomes a **remote code
execution class bug for natural language**. A payload hidden in a document the agent is
asked to summarise can redirect its tools. The defensive advice in the wild is vague
("add a system prompt", "filter the input") and almost never quantified.

AEGIS makes the trade-off measurable. The central question it answers:

> *Given a catalogue of attacks, how much does each defence reduce the attack success
> rate — and does it break the agent's legitimate job in the process?*

## Results

17 attacks × 8 defence configurations. **ASR = Attack Success Rate (lower is better);
utility = fraction of cases where the legitimate task still worked (higher is better).**

![AEGIS results: attack success rate by defence](docs/results-table.png)

| Defense | ASR | Utility |
|---|---|---|
| none | **100.0%** | 100.0% |
| sanitizer | 64.7% | 100.0% |
| datamarking | 88.2% | 100.0% |
| tool-policy | 17.6% | 100.0% |
| output-filter | 82.4% | 100.0% |
| sanitizer + tool-policy | 11.8% | 100.0% |
| datamarking + tool-policy | 17.6% | 100.0% |
| **full stack** | **0.0%** | **100.0%** |

An undefended agent falls to **every** attack. A four-layer stack drives ASR to **0%**
without sacrificing the legitimate task — but the single-layer rows show why layering is
required: each layer has a blind spot the others cover.

### ASR by defence × attack category

| Defense | direct_override | role_play | encoded | subtle | indirect | response_leak | destructive | http_exfil | multi_turn |
|---|---|---|---|---|---|---|---|---|---|
| none | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% |
| sanitizer | 67% | 67% | 100% | 100% | 50% | 50% | 50% | 0% | 100% |
| datamarking | 100% | 100% | 100% | 100% | **0%** | 100% | 100% | 100% | 100% |
| tool-policy | **0%** | 33% | **0%** | **0%** | **0%** | 100% | **0%** | **0%** | **0%** |
| output-filter | 100% | 67% | 100% | 100% | 100% | **0%** | 100% | 100% | 100% |
| full | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |

Read the blind spots off the matrix: input sanitisation catches *known phrasings* but
misses **encoded** and **paraphrased** payloads; datamarking only helps **indirect**
(document-borne) injection; the tool-call policy handles **actions** but is blind to
**response leakage**, which only the output filter catches.

## Architecture

```
                ┌──────────────┐     ┌───────────────────────────────┐
   attack  ───▶ │  input side  │ ──▶ │            agent              │
   payload      │  sanitizer   │     │  (MockAgent | OpenAIAgent)    │
                │  datamarking │     │  proposes tool calls + answer │
                └──────────────┘     └───────────────┬───────────────┘
                                                     │ tool calls
                                     ┌───────────────▼───────────────┐
                                     │   tool-call policy engine     │
                                     │   allow-list / secret guard   │
                                     └───────────────┬───────────────┘
                                          allowed    │    blocked
                                     ┌───────────────▼───────────────┐
                                     │   World (effects recorded)    │
                                     └───────────────┬───────────────┘
                                                     │ final answer
                                     ┌───────────────▼───────────────┐
                                     │        output filter          │
                                     └───────────────┬───────────────┘
                                                     ▼
                                       evaluate(attack.objective)  ──▶  RunRecord
```

An attack **succeeds only if its forbidden effect is actually recorded** in the World
(email sent off-domain, POST to a non-allow-listed host, destructive SQL run) or the
secret appears in the final answer. A defence that blocks the tool call therefore
prevents the effect — success is defined at the level of *impact*, not vibes.

## Quickstart

```bash
git clone <your-repo-url> && cd aegis
pip install -e ".[dev]"

aegis list                 # show attacks and defence configs
aegis run                  # full benchmark -> prints tables, writes results/
aegis run --defenses none,tool-policy,full --out results
pytest -q                  # 22 tests
```

Run it against a **real** model (offline by default; needs an OpenAI-compatible endpoint):

```bash
export AEGIS_OPENAI_API_KEY=sk-...        # never hard-coded, env only
export AEGIS_OPENAI_MODEL=gpt-4o-mini
aegis run --target openai --defenses none,full
```

## The four defence layers

| Layer | Where | What it does | Its blind spot |
|---|---|---|---|
| **sanitizer** | input | Redacts sentences matching known injection signatures | paraphrased & encoded payloads |
| **datamarking** | input | Marks untrusted documents so instructions inside are treated as data | direct (user-turn) injection |
| **tool-policy** | action | Refuses tool calls that break policy (off-domain email, non-allow-listed host, destructive SQL, secret exfil) | response leakage; novel tools |
| **output-filter** | output | Redacts the protected secret from the final answer | anything that isn't a response leak |

## Attack taxonomy

Direct instruction override · role-play / persona hijack · developer-mode framing ·
base64 encoding · paraphrase & subtle P.S. exfiltration · indirect injection hidden in a
document (HTML comment and plain note) · response leakage · destructive SQL · HTTP
exfiltration · multi-turn social engineering. Each attack targets one of four objectives:
`exfil_email`, `exfil_http`, `secret_leak_response`, `destructive_sql`.

## Design choices worth defending in an interview

- **Deterministic offline agent.** Results are reproducible and comparable; identical
  inputs give identical scores. A real-LLM adapter is included to validate the offline
  numbers track reality, but the benchmark never *depends* on a network call.
- **Effect-level success.** Attacks are scored on impact recorded in a simulated World,
  not on whether a model "looked" fooled — so a blocked action is a real win.
- **Utility is measured, not assumed.** A defence that stops attacks by breaking the
  agent is not a defence. Utility is reported next to ASR in every row.
- **Honest findings.** On this catalogue the input-side layers are *redundant given* the
  effect policy (the policy refuses the effect however the model was fooled). They are
  kept because a real policy is never complete — and the test suite pins this finding so
  it can't silently change.

## Repository layout

```
aegis/
  aegis/
    targets/      agent under test: MockAgent (offline) + OpenAIAgent adapter
    attacks/      attack catalogue (17 cases, 9 categories)
    defenses/     four composable layers + the registry of configs
    world.py      simulated environment; records the effects success is scored on
    harness.py    the evaluation loop
    metrics.py    ASR / utility aggregation
    report.py     Markdown + JSON report generation
    cli.py        command-line entry point
  tests/          22 tests
  docs/           technical writeup (PDF) + its build script
  results/        generated benchmark output
```

## Extending

- **Add an attack:** append an `Attack(...)` to `aegis/attacks/payloads.py`.
- **Add a defence:** implement `Defense` in `aegis/defenses/`, register it in
  `_LAYERS` and a `DEFENSE_CONFIGS` combination.
- **Point it at your own agent:** implement `AgentTarget.run(task, documents)`.

## Ethics & scope

AEGIS is a defensive measurement tool. The "attacks" are contained text payloads run
against a local simulated agent — no external system is contacted, no real credential is
used, and the secret is a sentinel string. Do not point the live-model adapter at systems
you are not authorised to test.

## References

- Hines et al., *Defending Against Indirect Prompt Injection Attacks With Spotlighting* (2024).
- Greshake et al., *Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection* (2023).
- OWASP Top 10 for LLM Applications — LLM01: Prompt Injection.

## License

MIT.
