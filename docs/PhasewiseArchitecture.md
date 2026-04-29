# Phase-Wise Architecture  
**AI-Powered Restaurant Recommendation System (Zomato Use Case)**

This document defines a practical implementation architecture in phases so the system can be built iteratively, tested continuously, and scaled safely.

---

## Phase 1: Data Foundation

### Goal
Build a reliable restaurant data layer from the Zomato dataset.

### Components
- **Dataset Source**: Hugging Face dataset (`ManikaSaini/zomato-restaurant-recommendation`)
- **Ingestion Module**: Fetches and stores raw data
- **Preprocessing Pipeline**:
  - Missing value handling
  - Type normalization (cost, rating, city, cuisine)
  - Duplicate removal
- **Structured Storage**:
  - Option A: CSV/Parquet for MVP
  - Option B: SQL database for production

### Output
- Clean restaurant catalog with required fields:
  - `restaurant_name`
  - `location`
  - `cuisine`
  - `cost_for_two` (or equivalent)
  - `rating`
  - optional metadata (service type, tags)

### Implemented Files
- `phase1/data_ingestion.py` — Fetches raw dataset from Hugging Face
- `phase1/preprocess.py` — Cleans, normalizes, and deduplicates
- `phase1/run_phase1.py` — CLI runner
- `phase1/web_ui.py` — Simple Flask form for collecting user preferences (input source only)

---

## Phase 2: User Preference Capture Layer

### Goal
Collect and validate user requirements for recommendations.

### Components
- **Input Interface** (Web UI form → JSON file, Phase 2 API optional)
- **Preference Schema**:
  - location
  - budget (low / medium / high)
  - cuisine (supports multi-cuisine, synonyms)
  - minimum_rating (0–5)
  - optional_preferences (comma-separated tags)
- **Validation & Normalization**:
  - Budget to numeric range mapping
  - Cuisine alias mapping (e.g., "North Indian" → "Indian")
  - Rating range checks

### Output
- Standardized user preference object ready for filtering.

### Implemented Files
- `phase2/schema.py` — Dataclasses for raw input and standardized preferences
- `phase2/normalize_validate.py` — Validation logic, alias mapping, budget ranges
- `phase2/run_phase2.py` — CLI runner
- `phase2/api.py` — Flask endpoint for programmatic validation

---

## Phase 3: Candidate Retrieval Engine

### Goal
Generate a shortlist of restaurants that match explicit constraints.

### Components
- **Rule-Based Filter Service**:
  - Hard filters: location, min rating, budget ceiling
  - Soft filters: cuisine match, optional preferences
- **Scoring Layer (pre-LLM)**:
  - Weighted score for each candidate (cuisine 40%, rating 40%, budget 20%)
  - Top-N selection for prompt efficiency
- **Fallback Strategy**:
  - Relax filters in controlled order if no results
    1. Relax cuisine constraint
    2. Reduce minimum rating
    3. Increase budget ceiling
    4. Relax location constraint
  - Provide user-friendly fallback message

### Output
- Top candidate set (e.g., 10–30 restaurants) with structured scores.

### Implemented Files
- `phase3/retrieval.py` — Filter, score, and fallback logic
- `phase3/run_phase3.py` — CLI runner

---

## Phase 4: LLM Recommendation Layer

### Goal
Use the LLM to rank candidates and produce natural-language explanations.

### Components
- **Prompt Builder**:
  - Injects user preferences + candidate list
  - Includes strict output format instructions
  - Requests JSON-only response (no markdown fences)
- **LLM Inference Service**:
  - Uses Groq API with `llama-3.3-70b-versatile`
  - Ranks top restaurants
  - Generates reason for each recommendation
  - Optionally produces comparison summary
- **Output Parser/Guardrails**:
  - Validates JSON format
  - Ensures recommendations only come from provided candidates
  - Deterministic fallback if LLM fails or returns garbage

### Output
- Ranked recommendations with explainable AI-generated rationale.

### Implemented Files
- `phase4/prompt_builder.py` — Builds system + user messages for Groq
- `phase4/llm_service.py` — Groq API call, JSON extraction
- `phase4/guardrails.py` — Validation, deduplication, deterministic fallback
- `phase4/run_phase4.py` — CLI runner

