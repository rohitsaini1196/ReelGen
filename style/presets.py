from creative.trend_bank import PALETTE_SETS

# brightness/contrast/saturation map onto ffmpeg's eq filter.
# temp_kelvin maps onto ffmpeg's colortemperature filter (default neutral ~6500K).
STYLE_PRESETS = {
    "warm-analog": {
        "brightness": 0.04,
        "contrast": 1.10,
        "saturation": 1.15,
        "grain": 0.02,
        "vignette": 0.3,
        "temp_kelvin": 5500,  # warm
        "palette": PALETTE_SETS["warm-analog"],
    },
    "cool-minimal": {
        "brightness": 0.06,
        "contrast": 1.05,
        "saturation": 0.90,
        "grain": 0.0,
        "vignette": 0.1,
        "temp_kelvin": 7500,  # cool
        "palette": PALETTE_SETS["cool-minimal"],
    },
    "golden-hour": {
        "brightness": 0.03,
        "contrast": 1.15,
        "saturation": 1.25,
        "grain": 0.01,
        "vignette": 0.4,
        "temp_kelvin": 4500,  # golden
        "palette": PALETTE_SETS["golden-hour"],
    },
    "moody-dark": {
        "brightness": -0.05,
        "contrast": 1.20,
        "saturation": 0.85,
        "grain": 0.03,
        "vignette": 0.5,
        "temp_kelvin": 5000,  # teal-orange leaning warm shadows
        "palette": PALETTE_SETS["moody-dark"],
    },
}


def get_preset(name: str) -> dict:
    return STYLE_PRESETS.get(name, STYLE_PRESETS["cool-minimal"])
