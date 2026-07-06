# 🧠 Brainrot

**Reddit-story reels over gameplay footage — fully automated, fully local.**

Brainrot is ReelGen's sibling pipeline. It turns a one-line mood prompt into a finished 8-20s vertical reel: an LLM writes a punchy first-person micro-story, a local TTS model narrates it, every word gets timestamp-aligned, karaoke captions get burned in, and it's all composited over randomly-sliced gameplay footage. The kind of video that floods Shorts and Reels — except yours renders on your own machine for pennies.

```bash
python brainrot.py generate --mood funny --telegram
```

Story, narration, word-synced captions, gameplay edit, metadata, delivery — done.

---

## ✨ Features

**📖 Stories that don't sound like AI**
An LLM director writes reddit-style micro-stories (funny / touchy / self-realization) with a hard 20-second cap — one setup, one punchline, no padding. Every story ships in two synced versions: a TTS-ready spoken script (numbers and currency spelled out) and a display script for captions ("$13.60" stays "$13.60" on screen).

**🗣️ Free, local, actually-good TTS**
Kokoro-82M (Apache 2.0) runs on CPU, costs nothing, and sounds like a narrator, not a robot. Three voices included by default (`am_adam`, `af_heart`, `am_michael`) — rotate per video or pin one.

**🎯 Word-perfect caption sync**
faster-whisper transcribes the generated audio for timestamps, then the timings get matched back onto the *known* script text (whisper's ears are trusted for timing, never for spelling). Result: karaoke-style word highlighting that actually lands on the word being spoken.

**🎬 Karaoke captions via real subtitles**
ASS/libass burn-in through ffmpeg — bold Montserrat, yellow-on-white word highlight, vertical-safe positioning. Not frame-by-frame image compositing; real subtitle rendering.

**🎮 Gameplay that never repeats itself**
Random 4-10s slices picked from your gameplay library, non-overlapping within a video, concatenated to match the narration's exact duration, scaled and center-cropped to 1080×1920. Short source? It loop-wraps gracefully instead of crashing.

**📦 Platform-ready output**
1080×1920 H.264/AAC, auto-compressed under the 50MB Instagram/Telegram cap, metadata JSON with caption and tags per video.

**📡 Telegram review flow**
Same delivery as ReelGen: finished reel lands in your Telegram for review. No auto-posting, by design — you're always the last set of eyes.

---

## 🚀 Quick start

Brainrot uses its **own venv** (its TTS stack needs different pins than ReelGen's CLIP stack):

```bash
# 1. Set up (from the repo root)
python3.11 -m venv brainrot/.venv
source brainrot/.venv/bin/activate
pip install -r brainrot/requirements.txt

# 2. ffmpeg with libass
# Your ffmpeg needs the `ass` filter (check: ffmpeg -filters | grep ass).
# If it doesn't have it, drop a static ffmpeg build (e.g. from evermeet.cx for macOS)
# at brainrot/bin/ffmpeg — the pipeline prefers that path automatically.

# 3. Configure keys (shared with ReelGen)
cp .env.example .env   # needs GEMINI_API_KEY; TELEGRAM_* optional

# 4. Add gameplay footage
# Put one or more .mp4 files in brainrot/library/gameplay/
# ⚠️ Use footage you have the rights to — for monetized use, that means an explicit
# royalty-free/commercial license, not just "found it on YouTube".
```

## 🎮 Usage

```bash
# Generate a reel
python brainrot.py generate --mood funny

# Moods: funny · touchy · self_realization
python brainrot.py generate --mood self_realization --guidance "about quitting social media"

# Just see the story, skip rendering
python brainrot.py generate --mood touchy --preview

# Use a specific gameplay file + push to Telegram
python brainrot.py generate --mood funny --gameplay brainrot/library/gameplay/mine.mp4 --telegram
```

First run downloads Kokoro (~330MB) and faster-whisper models from Hugging Face, then everything runs offline.

## 🏗️ How it works

```
mood + guidance
  │
  ▼
brainrot/director.py     LLM writes the micro-story (spoken + display scripts, schema-validated)
  │
  ▼
brainrot/tts.py          Kokoro-82M narrates the spoken script (local, free)
  │
  ▼
brainrot/align.py        faster-whisper timestamps → matched onto known script text
  │
  ▼
brainrot/captions.py     ASS karaoke subtitles, word-level highlight
  │
  ▼
brainrot/compositor.py   random gameplay slices + audio + caption burn-in, one ffmpeg pass
  │
  ▼
output/*.mp4 + metadata.json (caption, tags, voice, duration)
```

| Path | What lives here |
|---|---|
| `brainrot/director.py` | LLM story generation + repair-retry |
| `brainrot/prompts.py` | story prompt (format rules, 20s cap, dual-script contract) |
| `brainrot/text_norm.py` | TTS safety net: numbers/currency/emoji normalization |
| `brainrot/tts.py` | Kokoro wrapper |
| `brainrot/align.py` | whisper transcription + script alignment |
| `brainrot/captions.py` | ASS karaoke builder |
| `brainrot/compositor.py` | slice picker + ffmpeg composite + size cap |
| `brainrot/library/gameplay/` | your gameplay footage (gitignored) |

## ⚠️ Honest limitations

- **Render time is minutes, not seconds** — TTS + whisper + ffmpeg on CPU takes ~1-3 min per video depending on hardware.
- **Gemini's free tier is tight** (~20 requests/day) — fine for a daily batch, not for volume without a paid key.
- **Gameplay footage is on you** — the pipeline doesn't ship any. License matters if you monetize.
- **Emoji don't render in burned-in captions** (libass has no color-emoji fallback), so they're stripped from on-screen text. They stay in the post caption.
- **No auto-posting** — deliberate. Review before you publish.

## 📄 License

MIT, same as ReelGen (see repo root `LICENSE`).
