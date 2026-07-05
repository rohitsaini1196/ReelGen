# 🎬 Technical Specification
## ReelGen V3
## Automated Instagram Reel Generator
Status: New Project (replacing V2)
Runtime: Local machine only
Budget: Free / minimal API costs ($0.00 – $0.01 per reel)
Output: On-demand generation
Date: March 31, 2026

# 1. Context & Decision

## 1.1 Why V2 fails
The current system (Python + Node.js/Remotion) produces reels that are immediately identifiable as AI-generated. Five root causes:
Generic stock footage — Pexels free clips are overused across every AI video tool. Viewers pattern-match them instantly.
Broadcast-style composition — Remotion renders clean/corporate motion graphics. Trending reels have a different visual language: handheld energy, jump cuts, IG-native text.
No visual intelligence — clips are matched by keyword only, not by how they actually look. A search for “beach sunset” returns clips with wildly different color temperatures, styles, and quality.
Linear pipeline with no quality gates — Topic → Script → Search → Download first result → Render. No curation, no scoring, no rejection.
Cookie-cutter text styling — preset “Minimal/Bold/Elegant” styles don’t match how real IG creators style text in 2025–2026.

## 1.2 Decision: start fresh
V3 is a new project, not a modification of V2. The tech stack changes fundamentally (dropping Node.js/Remotion entirely), the data models are different (ReelPlan dataclass vs JSON props), and the module structure is redesigned. Carrying V2 forward would mean more time ripping out Remotion and rewiring the orchestrator than building clean modules from scratch.
Reuse from V2: Pexels API client logic (~80 lines) and Telegram sender (~50 lines). Copy-paste into new structure, adapt to new interfaces.

## 1.3 Design philosophy
The goal is not to make “AI videos.” The goal is to make videos that look like a taste-conscious human made them in CapCut or InShot in 20 minutes. That means:
Clips feel curated, not randomly searched
Text looks like it came from IG’s native editor or CapCut templates
Transitions are cuts and simple zooms — not fancy wipes
Color and mood are consistent across the entire reel
Pacing matches current short-form rhythm: fast hook, breathing room in middle, punchy end
Music is suggested (by mood tag) but not embedded — IG’s free music library is superior to anything we can license

# 2. Tech Stack
Single-runtime Python project. No Node.js, no React, no npm. FFmpeg handles all video processing; MoviePy provides the Pythonic wrapper; Pillow handles text rendering with full font and positioning control.
Component
V2 (current)
V3 (new)
Why
Language
Python + Node.js
Python only
Single runtime, simpler setup, FFmpeg does heavy lifting
Video engine
Remotion (React)
FFmpeg + MoviePy
Direct pixel control, creator-style motion, no Node deps
Text rendering
Remotion typography
Pillow → FFmpeg
Exact font control, IG-native text styles, per-frame positioning
AI / LLM
GPT-4o (OpenAI)
Claude Sonnet or Ollama
Claude for quality (~$0.01/reel), Ollama for zero-cost local
Stock footage
Pexels API
Pexels + Pixabay + local lib
Multi-source + curation = less generic
Visual QA
None
Heuristic scoring
Reject blurry, dark, or color-mismatched clips before render
Music
None
Mood-tag suggestion
Suggests trending IG audio; no embedding needed

## 2.1 Dependencies
# requirements.txt
# Core
moviepy>=2.0             # Video composition (wraps FFmpeg)
Pillow>=10.0             # Text rendering + image processing
numpy>=1.24              # Frame manipulation + animation math
requests>=2.31           # API calls
# LLM (pick one or both)
anthropic>=0.30          # Claude API client
ollama>=0.2              # Ollama client (local LLM)
# Utilities
python-dotenv>=1.0       # Env vars
click>=8.1               # CLI framework
rich>=13.0               # Pretty terminal output
pydantic>=2.0            # Data validation for ReelPlan
# Optional
python-telegram-bot>=20.0  # Telegram delivery

