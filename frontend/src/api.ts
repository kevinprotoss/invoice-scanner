export type ImageMeta = {
  page: number;
  image: string;
  width: number;
  height: number;
  sha256?: string;
  url: string;
};

export type InvoiceSummary = {
  invoice_id: string;
  document_id: string;
  ocr_ready: boolean;
  llm_ready: boolean;
  page_count: number;
  created_at: string;
  updated_at: string;
  images: ImageMeta[];
};

export type OcrItem = {
  id: number;
  text: string;
  confidence: number;
  bbox: [number, number][];
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
};

export type OcrPage = {
  page: number;
  image: string;
  image_width: number;
  image_height: number;
  items: OcrItem[];
};

export type OcrDocument = {
  schema_version: string;
  document_id: string;
  total_pages: number;
  pages: OcrPage[];
};

export type Address = {
  street: string | null;
  postal_code: string | null;
  city: string | null;
  country: string | null;
};

export type Supplier = {
  name: string | null;
  address: Address;
  vat_id: string | null;
  tax_number: string | null;
};

export type Customer = {
  name: string | null;
  address: Address;
  vat_id: string | null;
  customer_number: string | null;
};

export type InvoiceInfo = {
  invoice_number: string | null;
  invoice_date: string | null;
  service_date: string | null;
  due_date: string | null;
  currency: string | null;
};

export type TaxBreakdown = {
  tax_rate: string | null;
  net_amount: string | null;
  tax_amount: string | null;
};

export type Amounts = {
  net_amount: string | null;
  tax_amount: string | null;
  gross_amount: string | null;
  discount: string | null;
  tax_breakdown: TaxBreakdown[];
};

export type Payment = {
  payment_method: string | null;
  iban: string | null;
  bic: string | null;
  payment_reference: string | null;
};

export type LineItem = {
  description: string | null;
  quantity: string | null;
  unit: string | null;
  unit_price: string | null;
  net_amount: string | null;
  tax_rate: string | null;
  tax_amount: string | null;
  gross_amount: string | null;
  source_refs: string[];
};

export type FieldRelationship = {
  field: string;
  value: unknown;
  source_text: string[];
  source_refs: string[];
  reason: string;
};

export type UncertainItem = {
  field: string | null;
  reason: string;
  source_text: string[];
};

export type LlmMeta = {
  model: string;
  input_tokens: number;
  output_tokens: number;
  stop_reason: string | null;
  processing_time_seconds: number;
  processed_at: string;
};

export type StructuredInvoice = {
  schema_version: string;
  invoice_id: string;
  document_type: string;
  supplier: Supplier;
  customer: Customer;
  invoice: InvoiceInfo;
  amounts: Amounts;
  payment: Payment;
  line_items: LineItem[];
  field_relationships: FieldRelationship[];
  uncertain_items: UncertainItem[];
  validation: { status: string; issues: unknown[] };
  meta: LlmMeta;
};

async function jsonOrThrow<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    throw new Error(`${r.status} ${text || r.statusText}`);
  }
  return r.json() as Promise<T>;
}

export async function login(password: string): Promise<boolean> {
  const r = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
    credentials: "same-origin",
  });
  return r.ok;
}

export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" });
}

export async function me(): Promise<boolean> {
  const r = await fetch("/api/auth/me", { credentials: "same-origin" });
  if (!r.ok) return false;
  const j = await r.json();
  return !!j.authenticated;
}

export async function listInvoices(): Promise<InvoiceSummary[]> {
  return jsonOrThrow(await fetch("/api/invoices", { credentials: "same-origin" }));
}

export async function getInvoice(id: string): Promise<InvoiceSummary> {
  return jsonOrThrow(await fetch(`/api/invoices/${id}`, { credentials: "same-origin" }));
}

export async function getOcr(id: string): Promise<OcrDocument> {
  return jsonOrThrow(await fetch(`/api/invoices/${id}/ocr`, { credentials: "same-origin" }));
}

export async function getResult(id: string): Promise<StructuredInvoice> {
  return jsonOrThrow(
    await fetch(`/api/invoices/${id}/result`, { credentials: "same-origin" })
  );
}

export async function processInvoice(id: string): Promise<StructuredInvoice> {
  return jsonOrThrow(
    await fetch(`/api/invoices/${id}/process`, { method: "POST", credentials: "same-origin" })
  );
}

export async function retryInvoice(id: string): Promise<InvoiceSummary> {
  return jsonOrThrow(
    await fetch(`/api/invoices/${id}/retry`, { method: "POST", credentials: "same-origin" })
  );
}

export async function deleteInvoice(id: string): Promise<void> {
  await jsonOrThrow(
    await fetch(`/api/invoices/${id}`, { method: "DELETE", credentials: "same-origin" })
  );
}

export async function deleteAllInvoices(): Promise<{ status: string; count: number }> {
  return jsonOrThrow(
    await fetch("/api/invoices", { method: "DELETE", credentials: "same-origin" })
  );
}

export async function createInvoice(files: File[]): Promise<InvoiceSummary> {
  const fd = new FormData();
  for (const f of files) fd.append("files", f);
  return jsonOrThrow(
    await fetch("/api/invoices", { method: "POST", body: fd, credentials: "same-origin" })
  );
}

export function imageUrl(invoiceId: string, page: number): string {
  return `/api/invoices/${invoiceId}/images/${page}`;
}

export function rawLlmUrl(invoiceId: string): string {
  return `/api/invoices/${invoiceId}/raw`;
}