# 🎬 ReelGen

**Turn a topic into a scroll-stopping Instagram Reel — automatically.**

ReelGen is a local-first pipeline that takes a topic string and produces a fully edited, color-graded, captioned 15-30s vertical reel that looks like a human cut it in CapCut — not something an AI spat out. No cloud rendering, no subscription, pennies of API cost per reel.

```bash
python reelgen.py generate --topic "Hidden cafes in Tokyo's backstreets" --mood calm --style warm-analog
```

That's it. Plan, footage, color grade, motion, text, transitions, thumbnail, caption, hashtags — done.

---

## ✨ Features

**🧠 AI creative director**
Turns a topic into a full storyboard: hook, body beats, closer, color palette, mood, IG caption, and hashtags — all schema-validated so a bad LLM response never crashes your run. Two hook angles are generated per reel and the one with better-matching footage wins, automatically.

**🎯 Footage that actually matches**
Not keyword search — semantic search. Every candidate clip is scored with CLIP against the beat's visual description, so "turquoise water overhead drone shot" doesn't hand you a swimming pool. Weak matches automatically retry with better search phrasing before falling back.

**📹 Dual-source stock + your own footage**
Pulls from Pexels and Pixabay, and checks your personal clip library first if you've built one. Every candidate gets scored on sharpness, resolution, brightness, color-palette fit, and motion stability before the best one is picked.

**🎨 Real color grading, not filters**
Four style presets (warm-analog, cool-minimal, golden-hour, moody-dark) applied via direct FFmpeg color science — brightness, contrast, saturation, color temperature, film grain, vignette.

**🎥 Motion that feels handheld**
Subtle Ken Burns zoom plus a barely-there handheld jitter, so stock footage stops looking like stock footage.

**✍️ Text that looks IG-native**
Five background styles (pill, frosted glass, shadow, outline, clean), fade-up and pop-scale entrance animations, safe-zone aware positioning, font picked by the beat's mood (editorial serif for calm, bold impact for energetic, handwritten script for dreamy). If the footage match is weak, the text automatically gets a stronger anchor treatment so the caption still lands.

**🎞️ Pacing with an actual arc**
Hook hits hard, middle breathes, closer punches — moods vary across the reel on purpose, and transitions (hard cut / crossfade / whip-pan) are chosen by the real energy shift between beats, not random.

**📦 Instagram-ready output**
1080×1920, 30fps, H.264, auto-compressed to stay under IG's 50MB cap. Thumbnail auto-picked from the sharpest frame in the reel.

**📚 A library that gets better over time**
Add your own clips once, and the curator prefers them over stock forever after — auto-tagged with resolution and dominant colors.

**📡 Optional Telegram delivery**
Get the finished reel pushed straight to your phone the moment it's done.

**🙅 No auto-posting**
By design. You're always the last set of eyes before anything goes live.

---

## 🚀 Quick start

```bash
# 1. Set up
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# 2. Install ffmpeg
brew install ffmpeg   # or apt install ffmpeg

# 3. Configure keys
cp .env.example .env
```

Fill in `.env`:
| Key | Required? | Get it at |
|---|---|---|
| `GEMINI_API_KEY` | ✅ (default LLM) | aistudio.google.com — free tier |
| `PEXELS_API_KEY` | ✅ | pexels.com/api — free |
| `PIXABAY_API_KEY` | optional, adds a second footage source | pixabay.com/api — free |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | optional, for `--telegram` | @BotFather on Telegram |

Total cost per reel: **$0.00 – $0.01**.

## 🎮 Usage

```bash
# Generate a reel
python reelgen.py generate --topic "3 books that changed how I think" --mood dreamy --style warm-analog

# Just see the creative plan, skip rendering
python reelgen.py generate --topic "..." --preview

# Render and push straight to Telegram
python reelgen.py generate --topic "..." --telegram

# Teach it your own footage
python reelgen.py add-to-library my_clip.mp4 --tags "beach,sunset,drone"
```

**Style presets**: `warm-analog` · `cool-minimal` · `golden-hour` · `moody-dark`
**Moods**: `calm` · `energetic` · `dreamy` · `raw` · `neutral`

## 🏗️ How it works

```
topic
  │
  ▼
creative/director.py     LLM plans the storyboard (Gemini / Anthropic / OpenAI, swappable)
  │
  ▼
assets/curator.py        local library → Pexels → Pixabay, CLIP + QA scored, best clip wins
  │
  ▼
compose/compositor.py    color grade, Ken Burns + handheld motion, animated text, mood-aware transitions
  │
  ▼
compose/thumbnail.py     sharpest-frame thumbnail
  │
  ▼
delivery.py              optional Telegram push
  │
  ▼
output/*.mp4 + thumbnail.jpg + metadata.json (caption, hashtags, music suggestion)
```

| Path | What lives here |
|---|---|
| `creative/` | LLM prompts, curated palette/hook bank, director |
| `assets/` | Pexels/Pixabay clients, CLIP matcher, visual QA, local library |
| `style/` | color grade presets, motion (Ken Burns + shake) |
| `text/` | Pillow text renderer, fonts, layouts, animations |
| `compose/` | compositor, transitions, thumbnail extraction |
| `fonts/` | Google Fonts variable font files |
| `library/` | your personal footage + its index |
| `output/` | finished reels |

## 🎵 About music

ReelGen doesn't embed audio — Instagram's own free music library is better than anything we could license, and adding a track in-app takes five seconds. Each reel comes with a mood-matched music suggestion (genre, BPM, search terms) in its metadata JSON.

## ⚠️ Honest limitations

- Gemini's free tier caps at ~20 requests/day per key — fine for personal use, will need a paid key or backend swap for heavy use.
- Pixabay needs its own free key; Pexels alone works fine without it.
- No automated test suite yet — every module has been verified end-to-end against real APIs and real footage, but there's no CI.
- Views depend on you — posting cadence, trending audio, and captions matter as much as the reel itself.

## 🤝 Contributing

Issues and PRs welcome. If you're adding a feature, run it against a real topic end-to-end before opening a PR — this project has no mocks in its test history, keep it that way.

## 📄 License

MIT (see `LICENSE`).
