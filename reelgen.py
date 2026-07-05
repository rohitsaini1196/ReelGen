import os
import re
import sys
import time

import click

from creative.director import CreativeDirector
from assets import curator, local_library
from assets.local_library import _probe_duration
from compose import compositor
from compose.thumbnail import extract_thumbnail
from delivery import send_reel


def _slugify(topic: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")
    return slug[:40] or "reel"


@click.group()
def cli():
    """ReelGen-V3: Automated Instagram Reel Generator"""
    pass


@cli.command()
@click.option("--topic", prompt="Reel topic", help="Topic for the reel")
@click.option("--mood", default="neutral", help="Mood preference")
@click.option("--style", default="cool-minimal", help="Style preset preference")
@click.option("--preview", is_flag=True, help="Only generate and print the plan, skip rendering")
@click.option("--telegram", is_flag=True, help="Send the final reel to Telegram")
def generate(topic, mood, style, preview, telegram):
    """Generate a reel from a topic."""
    click.echo(f"Generating creative plan for: {topic}")
    try:
        director = CreativeDirector()
        plan = director.generate_plan(topic, mood=mood, style_preset=style)
    except Exception as e:
        click.echo(f"Creative planning failed: {e}", err=True)
        sys.exit(1)

    if preview:
        click.echo(plan.model_dump_json(indent=2))
        return

    click.echo(f"Plan ready: '{plan.title}' ({len(plan.all_beats())} beats, {plan.total_duration}s)")

    if plan.hook_alt:
        click.echo(f"Testing 2 hook angles: '{plan.hook.caption}' vs '{plan.hook_alt.caption}'")
        try:
            hook_a_asset = curator.fulfill_beat(plan.hook, palette=plan.color_palette, director=director)
        except Exception:
            hook_a_asset = None
        try:
            hook_b_asset = curator.fulfill_beat(plan.hook_alt, palette=plan.color_palette, director=director)
        except Exception:
            hook_b_asset = None

        score_a = hook_a_asset.final_score if hook_a_asset else -1
        score_b = hook_b_asset.final_score if hook_b_asset else -1

        if score_b > score_a:
            click.echo(f"   Winner: '{plan.hook_alt.caption}' ({score_b:.2f} vs {score_a:.2f})")
            plan.hook_alt.asset = hook_b_asset
            plan.hook, loser_asset = plan.hook_alt, hook_a_asset
        else:
            click.echo(f"   Winner: '{plan.hook.caption}' ({score_a:.2f} vs {score_b:.2f})")
            plan.hook.asset = hook_a_asset
            loser_asset = hook_b_asset

        if loser_asset and loser_asset.local_path and os.path.exists(loser_asset.local_path):
            os.remove(loser_asset.local_path)
        plan.hook_alt = None

    for beat in plan.all_beats():
        if beat is plan.hook and beat.asset:
            continue  # hook already resolved via A/B above
        try:
            beat.asset = curator.fulfill_beat(beat, palette=plan.color_palette, director=director)
        except Exception as e:
            click.echo(f"   Beat '{beat.caption}' failed to fulfill: {e}", err=True)
            beat.asset = None

    filled = sum(1 for b in plan.all_beats() if b.asset)
    click.echo(f"Fulfilled {filled}/{len(plan.all_beats())} beats with footage")

    if filled == 0:
        click.echo("No beats could be fulfilled with footage - nothing to render. Try a more common topic or check your API keys.", err=True)
        sys.exit(1)

    slug = _slugify(topic)
    filename = f"{slug}_{int(time.time())}.mp4"
    try:
        output_path = compositor.assemble_reel(plan, filename)
    except Exception as e:
        click.echo(f"Rendering failed: {e}", err=True)
        sys.exit(1)

    plan.total_duration = round(_probe_duration(output_path), 2)
    metadata_path = output_path + ".json"
    with open(metadata_path, "w") as f:
        f.write(plan.model_dump_json(indent=2))

    thumbnail_path = output_path.rsplit(".", 1)[0] + "_thumb.jpg"
    extract_thumbnail(output_path, thumbnail_path)

    click.echo(f"Reel rendered: {output_path}")
    click.echo(f"Thumbnail: {thumbnail_path}")
    click.echo(f"Metadata: {metadata_path}")

    if telegram:
        full_caption = f"{plan.ig_caption}\n\n{' '.join('#' + h for h in plan.ig_hashtags)}"
        if send_reel(output_path, full_caption):
            click.echo("Sent to Telegram")


@cli.command(name="add-to-library")
@click.argument("file_path")
@click.option("--tags", prompt="Tags (comma-separated)", help="Tags describing the clip")
def add_to_library(file_path, tags):
    """Add a local video file to the personal footage library."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    entry = local_library.add_clip(file_path, tag_list)
    click.echo(f"Added to library: {entry['filename']} (tags: {entry['tags']}, duration: {entry['duration']:.1f}s)")


if __name__ == "__main__":
    cli()
