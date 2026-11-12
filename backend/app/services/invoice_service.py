import hashlib
import json
import re
import shutil
import threading
import uuid
from datetime import datetime
from pathlib import Path

from ..config import settings
from ..models.invoice import ClaudeInvoicePayload
from .ocr_service import run_ocr

_id_lock = threading.Lock()

_INVOICE_RE = re.compile(r"^INV-(\d{8})-(\d{3,})$")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def detect_image_ext(data: bytes) -> str | None:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def read_image_size(path: Path) -> tuple[int, int]:
    from PIL import Image

    with Image.open(path) as im:
        return im.size


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def _atomic_write_text(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def invoices_root() -> Path:
    return Path(settings.data_dir) / "invoices"


def invoice_dir(invoice_id: str) -> Path:
    m = _INVOICE_RE.match(invoice_id)
    if not m:
        raise ValueError("invalid invoice_id")
    year = m.group(1)[:4]
    return invoices_root() / year / invoice_id


def _next_invoice_id() -> str:
    with _id_lock:
        day = datetime.now().strftime("%Y%m%d")
        year = day[:4]
        base = invoices_root() / year
        base.mkdir(parents=True, exist_ok=True)
        pattern = re.compile(rf"^INV-{day}-(\d+)$")
        max_n = 0
        for entry in base.iterdir():
            if not entry.is_dir():
                continue
            m = pattern.match(entry.name)
            if m:
                max_n = max(max_n, int(m.group(1)))
        return f"INV-{day}-{max_n + 1:03d}"


def create_invoice() -> tuple[str, str]:
    invoice_id = _next_invoice_id()
    document_id = uuid.uuid4().hex
    d = invoice_dir(invoice_id)
    (d / "original").mkdir(parents=True, exist_ok=True)
    (d / "ocr").mkdir(parents=True, exist_ok=True)
    return invoice_id, document_id


def invoice_exists(invoice_id: str) -> bool:
    try:
        return invoice_dir(invoice_id).is_dir()
    except ValueError:
        return False


def _existing_pages(invoice_id: str) -> list[dict]:
    d = invoice_dir(invoice_id) / "original"
    if not d.is_dir():
        return []
    result = []
    for p in sorted(d.iterdir()):
        m = re.match(r"^page_(\d+)\.(png|jpg|webp)$", p.name)
        if not m:
            continue
        page = int(m.group(1))
        width, height = read_image_size(p)
        result.append({"page": page, "image": p.name, "width": width, "height": height})
    return result


def add_image(invoice_id: str, original_filename: str, data: bytes) -> dict:
    if not data:
        raise ValueError("empty file")
    if len(data) > settings.max_upload_bytes:
        raise ValueError("file too large")
    ext = detect_image_ext(data)
    if ext is None:
        raise ValueError("unsupported image type")

    current = _existing_pages(invoice_id)
    if len(current) >= settings.max_images_per_invoice:
        raise ValueError("too many images")

    page = (current[-1]["page"] if current else 0) + 1
    stored = f"page_{page:03d}.{ext}"
    target = invoice_dir(invoice_id) / "original" / stored
    target.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_bytes(target, data)

    try:
        width, height = read_image_size(target)
    except Exception:
        target.unlink(missing_ok=True)
        raise

    sha = hashlib.sha256(data).hexdigest()
    return {
        "page": page,
        "image": stored,
        "width": width,
        "height": height,
        "sha256": sha,
    }


def _page_ocr_path(invoice_id: str, page: int) -> Path:
    return invoice_dir(invoice_id) / "ocr" / f"page_{page:03d}_ocr.json"


def _combined_ocr_path(invoice_id: str) -> Path:
    return invoice_dir(invoice_id) / "ocr" / "combined_ocr.json"


def ocr_ready(invoice_id: str) -> bool:
    try:
        return _combined_ocr_path(invoice_id).is_file()
    except ValueError:
        return False


def _build_combined(invoice_id: str, document_id: str, pages: list[dict]) -> dict:
    page_docs = []
    for img in pages:
        p = _page_ocr_path(invoice_id, img["page"])
        page_docs.append(json.loads(p.read_text("utf-8")))
    return {
        "schema_version": "1.0",
        "document_id": document_id,
        "total_pages": len(page_docs),
        "pages": page_docs,
    }


async def process_ocr(
    invoice_id: str,
    document_id: str,
    pages: list[dict] | None = None,
) -> dict:
    d = invoice_dir(invoice_id)
    (d / "ocr").mkdir(parents=True, exist_ok=True)
    images = pages if pages is not None else _existing_pages(invoice_id)

    for img in images:
        page_path = _page_ocr_path(invoice_id, img["page"])
        if page_path.is_file():
            continue
        image_path = d / "original" / img["image"]
        data = await run_ocr(image_path)
        page_doc = {
            "page": img["page"],
            "image": img["image"],
            "image_width": img["width"],
            "image_height": img["height"],
            "items": data["items"],
        }
        _atomic_write_text(page_path, json.dumps(page_doc, ensure_ascii=False, indent=2))

    combined = _build_combined(invoice_id, document_id, images)
    _atomic_write_text(
        _combined_ocr_path(invoice_id),
        json.dumps(combined, ensure_ascii=False, indent=2),
    )
    return combined


def _read_document_id(invoice_id: str) -> str | None:
    combined = _combined_ocr_path(invoice_id)
    if not combined.is_file():
        return None
    try:
        return json.loads(combined.read_text("utf-8")).get("document_id")
    except Exception:
        return None


def _document_id_for_new(invoice_id: str) -> str:
    meta = invoice_dir(invoice_id) / "document_id.txt"
    if meta.is_file():
        return meta.read_text("utf-8").strip()
    new_id = uuid.uuid4().hex
    _atomic_write_text(meta, new_id + "\n")
    return new_id


def ensure_document_id(invoice_id: str) -> str:
    existing = _read_document_id(invoice_id)
    if existing:
        return existing
    return _document_id_for_new(invoice_id)


def result_dir(invoice_id: str) -> Path:
    return invoice_dir(invoice_id) / "result"


def result_path(invoice_id: str) -> Path:
    return result_dir(invoice_id) / "invoice.json"


def raw_llm_path(invoice_id: str) -> Path:
    return result_dir(invoice_id) / "claude_raw.txt"


def llm_ready(invoice_id: str) -> bool:
    try:
        return result_path(invoice_id).is_file()
    except ValueError:
        return False


def read_invoice_json(invoice_id: str) -> dict | None:
    p = result_path(invoice_id)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text("utf-8"))
    except Exception:
        return None


