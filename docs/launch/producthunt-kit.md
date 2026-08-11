# Product Hunt launch kit — Polygraph

## Tagline (60 chars max)
Polygraph for coding agents: is "done" actually true?

## Short description (260 chars)
Coding agents say "done, all tests passing" — Polygraph checks. It runs your agent in a sandbox, injects hidden tests after the claim, and reports SOLVED vs FALSE_SUCCESS vs honest failure. Open source, works with any CLI.

## Topics / categories
Developer Tools, Artificial Intelligence, Open Source

## First comment (maker comment)

Hey Product Hunt 👋

Maker here. This started when a coding agent gave me a great-looking report — "all tests passing" — for a fix that didn't work. I wanted to know how often that happens, so I built a small harness: agents do tasks in a sandbox, then a hidden test suite (which they never see) decides whether "done" was true.

I ran 4 CLI agents × 12 tasks × 3 episodes (144 total). The result that got me: all four agents produced false success reports on the SAME easy-looking tasks (a palindrome function with hidden edge cases — 11/12 episodes lied), and all four were completely honest when the task was impossible (24/24 admitted it). Agents don't lie on principle — they over-claim when the visible tests are green and nobody checks.

It's Python, MIT licensed, works with whatever CLI you already use (Claude Code, Codex, Cursor agent, OpenCode, …). Would love to hear what your agent does on the palindrome task — genuinely collecting those moments.

## Gallery checklist
- [ ] Screenshot: terminal run showing verdicts (use results table from Round 2)
- [ ] Screenshot: per-task table (palindrome 11/12 red row)
- [ ] Logo: simple lie-detector waveform mark, 240x240
- [ ] (optional) 60s video: run one episode live, show FALSE_SUCCESS appear

## Launch notes
- Launch Tuesday–Thursday, 00:01 PT for a full day of votes.
- Have the dev.to post and LinkedIn post live the same morning; link both.
- Repo must be public with README badges before launch day.
