# Phase 3 (Separate Folder)

This folder implements **Phase 3: Candidate Retrieval Engine** from `docs/PhasewiseArchitecture.md`.

## Features

- Hard filters:
  - location
  - minimum rating
  - budget ceiling
- Soft filter:
  - cuisine match
- Pre-LLM scoring:
  - cuisine match signal
  - rating signal
  - budget fit signal
- Top-N candidate selection for prompt efficiency
- Controlled fallback relaxation:
  - relax cuisine constraint
  - reduce minimum rating
  - increase budget ceiling

## Run

```bash
python -m phase3.run_phase3
```

Defaults:

- Catalog input: `data/processed/restaurants_clean.csv`
- Preferences input: `data/phase2/standardized_preferences.json`
- Output: `data/phase3/candidate_set.json`

