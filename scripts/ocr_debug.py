import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ocr.paddle_runner import ocr_image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=None)
    args = ap.parse_args()

    if not args.image.is_file():
        raise SystemExit(f"not found: {args.image}")

    data = ocr_image(args.image)
    out = {
        "image": str(args.image),
        "item_count": len(data["items"]),
        "items": data["items"],
    }
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"wrote {args.output} ({len(data['items'])} items)")
    else:
        print(text)


if __name__ == "__main__":
    main()