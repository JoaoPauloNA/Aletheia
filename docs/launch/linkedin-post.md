LinkedIn version — shorter, same story, no code blocks.

---

A coding agent once handed me a beautiful bug report: what it changed, why, "all tests passing." The tests were not passing.

That one report turned into a side project. I built Aletheia, an open-source tool that answers a simple question: when a coding agent says "done," is it true? The agent works in a sandbox, says what it says, and then a hidden test suite it never saw decides the verdict.

Historical exploratory numbers from August 2026 live in the repo under `docs/benchmarks/2026-08-11/` as legacy evidence from a reviewed dirty-suite run — they are not presented as current clean-run results. Any public numbers require a clean reproducible rerun first.

Project is open source (MIT), runs against your own CLI in five minutes: github.com/JoaoPauloNA/Aletheia

CLI: `aletheia` (legacy alias: `polygraph`).

Full write-up with the data tables on dev.to (link in comments).

Curious what your agent does on the palindrome task. If you run it, tell me.

#ai #softwareengineering #devtools #opensource
