"""Zone configuration shared between pipeline scripts and viewer.

Each zone defines where textures live, what they're called, and what
prompts produce the best upscale results for that zone's art style.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VIEWER = ROOT / "viewer"

_WOW_TERRAIN_PROMPT = (
    "Upscale this seamless tiling ground texture to higher resolution. "
    "Keep the EXACT same composition, colors, patterns, and hand-painted art style. "
    "Add fine surface detail. Do not change the content at all, "
    "only increase quality and resolution. This is a World of Warcraft terrain texture."
)

ZONES = {
    "elwynn": {
        "label": "Elwynn Forest",
        "tex_dir": VIEWER / "textures",
        "tex_ext": ".webp",
        "tex_names": [
            "elwynngrassbase",
            "elwynndirtbase2",
            "elwynnrockbasetest2",
            "elwynncobblestonebase",
        ],
        "prompt": _WOW_TERRAIN_PROMPT,
        "tex_prompts": {
            "elwynngrassbase": (
                "Transform this grass ground texture into a highly detailed, realistic yet "
                "stylized lush meadow grass. Add individual grass blade detail, natural color "
                "variation from golden-green to deep emerald, subtle wildflower specks, and "
                "rich organic depth. Keep the hand-painted World of Warcraft art style with "
                "warm fantasy lighting. Seamless tiling ground texture for a fantasy RPG."
            ),
            "elwynndirtbase2": (
                "Transform this dirt ground texture into a highly detailed, realistic yet "
                "stylized forest floor earth. Add natural soil grain, tiny scattered pebbles, "
                "fine root impressions, dried leaf fragments, and organic debris. Rich brown "
                "earth tones with natural moisture variation. Keep the hand-painted World of "
                "Warcraft art style. Seamless tiling ground texture for a fantasy RPG."
            ),
            "elwynnrockbasetest2": (
                "Transform this rock ground texture into a highly detailed, realistic yet "
                "stylized natural stone surface. Add realistic weathering, fine grain structure, "
                "subtle lichen patches, natural cracks and stratification layers, and mineral "
                "color variation. Keep the hand-painted World of Warcraft art style with warm "
                "fantasy tones. Seamless tiling ground texture for a fantasy RPG."
            ),
            "elwynncobblestonebase": (
                "Transform this cobblestone ground texture into a highly detailed, realistic "
                "yet stylized medieval cobblestone road. Add individual stone detail with "
                "subtle chisel marks, worn surfaces, moss growing between stones, fine mortar "
                "lines, and natural wear patterns. Keep the hand-painted World of Warcraft "
                "art style with warm fantasy lighting. Seamless tiling ground texture."
            ),
        },
    },
    "nagrand": {
        "label": "Nagrand",
        "tex_dir": VIEWER / "textures" / "nagrand",
        "tex_ext": ".png",
        "tex_names": [
            "tex_187327",
            "tex_189024",
            "tex_187332",
            "tex_187357",
            "tex_187350",
            "tex_187338",
            "tex_186825",
            "tex_187341",
        ],
        "prompt": _WOW_TERRAIN_PROMPT,
        "tex_prompts": {},
    },
}


def get_zone(name):
    """Return zone config dict, or raise KeyError with available zones."""
    key = name.lower()
    if key not in ZONES:
        available = ", ".join(sorted(ZONES))
        raise KeyError(f"Unknown zone '{name}'. Available: {available}")
    return ZONES[key]


def zone_src_dir(zone):
    return zone["tex_dir"] / "original"


def zone_out_dir(zone):
    return zone["tex_dir"] / "v2"


def zone_normals_dir(zone):
    return zone["tex_dir"] / "normals"


def zone_heights_dir(zone):
    return zone["tex_dir"] / "heights"


def zone_tex_files(zone):
    """Return list of existing source texture paths for the zone."""
    src = zone_src_dir(zone)
    ext = zone["tex_ext"]
    return [src / f"{name}{ext}" for name in zone["tex_names"] if (src / f"{name}{ext}").exists()]


def prompt_for(zone, tex_name):
    """Return the best prompt for a texture: per-texture if available, else zone default."""
    return zone["tex_prompts"].get(tex_name, zone["prompt"])
