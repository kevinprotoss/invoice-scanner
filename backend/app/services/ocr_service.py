import asyncio
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ocr.paddle_runner import ocr_image  # noqa: E402


async def run_ocr(image_path: Path) -> dict:
    return await asyncio.to_thread(ocr_image, image_path)