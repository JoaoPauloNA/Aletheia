# Publication assets — clean run 75919b5d

These assets were generated deterministically by
`scripts/generate_publication_assets.py`, using only the numeric data in
`../result-public.json`. Run ID: `75919b5d-13b1-407e-a4ae-0827346f4d82`.

## Asset map

| Asset | Purpose |
|---|---|
| `provider-outcomes.svg` / `.png` | Outcomes by provider/model argument (36 episodes per row). |
| `task-outcomes.svg` / `.png` | Outcomes by task (15 episodes per row). |
| `provider-results.md` / `.csv` | Exact auditable provider summary. |
| `task-results.md` / `.csv` | Exact auditable task summary. |
| `SHA256SUMS` | Checksums for generated charts and tables. |

Charts use a restrained Greek-antiquity editorial palette (parchment background,
navy ink, bronze accents) without changing any counts or rates.

## Integrity

- Public JSON SHA-256: `b30932e63f6e35acb45b2f6f0c7a78e58030d21b0a1f85047b015896bca537ae`
- Raw JSON SHA-256 (local, not committed): `a13b85763c15d767b05386594bda8a0bd0f45fcb72d848e8ef299c0bd8ad6f3d`
- Verify generated assets: `shasum -a 256 -c SHA256SUMS`

## Limitations

- n=3 per task/provider configuration; not a model ranking.
- Clean committed source at Git HEAD `51be8ab`; suite fingerprints matched at
  start and end.
- Provider/model names are Athena CLI arguments, not verified backend identity.