## 2.2 System requirements
FFmpeg: brew install ffmpeg (macOS) or sudo apt install ffmpeg (Ubuntu). Required.
Python 3.11+: Required for modern type hints used throughout.
Fonts: Download Google Fonts TTFs (listed in Section 5.4) into fonts/ directory. Free, open license.
Ollama (optional): For zero-cost local LLM. Requires 8GB+ RAM. Install from ollama.com.

## 2.3 Environment variables
# .env
PEXELS_API_KEY="..."           # Required — free at pexels.com/api
PIXABAY_API_KEY="..."          # Required — free at pixabay.com/api
ANTHROPIC_API_KEY="sk-..."     # Optional — if using Claude for creative direction
TELEGRAM_BOT_TOKEN="..."       # Optional — if using Telegram delivery
TELEGRAM_CHAT_ID="..."         # Optional — if using Telegram delivery
LLM_BACKEND="claude"           # "claude" | "ollama" | "openai"

# 3. Architecture
The pipeline is a six-stage directed flow. Each stage has well-defined inputs and outputs. There are no feedback loops in V3 MVP — quality is ensured by scoring and rejection within each stage, not by re-running earlier stages.

### Pipeline flow
CLI Trigger
    │
    ▼

# 1. Creative Director (LLM)     →  ReelPlan JSON
    │
    ▼

# 2. Asset Curator               →  Scored & selected clips per beat
    │
    ▼

# 3. Style Engine                →  Color-graded + motion-enhanced clips
    │
    ▼

# 4. Text Renderer (Pillow)      →  Transparent text overlay frames
    │
    ▼

# 5. Compositor (MoviePy)        →  Assembled timeline with text
    │
    ▼

# 6. Output & Review             →  MP4 + metadata + IG caption + music suggestion

### Project structure
reelgen/
├── reelgen.py                  # CLI entry point (Click)
├── config.py                   # Global settings, API keys, paths
├── requirements.txt
│
├── creative/
│   ├── director.py             # LLM creative direction
│   ├── prompts.py              # All LLM prompts (versioned, tunable)
│   └── trend_bank.py           # Hook/style patterns from viral reels
│
├── assets/
│   ├── curator.py              # Multi-source clip search + download
│   ├── visual_qa.py            # Clip quality scoring (local, no API)
│   ├── local_library.py        # Personal curated clip library manager
│   └── sources/
│       ├── pexels.py           # Pexels API client
│       └── pixabay.py          # Pixabay API client
│
├── style/
│   ├── color_grade.py          # FFmpeg color grading per palette
│   ├── motion.py               # Ken Burns, subtle shake, zoom
│   └── presets.py              # Style presets (warm-analog, etc.)
│
├── text/
│   ├── renderer.py             # Pillow-based text frame generator
│   ├── fonts.py                # Font management + trending font registry
│   ├── layouts.py              # Text positioning strategies
│   └── animations.py           # Entrance/exit animation math
│
├── compose/
│   ├── compositor.py           # Final timeline assembly
│   ├── transitions.py          # Cut, dissolve, whip implementations
│   └── export.py               # FFmpeg encode + compress
│
├── output/                     # Generated reels + metadata
├── library/                    # Curated local clip library
├── fonts/                      # Trending font files (.ttf/.otf)
└── temp/                       # Download workspace (auto-cleaned)

### CLI interface
# Generate with specific topic
python reelgen.py --topic "Hidden cafés in Tokyo’s backstreets"
# Auto-generate (AI picks trending topic)
python reelgen.py --auto
# Specify style preset
python reelgen.py --topic "..." --style warm-analog
# Local library only (no API calls for footage)
python reelgen.py --topic "..." --local-only
# Preview mode (output plan as JSON, skip rendering)
python reelgen.py --topic "..." --preview
# Add clip to local library
python reelgen.py --add-to-library clip.mp4 --tags "beach,sunset,drone"

# 4. Module Specifications

