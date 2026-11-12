import { useEffect, useState } from "react";
import { deleteAllInvoices, deleteInvoice, InvoiceSummary, listInvoices } from "../api";

export default function InvoiceList() {
  const [items, setItems] = useState<InvoiceSummary[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [clearing, setClearing] = useState(false);

  async function reload() {
    try {
      setErr(null);
      setItems(await listInvoices());
    } catch (e: any) {
      setErr(e.message);
    }
  }

  useEffect(() => {
    reload();
  }, []);

  async function del(id: string) {
    if (!window.confirm(`删除 ${id}？此操作不可恢复。`)) return;
    setBusy(id);
    try {
      await deleteInvoice(id);
      await reload();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(null);
    }
  }

  async function clearAll() {
    const total = items?.length ?? 0;
    if (total === 0) return;

    if (
      !window.confirm(
        `⚠️ 将删除全部 ${total} 份账单，包括原始图片、OCR 结果和 Claude 解析结果。\n\n此操作不可恢复。确定继续？`
      )
    ) {
      return;
    }

    const typed = window.prompt(
      `请输入 DELETE（全大写）以确认清空全部 ${total} 份账单：`
    );
    if (typed !== "DELETE") {
      alert("输入不匹配，已取消。");
      return;
    }

    setClearing(true);
    setErr(null);
    try {
      const res = await deleteAllInvoices();
      await reload();
      alert(`已清空 ${res.count} 份账单。`);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setClearing(false);
    }
  }

  if (items === null) return <div className="muted">加载中…</div>;

  return (
    <div className="stack">
      <div className="row">
        <h2 style={{ flex: 1, margin: 0 }}>账单</h2>
        {items.length > 0 && (
          <button
            className="link danger"
            onClick={clearAll}
            disabled={clearing}
            title="删除所有账单"
          >
            {clearing ? "清空中…" : "清空全部"}
          </button>
        )}
        <a href="#/upload" className="btn">新建</a>
      </div>
      {err && <div className="error">{err}</div>}
      {items.length === 0 && <div className="muted">还没有账单。</div>}
      {items.map((it) => (
        <div key={it.invoice_id} className="card row">
          <div style={{ flex: 1, minWidth: 0 }}>
            <a href={`#/invoice/${it.invoice_id}`} className="strong link-plain">
              {it.invoice_id}
            </a>
            <div className="muted small ellipsis">
              {it.page_count} 页 · {it.ocr_ready ? "OCR 已完成" : "未完成"} · {it.created_at}
            </div>
          </div>
          <button
            className="link danger"
            disabled={busy === it.invoice_id || clearing}
            onClick={() => del(it.invoice_id)}
          >
            删除
          </button>
        </div>
      ))}
    </div>
  );
}