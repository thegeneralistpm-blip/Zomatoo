# Phase 1 (Separate Folder)

This folder contains a dedicated implementation of **Phase 1** from `docs/PhasewiseArchitecture.md`.

## What is included

- `data_ingestion.py`: loads raw restaurant data from Hugging Face
- `preprocess.py`: cleans, normalizes, and deduplicates records
- `run_phase1.py`: runs the full Phase 1 pipeline
- `web_ui.py`: basic web UI to capture user input preferences (MVP input source)

## Run data pipeline

```bash
python -m phase1.run_phase1
```

Outputs are written to:

- `data/processed/restaurants_clean.csv`
- `data/processed/restaurants_clean.parquet`

## Run basic web UI

```bash
python -m phase1.web_ui
```

Open:

- `http://127.0.0.1:5000`

Submitted preferences are saved to:

- `data/phase1/user_input/latest_preferences.json`
