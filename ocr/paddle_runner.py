import os
import threading
from pathlib import Path

from paddleocr import PaddleOCR

_OCR_LANG = os.environ.get("OCR_LANG", "german")
_OCR_USE_GPU = os.environ.get("OCR_USE_GPU", "0") == "1"

_engine: PaddleOCR | None = None
_engine_lock = threading.Lock()
_ocr_lock = threading.Lock()


def _get_engine() -> PaddleOCR:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = PaddleOCR(
                    use_angle_cls=True,
                    lang=_OCR_LANG,
                    use_gpu=_OCR_USE_GPU,
                    show_log=False,
                )
    return _engine


def ocr_image(image_path: str | Path) -> dict:
    """Run OCR on a single image and return {"items": [...]}.

    Each item preserves the original PaddleOCR structure:
    id, text, confidence, bbox (4 points), x_min, y_min, x_max, y_max.
    """
    image_path = Path(image_path)
    if not image_path.is_file():
        raise FileNotFoundError(image_path)

    with _ocr_lock:
        result = _get_engine().ocr(str(image_path), cls=True)

    items = []
    if result:
        for page in result:
            if not page:
                continue
            for line in page:
                if not line:
                    continue
                bbox = line[0]
                text = line[1][0]
                confidence = float(line[1][1])
                points = [[float(x), float(y)] for x, y in bbox]
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                items.append(
                    {
                        "id": len(items),
                        "text": text,
                        "confidence": confidence,
                        "bbox": points,
                        "x_min": min(xs),
                        "y_min": min(ys),
                        "x_max": max(xs),
                        "y_max": max(ys),
                    }
                )
    return {"items": items}