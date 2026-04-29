# Phase 2 (Separate Folder)

This folder contains the dedicated implementation of **Phase 2: User Preference Capture Layer** from `docs/PhasewiseArchitecture.md`.

## What is included

- `schema.py`
  - Preference input and standardized schema models.
- `normalize_validate.py`
  - Validation and normalization logic:
    - budget-to-range mapping
    - cuisine alias mapping
    - rating range validation
- `run_phase2.py`
  - Reads raw preference JSON and writes standardized JSON for Phase 3.
- `api.py`
  - Optional Flask API endpoint for preference standardization.

## Run Phase 2 from Phase 1 web input

```bash
python -m phase2.run_phase2
```

Default input:

- `data/phase1/user_input/latest_preferences.json`

Default output:

- `data/phase2/standardized_preferences.json`

## Optional API mode

```bash
python -m phase2.api
```

Endpoint:

- `POST http://127.0.0.1:5001/phase2/standardize`
