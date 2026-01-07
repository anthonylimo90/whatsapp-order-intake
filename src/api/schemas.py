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
    # Cumulative state fields
    cumulative_state: Optional["CumulativeStateResponse"] = None
    changes: Optional["ChangesResponse"] = None


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
    # Confidence scoring
    confidence_score: Optional[float] = None
    overall_confidence: Optional[str] = None
    # Cumulative state for ExtractionPanel display and follow-up modifications
    cumulative_state: Optional["CumulativeStateResponse"] = None


# Cumulative order state schemas
class CumulativeItemResponse(BaseModel):
    """An item in the cumulative order state."""
    product_name: str
    normalized_name: Optional[str] = None
    quantity: float
    unit: str
    confidence: str
    original_text: Optional[str] = None
    notes: Optional[str] = None
    modification_count: int = 0
    is_active: bool = True
    first_mentioned_message_id: Optional[int] = None
    last_modified_message_id: Optional[int] = None


class ItemChangeResponse(BaseModel):
    """A change to an item (for modified items)."""
    product_name: str
    old_quantity: Optional[float] = None
    new_quantity: float
    old_unit: Optional[str] = None
    unit: str


class ChangesResponse(BaseModel):
    """Changes made in an extraction."""
    added: list[CumulativeItemResponse] = []
    modified: list[ItemChangeResponse] = []
    unchanged: list[dict] = []


class SnapshotResponse(BaseModel):
    """A snapshot of order state at a point in time."""
    id: int
    version: int
    items: list[CumulativeItemResponse]
    changes: Optional[ChangesResponse] = None
    message_id: int
    extraction_confidence: Optional[str] = None
    requires_clarification: bool = False
    created_at: datetime


class CumulativeStateResponse(BaseModel):
    """Current cumulative order state."""
    id: int
    conversation_id: int
    items: list[CumulativeItemResponse]
    customer_name: Optional[str] = None
    customer_organization: Optional[str] = None
    delivery_date: Optional[str] = None
    urgency: Optional[str] = None
    overall_confidence: str
    requires_clarification: bool
    pending_clarifications: list[str] = []
    version: int
    last_updated_at: Optional[datetime] = None


class ConversationStateResponse(BaseModel):
    """Full conversation state for frontend hydration."""
    conversation_id: int
    customer_name: Optional[str] = None
    status: str
    messages: list[MessageResponse]
    cumulative_state: Optional[CumulativeStateResponse] = None
    snapshots: list[SnapshotResponse] = []
    created_at: datetime
    updated_at: datetime


# Rebuild models to resolve forward references
ProcessMessageResponse.model_rebuild()
