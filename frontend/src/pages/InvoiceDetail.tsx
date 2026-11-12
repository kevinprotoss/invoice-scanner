import { useEffect, useRef, useState } from "react";
import {
  FieldRelationship,
  getInvoice,
  getOcr,
  getResult,
  imageUrl,
  InvoiceSummary,
  OcrDocument,
  processInvoice,
  rawLlmUrl,
  retryInvoice,
  StructuredInvoice,
} from "../api";

type Phase = "loading" | "ocr-only" | "llm-running" | "ready" | "llm-failed";

export default function InvoiceDetail({ id }: { id: string }) {
  const [inv, setInv] = useState<InvoiceSummary | null>(null);
  const [ocr, setOcr] = useState<OcrDocument | null>(null);
  const [structured, setStructured] = useState<StructuredInvoice | null>(null);
  const [phase, setPhase] = useState<Phase>("loading");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [page, setPage] = useState(1);
  const [active, setActive] = useState<number | null>(null);
  const startedRef = useRef(false);

  async function loadOcr(invoiceId: string) {
    try {
      setOcr(await getOcr(invoiceId));
    } catch {
      setOcr(null);
    }
  }

  async function runLlm(invoiceId: string) {
    setPhase("llm-running");
    setErr(null);
    try {
      const doc = await processInvoice(invoiceId);
      setStructured(doc);
      setPhase("ready");
    } catch (e: any) {
      setErr(e.message);
      setPhase("llm-failed");
    }
  }

  async function bootstrap() {
    setPhase("loading");
    setErr(null);
    try {
      const i = await getInvoice(id);
      setInv(i);
      if (i.ocr_ready) {
        await loadOcr(id);
      }
      if (i.llm_ready) {
        try {
          setStructured(await getResult(id));
          setPhase("ready");
          return;
        } catch {
          // fall through
        }
      }
      if (i.ocr_ready) {
        await runLlm(id);
      } else {
        setPhase("ocr-only");
      }
    } catch (e: any) {
      setErr(e.message);
      setPhase("ocr-only");
    }
  }

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    bootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function retryOcr() {
    setBusy(true);
    setErr(null);
    try {
      const i = await retryInvoice(id);
      setInv(i);
      if (i.ocr_ready) {
        await loadOcr(id);
        await runLlm(id);
      }
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  function refreshStructured() {
    runLlm(id);
  }

  if (!inv) {
    return err ? <div className="error">{err}</div> : <div className="muted">加载中…</div>;
  }

  const current = ocr?.pages.find((p) => p.page === page) || ocr?.pages[0] || null;

  return (
    <div className="stack">
      <div className="row">
        <h2 style={{ flex: 1, margin: 0, wordBreak: "break-all" }}>{inv.invoice_id}</h2>
        <a href="#/" className="link">返回</a>
      </div>
      <div className="muted small">
        {inv.page_count} 页 · {inv.created_at}
      </div>

      {err && <div className="error">{err}</div>}

      {phase === "loading" && <div className="muted">加载中…</div>}

      {phase === "ocr-only" && (
        <div className="card">
          <p>OCR 未完成。可重试 OCR。</p>
          <button className="btn" onClick={retryOcr} disabled={busy}>
            {busy ? "处理中…" : "重试 OCR"}
          </button>
        </div>
      )}

      {phase === "llm-running" && (
        <div className="banner">
          正在解析账单结构…（Claude 处理中，可能需要 10–60 秒）
        </div>
      )}

      {phase === "llm-failed" && (
        <div className="banner error-banner">
          <div>账单解析失败：{err}</div>
          <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button className="btn" onClick={refreshStructured}>
              重试解析
            </button>
            <a className="btn secondary" href={rawLlmUrl(id)} target="_blank" rel="noreferrer">
              查看原始响应
            </a>
          </div>
        </div>
      )}

      {structured && <SummaryCard doc={structured} />}

      {structured && (
        <details className="card">
          <summary>字段关联关系 · {structured.field_relationships.length} 条</summary>
          <div style={{ marginTop: 12 }}>
            {structured.field_relationships.length === 0 && (
              <div className="muted">Claude 未返回字段关联关系。</div>
            )}
            {structured.field_relationships.map((r, i) => (
              <RelationshipRow key={i} rel={r} />
            ))}
          </div>
        </details>
      )}

      {structured && structured.uncertain_items.length > 0 && (
        <details className="card">
          <summary>不确定项 · {structured.uncertain_items.length} 条</summary>
          <div style={{ marginTop: 12 }}>
            {structured.uncertain_items.map((u, i) => (
              <div key={i} className="rel-row">
                <div className="strong">{u.field ?? "（未指定字段）"}</div>
                <div>{u.reason}</div>
                {u.source_text.length > 0 && (
                  <div className="muted small">原文：{u.source_text.join(" / ")}</div>
                )}
              </div>
            ))}
          </div>
        </details>
      )}

      {ocr && (
        <details className="card ocr-fold" open={!structured}>
          <summary>
            OCR 原始结果 · {ocr.total_pages} 页 ·{" "}
            {ocr.pages.reduce((n, p) => n + p.items.length, 0)} 项
          </summary>

          <div className="tabs" style={{ marginTop: 12 }}>
            {ocr.pages.map((p) => (
              <button
                key={p.page}
                className={`tab ${p.page === page ? "active" : ""}`}
                onClick={() => {
                  setPage(p.page);
                  setActive(null);
                }}
              >
                第 {p.page} 页
              </button>
            ))}
          </div>

          {current && (
            <div className="ocr-view" style={{ marginTop: 12 }}>
              <div className="ocr-image">
                <div style={{ position: "relative", display: "inline-block", maxWidth: "100%" }}>
                  <img
                    src={imageUrl(id, current.page)}
                    alt=""
                    style={{ width: "100%", display: "block" }}
                  />
                  <svg
                    viewBox={`0 0 ${current.image_width} ${current.image_height}`}
                    preserveAspectRatio="none"
                    style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
                  >
                    {current.items.map((it) => (
                      <polygon
                        key={it.id}
                        points={it.bbox.map((p) => p.join(",")).join(" ")}
                        fill={active === it.id ? "rgba(37,99,235,0.25)" : "transparent"}
                        stroke={active === it.id ? "#2563eb" : "rgba(37,99,235,0.45)"}
                        strokeWidth={active === it.id ? 3 : 1}
                        onClick={() => setActive(it.id)}
                        style={{ cursor: "pointer" }}
                      />
                    ))}
                  </svg>
                </div>
              </div>

              <div className="ocr-list">
                {current.items.map((it) => (
                  <div
                    key={it.id}
                    className={`ocr-item ${active === it.id ? "active" : ""}`}
                    onClick={() => setActive(it.id)}
                  >
                    <div className="strong">{it.text}</div>
                    <div className="muted small">
                      id {it.id} · conf {it.confidence.toFixed(3)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </details>
      )}

      {structured && (
        <div className="muted small">
          {structured.meta.model} · in {structured.meta.input_tokens} / out{" "}
          {structured.meta.output_tokens} tokens · {structured.meta.processing_time_seconds}s
        </div>
      )}
    </div>
  );
}

function SummaryCard({ doc }: { doc: StructuredInvoice }) {
  const a = doc.amounts;
  const inv = doc.invoice;
  return (
    <div className="card stack">
      <div className="row" style={{ alignItems: "baseline" }}>
        <div className="strong" style={{ fontSize: 18, flex: 1 }}>
          {doc.supplier.name ?? "（未识别供应商）"}
        </div>
        <span className="badge">{doc.document_type}</span>
      </div>

      <div className="kv">
        <div>单据号</div>
        <div>{inv.invoice_number ?? "—"}</div>
        <div>日期</div>
        <div>{inv.invoice_date ?? "—"}</div>
        <div>币种</div>
        <div>{inv.currency ?? "—"}</div>
      </div>

      <div className="kv">
        <div>净额</div>
        <div>{fmtMoney(a.net_amount, inv.currency)}</div>
        <div>税额</div>
        <div>{fmtMoney(a.tax_amount, inv.currency)}</div>
        <div>总额</div>
        <div className="strong">{fmtMoney(a.gross_amount, inv.currency)}</div>
      </div>

      {a.tax_breakdown.length > 0 && (
        <div>
          <div className="muted small" style={{ marginBottom: 4 }}>VAT 明细</div>
          <table className="table">
            <thead>
              <tr>
                <th>税率</th>
                <th>净额</th>
                <th>税额</th>
              </tr>
            </thead>
            <tbody>
              {a.tax_breakdown.map((t, i) => (
                <tr key={i}>
                  <td>{t.tax_rate ?? "—"}</td>
                  <td>{t.net_amount ?? "—"}</td>
                  <td>{t.tax_amount ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {doc.line_items.length > 0 && (
        <div>
          <div className="muted small" style={{ marginBottom: 4 }}>
            商品明细 · {doc.line_items.length} 行
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>描述</th>
                <th>数量</th>
                <th>单价</th>
                <th>净额</th>
                <th>税率</th>
                <th>金额</th>
              </tr>
            </thead>
            <tbody>
              {doc.line_items.map((li, i) => (
                <tr key={i}>
                  <td>{li.description ?? "—"}</td>
                  <td>{li.quantity ?? "—"}</td>
                  <td>{li.unit_price ?? "—"}</td>
                  <td>{li.net_amount ?? "—"}</td>
                  <td>{li.tax_rate ?? "—"}</td>
                  <td>{li.gross_amount ?? li.net_amount ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {doc.payment.iban && (
        <div className="muted small">
          付款：{doc.payment.payment_method ?? "—"} · IBAN {doc.payment.iban}
        </div>
      )}
    </div>
  );
}

function RelationshipRow({ rel }: { rel: FieldRelationship }) {
  const isScalar =
    rel.value === null ||
    typeof rel.value === "string" ||
    typeof rel.value === "number" ||
    typeof rel.value === "boolean";

  return (
    <div className="rel-row">
      <div className="strong">{rel.field}</div>
      <div>
        值：
        {isScalar ? (
          <span>{rel.value === null ? "null" : String(rel.value)}</span>
        ) : (
          <details style={{ marginTop: 4 }}>
            <summary className="muted small">展开结构（JSON）</summary>
            <pre className="json-pre">{JSON.stringify(rel.value, null, 2)}</pre>
          </details>
        )}
      </div>
      {rel.source_text.length > 0 && (
        <div className="muted small">原文：{rel.source_text.join(" / ")}</div>
      )}
      {rel.source_refs.length > 0 && (
        <div className="muted small">引用：{rel.source_refs.join(", ")}</div>
      )}
      <div className="muted small">理由：{rel.reason}</div>
    </div>
  );
}

function fmtMoney(v: string | null, currency: string | null): string {
  if (v === null || v === "") return "—";
  return currency ? `${v} ${currency}` : v;
}