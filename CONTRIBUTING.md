# Contributing

Thanks for improving AEGIS. Two kinds of contribution matter most: new attacks and new
defences. Both are small, self-contained changes.

## Setup

```bash
git clone <your-fork> && cd aegis
pip install -e ".[dev]"
pytest -q          # should be green before you start
aegis run          # regenerates results/
```

## Add an attack

Append an `Attack(...)` to `aegis/attacks/payloads.py`:

```python
Attack(
    id="my_attack",                 # unique, snake_case
    name="Human-readable name",
    category="encoded",             # group it with similar attacks
    channel="user",                 # "user" (direct) or "document" (indirect)
    objective="exfil_email",        # one of OBJECTIVES in aegis/types.py
    payload="...",
)
```

Rules: it must target exactly one of the four objectives; it must be a *contained text
payload* (no code, no real endpoints); and it should demonstrate something the existing
catalogue does not.

## Add a defence

Implement `Defense` in a new module under `aegis/defenses/`, then register it in
`_LAYERS` and add at least one combination to `DEFENSE_CONFIGS` in
`aegis/defenses/__init__.py`. Layers transform inputs, filter tool calls, or filter the
response - pick the right hook.

## Before you open a PR

- `pytest -q` passes.
- `aegis run` completes and `results/report.md` looks sane.
- If your change alters the benchmark numbers, update the tables in `README.md` and
  say so in the PR description.
- Keep the writing in the README and the writeup in plain, concrete language - claims
  carry a number, a name, or a date.

## Commit style

Short imperative subject line (`add base64-encoded attack`), body only if it explains
*why*. One logical change per commit.