---

## Phase 5: Presentation & Experience Layer (Backend + Frontend)

### Goal
Build a production-ready backend API and a modern frontend that together provide a complete end-to-end user experience — from preference input to recommendation display.

### 5A: Backend (Unified Flask API)

#### Architecture
A single Flask application that exposes a REST API for the complete recommendation pipeline. All phase logic (Phase 1–4) is orchestrated behind one endpoint.

#### Folder Structure
```
backend/
├── app.py                  # Flask application entry point
├── config.py               # Configuration (env vars, model settings, paths)
├── routes/
│   ├── __init__.py
│   ├── recommend.py        # POST /api/recommend — main recommendation endpoint
│   ├── health.py           # GET  /api/health — service health check
│   └── metadata.py         # GET  /api/metadata — available locations, cuisines, etc.
├── services/
│   ├── __init__.py
│   ├── pipeline.py         # Orchestrates Phase 2 → 3 → 4 sequentially
│   ├── preference_service.py    # Wraps Phase 2 validation/normalization
│   ├── retrieval_service.py     # Wraps Phase 3 candidate retrieval
│   ├── llm_service.py           # Wraps Phase 4 LLM ranking
│   └── formatter.py             # Formats final response for frontend
├── errors.py               # Custom exception classes + error handlers
└── requirements.txt        # Backend-specific dependencies
```

#### API Contract

**`POST /api/recommend`**
```json
// Request
{
  "location": "bangalore",
  "budget": "medium",
  "cuisine": "indian, chinese",
  "minimum_rating": 3.5,
  "optional_preferences": "family-friendly"
}

// Success Response (200)
{
  "status": "success",
  "source": "llm",
  "llm_model": "llama-3.3-70b-versatile",
  "recommendations": [
    {
      "rank": 1,
      "restaurant_name": "Saffron House",
      "location": "Koramangala",
      "cuisine": "North Indian, Chinese",
      "cost_for_two": 1200,
      "rating": 4.3,
      "reason": "Highly rated North Indian restaurant within budget..."
    }
  ],
  "comparison_summary": "Top picks emphasize cuisine alignment and...",
  "applied_filters": {
    "location": "bangalore",
    "minimum_rating": 3.5,
    "budget_max": 2000,
    "preferred_cuisines": ["indian", "chinese"]
  },
  "fallback_actions": []
}

// Validation Error Response (400)
{
  "status": "error",
  "error_type": "validation",
  "message": "minimum_rating must be between 0 and 5."
}

// Server Error Response (500)
{
  "status": "error",
  "error_type": "internal",
  "message": "An unexpected error occurred."
}
```

**`GET /api/metadata`**
```json
// Response (200)
{
  "locations": ["bangalore", "delhi", "mumbai", ...],
  "cuisines": ["indian", "chinese", "italian", ...],
  "budget_options": ["low", "medium", "high"],
  "rating_range": { "min": 0, "max": 5 }
}
```

**`GET /api/health`**
```json
{
  "status": "ok",
  "catalog_loaded": true,
  "catalog_rows": 8530,
  "groq_key_set": true
}
```

#### Key Design Decisions
1. **Single pipeline endpoint**: No per-phase APIs exposed to frontend — one call does everything
2. **Catalog loaded once at startup**: Restaurant catalog loaded into memory on application boot, not per-request
3. **CORS enabled**: Frontend served separately during development
4. **Error boundaries**: Each phase wrapped in try/except, errors propagated with clear messages
5. **Timeout handling**: Groq calls have configurable timeout; on failure, deterministic fallback fires

---

### 5B: Frontend (Modern Web UI)

#### Architecture
A modern, component-driven frontend application built with **Next.js (React)** that communicates seamlessly with the backend API. It leverages React hooks for state management and dynamic data fetching.

#### Folder Structure
```
frontend/
├── app/
│   ├── layout.js           # Next.js root layout with global font/meta settings
│   ├── page.js             # Main SPA application page (Client Component)
│   └── globals.css         # Design tokens, variables, and custom styling
├── next.config.mjs         # API proxy rewrites to Flask backend
├── package.json            # Node dependencies (React, Next.js)
└── public/                 # Static assets (images, fonts, SVG placeholders)
```

