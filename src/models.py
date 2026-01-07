"""Data models for order extraction."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExtractedItem(BaseModel):
    """A single item extracted from the order."""

    product_name: str = Field(description="Name of the product")
    quantity: float = Field(description="Quantity ordered")
    unit: str = Field(description="Unit of measurement (kg, L, pieces, boxes, rolls, etc.)")
    confidence: ConfidenceLevel = Field(description="Confidence in this extraction")
    original_text: str = Field(description="Original text this was extracted from")
    notes: Optional[str] = Field(default=None, description="Any ambiguity or clarification needed")


class DetectedLanguage(str, Enum):
    ENGLISH = "english"
    SWAHILI = "swahili"
    MIXED = "mixed"


class ExtractedOrder(BaseModel):
    """Structured order data extracted from a WhatsApp message."""

    customer_name: str = Field(description="Name of the customer or contact person")
    customer_organization: Optional[str] = Field(default=None, description="Lodge/hotel name if mentioned")
    items: list[ExtractedItem] = Field(description="List of items ordered")
    requested_delivery_date: Optional[str] = Field(default=None, description="When delivery is needed")
    delivery_urgency: Optional[str] = Field(default=None, description="Urgency indicators like 'ASAP', 'latest', etc.")
    overall_confidence: ConfidenceLevel = Field(description="Overall confidence in the extraction")
    requires_clarification: bool = Field(description="Whether human follow-up is needed")
    clarification_needed: list[str] = Field(default_factory=list, description="List of items needing clarification")
    detected_language: DetectedLanguage = Field(default=DetectedLanguage.ENGLISH, description="Primary language detected in the message")
    raw_message: str = Field(description="Original message text")


class ERPOrderPayload(BaseModel):
    """Structured payload ready for ERP API submission."""

    customer_identifier: str = Field(description="Customer name or organization for lookup")
    order_lines: list[dict] = Field(description="List of order lines for ERP")
    requested_delivery_date: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    source_channel: str = Field(default="whatsapp")
    confidence_score: float = Field(ge=0.0, le=1.0)
    requires_review: bool = Field(default=False)


class OdooSubmissionResult(BaseModel):
    """Result of submitting an order to Odoo."""

    success: bool
    order_id: Optional[int] = None
    order_name: Optional[str] = None
    error: Optional[str] = None
    unmatched_products: list[str] = Field(default_factory=list)


class ProcessingResult(BaseModel):
    """Complete result of processing a WhatsApp order message."""

    success: bool
    extracted_order: Optional[ExtractedOrder] = None
    erp_payload: Optional[ERPOrderPayload] = None
    confirmation_message: Optional[str] = None
    odoo_result: Optional[OdooSubmissionResult] = None
    error: Optional[str] = None
