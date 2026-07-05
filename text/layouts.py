def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def anchor_y(position: str, canvas_h: int, block_h: int) -> int:
    safe_top = int(canvas_h * 0.15)
    safe_bottom = int(canvas_h * 0.90)
    margin = 24

    if position == "top":
        return safe_top + block_h // 2 + margin
    elif position == "bottom":
        return safe_bottom - block_h // 2 - margin
    return canvas_h // 2  # center