#### UI Sections

1. **Hero Section**
   - App title, tagline, subtle animated gradient background  
   - Immediately draws user into the input form

2. **Preference Input Form**
   - Location: Autocomplete searchable dropdown (dynamically populated & alphabetized from `/api/metadata`).
   - Cuisines: Autocomplete searchable dropdown (populated from metadata) paired with a **"Veg Only" toggle switch**.
   - Budget: Autocomplete dropdown mapped to specific ranges (e.g., Up to 500, 1000-1500).
   - Minimum Rating: Dropdown picker for thresholds.
   - Additional Preferences: Text input with autocomplete suggestions for tags (e.g., "Quiet Romantic", "Vegan Friendly").
   - Submit button with loading state.

3. **Loading State**
   - Skeleton card placeholders with shimmer animation
   - "Finding the best restaurants for you..." message

4. **Results Section**
   - Recommendation cards showing essential metrics: restaurant name, location, cuisine badges, rating stars, and exact **cost for two as per data**.
   - **Explainability**: A dedicated "Why we chose this" block in the card displaying the LLM's tailored rationale for that specific restaurant.
   - Source indicator (LLM vs Deterministic Fallback).
   - Error/empty-state messaging with suggested actions.

5. **Footer**
   - Credits, data source link

#### Design System
- **Color Palette**: Dark mode primary with accent highlights (deep slate `#0f172a`, warm amber `#f59e0b`, emerald `#10b981`)
- **Typography**: Inter (Google Fonts) for clean readability
- **Cards**: Glassmorphism-style with backdrop-blur, subtle borders
- **Animations**: Fade-in on results, hover lift on cards, pulse on loading
- **Responsive**: Mobile-first, with breakpoints at 640px, 768px, 1024px

---

### 5C: Streamlit Cloud UI (Alternative Frontend)

#### Architecture
A lightweight, Python-native frontend designed specifically for rapid deployment on **Streamlit Community Cloud**. It bypasses the Flask API to directly invoke the backend Python pipeline, significantly reducing deployment complexity.

#### Key Features
- **Direct Pipeline Integration**: Imports `run_pipeline` from `backend.services.pipeline` natively instead of making HTTP requests.
- **Serverless-Friendly**: Requires only a GitHub repository connected to Streamlit Cloud. No separate backend server provisioning needed.
- **Caching**: Uses `@st.cache_data` to load the dataset into memory once per session/container, minimizing latency.
- **UI Components**: 
  - Dual-column layout for preferences
  - Customized CSS for aesthetic dark-mode restaurant cards
  - Real-time pipeline processing with loading spinners

---

### 5D: Data Flow (End-to-End via API)

