import os
import subprocess
import shutil
import uuid

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from config import settings
from text.fonts import category_for_mood, font_path, font_variation
from text.layouts import wrap_text, anchor_y
from text.animations import envelope, animation_for_mood

FONT_SIZE = 68
ENTRANCE_FRAMES = 8
EXIT_FRAMES = 6


def _load_font(mood: str):
    category = category_for_mood(mood)
    try:
        font = ImageFont.truetype(font_path(category), FONT_SIZE)
    except OSError:
        font = ImageFont.load_default(size=FONT_SIZE)
        return font
    variation = font_variation(category)
    if variation:
        try:
            font.set_variation_by_name(variation)
        except Exception:
            pass
    return font


def _draw_text_block(draw, lines, font, center_xy, line_height, style: str):
    cx, cy = center_xy
    total_h = line_height * len(lines)
    top = cy - total_h // 2

    if style == "pill":
        max_w = max(draw.textbbox((0, 0), line, font=font)[2] for line in lines)
        pad_x, pad_y = 24, 16
        box = (cx - max_w // 2 - pad_x, top - pad_y, cx + max_w // 2 + pad_x, top + total_h + pad_y)
        draw.rounded_rectangle(box, radius=12, fill=(0, 0, 0, 160))

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = cx - w // 2
        y = top + i * line_height

        if style == "outline":
            draw.text((x, y), line, font=font, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0, 255))
        elif style == "shadow":
            draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        else:  # clean, frosted (background drawn separately for frosted)
            draw.text((x, y), line, font=font, fill=(255, 255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0, 120))


def _render_static_layer(caption: str, mood: str, position: str, style: str, size) -> Image.Image:
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    font = _load_font(mood)
    draw = ImageDraw.Draw(layer)

    max_text_width = int(w * 0.85)
    lines = wrap_text(draw, caption, font, max_text_width)
    bbox = draw.textbbox((0, 0), "Ag", font=font)
    line_height = int((bbox[3] - bbox[1]) * 1.4)
    block_h = line_height * len(lines)

    cy = anchor_y(position, h, block_h)
    cx = w // 2

    if style == "frosted":
        max_w = max(draw.textbbox((0, 0), line, font=font)[2] for line in lines)
        pad_x, pad_y = 28, 20
        box = (cx - max_w // 2 - pad_x, cy - block_h // 2 - pad_y, cx + max_w // 2 + pad_x, cy + block_h // 2 + pad_y)
        frost = Image.new("RGBA", size, (0, 0, 0, 0))
        frost_draw = ImageDraw.Draw(frost)
        frost_draw.rounded_rectangle(box, radius=20, fill=(255, 255, 255, 90))
        frost = frost.filter(ImageFilter.GaussianBlur(12))
        layer = Image.alpha_composite(layer, frost)
        draw = ImageDraw.Draw(layer)
    elif style == "shadow":
        shadow = Image.new("RGBA", size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        for i, line in enumerate(lines):
            lbbox = shadow_draw.textbbox((0, 0), line, font=font)
            lw = lbbox[2] - lbbox[0]
            x = cx - lw // 2 + 3
            y = (cy - block_h // 2) + i * line_height + 4
            shadow_draw.text((x, y), line, font=font, fill=(0, 0, 0, 200))
        shadow = shadow.filter(ImageFilter.GaussianBlur(4))
        layer = Image.alpha_composite(layer, shadow)
        draw = ImageDraw.Draw(layer)

    _draw_text_block(draw, lines, font, (cx, cy), line_height, style)
    return layer


def render_beat_overlay(caption: str, mood: str, position: str, style: str, duration: float, fps: int = None) -> str:
    """Renders an animated transparent-alpha video overlay for a beat's caption. Returns path to a .mov file."""
    fps = fps or settings.DEFAULT_FPS
    size = settings.DEFAULT_RESOLUTION
    total_frames = max(1, int(duration * fps))

    static_layer = _render_static_layer(caption, mood, position, style, size)
    anim_style = animation_for_mood(mood)

    run_id = uuid.uuid4().hex[:8]
    frame_dir = os.path.join(settings.TEMP_DIR, f"txt_{run_id}")
    os.makedirs(frame_dir, exist_ok=True)

    for i in range(total_frames):
        alpha_mult, y_offset, scale = envelope(i, total_frames, ENTRANCE_FRAMES, EXIT_FRAMES, anim_style)
        frame = static_layer

        if scale != 1.0 and scale > 0:
            w, h = size
            scaled = static_layer.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
            frame = Image.new("RGBA", size, (0, 0, 0, 0))
            paste_x = (w - scaled.width) // 2
            paste_y = (h - scaled.height) // 2
            frame.paste(scaled, (paste_x, paste_y), scaled)
        elif y_offset != 0:
            frame = Image.new("RGBA", size, (0, 0, 0, 0))
            frame.paste(static_layer, (0, y_offset), static_layer)

        if alpha_mult < 1.0:
            r, g, b, a = frame.split()
            a = a.point(lambda p: int(p * alpha_mult))
            frame = Image.merge("RGBA", (r, g, b, a))

        frame.save(os.path.join(frame_dir, f"f_{i:04d}.png"))

    overlay_path = os.path.join(settings.TEMP_DIR, f"overlay_{run_id}.mov")
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", os.path.join(frame_dir, "f_%04d.png"),
            "-c:v", "qtrle",
            overlay_path,
        ],
        capture_output=True, text=True,
    )
    shutil.rmtree(frame_dir)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg overlay encode failed: {result.stderr[-1500:]}")

    return overlay_path


if __name__ == "__main__":
    path = render_beat_overlay("Hidden gems await", "energetic", "center", "pill", 3.0)
    print(path)
