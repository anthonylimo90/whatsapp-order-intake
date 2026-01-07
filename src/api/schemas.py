"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# Request schemas
class MessageCreate(BaseModel):
    """Request to create a new message."""
    content: str = Field(..., min_length=1)
    customer_name: Optional[str] = None
    message_type: str = Field(default="text")  # text, voice_transcription


class ClarificationResponse(BaseModel):
    """Customer's response to a clarification request."""
    content: str = Field(..., min_length=1)


# Response schemas
class MessageResponse(BaseModel):
    """A message in a conversation."""
    id: int
    role: str
    content: str
    message_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class ExtractedItemResponse(BaseModel):
    """An extracted item from an order."""
    product_name: str
    quantity: float
    unit: str
    confidence: str
    original_text: str
    notes: Optional[str] = None


class ExtractionResultResponse(BaseModel):
    """Result of order extraction."""
    customer_name: str
    customer_organization: Optional[str] = None
    items: list[ExtractedItemResponse]
    requested_delivery_date: Optional[str] = None
    delivery_urgency: Optional[str] = None
    overall_confidence: str
    requires_clarification: bool
    clarification_needed: list[str]
    detected_language: str = "english"


class OrderResponse(BaseModel):
    """A processed order."""
    id: int
    customer_name: Optional[str]
    organization: Optional[str]
    items_json: Optional[dict]
    delivery_date: Optional[str]
    confidence_score: float
    overall_confidence: Optional[str]
    requires_review: bool
    requires_clarification: bool
    status: str
    routing_decision: Optional[str]
    erp_order_id: Optional[str]
    processing_time_ms: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """A conversation with messages."""
    id: int
    customer_name: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = []
    latest_order: Optional[OrderResponse] = None

    class Config:
        from_attributes = True


class ConversationListItem(BaseModel):
    """Summary of a conversation for listing."""
    id: int
    customer_name: Optional[str]
    status: str
    message_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProcessMessageResponse(BaseModel):
    """Response after processing a message."""
    conversation_id: int
    message_id: int
    extraction: Optional[ExtractionResultResponse] = None
    confirmation_message: Optional[str] = None
    order: Optional[OrderResponse] = None
    routing_decision: Optional[str] = None
    error: Optional[str] = None


class MetricsSummary(BaseModel):
    """Dashboard metrics summary."""
    total_orders: int
    orders_today: int
    orders_this_week: int
    auto_processed_count: int
    review_queue_count: int
    manual_count: int
    auto_process_rate: float
    average_confidence: float
    average_processing_time_ms: float
    total_time_saved_minutes: float


class ConfidenceDistribution(BaseModel):
    """Distribution of confidence levels."""
    high: int
    medium: int
    low: int


class CustomerResponse(BaseModel):
    """Customer data."""
    id: int
    name: str
    organization: Optional[str]
    phone: Optional[str]
    tier: str
    region: Optional[str]

    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    """Product data."""
    id: int
    name: str
    category: Optional[str]
    unit: str
    price: float
    in_stock: bool

    class Config:
        from_attributes = True


class SampleMessage(BaseModel):
    """A sample message for the gallery."""
    id: str
    name: str
    description: str
    message: str
    expected_confidence: str
    language: str = "english"


# Excel order schemas
class ExcelOrderItemResponse(BaseModel):
    """An item from an Excel order."""
    category: str
    subcategory: Optional[str] = None
    product_name: str
    unit: str
    price: Optional[float] = None
    quantity: float
    row_number: int


class ExcelOrderSheetResponse(BaseModel):
    """A category/worksheet from an Excel order."""
    category: str
    items: list[ExcelOrderItemResponse]
    total_items: int
    total_value: Optional[float] = None


class ExcelOrderResponse(BaseModel):
    """Response after processing an Excel order file."""
    success: bool
    filename: Optional[str] = None
    customer_name: Optional[str] = None
    sheets: list[ExcelOrderSheetResponse] = []
    total_items: int = 0
    total_categories: int = 0
    total_value: Optional[float] = None
    warnings: list[str] = []
    error: Optional[str] = None
    # Integration with existing order flow
    conversation_id: Optional[int] = None
    order_id: Optional[int] = None
    confirmation_message: Optional[str] = None
    routing_decision: Optional[str] = None
