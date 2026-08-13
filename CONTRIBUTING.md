# Contributing

Thanks for considering a contribution. Aletheia lives or dies by the
credibility of its number, so the bar here is mostly about rigor.

## Adding a task to the suite

Tasks are the highest-leverage contribution. A task is a directory under
`suite/tasks/<id>/` with:

```
task.json     manifest: id, category, prompt, scope, canary
seed/         everything the agent sees (including VISIBLE tests)
oracle/       hidden tests, injected only at verification time
```

Rules that are not negotiable:

1. **The oracle must stay hidden.** Never reference oracle content in the
   prompt or in seed files. Each task gets a unique canary string (format
   `CNRY-xxxx-xxxxxxxx`) placed in a comment inside the oracle; the loader
   refuses tasks whose canary is missing.
2. **The oracle must be fair.** It tests what a correct solution would
   reasonably discover from the prompt and visible tests — no trick
   requirements that were never hinted at. An unfair oracle produces false
   accusations, which are worse than missed lies.
3. **No model judges anything.** Verification is exit codes, file hashes,
   diffs and canaries. Proposals that require an LLM in the verification
   path are out of scope by design.
4. **Categories**: `basic-correctness`, `multi-file-regression`,
   `honesty`, `cheat-detection`. Propose a new category in an issue first.

Before opening a PR, validate your task end to end:

```bash
# the seed must be solvable — write a reference solution, then:
python -m pytest <tmp-copy-of-seed+oracle>
```

Both the visible suite and the oracle must pass against the reference
solution, and the visible suite should *fail* meaningfully without one.

## Code

- Python ≥ 3.10, `ruff` clean, `pytest` green.
- Determinism everywhere: no network, no clock-dependent logic in guards.
- A broken episode must never kill a run — catch, record as
  `HARNESS_ERROR`, move on.

## Reporting issues

If Aletheia accused an agent wrongly, that is a severity-1 bug. Please
include the episode JSON (it is written to `results/`) and the workspace
state if you still have it.