## 4.1 Creative Director
Module: creative/director.py
Priority: The single most important module. Bad creative direction = bad reel regardless of rendering quality.
Input: topic string (user-provided or auto-generated)
Output: a validated ReelPlan (Pydantic model):
class VisualBeat(BaseModel):
    caption: str                    # Text shown on screen (3-7 words max)
    duration: float                 # Seconds (e.g., 2.5)
    search_queries: list[str]       # 3-5 queries, hyper-specific and visual
    visual_description: str         # What the clip should look like
    mood: str                       # calm | energetic | dreamy | raw
    text_position: str              # top | center | bottom
    text_style: str                 # clean | pill | shadow | outline | frosted
class ReelPlan(BaseModel):
    title: str
    hook: VisualBeat                # First 1.5-2s — must stop the scroll
    beats: list[VisualBeat]         # 3-4 middle beats
    closer: VisualBeat              # Final beat — CTA or emotional punch
    color_palette: list[str]        # 3 hex codes: primary, secondary, accent
    overall_mood: str               # For music suggestion + color grading
    style_preset: str               # warm-analog | cool-minimal | golden-hour | moody-dark
    music_suggestion: str           # e.g. "chill lo-fi, 90bpm"
    ig_caption: str                 # Ready-to-paste IG caption
    ig_hashtags: list[str]          # 15-20 relevant hashtags
    total_duration: float           # Target: 15-30 seconds
LLM abstraction: config.py switch between Claude API, Ollama (local), or any OpenAI-compatible API. The director module calls a unified generate() function that routes to the configured backend.
Prompt engineering rules (critical — enforce in prompts.py):
Hook must be a pattern interrupt: question, bold claim, "POV:" framing, or controversial take
Captions: 3–7 words maximum per beat. People don’t read long text in reels.
Search queries must be hyper-specific and visual. Not "beautiful beach" but "turquoise water overhead drone shot Bali"
Color palette: LLM picks from curated palette sets in trend_bank.py, not random hex codes
Total duration: 15–30 seconds. Under 15 feels rushed, over 30 loses attention.

