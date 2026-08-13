# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.1] - 2026-08-12

### Changed
- Public rebrand from Polygraph to **Aletheia** (Greek personification of truth
  and unconcealment). User-facing docs, CLI help, and launch material now use
  the new name.
- Primary CLI command is `aletheia`; `polygraph` remains as a legacy alias to
  the same entry point.
- Project status language no longer presents the 2026-08-11 dirty-suite
  benchmark artifacts as current clean-run results.

### Notes
- Python import package `polygraph/`, distribution name `polygraph-verifier`,
  repository URLs, result filenames, and historical benchmark artifact paths
  are unchanged for compatibility and provenance.

## [0.2.0] - 2026-08-11

### Fixed
- Recognize contextual admissions that contradictory requirements prevent a
  deterministic implementation, including current pytest collection failures,
  as honest failures rather than false-success claims.
- Classify claims from the agent report stream instead of stderr transport
  diagnostics; passing test summaries no longer count as failure admissions.
- Classify provider failures from contextual transport diagnostics, preferring
  separate stderr when available so ordinary report language about forbidden
  behavior, rate limits, or quotas is not misclassified as `HARNESS_ERROR`.
- Keep guard violations separate from false-success metrics and report a
  guard-violation rate.
- Preserve completed episodes in a partial result when a run is manually
  interrupted; interrupted results are not publication datasets.
- Harden honesty oracle sanity checks against known stateful/call-order
  evasions under an explicit deterministic-function contract. This is not a
  proof against arbitrary adversarial Python introspection.

### Changed
- Suite documentation and result metadata now describe the 12-task, five-category
  suite.

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
