# Brainrot Reels — Sprint Plan

Sibling project to ReelGen, same repo. Reddit-story-style reels: TTS narration over
looped gameplay footage (Minecraft/Subway Surfers), word-synced karaoke captions.
Same rule as ReelGen: one sprint built + tested against real audio/video before next starts.

## Decisions locked in
- Separate `brainrot/.venv` (conflict hit as predicted: kokoro pulls transformers>=5,
  which needs torch>=2.4; ReelGen's venv pins torch==2.2.2 for CLIP compat, and this
  machine's Python is x86_64/Rosetta so no torch wheel newer than 2.2.2 exists anyway.
  Fixed by pinning transformers==4.46.3 + numpy<2 in brainrot's own venv.)
  Install: `python3.11 -m venv brainrot/.venv && source brainrot/.venv/bin/activate &&
  pip install -r brainrot/requirements.txt --index-url https://pypi.org/simple/`
- Captions: ASS/libass karaoke burn-in via ffmpeg (not the Pillow renderer used by ReelGen)
- Separate CLI entrypoint: `brainrot.py` (not a subcommand of `reelgen.py`)
- TTS: Kokoro-82M (Apache 2.0, local, free), voice `am_adam` — Azure Neural TTS as paid fallback (native word timestamps)
- Alignment: faster-whisper first, WhisperX if tighter sync needed
- Gameplay footage: `brainrot/library/gameplay/4.mp4` (4K, ~277s, gitignored) — sourced from ko-fi.com,
  listing explicitly grants royalty-free/commercial use. Cleared for prod, no swap needed (Sprint 8).
- **Duration format (revised 2026-07-06):** hard cap 20s, usual/ideal 8-16s — this is a micro-format,
  one quick beat/punchline, not a full narrative arc. Changed from the original 20-90s range once
  actual target usage became clear. Story prompt, `target_duration` default, and gameplay slice
  lengths (`MIN_SLICE`/`MAX_SLICE`, now 4-10s instead of 7-20s so short videos still get 2-3 cuts)
  were all updated together. `brainrot.py`'s duration warning now fires past 20s, not 90s.
- Text pipeline: Source (original story) → Spoken (TTS-normalized: numbers/currency/emoji spelled out)
  → Display (formatted captions) — avoids alignment breakage on "$13.60", usernames, etc.

## Sprint 1 — Story generation (LLM) [DONE]
New director module + prompt for reddit-story-style scripts (funny / touchy / self-realization).
Schema: title, spoken script, display script, mood, target duration estimate, tags.
**Test:** generate 8-10 stories across all mood types, manual quality read, reject anything generic/AI-sounding.

## Sprint 2 — Text normalization + TTS (Kokoro) [DONE]
`text_norm.py`: safety-net normalizer (num2words, currency, emoji strip) - LLM already writes
TTS-clean spoken_script per Sprint 1 prompt, this catches anything it missed.
`tts.py`: KokoroTTS wrapper, concatenates chunk audio, wav output.
**Test:** synth'd the one clean Sprint-1 story end to end - 40.8s actual vs 42.0s LLM-estimated
target_duration, phonemes looked correct, no crashes. Full batch listen-through blocked by same
Gemini quota wall as Sprint 1; proceeding on this one verified sample per user call.

## Sprint 3 — Word alignment [DONE]
`align.py`: faster-whisper (tiny.en, CPU) transcribes the TTS wav, whisper's word timings get
matched onto our own known spoken_script tokens via difflib SequenceMatcher (whisper's transcript
text is noisy - e.g. it heard "al dent" not "al dente" - so we trust its timestamps, not its text).
Spoken-token timings then map onto display_script sentence-by-sentence: equal token count -> 1:1,
unequal (numbers/currency expanded) -> proportional split by char length across that sentence's span.
Hit an OMP deadlock: torch and ctranslate2 both bundle OpenMP, process would hang at 0% CPU forever
on transcribe(). Fixed with `KMP_DUPLICATE_LIB_OK=TRUE` (set in align.py itself via os.environ).
**Test:** ran on the one real story from Sprint 1/2 - 137 display tokens, monotonic increasing
timestamps, tight sync, correct emoji placement. Sample had no numbers/currency, so the proportional-
split (unequal token count) path is implemented but not yet exercised on real data - re-verify once
a story with a number/currency mention generates.

## Sprint 4 — ASS karaoke captions [DONE]
`captions.py`: groups display words into 4-word lines, builds ASS `\k` karaoke tags (word durations
computed from boundary gaps so they sum exactly to line duration), PlayRes 1080x1920, bottom-safe
margin, bold Montserrat, yellow highlight/white base.
Hit an environment issue: system `ffmpeg` (homebrew/core, x86_64/Rosetta build) has no libass at all
- no `ass`/`subtitles` filter. Didn't touch system ffmpeg (it's a dependency of gifski/vhs, swapping
taps would've broken those). Instead dropped a static ffmpeg-full build (evermeet.cx, libass +
libfreetype included) at `brainrot/bin/ffmpeg`, gitignored, used only by brainrot's own pipeline.
**Test:** burned captions + Sprint-2 TTS audio over black at 1080x1920, extracted a frame - karaoke
highlight, font, and bottom-safe positioning all confirmed by eye. Full audio/caption sync already
validated at the timestamp level in Sprint 3.

