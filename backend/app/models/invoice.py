from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Address(StrictModel):
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country: str | None = None


class Supplier(StrictModel):
    name: str | None = None
    address: Address = Field(default_factory=Address)
    vat_id: str | None = None
    tax_number: str | None = None


class Customer(StrictModel):
    name: str | None = None
    address: Address = Field(default_factory=Address)
    vat_id: str | None = None
    customer_number: str | None = None


class InvoiceInfo(StrictModel):
    invoice_number: str | None = None
    invoice_date: str | None = None
    service_date: str | None = None
    due_date: str | None = None
    currency: str | None = None


class TaxBreakdown(StrictModel):
    tax_rate: str | None = None
    net_amount: str | None = None
    tax_amount: str | None = None


class Amounts(StrictModel):
    net_amount: str | None = None
    tax_amount: str | None = None
    gross_amount: str | None = None
    discount: str | None = None
    tax_breakdown: list[TaxBreakdown] = Field(default_factory=list)


class Payment(StrictModel):
    payment_method: str | None = None
    iban: str | None = None
    bic: str | None = None
    payment_reference: str | None = None


class LineItem(StrictModel):
    description: str | None = None
    quantity: str | None = None
    unit: str | None = None
    unit_price: str | None = None
    net_amount: str | None = None
    tax_rate: str | None = None
    tax_amount: str | None = None
    gross_amount: str | None = None
    source_refs: list[str] = Field(default_factory=list)


class FieldRelationship(StrictModel):
    field: str
    value: Any = None
    source_text: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    reason: str


class UncertainItem(StrictModel):
    field: str | None = None
    reason: str
    source_text: list[str] = Field(default_factory=list)


class ClaudeInvoicePayload(StrictModel):
    document_type: str = "invoice"
    supplier: Supplier = Field(default_factory=Supplier)
    customer: Customer = Field(default_factory=Customer)
    invoice: InvoiceInfo = Field(default_factory=InvoiceInfo)
    amounts: Amounts = Field(default_factory=Amounts)
    payment: Payment = Field(default_factory=Payment)
    line_items: list[LineItem] = Field(default_factory=list)
    field_relationships: list[FieldRelationship] = Field(default_factory=list)
    uncertain_items: list[UncertainItem] = Field(default_factory=list)


class ValidationResult(BaseModel):
    status: str = "PENDING"
    issues: list[dict[str, Any]] = Field(default_factory=list)


class LlmMeta(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    stop_reason: str | None
    processing_time_seconds: float
    processed_at: str


class InvoiceDocument(BaseModel):
    schema_version: str = "1.0"
    invoice_id: str
    document_type: str = "invoice"
    supplier: Supplier
    customer: Customer
    invoice: InvoiceInfo
    amounts: Amounts
    payment: Payment
    line_items: list[LineItem]
    field_relationships: list[FieldRelationship]
    uncertain_items: list[UncertainItem]
    validation: ValidationResult = Field(default_factory=ValidationResult)
    meta: LlmMeta