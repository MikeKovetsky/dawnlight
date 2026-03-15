import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
INPUT_DIR = ASSETS / "input"
UPSCALED_DIR = ASSETS / "upscaled"
MESHES_DIR = ASSETS / "meshes"

fal_key = os.getenv("FAL_KEY") or os.getenv("FAL_API_KEY")
if fal_key:
    os.environ["FAL_KEY"] = fal_key

ESRGAN = "fal-ai/esrgan"
TRELLIS = "fal-ai/trellis-2"

IMG_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tga", ".webp"}


def ensure_dirs():
    for d in (INPUT_DIR, UPSCALED_DIR, MESHES_DIR):
        d.mkdir(parents=True, exist_ok=True)
