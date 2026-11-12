import { useRef, useState } from "react";
import { createInvoice } from "../api";

type Item = { file: File; url: string; key: string };

export default function Upload({ onDone }: { onDone: (id: string) => void }) {
  const [items, setItems] = useState<Item[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const albumRef = useRef<HTMLInputElement>(null);

  function addFiles(files: FileList | null) {
    if (!files) return;
    const next: Item[] = [];
    for (const f of Array.from(files)) {
      if (!f.type.startsWith("image/")) continue;
      next.push({
        file: f,
        url: URL.createObjectURL(f),
        key: `${f.name}-${f.size}-${Math.random().toString(36).slice(2)}`,
      });
    }
    setItems((cur) => [...cur, ...next]);
  }

  function remove(key: string) {
    setItems((cur) =>
      cur.filter((x) => {
        if (x.key === key) {
          URL.revokeObjectURL(x.url);
          return false;
        }
        return true;
      })
    );
  }

  function move(key: string, dir: -1 | 1) {
    setItems((cur) => {
      const idx = cur.findIndex((x) => x.key === key);
      if (idx < 0) return cur;
      const tgt = idx + dir;
      if (tgt < 0 || tgt >= cur.length) return cur;
      const copy = [...cur];
      [copy[idx], copy[tgt]] = [copy[tgt], copy[idx]];
      return copy;
    });
  }

  async function submit() {
    if (items.length === 0) return;
    setBusy(true);
    setErr(null);
    try {
      const inv = await createInvoice(items.map((x) => x.file));
      items.forEach((x) => URL.revokeObjectURL(x.url));
      setItems([]);
      onDone(inv.invoice_id);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <div className="row">
        <h2 style={{ flex: 1, margin: 0 }}>上传账单</h2>
        <a href="#/" className="link">返回</a>
      </div>

      {/* 拍照：直接调起后置摄像头，一次一张 */}
      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        style={{ display: "none" }}
        onChange={(e) => {
          addFiles(e.target.files);
          e.target.value = "";
        }}
      />

      {/* 相册：可多选 */}
      <input
        ref={albumRef}
        type="file"
        accept="image/*"
        multiple
        style={{ display: "none" }}
        onChange={(e) => {
          addFiles(e.target.files);
          e.target.value = "";
        }}
      />

      <div className="row" style={{ gap: 8 }}>
        <button
          className="btn"
          style={{ flex: 1 }}
          onClick={() => cameraRef.current?.click()}
          disabled={busy}
        >
          📷 拍照
        </button>
        <button
          className="btn secondary"
          style={{ flex: 1 }}
          onClick={() => albumRef.current?.click()}
          disabled={busy}
        >
          从相册选择
        </button>
      </div>

      {items.length > 0 && (
        <div className="grid">
          {items.map((it, i) => (
            <div className="thumb" key={it.key}>
              <img src={it.url} alt="" />
              <div className="thumb-actions">
                <button disabled={busy || i === 0} onClick={() => move(it.key, -1)}>↑</button>
                <button disabled={busy || i === items.length - 1} onClick={() => move(it.key, 1)}>↓</button>
                <button disabled={busy} onClick={() => remove(it.key)}>✕</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {err && <div className="error">{err}</div>}

      <button
        className="btn primary"
        onClick={submit}
        disabled={busy || items.length === 0}
      >
        {busy ? "处理中…（OCR 可能需要几分钟）" : `上传 ${items.length} 张`}
      </button>

      {busy && (
        <div className="muted small">
          请勿关闭页面。多页 OCR 会依次执行，完成后自动跳转。
        </div>
      )}
    </div>
  );
}