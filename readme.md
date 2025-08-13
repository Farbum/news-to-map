# News → Map (Streamlit + Gemini + Nominatim)

Extract real-world locations from a news article (URL or pasted text), geocode them with OpenStreetMap’s Nominatim, and visualize results on an interactive Folium map inside a Streamlit app.

> Paste a URL or raw text → Gemini finds place names → Nominatim resolves coordinates → Folium map displays results.

---

## Table of Contents

- [Features](#features)
- [Project Layout](#project-layout)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
  - [1) Create a virtual environment](#1-create-a-virtual-environment)
  - [2) Install dependencies](#2-install-dependencies)
  - [3) Configure your API key](#3-configure-your-api-key)
- [Run the App](#run-the-app)
  - [A) Streamlit UI](#a-streamlit-ui)
  - [B) Command-line (no UI)](#b-command-line-no-ui)
- [How It Works](#how-it-works)
- [Configuration Notes](#configuration-notes)
- [Troubleshooting](#troubleshooting)
- [Development Tips](#development-tips)
- [License](#license)

---

## Features

- Article ingestion from URL *or* pasted text  
- Location extraction with **Google Gemini** (`gemini-2.5-pro`)  
- Geocoding via **OpenStreetMap Nominatim** (rate-limited & cached)  
- Interactive map with **Folium** rendered in **Streamlit**  
- CLI mode for quick non-UI runs

---

## Project Layout

```
src/
  app.py                      # Streamlit app wrapper
  main_pipeline.py            # Orchestrates text → locations → coords → map
  article_text_extractor.py   # URL → article text
  nlp_loc_extractor.py        # Gemini call → structured locations
  geocode_loc_finder.py       # Locations → coordinates (Nominatim)
  map_viz.py                  # Folium map creation & saving
  .streamlit/
    secrets.toml              # Streamlit secrets (GEMINI_API_KEY lives here)
  .vscode/
    settings.json             # Optional editor config
.gitignore
.env                          # Local dev env vars (GEMINI_API_KEY lives here)
geocode_cache.sqlite          # Auto-created by requests-cache
interactive_map.html          # Optional map export
readme.md
requirements.txt
```

---

## Prerequisites

- **Python 3.9+** (3.10/3.11 recommended)
- A **Google AI Studio** API key for **Gemini**
- Internet access (for article fetches, Gemini API, and Nominatim)

> Please respect the **OpenStreetMap/Nominatim usage policy**. This app already rate-limits to ~1 request/second.

---

## Setup

### 1) Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 2) Configure your API key

You can set the same key in both places below. Streamlit uses `secrets.toml`; the CLI reads `.env` / environment variables.

**Option A — `.env` at repo root (for local dev & CLI)**
```
GEMINI_API_KEY="your_api_key_here"
```

**Option B — Streamlit secrets (`.streamlit/secrets.toml`)**
```toml
GEMINI_API_KEY = "your_api_key_here"
```

`app.py` reads `st.secrets["GEMINI_API_KEY"]`.  
`main_pipeline.py` falls back to the `GEMINI_API_KEY` environment variable (loaded via `python-dotenv`) if no key is passed in.

---

## Run the App

### A) Streamlit UI

From the project root (with the venv activated):

```bash
streamlit run src/app.py
```

### B) Command-line (no UI)

Process a URL:
```bash
python src/main_pipeline.py --url "https://example.com/news/article"
```

Process pasted text:
```bash
python src/main_pipeline.py --text "Paste the full article text here"
```

Provide an API key explicitly (optional if using `.env`/secrets):
```bash
python src/main_pipeline.py --api-key "your_api_key_here" --url "https://example.com/news/article"
```

---

## How It Works

- **`ArticleLocationExtractor`** (`src/main_pipeline.py`)
  - Initializes the **Gemini** client (default model: `gemini-2.5-pro`).
  - Configures **Nominatim** with `RateLimiter(min_delay_seconds=1.0)`.
  - Enables **requests-cache** with a 7-day expiry (`geocode_cache.sqlite`).
  - Pipeline:
    1. URL → text (`article_text_extractor.extract_article_text`)
    2. text → locations (`nlp_loc_extractor.extract_locations_with_gemini`)
    3. locations → lat/lon (`geocode_loc_finder.geocode_nominatim`)
    4. data → map (`map_viz.create_styled_map`, rendered in Streamlit)

If a site blocks scraping (`403 Forbidden`), use **Paste text** mode.

---

## Configuration Notes

- **Model**: Defaults to `gemini-2.5-pro`. You can pass a different `model_name` when creating `ArticleLocationExtractor`.
- **Caching**: `geocode_cache.sqlite` is created automatically. Delete it to force fresh geocoding.
- **Rate limiting**: Keep the 1 req/sec rate to respect Nominatim.
- **Map export**: In CLI mode, `map_viz.save_open_map_in_browser` may save/open `interactive_map.html`.

---

## Troubleshooting

- **`ValueError: Gemini API key not provided`**  
  Ensure `.env` or `.streamlit/secrets.toml` is set, or pass `--api-key`.

- **`403 Forbidden` when fetching a URL`**  
  The site likely blocks bots. Use **Paste text** mode.

- **`ModuleNotFoundError`**  
  Re-install deps: `pip install -r requirements.txt`. Verify package names (`google-genai`, `requests-cache`, `streamlit-folium`, etc.).

- **Map doesn’t render in Streamlit**  
  Start with `streamlit run src/app.py` and ensure `streamlit-folium` is installed.

- **Slow geocoding**  
  Normal for first runs; cache speeds up repeats.

---