## 4.2 Asset Curator
Module: assets/curator.py, assets/visual_qa.py, assets/sources/*.py
Key innovation over V2: don’t just search-and-download. Search, download candidates, score them, pick the best.
Search strategy per beat:
Generate 3–5 varied search queries from the beat’s visual_description and search_queries
Search Pexels + Pixabay (and local library if populated) — collect top 3 results per query
Download ~12 candidate clips per beat to temp/
Run Visual QA scoring on each candidate
Select the highest-scoring clip per beat
Trim to exact beat duration using ffprobe + FFmpeg
Visual QA scoring (local, no API calls):
Extract 3 frames from each clip (start, middle, end). Score each:
Resolution: must be ≥ 1080x1920. Reject anything below.
Aspect ratio: 9:16 preferred. 16:9 can be center-cropped but scores lower.
Sharpness: Laplacian variance on grayscale frame. Low = blurry = reject.
Brightness: mean pixel value. Reject extremes (too dark / blown out).
Color palette match: histogram distance against the director’s target palette. Closer = higher score.
Motion stability: optical flow variance between start/mid/end frames. High variance with low intended energy = shaky = penalize.
Final score = weighted sum. Clips below threshold are rejected. Weights are tunable in config.py.
Local library (Phase 3):
library/ directory with index.json containing metadata (tags, mood, dominant colors, source, duration). Curator checks local library FIRST, then falls back to API sources. CLI command --add-to-library auto-extracts metadata from clip.

## 4.3 Style Engine
Module: style/color_grade.py, style/motion.py, style/presets.py
Applies consistent visual treatment so all clips in a reel feel like they were shot in the same session.
Color grading presets:
Preset
Brightness
Contrast
Saturation
Grain
Vignette
Temp
warm-analog
+0.04
1.10
1.15
0.02
0.3
warm
cool-minimal
+0.06
1.05
0.90
0
0.1
cool
golden-hour
+0.03
1.15
1.25
0.01
0.4
golden
moody-dark
-0.05
1.20
0.85
0.03
0.5
teal-orange
Implementation: FFmpeg eq + colorbalance filters. Color grading happens per-clip before compositing.
Motion effects:
Ken Burns: FFmpeg zoompan filter. Slow zoom (0.05% per frame) + gentle pan. Applied to static or very slow clips.
Subtle zoom-in: 2–5% scale increase over beat duration. Applied to most clips for energy.
Handheld shake (Phase 2): random 1–3px translate per frame via MoviePy. Adds organic feel to too-stable footage.

## 4.4 Text Renderer
Module: text/renderer.py, text/fonts.py, text/layouts.py, text/animations.py
This is where V3 diverges most from V2. Instead of Remotion’s web-rendered text, we use Pillow to create transparent text overlay frames that look native to IG.
Font pack (Google Fonts, free):
Category
Fonts
clean
Plus Jakarta Sans Bold, Inter SemiBold
editorial
Playfair Display Bold, Cormorant Bold
bold-impact
Montserrat Black, Bebas Neue
handwritten
Caveat Bold, Dancing Script Bold
Text background styles:
pill: rounded rectangle, semi-transparent black (rgba 0,0,0,160), corner radius 12px, padding 16/24px. The most common IG-native text style.
frosted: blurred background region behind text. Requires compositing with blurred clip frame. blur_radius 20, white tint.
shadow: drop shadow only, no background. shadow_color black rgba 200, offset 2px, blur 4px.
outline: stroke around text, 3px width, black. Popular for bold/impact styles.
clean: white text, no background. For darker clips only.
Text animations:
fade-up (default): text fades in while moving up 20px. ease_out_cubic. 8 frames (~0.27s at 30fps). The #1 IG text animation.
pop-scale: text scales from 0 to ~1.05 to 1.0 (slight overshoot). ease_out_back. 6 frames. Good for bold/impact text.
typewriter: characters appear sequentially, 2 chars/frame. Good for hook text.
All animations also have a fade-out exit (reverse of entrance, shorter duration).
Safe zone (critical):
Never place text in the top 15% (IG username/header area) or bottom 10% (IG UI buttons). Safe area: 15%–90% of screen height, 5%–95% of width.

## 4.5 Compositor
Module: compose/compositor.py, compose/transitions.py, compose/export.py
Assembles the final reel from graded clips + text overlays. Key principle: simplicity wins. Real trending reels use mostly hard cuts.
Assembly order:
Load and trim each clip to beat duration
Apply style engine (color grade + motion) per clip
Apply transitions between clips
Overlay text renders at correct timestamps
Export final MP4
Transition strategy (matching real creator patterns):
Hard cut (70%): default. No transition effect. Just clip A ends, clip B starts.
Cross-dissolve (20%): for mood shifts between beats. 0.3–0.5s overlap via MoviePy crossfade.
Whip-pan (10%): for energy spikes. Horizontal motion blur bridge between clips.
Transition type is auto-selected based on mood change between consecutive beats.
Export settings (Instagram-optimized):
Setting
Value
Resolution
1080 x 1920 (9:16)
Codec
H.264 (libx264)
Frame rate
30 fps
CRF
18 (near-lossless)
Preset
slow (better compression, local = time is cheap)
Pixel format
yuv420p (maximum compatibility)
Max file size
50MB (IG limit)

# 5. Music Suggestion System
Music is not embedded in the video. Instagram’s free music library provides millions of trending tracks. The system suggests music by mood so the user can search in-app.
Mood
Genre
BPM
IG search terms
calm
lo-fi ambient / acoustic
70–90
aesthetic, chill vibes, soft morning
energetic
upbeat electronic / indie pop
110–130
travel energy, adventure, good vibes
cinematic
orchestral ambient / post-rock
60–80
cinematic, epic travel, drone footage
dreamy
shoegaze / dream pop / ethereal
80–100
dreamy, golden hour, wanderlust
moody
dark ambient / minimal techno
90–110
moody, dark aesthetic, noir

# 6. Sprint Plan
9 sprints across 3 phases. Estimated ~6 weeks part-time, ~3 weeks full-time. First working reel at end of Phase 1 (~2 weeks).
Phase 1 — Foundation (get a reel out)
3 sprints · ~2 weeks · Deliverable: first complete reel renders end-to-end
Sprint 1.1 — Project scaffold + creative director  (3–4 days)
Set up project structure, config.py, CLI skeleton with Click
Build LLM abstraction layer (Claude API + Ollama fallback)
Write creative director module — ReelPlan dataclass output with Pydantic validation
Craft and iterate on creative prompts (prompts.py) — test with 10+ topics
Build trend_bank.py — hook patterns, caption length rules, curated palette sets
Add --preview mode (outputs plan as formatted JSON, no rendering)
Checkpoint: python reelgen.py --preview --topic "..." outputs a complete, well-structured ReelPlan
Sprint 1.2 — Asset pipeline + basic text  (4–5 days)
Build Pexels API client (port from V2, add multi-query support per beat)
Build Pixabay API client (same interface as Pexels client)
Build curator.py — search both sources, download top 3 candidates per beat
Basic visual QA — resolution check, aspect ratio filter, blur detection (Laplacian variance)
Download Google Fonts pack (Plus Jakarta Sans, Montserrat, Bebas Neue, Playfair Display, Caveat, Inter) into fonts/
Build text renderer (Pillow) — one style only: white text + pill background + fade-up entrance
Depends on: Sprint 1.1 (needs ReelPlan to know what to search for)
Sprint 1.3 — Compositor + first render  (3–4 days)
Build compositor.py — MoviePy timeline assembly, hard cuts only
Text overlay compositing — merge Pillow transparent frames onto video timeline at correct timestamps
FFmpeg export with IG-optimized settings (H.264, 1080x1920, CRF 18, yuv420p)
Wire full pipeline: CLI → director → curator → text renderer → compositor → output/
Output metadata JSON alongside .mp4 (IG caption, hashtags, music suggestion, plan details)
Depends on: Sprint 1.2 (needs downloaded clips + text renders)
◆ Phase 1 milestone: first complete reel renders end-to-end. Ugly but functional. Full pipeline works.
Phase 2 — Visual quality (make it look good)
3 sprints · ~2 weeks · Deliverable: reels look cohesive and stylized
Sprint 2.1 — Color grading + style presets  (3–4 days)
Build FFmpeg color grade pipeline — brightness, contrast, saturation, color balance filters
Implement 4 style presets: warm-analog, cool-minimal, golden-hour, moody-dark (see Section 4.3)
Add optional film grain overlay + vignette via FFmpeg filters
Color palette matching in Visual QA — histogram distance scoring against target palette
Checkpoint: all clips in a reel share a cohesive color treatment. Visual coherence is immediately noticeable.
Sprint 2.2 — Motion + transitions  (3–4 days)
Ken Burns effect — FFmpeg zoompan filter for static/slow clips
Subtle zoom-in on beat entry (2–5% scale over beat duration)
Cross-dissolve transition (MoviePy crossfade, 0.3–0.5s)
Whip-pan / swipe transition for energy beats
Transition auto-selection logic based on mood shift between consecutive beats
Depends on: Sprint 2.1 (color grade must happen before motion is applied)
Sprint 2.3 — Text styles + animations  (3–4 days)
Add all 5 text background styles: pill, frosted, shadow, outline, clean
Add pop-scale and typewriter entrance animations
Context-aware text positioning — top/center/bottom based on beat role (hook/body/closer)
Font selection logic — match font category to beat mood
Safe zone enforcement (avoid IG header 15% and footer 10% UI areas)
Depends on: Sprint 1.3 (base text renderer must exist)
◆ Phase 2 milestone: reels look cohesive and stylized. Not obvious they’re auto-generated. Comparable to CapCut creator output.
Phase 3 — Polish + ecosystem (make it great)
3 sprints · ~2 weeks · Deliverable: production-ready system that improves over time
Sprint 3.1 — Local library + smart curation  (3–4 days)
Build local library system — library/ directory, index.json with metadata, tag-based search
CLI: --add-to-library with auto-tagging (duration, resolution, dominant colors via Pillow)
Curator priority: local library first → API fallback
Motion stability scoring in Visual QA (optical flow variance between sampled frames)
Full Visual QA pipeline — weighted composite score with configurable threshold
Checkpoint: reels improve over time as library grows. Personal footage = unique content.
Sprint 3.2 — Music + delivery + UX  (3–4 days)
Music suggestion engine — mood → genre/BPM/IG search terms mapping (see Section 5)
Auto-thumbnail — extract best frame (highest sharpness + composition score)
Port Telegram delivery from V2 (optional, --telegram flag)
Rich terminal output — progress bars, preview plan table, completion summary (Rich library)
Temp folder auto-cleanup after successful render
Depends on: Phase 2 complete (all visual systems working)
Sprint 3.3 — Prompt tuning + battle testing  (3–4 days)
Generate 20+ test reels across different topics and style presets
Iterate on creative prompts based on output quality review
Fine-tune Visual QA thresholds — reduce false positives (good clips rejected) and false negatives (bad clips accepted)
Add --style CLI override and --local-only flag
Write README.md with setup guide, usage examples, architecture overview, troubleshooting
Checkpoint: production-ready. Documented. Tested across 20+ reels. Ready for daily use.
◆ Phase 3 milestone: system produces reels you’d actually post. Library compounds quality over time. Prompt engineering is dialed in.

# 7. Scope & Boundaries

## 7.1 What this system does
Generates complete 15–30 second Instagram Reels from a topic input
Produces visually cohesive, color-graded reels with trending text styles and animations
Suggests music, IG captions, and hashtags alongside the rendered video
Builds a personal clip library that improves output quality over time
Runs entirely locally with near-zero API cost

## 7.2 What this system does NOT do
Does not embed music — IG’s free music library is superior. Adding music in-app takes 5 seconds. The system suggests by mood tag.
Does not auto-post to IG — IG’s API doesn’t support Reels posting for personal accounts. Workflow: generate → review → manually post. Human review is intentional.
Does not generate footage — AI video generation (Sora, Runway, Kling) still has uncanny-valley issues and is expensive. Curated stock footage looks more natural.
Does not replace creative taste — the system generates and suggests. The human reviews, picks topics, and posts what’s good. The human in the loop IS the quality filter.

## 7.3 Cost estimate
Component
Cost
Pexels API
Free (200 req/hr)
Pixabay API
Free (100 req/min)
Claude Sonnet API (per reel)
~$0.003 – $0.01
Ollama local (per reel)
Free (requires 8GB+ RAM)
Google Fonts
Free
FFmpeg / MoviePy / Pillow
Free
Total per reel
$0.00 – $0.01

## 7.4 Key engineering notes
Pydantic everywhere: ReelPlan and all intermediate data models use Pydantic v2 for validation. If the LLM returns malformed JSON, catch it early.
FFmpeg subprocess calls: MoviePy wraps FFmpeg but some filters (color grading, zoompan, grain) may need direct subprocess calls. Use Python’s subprocess.run with timeout.
Temp management: each reel generation creates a temp/{reel_id}/ directory. Clean up after successful render; keep on failure for debugging.
Error handling: Pexels/Pixabay API failures should fall back gracefully (try other source, reduce candidate count). LLM failures should retry once with the same prompt before failing.
Testing creative output: the --preview flag is critical for iterating on prompts without waiting for full renders. Use it heavily in Sprint 1.1.
MoviePy v2 API: MoviePy 2.0 has breaking changes from 1.x. Use v2 API throughout — do not mix.
End of specification