def read_raw_llm(invoice_id: str) -> str | None:
    p = raw_llm_path(invoice_id)
    if not p.is_file():
        return None
    try:
        return p.read_text("utf-8")
    except Exception:
        return None


def write_llm_raw(invoice_id: str, raw_text: str) -> None:
    d = result_dir(invoice_id)
    d.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(raw_llm_path(invoice_id), raw_text)


def write_invoice_result(
    invoice_id: str,
    payload: ClaudeInvoicePayload,
    raw_text: str,
    meta: dict,
) -> dict:
    d = result_dir(invoice_id)
    d.mkdir(parents=True, exist_ok=True)

    # raw first: even if the JSON write fails, the raw response survives
    _atomic_write_text(raw_llm_path(invoice_id), raw_text)

    doc = {
        "schema_version": "1.0",
        "invoice_id": invoice_id,
        **payload.model_dump(),
        "validation": {"status": "PENDING", "issues": []},
        "meta": meta,
    }
    _atomic_write_text(
        result_path(invoice_id),
        json.dumps(doc, ensure_ascii=False, indent=2),
    )
    return doc


def get_invoice(invoice_id: str) -> dict | None:
    if not invoice_exists(invoice_id):
        return None
    pages = _existing_pages(invoice_id)
    d = invoice_dir(invoice_id)
    document_id = ensure_document_id(invoice_id)
    return {
        "invoice_id": invoice_id,
        "document_id": document_id,
        "ocr_ready": ocr_ready(invoice_id),
        "llm_ready": llm_ready(invoice_id),
        "page_count": len(pages),
        "created_at": datetime.fromtimestamp(d.stat().st_ctime).isoformat(timespec="seconds"),
        "updated_at": datetime.fromtimestamp(d.stat().st_mtime).isoformat(timespec="seconds"),
        "images": [
            {**p, "url": f"/api/invoices/{invoice_id}/images/{p['page']}"}
            for p in pages
        ],
    }


def list_invoices() -> list[dict]:
    root = invoices_root()
    if not root.is_dir():
        return []
    out = []
    for year_dir in sorted(root.iterdir(), reverse=True):
        if not year_dir.is_dir():
            continue
        for inv_dir in sorted(year_dir.iterdir(), reverse=True):
            if not inv_dir.is_dir():
                continue
            invoice_id = inv_dir.name
            if not _INVOICE_RE.match(invoice_id):
                continue
            try:
                out.append(get_invoice(invoice_id))
            except Exception:
                continue
    return [x for x in out if x is not None]


def get_image_path(invoice_id: str, page: int) -> Path | None:
    if not invoice_exists(invoice_id):
        return None
    for img in _existing_pages(invoice_id):
        if img["page"] == page:
            p = invoice_dir(invoice_id) / "original" / img["image"]
            return p if p.is_file() else None
    return None


def read_combined_ocr(invoice_id: str) -> dict | None:
    if not ocr_ready(invoice_id):
        return None
    try:
        return json.loads(_combined_ocr_path(invoice_id).read_text("utf-8"))
    except Exception:
        return None


def delete_invoice(invoice_id: str) -> bool:
    if not invoice_exists(invoice_id):
        return False
    shutil.rmtree(invoice_dir(invoice_id))
    return True

def delete_all_invoices() -> int:
    """Delete every invoice under data/invoices. Returns number of invoices removed."""
    root = invoices_root()
    if not root.is_dir():
        return 0
    count = 0
    for year_dir in root.iterdir():
        if not year_dir.is_dir():
            continue
        for inv_dir in year_dir.iterdir():
            if inv_dir.is_dir() and _INVOICE_RE.match(inv_dir.name):
                shutil.rmtree(inv_dir)
                count += 1
    return count