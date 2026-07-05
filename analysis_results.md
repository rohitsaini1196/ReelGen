# Codebase Scan & Current State Analysis

We conducted a thorough scan of the codebase to determine the current state of **ReelGen-V3**. Below is a summary of what has been implemented, what remains as a gap relative to the **ReelGen-V3 Technical Specification**, and the next steps to get the pipeline fully operational.

---

## 🔍 Codebase Overview

The codebase is currently structured flat in the root directory (unlike the modular folder structure proposed in the specification).

### Core Components Found
- [reelgen.py](file:///Users/rohit/projects/autoreel/reelgen.py): CLI entry point using the `click` library.
- [director.py](file:///Users/rohit/projects/autoreel/director.py): Orchestrates creative planning (supports Claude, OpenAI, and local Ollama fallback).
- [prompts.py](file:///Users/rohit/projects/autoreel/prompts.py): System and user prompts for scriptwriting and beat planning.
- [curator.py](file:///Users/rohit/projects/autoreel/curator.py): Fulfillment engine fetching stock clips (supports Pexels API and local library).
- [visual_qa.py](file:///Users/rohit/projects/autoreel/visual_qa.py): Sharpness (Laplacian variance) and resolution validation.
- [text_renderer.py](file:///Users/rohit/projects/autoreel/text_renderer.py): Pillow-based transparent overlay frame renderer for safe zones.
- [compositor.py](file:///Users/rohit/projects/autoreel/compositor.py): Concatenates video segments and overlays text using MoviePy v2.
- [library.py](file:///Users/rohit/projects/autoreel/library.py): Manages local footage library indexing.
- [trend_bank.py](file:///Users/rohit/projects/autoreel/trend_bank.py): Defines style presets and mood mappings.
- [music_engine.py](file:///Users/rohit/projects/autoreel/music_engine.py): Maps video moods to search tags for IG trending audio.
- [delivery.py](file:///Users/rohit/projects/autoreel/delivery.py): Telegram delivery implementation.
- [models.py](file:///Users/rohit/projects/autoreel/models.py): Contains Pydantic V2 schemas (`Asset`, `Beat`, `ReelPlan`).

---

## ⚖️ Gaps vs. Technical Specification

| Feature Area | Spec Requirement | Current Implementation State | Gap Level |
| :--- | :--- | :--- | :--- |
| **Project Directory Structure** | Modular subdirectories (`creative/`, `assets/`, `style/`, `text/`, `compose/`) | Flat directory structure | 🟡 Minor |
| **LLM Orchestration** | Resilient schema generation and fallback | Strict Pydantic parsing can fail on local Ollama outputs due to missing fields | 🔴 Critical |
| **Asset Curation** | Search Pexels + Pixabay; download candidates & score; pick best | Only Pexels implemented. Pixabay is a stub. Only downloads first result; no multi-candidate QA check | 🔴 Critical |
| **Visual QA** | Resolution, sharpness, palette matching, motion stability | Sharpness and resolution checks work. Palette matching and motion stability are stubs | 🟡 Minor |
| **Style & Color Grading** | FFmpeg filters (brightness, contrast, saturation, vignette, grain) | Commented out in `compositor.py` | 🔴 Critical |
| **Motion Effects** | Ken Burns (slow zoom) + handheld shake | Commented out / missing | 🔴 Critical |
| **Typography & Fonts** | Google Fonts TTFs; 5 text background styles; entrance/exit animations | Fonts directory is empty. Animations and context-aware positioning are missing | 🔴 Critical |
| **Transitions** | Hard cuts, cross-dissolves, whip-pans | Simple crossfade only. No whip-pan or swipe | 🟡 Minor |

---

## ⚡ Current Execution Status

1. **API Keys**:
   - The OpenAI API key in `.env` has exceeded its quota, resulting in `429 Insufficient Quota`.
   - The Anthropic API key is a placeholder starting with `sk-ant-api03`.
   - To make the project functional out-of-the-box, we updated `.env` to fallback to the local Ollama instance using the installed `llama3.2:3b` model.

2. **Ollama Test Outcome**:
   - The `llama3.2:3b` model successfully generates storyboard JSON, but occasionally omits fields like `hashtags` or `estimated_duration` depending on the run. This causes Pydantic validation errors.
   - **Fix needed**: Make `ReelPlan` schema defaults more robust (e.g. `hashtags` default to empty list, `estimated_duration` calculated if missing).

---

## 🗺️ Recommended Roadmap / Next Steps

To align the project with the original vision and make it production-ready, we should execute the following sprints:

### 1. Robust LLM & Scaffolding Fixes
- Add Pydantic defaults in [models.py](file:///Users/rohit/projects/autoreel/models.py) to prevent failure on minor LLM formatting omissions.
- Restructure files into the modular subdirectories (`creative/`, `assets/`, `style/`, `text/`, `compose/`) if desired, or keep flat while cleaning up.

### 2. Complete Asset & Style Pipelines (Phase 2 Focus)
- Implement Pixabay API search.
- Enable multi-candidate downloading and best-clip selection using the visual QA score in [curator.py](file:///Users/rohit/projects/autoreel/curator.py).
- Implement the Color Grading and Ken Burns filters in [compositor.py](file:///Users/rohit/projects/autoreel/compositor.py).

### 3. Advanced Typography (Pillow & Fonts)
- Download and place standard Google Fonts in `fonts/` (`Montserrat`, `Bebas Neue`, `Playfair Display`, `Inter`, `Caveat`).
- Implement modern text background styling (pill, frosted, outline) and entrance animations (fade-up, pop-scale).
