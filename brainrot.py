import os
# Must be set before torch (kokoro) or ctranslate2 (faster-whisper) load - both bundle their own
# OpenMP runtime and deadlock under real contention if left at default thread counts.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import re
import sys
import time
import json

import click

from brainrot.director import BrainrotDirector
from brainrot.tts import KokoroTTS
from brainrot.align import WordAligner
from brainrot.captions import build_ass
from brainrot import compositor
from delivery import send_reel

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return slug[:40] or "brainrot"


@click.group()
def cli():
    """Brainrot: Reddit-story reels over gameplay footage."""
    pass


@cli.command()
@click.option("--mood", default="funny", type=click.Choice(["funny", "touchy", "self_realization"]), help="Story mood")
@click.option("--guidance", default="", help="Extra guidance for the story LLM prompt")
@click.option("--gameplay", default=None, help="Path to a specific gameplay source (random pick from library if omitted)")
@click.option("--preview", is_flag=True, help="Only generate and print the story, skip TTS/render")
@click.option("--telegram", is_flag=True, help="Send the final reel to Telegram")
def generate(mood, guidance, gameplay, preview, telegram):
    """Generate a brainrot reel."""
    click.echo(f"Generating story (mood={mood})...")
    try:
        director = BrainrotDirector()
        story = director.generate_story(mood=mood, guidance=guidance)
    except Exception as e:
        click.echo(f"Story generation failed: {e}", err=True)
        sys.exit(1)

    click.echo(f"Story ready: '{story.title}' (~{story.target_duration:.0f}s)")

    if preview:
        click.echo(story.model_dump_json(indent=2))
        return

    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    slug = _slugify(story.title)
    run_id = f"{slug}_{int(time.time())}"

    wav_path = os.path.join(TEMP_DIR, f"{run_id}.wav")
    ass_path = os.path.join(TEMP_DIR, f"{run_id}.ass")
    out_path = os.path.join(OUTPUT_DIR, f"{run_id}.mp4")

    click.echo("Synthesizing TTS (Kokoro)...")
    try:
        tts = KokoroTTS()
        duration = tts.synthesize(story.spoken_script, wav_path)
    except Exception as e:
        click.echo(f"TTS synthesis failed: {e}", err=True)
        sys.exit(1)
    click.echo(f"   {duration:.1f}s of audio")
    if duration > 20:
        click.echo(f"   Warning: {duration:.0f}s exceeds this format's 20s hard cap (usual 8-16s) - "
                   f"the LLM overran its length rule. Still renders, but consider regenerating.")

    click.echo("Aligning words (faster-whisper)...")
    try:
        aligner = WordAligner()
        word_timings = aligner.align(wav_path, story.spoken_script, story.display_script)
    except Exception as e:
        click.echo(f"Word alignment failed: {e}", err=True)
        sys.exit(1)

    click.echo("Building captions...")
    try:
        build_ass(word_timings, ass_path)
    except Exception as e:
        click.echo(f"Caption build failed: {e}", err=True)
        sys.exit(1)

    gameplay_path = gameplay or compositor.pick_gameplay_source()
    click.echo(f"Compositing over gameplay: {os.path.basename(gameplay_path)}...")
    try:
        compositor.build_video(gameplay_path, wav_path, ass_path, out_path, duration)
    except Exception as e:
        click.echo(f"Compositing failed: {e}", err=True)
        sys.exit(1)

    metadata = {
        "title": story.title,
        "mood": story.mood,
        "duration": round(duration, 2),
        "tags": story.tags,
        "gameplay_source": os.path.basename(gameplay_path),
        "ig_caption": f"{story.title}\n\n{' '.join('#' + t for t in story.tags)}",
    }
    metadata_path = out_path + ".json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    click.echo(f"Reel rendered: {out_path}")
    click.echo(f"Metadata: {metadata_path}")

    if telegram:
        if send_reel(out_path, metadata["ig_caption"]):
            click.echo("Sent to Telegram")


if __name__ == "__main__":
    cli()
