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
