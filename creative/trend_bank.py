HOOK_PATTERNS = [
    "question",       # "Ever wondered why...?"
    "bold_claim",     # "This is the best coffee shop you've never heard of."
    "pov",            # "POV: you just found the last quiet beach in Bali."
    "controversial",  # "Stop doing X. Here's why."
]

# Curated palette sets — LLM picks from these, not random hex codes.
PALETTE_SETS = {
    "warm-analog":  ["#3a2a1e", "#f4e3c1", "#c9822f"],
    "cool-minimal": ["#1c1f26", "#f5f7fa", "#5a7d9a"],
    "golden-hour":  ["#3d2b1f", "#ffd27a", "#ff8c42"],
    "moody-dark":   ["#0d0d0d", "#e0e0e0", "#8a3ffc"],
}

STYLE_PRESETS = list(PALETTE_SETS.keys())
