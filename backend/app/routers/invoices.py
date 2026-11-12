import asyncio

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from ..auth import require_auth
from ..services import invoice_service as svc
from ..services import llm_service

router = APIRouter(prefix="/api/invoices")


def _ensure_auth(request: Request) -> None:
    require_auth(request)


@router.post("", status_code=201)
async def create_invoice(request: Request, files: list[UploadFile] = File(...)):
    _ensure_auth(request)
    if not files:
        raise HTTPException(400, "no files")
    if len(files) > svc.settings.max_images_per_invoice:
        raise HTTPException(400, "too many files")

    invoice_id, _ = svc.create_invoice()
    document_id = svc.ensure_document_id(invoice_id)

    saved: list[dict] = []
    for f in files:
        data = await f.read()
        if not data:
            continue
        try:
            saved.append(svc.add_image(invoice_id, f.filename or "upload", data))
        except ValueError as e:
            if not saved:
                svc.delete_invoice(invoice_id)
            raise HTTPException(400, str(e))

    if not saved:
        svc.delete_invoice(invoice_id)
        raise HTTPException(400, "no valid images")

    try:
        await svc.process_ocr(invoice_id, document_id, saved)
    except Exception as e:
        raise HTTPException(500, f"OCR failed: {e}. Files kept on disk, use retry.")

    return svc.get_invoice(invoice_id)


@router.post("/{invoice_id}/images")
async def append_images(invoice_id: str, request: Request, files: list[UploadFile] = File(...)):
    _ensure_auth(request)
    if not svc.invoice_exists(invoice_id):
        raise HTTPException(404, "invoice not found")
    if not files:
        raise HTTPException(400, "no files")

    document_id = svc.ensure_document_id(invoice_id)
    saved: list[dict] = []
    for f in files:
        data = await f.read()
        if not data:
            continue
        try:
            saved.append(svc.add_image(invoice_id, f.filename or "upload", data))
        except ValueError as e:
            raise HTTPException(400, str(e))

    if not saved:
        raise HTTPException(400, "no valid images")

    try:
        await svc.process_ocr(invoice_id, document_id, None)
    except Exception as e:
        raise HTTPException(500, f"OCR failed: {e}. Use retry.")

    return svc.get_invoice(invoice_id)


@router.post("/{invoice_id}/retry")
async def retry_invoice(invoice_id: str, request: Request):
    _ensure_auth(request)
    if not svc.invoice_exists(invoice_id):
        raise HTTPException(404, "invoice not found")
    document_id = svc.ensure_document_id(invoice_id)
    try:
        await svc.process_ocr(invoice_id, document_id, None)
    except Exception as e:
        raise HTTPException(500, f"OCR failed: {e}")
    return svc.get_invoice(invoice_id)


@router.post("/{invoice_id}/process")
async def process_invoice(invoice_id: str, request: Request):
    """Run Claude once. Idempotent: if result/invoice.json exists, return it."""
    _ensure_auth(request)
    if not svc.invoice_exists(invoice_id):
        raise HTTPException(404, "invoice not found")

    existing = svc.read_invoice_json(invoice_id)
    if existing is not None:
        return existing

    if not svc.ocr_ready(invoice_id):
        raise HTTPException(409, "OCR not ready; run retry first")

    combined = svc.read_combined_ocr(invoice_id)
    if combined is None:
        raise HTTPException(500, "combined OCR unreadable")

    try:
        payload, raw_text, meta = await asyncio.to_thread(llm_service.analyze, combined)
    except llm_service.LlmError as e:
        if e.raw_text:
            try:
                svc.write_llm_raw(invoice_id, e.raw_text)
            except Exception:
                pass
        raise HTTPException(500, f"LLM failed: {e}")

    doc = svc.write_invoice_result(invoice_id, payload, raw_text, meta)
    return doc


@router.get("")
def list_invoices(request: Request):
    _ensure_auth(request)
    return svc.list_invoices()


@router.get("/{invoice_id}")
def get_invoice(invoice_id: str, request: Request):
    _ensure_auth(request)
    inv = svc.get_invoice(invoice_id)
    if inv is None:
        raise HTTPException(404, "invoice not found")
    return inv


@router.get("/{invoice_id}/result")
def get_result(invoice_id: str, request: Request):
    _ensure_auth(request)
    if not svc.invoice_exists(invoice_id):
        raise HTTPException(404, "invoice not found")
    doc = svc.read_invoice_json(invoice_id)
    if doc is None:
        raise HTTPException(404, "result not found")
    return JSONResponse(doc)


@router.get("/{invoice_id}/raw")
def get_raw(invoice_id: str, request: Request):
    _ensure_auth(request)
    if not svc.invoice_exists(invoice_id):
        raise HTTPException(404, "invoice not found")
    text = svc.read_raw_llm(invoice_id)
    if text is None:
        raise HTTPException(404, "raw not found")
    return PlainTextResponse(text, media_type="text/plain; charset=utf-8")


@router.get("/{invoice_id}/images")
def get_images(invoice_id: str, request: Request):
    _ensure_auth(request)
    inv = svc.get_invoice(invoice_id)
    if inv is None:
        raise HTTPException(404, "invoice not found")
    return inv["images"]


@router.get("/{invoice_id}/images/{page}")
def get_image(invoice_id: str, page: int, request: Request):
    _ensure_auth(request)
    path = svc.get_image_path(invoice_id, page)
    if path is None:
        raise HTTPException(404, "image not found")
    return FileResponse(path)


@router.get("/{invoice_id}/ocr")
def get_ocr(invoice_id: str, request: Request):
    _ensure_auth(request)
    if not svc.invoice_exists(invoice_id):
        raise HTTPException(404, "invoice not found")
    data = svc.read_combined_ocr(invoice_id)
    if data is None:
        raise HTTPException(409, "OCR not ready")
    return JSONResponse(data)


@router.delete("/{invoice_id}")
def delete_invoice(invoice_id: str, request: Request):
    _ensure_auth(request)
    if not svc.delete_invoice(invoice_id):
        raise HTTPException(404, "invoice not found")
    return {"status": "deleted", "invoice_id": invoice_id}

@router.delete("")
def delete_all_invoices(request: Request):
    _ensure_auth(request)
    count = svc.delete_all_invoices()
    return {"status": "deleted", "count": count}