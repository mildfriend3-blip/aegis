# AEGIS — conference talk proposal

Ready-to-paste material for a CFP submission. Target venues: **nullcon**,
**c0c0n**, **BSides Delhi / Bangalore**, or the AI-security track at a Python or
appsec conference. Pick the abstract length the CFP allows.

---

## Title

**AEGIS: Measuring What Prompt Injection Actually Costs a Tool-Using LLM Agent**

*(Shorter alternative: "Your Agent Has Hands: Quantifying Prompt Injection in
Tool-Using LLMs")*

**Track:** Application Security / AI & ML Security. **Format:** 25-minute talk
(20 min + 5 min Q&A). **Level:** intermediate.

---

## Abstract (long — ~230 words)

An LLM agent that can call tools — send email, POST to a URL, run SQL, read files —
turns a prompt injection from a party trick into a remote-execution class bug for
natural language. A payload hidden in a document the agent is asked to summarise can
quietly redirect its tools. The defensive advice in the wild is vague ("add a system
prompt", "filter the input") and almost never quantified, so defenders cannot tell
which control actually reduces risk.

This talk presents **AEGIS**, an open-source benchmark that makes the trade-off
measurable. It runs 17 prompt-injection attacks across 9 categories — direct override,
role-play, base64 encoding, paraphrase, indirect document injection, response leakage,
destructive SQL, HTTP exfiltration, and multi-turn social engineering — against a
tool-using agent, and reports two numbers for every defence: the **attack success
rate** and the **legitimate-task utility**.

The results are blunt. An undefended agent falls to **100%** of the attacks. A
four-layer stack — input sanitisation, datamarking, a tool-call policy engine, and an
output filter — drives that to **0%** with no loss of utility. But no single layer is
enough, and the benchmark shows exactly where each one fails: signature filters miss
encoded and paraphrased payloads, datamarking only stops indirect injection, and a
tool-call policy is blind to secrets leaked in the reply. Attendees leave with a
reproducible harness and a concrete, measured model of defence in depth for agents.

---

## Abstract (short — ~120 words)

LLM agents with tools turn prompt injection into an RCE-class bug: a payload hidden in
a document can redirect the agent's email, HTTP, or SQL calls. Defensive advice is
vague and unquantified. **AEGIS** is an open-source benchmark that fixes that — 17
attacks across 9 categories against a tool-using agent, scoring each defence on attack
success rate *and* legitimate-task utility. An undefended agent falls to **100%** of
attacks; a four-layer stack reaches **0%** with no utility loss. No single layer
suffices, and the benchmark shows each one's blind spot. This talk walks through the
attacks, the defences, a live demo, and what the numbers mean for anyone shipping an
agent.

---

## Key takeaways

1. **Prompt injection against an agent is impact, not vibes.** Score it on the effect
   that actually happens — data exfiltrated, SQL run — not on whether the model
   "looked" fooled.
2. **Layer the defence, and know each layer's blind spot.** Input filters miss encoded
   and paraphrased payloads; datamarking only covers indirect injection; a tool-call
   policy cannot see response leakage; only an output filter does.
3. **A defence that breaks the agent is not a defence.** Utility must be measured
   next to security; in AEGIS the full stack holds utility at 100% while driving ASR
   to 0%.
4. **Effect-level policy dominates.** Refusing the forbidden action catches attacks
   regardless of how the model was fooled — the single highest-leverage control.

---

## Outline (25 minutes)

| Min | Segment |
|-----|---------|
| 0–3 | Why a tool-using agent changes the stakes: prompt injection as RCE for natural language |
| 3–7 | Benchmark design: the four forbidden effects, effect-level success, utility measured alongside ASR |
| 7–16 | Live demo: the attack catalogue, then the same attacks under each defence layer and the full stack |
| 16–21 | Reading the matrix — each layer's blind spot, and why the effect-level policy carries the most weight |
| 21–25 | Limitations, future work (adaptive attacks, real-LLM runs), and how to reproduce in one command |

---

## Speaker bio

**Mildfriend** is a final-year B.Tech Computer Science (Cyber Security) student at
**Central University of Jammu**. AEGIS is their capstone project: an open-source
evaluation-and-defence framework for prompt-injection attacks on tool-using LLM agents,
with a deterministic offline benchmark, a four-layer defence stack, and a 22-test
suite. The project is on GitHub at `github.com/mildfriend3-blip/aegis`.

---

## Submission checklist

- [ ] Pick the abstract length the CFP allows (long or short above).
- [ ] Add the conference name and dates, and confirm the track.
- [ ] Attach a link to the repo and, if asked, the technical writeup PDF.
- [ ] Offer a live demo — it lands well, and the benchmark runs offline with no API key.
- [ ] If it is a workshop CFP, propose running the harness live with attendees adding
      their own attack or defence.
