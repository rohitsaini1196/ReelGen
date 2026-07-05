import math


def build_filter_chain(preset: dict) -> str:
    """Returns an ffmpeg -vf filter fragment (no leading/trailing comma) for a style preset."""
    parts = [
        f"eq=brightness={preset['brightness']}:contrast={preset['contrast']}:saturation={preset['saturation']}",
        f"colortemperature=temperature={preset['temp_kelvin']}",
    ]

    vignette_strength = max(0.0, min(preset.get("vignette", 0.0), 0.9))
    if vignette_strength > 0:
        angle = (math.pi / 2) * (1 - vignette_strength)
        parts.append(f"vignette=angle={angle:.4f}")

    grain = preset.get("grain", 0.0)
    if grain > 0:
        noise_strength = max(1, int(grain * 500))
        parts.append(f"noise=alls={noise_strength}:allf=t+u")

    return ",".join(parts)
