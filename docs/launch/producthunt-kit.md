# Product Hunt launch kit — Aletheia

## Tagline (60 chars max)
Aletheia for coding agents: is "done" actually true?

## Short description (260 chars)
Coding agents say "done, all tests passing" — Aletheia checks. It runs your agent in a sandbox, injects hidden tests after the claim, and reports SOLVED vs FALSE_SUCCESS vs honest failure. Open source, works with any CLI.

## Topics / categories
Developer Tools, Artificial Intelligence, Open Source

## First comment (maker comment)

Hey Product Hunt 👋

Maker here. This started when a coding agent gave me a great-looking report — "all tests passing" — for a fix that didn't work. I wanted to know how often that happens, so I built a small harness: agents do tasks in a sandbox, then a hidden test suite (which they never see) decides whether "done" was true.

Historical exploratory numbers from August 2026 are archived under `docs/benchmarks/2026-08-11/` and are **not** presented as current clean-run results. Any future launch post requires a clean, reproducible benchmark rerun committed to the repository first.

It's Python, MIT licensed, works with whatever CLI you already use (Claude Code, Codex, Cursor agent, OpenCode, …). Would love to hear what your agent does on the palindrome task — genuinely collecting those moments.

## Gallery checklist
- [ ] Screenshot: terminal run showing verdicts (use results table from Round 2)
- [ ] Screenshot: per-task table (palindrome 11/12 red row)
- [ ] Logo: simple truth/unconcealment mark, 240x240
- [ ] (optional) 60s video: run one episode live, show FALSE_SUCCESS appear

## Launch notes
- Launch Tuesday–Thursday, 00:01 PT for a full day of votes.
- Have the dev.to post and LinkedIn post live the same morning; link both.
- Repo must be public with README badges before launch day.
- CLI command: `aletheia` (legacy alias: `polygraph`).