```
┌──────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                   │
│                                                                      │
│  User fills form  ──►  POST /api/recommend  ──►  Display results     │
│  (location, budget,     { JSON payload }          (cards, summary)   │
│   cuisine, rating)                                                   │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                           BACKEND (Flask)                            │
│                                                                      │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐            │
│  │  Phase 2    │    │  Phase 3     │    │  Phase 4     │            │
│  │  Validate & │───►│  Filter &    │───►│  LLM Rank &  │            │
│  │  Normalize  │    │  Score       │    │  Explain     │            │
│  └─────────────┘    └──────────────┘    └──────────────┘            │
│         │                  │                   │                      │
│         ▼                  ▼                   ▼                      │
│  Standardized       Candidate Set       Ranked + Explained           │
│  Preferences        (top 20)            Recommendations              │
│                                                │                      │
│                                     ┌──────────┴──────────┐          │
│                                     │  Formatter          │          │
│                                     │  (Phase 5 output)   │          │
│                                     └──────────┬──────────┘          │
│                                                │                      │
│                                          JSON Response               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Phase 6: Quality, Safety, and Evaluation

### Goal
Ensure recommendation quality, stability, and correctness.

### Components
- **Test Suite**:
  - Unit tests for filtering and scoring
  - Unit tests for validation and normalization
  - Integration tests for full pipeline (Phase 2 → 3 → 4)
  - API endpoint tests (backend routes)
- **Offline Evaluation**:
  - Precision@K / relevance checks (if labeled data is available)
  - Human review for explanation quality
- **Prompt Regression Checks**:
  - Detect quality drops after prompt/model updates
  - Benchmark suite with fixed inputs

### Output
- Measurable quality benchmarks and reliable behavior.

---

## Phase 7: Deployment & Observability

### Goal
Run the system in production with monitoring and continuous improvement.

### Components
- **Service Deployment**:
  - Backend: Flask behind Gunicorn/Waitress (for API clients)
  - Frontend (Node.js): Static files served via Next.js or Nginx
  - **Frontend (Streamlit)**: Hosted natively on Streamlit Community Cloud linked via GitHub.
  - Docker Compose for full containerized deployment (optional)
- **Caching**:
  - Cache repeated preference queries
  - Cache LLM responses for cost control
- **Monitoring & Logging**:
  - Latency tracking per phase
  - LLM token usage and cost
  - Errors and fallback rate
  - Recommendation acceptance signals (if available)

### Output
- Production-ready, observable recommendation service.

---

## End-to-End Data Flow (High Level)

1. User opens frontend and fills preference form  
2. Frontend sends `POST /api/recommend` to backend  
3. Backend validates and normalizes input (Phase 2)  
4. Candidate retrieval filters and scores restaurants (Phase 3)  
5. Top candidates are sent to LLM via prompt builder (Phase 4)  
6. LLM returns ranked recommendations with explanations  
7. Response formatter returns final user-facing JSON (Phase 5)  
8. Frontend renders recommendation cards with reason, rating, cost  
9. Logs/metrics are captured for monitoring and improvement (Phase 7)

---

## Updated Project Folder Structure

```
Zomatooo/
├── .env                         # API keys (GROQ_API_KEY)
├── requirements.txt             # Python dependencies
│
├── docs/
│   ├── PhasewiseArchitecture.md # This document
│   ├── Problemstatement.md
│   └── DetailedEdgeCases.md
│
├── data/
│   ├── processed/               # Phase 1 output (cleaned CSV/Parquet)
│   ├── phase1/                  # User input JSON from web form
│   ├── phase2/                  # Standardized preferences
│   ├── phase3/                  # Candidate set
│   └── phase4/                  # LLM recommendations
│
├── phase1/                      # Data ingestion & preprocessing
├── phase2/                      # Preference validation & normalization
├── phase3/                      # Candidate retrieval engine
├── phase4/                      # LLM recommendation layer
│
├── backend/                     # ★ Phase 5A — Unified Flask API
│   ├── app.py
│   ├── config.py
│   ├── errors.py
│   ├── requirements.txt
│   ├── routes/
│   │   ├── recommend.py
│   │   ├── health.py
│   │   └── metadata.py
│   └── services/
│       ├── pipeline.py
│       ├── preference_service.py
│       ├── retrieval_service.py
│       ├── llm_service.py
│       └── formatter.py
│
├── frontend/                    # ★ Phase 5B — Modern Web UI
│   ├── app/
│   │   ├── layout.js
│   │   ├── page.js
│   │   └── globals.css
│   ├── next.config.mjs
│   ├── package.json
│   └── public/
│
├── streamlit_app.py             # ★ Phase 5C — Streamlit Cloud Frontend
│
├── tests/                       # Phase 6 — Quality & testing
│   ├── test_phase2.py
│   ├── test_phase3.py
│   ├── test_phase4.py
│   ├── test_pipeline.py
│   └── test_api.py
│
└── src/                         # Shared utilities (if needed)
    └── __init__.py
```

---

## Suggested MVP Cut (Fastest Path)

Implement first:
- Phase 1 (basic preprocessing) ✅ Done
- Phase 2 (simple input validation) ✅ Done
- Phase 3 (hard filtering + basic scoring) ✅ Done
- Phase 4 (single prompt template + fixed top 5 output) ✅ Done
- Phase 5 (backend API + Next.js UI with dynamic fields & reasoning display) ✅ Done

Add next:
- Phase 6 (tests + prompt regression)
- Phase 7 (monitoring + caching + production hardening)
