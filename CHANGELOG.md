# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-08-09

### Added
- Episode protocol: seed snapshot → agent run → deterministic guards →
  hidden oracle injection → full suite run → claimed-vs-verified verdict
- Five verdicts: `SOLVED`, `FALSE_SUCCESS`, `FAILED_HONEST`,
  `GUARD_VIOLATION`, `LEAKED` — erring and lying never merged
- Deterministic guards: visible-test hash check, file-scope check, oracle
  canary leak detection
- Suite v0.1: 6 tasks across basic-correctness, cheat-detection,
  multi-file-regression and honesty
- CLI: `polygraph list`, `polygraph run --providers ...` with per-provider
  summary and false-success rate; results in `results/`
- CLI transport via [Athena](https://github.com/JoaoPauloNA/athena) provider
  adapters (no adapter re-implementation)
- Documentation in English, Português, 中文, Español and Deutsch
