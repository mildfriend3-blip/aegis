# Changelog

All notable changes to AEGIS are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-22

### Added
- Deterministic offline agent (`MockAgent`) that models instruction-following,
  including base64-decoding and datamark-awareness, plus an `OpenAIAgent` adapter for
  any OpenAI-compatible endpoint (env-var configuration only).
- Attack catalogue: 17 attacks across 9 categories (direct override, role-play,
  developer-mode, encoded, paraphrase, subtle, indirect, response leak, destructive
  SQL, HTTP exfil, multi-turn), each targeting one of four forbidden effects.
- Four composable defence layers: input sanitizer, datamarking/spotlighting, tool-call
  policy engine, and output filter, with eight named configurations.
- Evaluation harness scoring attacks at the level of recorded impact, and reporting
  utility alongside attack success rate.
- Metrics, Markdown/JSON report generation, and a CLI (`aegis run`, `aegis list`).
- 22-test suite and GitHub Actions CI (Python 3.10 and 3.12).
- Technical writeup (`docs/AEGIS-writeup.pdf`) and its reportlab build script.
