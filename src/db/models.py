"""SQLAlchemy ORM models for the demo database."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from .database import Base


class Customer(Base):
    """Customer/business entity."""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    organization = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    tier = Column(String(50), default="standard")  # standard, premium, vip
    region = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversations = relationship("Conversation", back_populates="customer")
    orders = relationship("Order", back_populates="customer")


class Product(Base):
    """Product catalog entry."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=True)
    unit = Column(String(50), default="pieces")
    price = Column(Float, default=0.0)
    in_stock = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Conversation(Base):
    """A conversation thread with a customer."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    customer_name = Column(String(255), nullable=True)
    status = Column(String(50), default="active")  # active, completed, needs_clarification
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")
    orders = relationship("Order", back_populates="conversation")
    cumulative_state = relationship("CumulativeOrderState", back_populates="conversation", uselist=False)


class Message(Base):
    """A single message in a conversation."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(50), nullable=False)  # customer, system, assistant
    content = Column(Text, nullable=False)
    message_type = Column(String(50), default="text")  # text, voice_transcription, clarification
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class Order(Base):
    """A processed order."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    customer_name = Column(String(255), nullable=True)
    organization = Column(String(255), nullable=True)

    items_json = Column(JSON, nullable=True)  # Extracted items as JSON
    delivery_date = Column(String(100), nullable=True)
    urgency = Column(String(100), nullable=True)

    confidence_score = Column(Float, default=0.0)
    overall_confidence = Column(String(50), nullable=True)  # high, medium, low
    requires_review = Column(Boolean, default=False)
    requires_clarification = Column(Boolean, default=False)
    clarification_items = Column(JSON, nullable=True)

    status = Column(String(50), default="pending")  # pending, auto_processed, review_queue, manual, completed
    routing_decision = Column(String(50), nullable=True)  # auto_process, review, manual

    erp_order_id = Column(String(100), nullable=True)  # e.g., SO1001
    erp_payload = Column(JSON, nullable=True)

    processing_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="orders")
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    """Individual item in an order - used for order history lookups."""
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)

    product_name = Column(String(255), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=True)
    confidence = Column(String(50), nullable=True)

    resolved_from = Column(String(255), nullable=True)  # If resolved from "the usual", note what it was
    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="items")


class CumulativeOrderState(Base):
    """Running total of order items for a conversation - the 'current truth'."""
    __tablename__ = "cumulative_order_states"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), unique=True, nullable=False)

    # Current cumulative items (the merged result)
    items_json = Column(JSON, nullable=False, default=lambda: {"items": []})

    # Customer metadata
    customer_name = Column(String(255), nullable=True)
    customer_organization = Column(String(255), nullable=True)
    delivery_date = Column(String(100), nullable=True)
    urgency = Column(String(100), nullable=True)

    # Confidence for the cumulative state
    overall_confidence = Column(String(50), default="medium")
    requires_clarification = Column(Boolean, default=False)
    pending_clarifications = Column(JSON, default=lambda: [])

    # Versioning
    version = Column(Integer, default=1)
    last_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="cumulative_state")
    snapshots = relationship("OrderSnapshot", back_populates="cumulative_state", order_by="OrderSnapshot.version")
    cumulative_items = relationship("CumulativeOrderItem", back_populates="cumulative_state")


class OrderSnapshot(Base):
    """Snapshot of order state at a point in time - preserves extraction history."""
    __tablename__ = "order_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    cumulative_state_id = Column(Integer, ForeignKey("cumulative_order_states.id"), nullable=False)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)

    # Snapshot of items at this point
    items_json = Column(JSON, nullable=False)

    # What changed in this extraction
    changes_json = Column(JSON, nullable=True)  # {"added": [], "modified": [], "unchanged": []}

    # Extraction metadata
    version = Column(Integer, nullable=False)
    extraction_confidence = Column(String(50), nullable=True)
    requires_clarification = Column(Boolean, default=False)
    clarification_items = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    cumulative_state = relationship("CumulativeOrderState", back_populates="snapshots")
    message = relationship("Message")


class ProductAlias(Base):
    """Product name aliases for fuzzy matching."""
    __tablename__ = "product_aliases"

    id = Column(Integer, primary_key=True, index=True)
    alias = Column(String(255), nullable=False, index=True)
    canonical_name = Column(String(255), nullable=False)
    language = Column(String(20), default="en")  # 'en', 'sw' for Swahili
    category = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProductMappingCache(Base):
    """Cache of successful product name mappings."""
    __tablename__ = "product_mapping_cache"

    id = Column(Integer, primary_key=True, index=True)
    input_text = Column(String(255), unique=True, nullable=False, index=True)
    matched_product_name = Column(String(255), nullable=False)
    confidence = Column(Float, default=0.0)
    hit_count = Column(Integer, default=1)
    last_used = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class CumulativeOrderItem(Base):
    """Individual item in cumulative order with modification tracking."""
    __tablename__ = "cumulative_order_items"

    id = Column(Integer, primary_key=True, index=True)
    cumulative_state_id = Column(Integer, ForeignKey("cumulative_order_states.id"), nullable=False)

    # Item details
    product_name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False, index=True)  # For matching
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=True)
    confidence = Column(String(50), default="medium")

    # Tracking
    first_mentioned_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    last_modified_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    modification_count = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)  # False if removed by user
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cumulative_state = relationship("CumulativeOrderState", back_populates="cumulative_items")
