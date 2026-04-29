# Phase 4 (Separate Folder) - Groq LLM

This folder implements **Phase 4: LLM Recommendation Layer** from `docs/PhasewiseArchitecture.md` using **Groq**.

## Components

- `prompt_builder.py`
  - Builds strict prompts with candidate IDs and JSON output schema.
- `llm_service.py`
  - Calls Groq Chat Completions API.
- `guardrails.py`
  - Validates LLM output format.
  - Ensures recommendations only use provided candidates.
  - Falls back to deterministic ranking if output is invalid/unavailable.
- `run_phase4.py`
  - Runs the full Phase 4 flow from Phase 3 candidate set.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set Groq key:

```bash
set GROQ_API_KEY=your_groq_api_key
```

## Run

Normal run (Groq):

```bash
python -m phase4.run_phase4
```

Dry-run (no LLM call, deterministic fallback):

```bash
python -m phase4.run_phase4 --dry-run
```

## IO

- Input: `data/phase3/candidate_set.json`
- Output: `data/phase4/recommendations.json`