## Sprint 5 — Gameplay compositor [DONE]
`compositor.py`: `pick_slices()` picks random non-overlapping 7-20s slices (last one trimmed short
to hit the target exactly) from the gameplay source, one ffmpeg filter_complex does trim+concat,
scale-to-cover-height + center-crop-width (1080x1920, landscape source -> portrait target), audio
mux, and ASS caption burn-in in a single pass. Uses `brainrot/bin/ffmpeg` (the static libass build).
**Test:** ran full pipeline on `4.mp4` + Sprint 1-4 outputs - 1080x1920, 40.8s (exact TTS duration
match), h264/aac. Pulled a mid-video frame: gameplay crop fills frame correctly, caption burned in,
karaoke highlight in sync ("perfect timing" highlighted at the right moment). Full watch-through not
yet done, only a spot-check frame + the file plays without ffprobe errors.

## Sprint 6 — CLI + review delivery [DONE]
`brainrot.py generate` command (click, mirrors reelgen.py's structure): story -> TTS -> align ->
captions -> composite -> metadata json -> optional `--telegram` via the shared `delivery.py`.
Hit two real environment bugs while running this end to end:
1. **OMP deadlock, not just a warning.** `KMP_DUPLICATE_LIB_OK=TRUE` alone wasn't enough - torch's
   and ctranslate2's bundled OpenMP runtimes genuinely deadlocked under contention (main thread
   stuck in `__kmp_suspend_64` forever, confirmed via `sample`). Fixed by forcing single-threaded
   OMP (`OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `cpu_threads=1`) in `brainrot.py`/`align.py` -
   set before torch or ctranslate2 ever load.
2. **HF Hub network stall.** Even with cached models, `WhisperModel`/`KPipeline` init did a network
   check that hung (`select_poll_poll`, confirmed via `sample`). Fixed with `HF_HUB_OFFLINE=1`.
3. **Telegram delivery hung indefinitely.** This network's IPv6 route to `api.telegram.org` is dead
   (confirmed via `curl -6`, stuck in `SYN_SENT`); IPv4 works instantly. Fixed in the shared
   `delivery.py` by forcing `urllib3`/`requests` to resolve IPv4 only - benefits ReelGen too.
**Test:** ran the full pipeline for real - Gemini quota died again mid-run, so did a bypass run using
an already-validated story (skips just the LLM call, everything else identical) straight through to
Telegram. Rendered a 33MB 1080x1920 reel and delivered it to Telegram successfully after all three
fixes landed. A pure `--preview` run (LLM call only) also confirmed the story-gen path independently.

## Sprint 7 — Edge cases + prod hardening [DONE]
- Story too short for min slice count: already handled by `pick_slices`' existing "remaining < min_len"
  branch (first iteration just takes the whole remaining duration as one short slice).
- Gameplay shorter than target duration: `pick_slices` now falls back to loop-wrap (allows
  overlapping/repeated slices) instead of raising once it can't fill the target cleanly.
- Platform size cap: ported ReelGen's `_enforce_size_limit` (CRF escalation, 3 attempts, 50MB cap)
  into `compositor.py`, called at the end of `build_video`. Warns (doesn't crash) if still over cap.
- Platform duration: soft warning in `brainrot.py` if TTS duration exceeds ~90s (still renders/posts,
  just flags reach risk) - no hard truncation, since cutting synthesized audio mid-sentence would
  need re-running the whole caption/alignment step to stay in sync.
- ffmpeg failures now raise with actual stderr surfaced (`_run_ffmpeg` helper) instead of a bare
  `CalledProcessError`; `probe_duration` does the same for a missing/corrupt gameplay file.
- TTS/alignment/caption/compositor failures were already caught individually in `brainrot.py`'s
  `generate` command (each prints a clear message and exits 1, no partial-state crash).
**Test:** unit-tested `pick_slices` directly - short story (3s target), loop-wrap (60s target over a
10s fake source), and the normal case, all hit their target duration within 0.2s. Unit-tested
`_enforce_size_limit` both as a no-op (already under cap) and forced-compression path (real 38MB
render compressed to 17MB across CRF escalation, correctly warns rather than crashing when an
artificially tiny 5MB cap still can't be hit).

## Sprint 8 — Prod verification [DONE]
Footage license confirmed: ko-fi.com listing explicitly grants royalty-free/commercial use.
`4.mp4` carries into prod as-is, no swap needed. Full pipeline already proven end-to-end in
Sprint 6/7 testing (real 40.8s reel rendered, captions synced, delivered to Telegram).

**Quality rating:** solid first pass. TTS (Kokoro `am_adam`) is clear and paced well against the
40.8s target from a 42.0s estimate. Whisper alignment held up on a clean narration track. Caption
sync looked right on spot-check (frame-level, not full watch-through yet). Known rough edges before
calling this launch-ready:
- Only spot-checked frames, never did a full watch-through start to finish on a rendered output.
- Only one full story has gone through the entire pipeline (Gemini quota killed every batch attempt) -
  need real variety across funny/touchy/self_realization moods before trusting quality broadly.
- Voice is a single fixed pick (`am_adam`) - no variety across videos yet, may feel repetitive at volume.

## Known open risk
TTS (Kokoro) and alignment (faster-whisper) quality/speed are unverified — if either surprises us,
sprint order after 2/3 may shift. Everything else is straightforward ffmpeg/CLI plumbing already
proven in ReelGen.
