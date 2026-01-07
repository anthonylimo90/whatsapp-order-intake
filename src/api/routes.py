"""FastAPI route definitions."""

import time
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_db, Conversation, Message, Order, OrderItem, Customer, Product
from ..processor import OrderProcessor
from ..models import ConfidenceLevel
from ..services.history import (
    get_customer_order_history,
    get_customer_frequent_items,
    format_order_history_context,
)
from .schemas import (
    MessageCreate,
    ClarificationResponse,
    MessageResponse,
    ConversationResponse,
    ConversationListItem,
    OrderResponse,
    ProcessMessageResponse,
    ExtractionResultResponse,
    ExtractedItemResponse,
    MetricsSummary,
    ConfidenceDistribution,
    CustomerResponse,
    ProductResponse,
    SampleMessage,
)

router = APIRouter()

# Sample messages for the gallery
SAMPLE_MESSAGES = [
    SampleMessage(
        id="clear_order",
        name="Clear Order",
        description="Well-structured order with specific quantities",
        message="Hi, this is Sarah from Saruni Mara. We need to restock for the weekend:\n- 50kg Basmati rice\n- 20kg sugar\n- 10L cooking oil\n- 5 trays of eggs\n\nPlease deliver by Friday morning. Thanks!",
        expected_confidence="high",
        language="english",
    ),
    SampleMessage(
        id="ambiguous_items",
        name="Ambiguous Items",
        description="Vague references like 'the usual' requiring clarification",
        message="Hey it's Peter from Governors Camp. We're running low on a few things - can you send the usual soap and some flour? Also need more of that cleaning stuff we got last time. Thanks",
        expected_confidence="low",
        language="english",
    ),
    SampleMessage(
        id="multiple_items",
        name="Multiple Items Mixed",
        description="Mix of clear and slightly ambiguous items",
        message="Good morning! Angama Mara here. Please send:\n1. Rice 25kg (the good one)\n2. 15kg sugar\n3. Fresh milk 20L\n4. Bread - 30 loaves\n5. Some vegetables for salads\n\nNeed it by Thursday.",
        expected_confidence="medium",
        language="english",
    ),
    SampleMessage(
        id="voice_transcription",
        name="Voice Transcription",
        description="Messy voice note with filler words",
        message="hey um its peter from governors camp we need uh some rice like maybe 30 kilos and um also cooking oil about 10 liters and uh what else oh yeah eggs we need eggs maybe like 5 trays and um can you deliver tomorrow morning thanks",
        expected_confidence="medium",
        language="english",
    ),
    SampleMessage(
        id="swahili_order",
        name="Swahili Order",
        description="Order in Swahili language",
        message="Habari, tunahitaji mchele kilo 50 na sukari kilo 20. Pia tunahitaji mafuta ya kupikia lita 10. Delivery kesho asubuhi tafadhali. Asante - Saruni Lodge",
        expected_confidence="medium",
        language="swahili",
    ),
    SampleMessage(
        id="urgent_order",
        name="Urgent Order",
        description="High-urgency order needing immediate attention",
        message="URGENT! Diani Reef here - we have a large group arriving tonight and we're completely out of beverages. Need ASAP:\n- 20 crates Tusker beer\n- 10 crates sodas (mixed)\n- 50 bottles mineral water\n\nPlease confirm immediately!",
        expected_confidence="high",
        language="english",
    ),
]


def get_routing_decision(confidence_score: float, requires_clarification: bool) -> str:
    """Determine routing based on confidence score."""
    if requires_clarification:
        return "manual"
    if confidence_score >= 0.95:
        return "auto_process"
    elif confidence_score >= 0.80:
        return "review"
    else:
        return "manual"


@router.post("/messages", response_model=ProcessMessageResponse)
async def process_message(
    request: MessageCreate,
    db: AsyncSession = Depends(get_db),
):
    """Process a new WhatsApp message and extract order."""
    start_time = time.time()

    # Create conversation
    conversation = Conversation(
        customer_name=request.customer_name,
        status="active",
    )
    db.add(conversation)
    await db.flush()

    # Add customer message
    customer_message = Message(
        conversation_id=conversation.id,
        role="customer",
        content=request.content,
        message_type=request.message_type,
    )
    db.add(customer_message)
    await db.flush()

    # Try to extract customer/organization for history lookup
    # Simple pattern matching for common formats
    order_history_context = ""
    message_lower = request.content.lower()

    # Try to identify organization from message
    organization_hints = None
    for keyword in ["from ", "- ", "here at ", "at "]:
        if keyword in message_lower:
            # Extract potential organization name
            parts = message_lower.split(keyword)
            if len(parts) > 1:
                # Take the part after the keyword, clean it up
                potential_org = parts[-1].split(".")[0].split(",")[0].split("\n")[0].strip()
                if len(potential_org) > 3 and len(potential_org) < 50:
                    organization_hints = potential_org
                    break

    # Fetch order history if we identified a potential customer
    if organization_hints or request.customer_name:
        try:
            history = await get_customer_order_history(
                db,
                customer_name=request.customer_name,
                organization=organization_hints,
                limit=5,
            )
            frequent_items = await get_customer_frequent_items(
                db,
                customer_name=request.customer_name,
                organization=organization_hints,
                limit=10,
            )
            order_history_context = format_order_history_context(history, frequent_items)
        except Exception:
            # Don't fail if history lookup fails
            pass

    # Process the message
    processor = OrderProcessor()
    try:
        result = processor.process(request.content, order_history_context=order_history_context)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

    processing_time_ms = int((time.time() - start_time) * 1000)

    if not result.success or not result.extracted_order:
        # Add error message
        error_message = Message(
            conversation_id=conversation.id,
            role="system",
            content=f"Failed to process order: {result.error}",
            message_type="text",
        )
        db.add(error_message)
        conversation.status = "error"
        await db.commit()

        return ProcessMessageResponse(
            conversation_id=conversation.id,
            message_id=customer_message.id,
            error=result.error,
        )

    extracted = result.extracted_order
    erp_payload = result.erp_payload

    # Calculate confidence score
    confidence_map = {"high": 0.95, "medium": 0.75, "low": 0.50}
    confidence_score = confidence_map.get(extracted.overall_confidence.value, 0.50)

    # Determine routing
    routing_decision = get_routing_decision(confidence_score, extracted.requires_clarification)

    # Create order record
    order = Order(
        conversation_id=conversation.id,
        customer_name=extracted.customer_name,
        organization=extracted.customer_organization,
        items_json={
            "items": [item.model_dump() for item in extracted.items],
        },
        delivery_date=extracted.requested_delivery_date,
        urgency=extracted.delivery_urgency,
        confidence_score=confidence_score,
        overall_confidence=extracted.overall_confidence.value,
        requires_review=erp_payload.requires_review if erp_payload else True,
        requires_clarification=extracted.requires_clarification,
        clarification_items=extracted.clarification_needed,
        status="pending" if routing_decision == "manual" else routing_decision,
        routing_decision=routing_decision,
        erp_payload=erp_payload.model_dump() if erp_payload else None,
        processing_time_ms=processing_time_ms,
    )
    db.add(order)
    await db.flush()

    # Create order items for history
    for item in extracted.items:
        order_item = OrderItem(
            order_id=order.id,
            product_name=item.product_name,
            quantity=item.quantity,
            unit=item.unit,
            confidence=item.confidence.value,
        )
        db.add(order_item)

    # Add confirmation message
    if result.confirmation_message:
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=result.confirmation_message,
            message_type="text",
        )
        db.add(assistant_message)

    # Update conversation status
    if extracted.requires_clarification:
        conversation.status = "needs_clarification"
    else:
        conversation.status = "completed"
    conversation.customer_name = extracted.customer_name

    await db.commit()

    # Build response
    extraction_response = ExtractionResultResponse(
        customer_name=extracted.customer_name,
        customer_organization=extracted.customer_organization,
        items=[
            ExtractedItemResponse(
                product_name=item.product_name,
                quantity=item.quantity,
                unit=item.unit,
                confidence=item.confidence.value,
                original_text=item.original_text,
                notes=item.notes,
            )
            for item in extracted.items
        ],
        requested_delivery_date=extracted.requested_delivery_date,
        delivery_urgency=extracted.delivery_urgency,
        overall_confidence=extracted.overall_confidence.value,
        requires_clarification=extracted.requires_clarification,
        clarification_needed=extracted.clarification_needed,
        detected_language=extracted.detected_language.value if hasattr(extracted, 'detected_language') else "english",
    )

    return ProcessMessageResponse(
        conversation_id=conversation.id,
        message_id=customer_message.id,
        extraction=extraction_response,
        confirmation_message=result.confirmation_message,
        order=OrderResponse(
            id=order.id,
            customer_name=order.customer_name,
            organization=order.organization,
            items_json=order.items_json,
            delivery_date=order.delivery_date,
            confidence_score=order.confidence_score,
            overall_confidence=order.overall_confidence,
            requires_review=order.requires_review,
            requires_clarification=order.requires_clarification,
            status=order.status,
            routing_decision=order.routing_decision,
            erp_order_id=order.erp_order_id,
            processing_time_ms=order.processing_time_ms,
            created_at=order.created_at,
        ),
        routing_decision=routing_decision,
    )


@router.get("/conversations", response_model=list[ConversationListItem])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    """List all conversations."""
    query = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    conversations = result.scalars().all()

    return [
        ConversationListItem(
            id=conv.id,
            customer_name=conv.customer_name,
            status=conv.status,
            message_count=len(conv.messages),
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )
        for conv in conversations
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a conversation with all messages."""
    query = (
        select(Conversation)
        .options(selectinload(Conversation.messages), selectinload(Conversation.orders))
        .where(Conversation.id == conversation_id)
    )
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    latest_order = conversation.orders[-1] if conversation.orders else None

    return ConversationResponse(
        id=conversation.id,
        customer_name=conversation.customer_name,
        status=conversation.status,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                message_type=msg.message_type,
                created_at=msg.created_at,
            )
            for msg in conversation.messages
        ],
        latest_order=OrderResponse(
            id=latest_order.id,
            customer_name=latest_order.customer_name,
            organization=latest_order.organization,
            items_json=latest_order.items_json,
            delivery_date=latest_order.delivery_date,
            confidence_score=latest_order.confidence_score,
            overall_confidence=latest_order.overall_confidence,
            requires_review=latest_order.requires_review,
            requires_clarification=latest_order.requires_clarification,
            status=latest_order.status,
            routing_decision=latest_order.routing_decision,
            erp_order_id=latest_order.erp_order_id,
            processing_time_ms=latest_order.processing_time_ms,
            created_at=latest_order.created_at,
        )
        if latest_order
        else None,
    )


@router.post("/conversations/{conversation_id}/clarify", response_model=ProcessMessageResponse)
async def submit_clarification(
    conversation_id: int,
    request: ClarificationResponse,
    db: AsyncSession = Depends(get_db),
):
    """Submit a clarification response and reprocess."""
    start_time = time.time()

    # Get conversation with messages
    query = (
        select(Conversation)
        .options(selectinload(Conversation.messages), selectinload(Conversation.orders))
        .where(Conversation.id == conversation_id)
    )
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get original message
    original_message = next(
        (m for m in conversation.messages if m.role == "customer"),
        None,
    )
    if not original_message:
        raise HTTPException(status_code=400, detail="No original message found")

    # Add clarification message
    clarification_message = Message(
        conversation_id=conversation.id,
        role="customer",
        content=request.content,
        message_type="clarification",
    )
    db.add(clarification_message)
    await db.flush()

    # Build context with original message + clarification
    combined_message = f"""Original order message:
{original_message.content}

Customer clarification:
{request.content}"""

    # Reprocess with clarification context
    processor = OrderProcessor()
    try:
        result = await processor.process(combined_message)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

    processing_time_ms = int((time.time() - start_time) * 1000)

    if not result.success or not result.extracted_order:
        return ProcessMessageResponse(
            conversation_id=conversation.id,
            message_id=clarification_message.id,
            error=result.error,
        )

    extracted = result.extracted_order
    erp_payload = result.erp_payload

    confidence_map = {"high": 0.95, "medium": 0.75, "low": 0.50}
    confidence_score = confidence_map.get(extracted.overall_confidence.value, 0.50)
    routing_decision = get_routing_decision(confidence_score, extracted.requires_clarification)

    # Create new order record
    order = Order(
        conversation_id=conversation.id,
        customer_name=extracted.customer_name,
        organization=extracted.customer_organization,
        items_json={"items": [item.model_dump() for item in extracted.items]},
        delivery_date=extracted.requested_delivery_date,
        urgency=extracted.delivery_urgency,
        confidence_score=confidence_score,
        overall_confidence=extracted.overall_confidence.value,
        requires_review=erp_payload.requires_review if erp_payload else True,
        requires_clarification=extracted.requires_clarification,
        clarification_items=extracted.clarification_needed,
        status="pending" if routing_decision == "manual" else routing_decision,
        routing_decision=routing_decision,
        erp_payload=erp_payload.model_dump() if erp_payload else None,
        processing_time_ms=processing_time_ms,
    )
    db.add(order)
    await db.flush()

    # Add confirmation message
    if result.confirmation_message:
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=result.confirmation_message,
            message_type="text",
        )
        db.add(assistant_message)

    # Update conversation status
    conversation.status = "completed" if not extracted.requires_clarification else "needs_clarification"
    await db.commit()

    extraction_response = ExtractionResultResponse(
        customer_name=extracted.customer_name,
        customer_organization=extracted.customer_organization,
        items=[
            ExtractedItemResponse(
                product_name=item.product_name,
                quantity=item.quantity,
                unit=item.unit,
                confidence=item.confidence.value,
                original_text=item.original_text,
                notes=item.notes,
            )
            for item in extracted.items
        ],
        requested_delivery_date=extracted.requested_delivery_date,
        delivery_urgency=extracted.delivery_urgency,
        overall_confidence=extracted.overall_confidence.value,
        requires_clarification=extracted.requires_clarification,
        clarification_needed=extracted.clarification_needed,
        detected_language=extracted.detected_language.value if hasattr(extracted, 'detected_language') else "english",
    )

    return ProcessMessageResponse(
        conversation_id=conversation.id,
        message_id=clarification_message.id,
        extraction=extraction_response,
        confirmation_message=result.confirmation_message,
        order=OrderResponse(
            id=order.id,
            customer_name=order.customer_name,
            organization=order.organization,
            items_json=order.items_json,
            delivery_date=order.delivery_date,
            confidence_score=order.confidence_score,
            overall_confidence=order.overall_confidence,
            requires_review=order.requires_review,
            requires_clarification=order.requires_clarification,
            status=order.status,
            routing_decision=order.routing_decision,
            erp_order_id=order.erp_order_id,
            processing_time_ms=order.processing_time_ms,
            created_at=order.created_at,
        ),
        routing_decision=routing_decision,
    )


@router.get("/orders", response_model=list[OrderResponse])
async def list_orders(
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List orders with optional status filter."""
    query = select(Order).order_by(Order.created_at.desc())

    if status:
        query = query.where(Order.status == status)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    orders = result.scalars().all()

    return [
        OrderResponse(
            id=order.id,
            customer_name=order.customer_name,
            organization=order.organization,
            items_json=order.items_json,
            delivery_date=order.delivery_date,
            confidence_score=order.confidence_score,
            overall_confidence=order.overall_confidence,
            requires_review=order.requires_review,
            requires_clarification=order.requires_clarification,
            status=order.status,
            routing_decision=order.routing_decision,
            erp_order_id=order.erp_order_id,
            processing_time_ms=order.processing_time_ms,
            created_at=order.created_at,
        )
        for order in orders
    ]


@router.get("/metrics/summary", response_model=MetricsSummary)
async def get_metrics_summary(db: AsyncSession = Depends(get_db)):
    """Get dashboard metrics summary."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())

    # Total orders
    total_result = await db.execute(select(func.count(Order.id)))
    total_orders = total_result.scalar() or 0

    # Orders today
    today_result = await db.execute(
        select(func.count(Order.id)).where(Order.created_at >= today_start)
    )
    orders_today = today_result.scalar() or 0

    # Orders this week
    week_result = await db.execute(
        select(func.count(Order.id)).where(Order.created_at >= week_start)
    )
    orders_this_week = week_result.scalar() or 0

    # Routing counts
    auto_result = await db.execute(
        select(func.count(Order.id)).where(Order.routing_decision == "auto_process")
    )
    auto_processed_count = auto_result.scalar() or 0

    review_result = await db.execute(
        select(func.count(Order.id)).where(Order.routing_decision == "review")
    )
    review_queue_count = review_result.scalar() or 0

    manual_result = await db.execute(
        select(func.count(Order.id)).where(Order.routing_decision == "manual")
    )
    manual_count = manual_result.scalar() or 0

    # Auto process rate
    auto_process_rate = (auto_processed_count / total_orders * 100) if total_orders > 0 else 0

    # Average confidence
    avg_conf_result = await db.execute(select(func.avg(Order.confidence_score)))
    average_confidence = avg_conf_result.scalar() or 0

    # Average processing time
    avg_time_result = await db.execute(select(func.avg(Order.processing_time_ms)))
    average_processing_time_ms = avg_time_result.scalar() or 0

    # Time saved (assuming 3 minutes manual processing per order)
    manual_time_per_order_minutes = 3
    total_time_saved_minutes = total_orders * manual_time_per_order_minutes - (
        total_orders * (average_processing_time_ms / 60000)
    )

    return MetricsSummary(
        total_orders=total_orders,
        orders_today=orders_today,
        orders_this_week=orders_this_week,
        auto_processed_count=auto_processed_count,
        review_queue_count=review_queue_count,
        manual_count=manual_count,
        auto_process_rate=round(auto_process_rate, 1),
        average_confidence=round(average_confidence, 2),
        average_processing_time_ms=round(average_processing_time_ms, 0),
        total_time_saved_minutes=round(max(0, total_time_saved_minutes), 1),
    )


@router.get("/metrics/confidence", response_model=ConfidenceDistribution)
async def get_confidence_distribution(db: AsyncSession = Depends(get_db)):
    """Get distribution of confidence levels."""
    high_result = await db.execute(
        select(func.count(Order.id)).where(Order.overall_confidence == "high")
    )
    high = high_result.scalar() or 0

    medium_result = await db.execute(
        select(func.count(Order.id)).where(Order.overall_confidence == "medium")
    )
    medium = medium_result.scalar() or 0

    low_result = await db.execute(
        select(func.count(Order.id)).where(Order.overall_confidence == "low")
    )
    low = low_result.scalar() or 0

    return ConfidenceDistribution(high=high, medium=medium, low=low)


@router.get("/customers", response_model=list[CustomerResponse])
async def list_customers(db: AsyncSession = Depends(get_db)):
    """List all customers."""
    result = await db.execute(select(Customer).order_by(Customer.name))
    customers = result.scalars().all()
    return [
        CustomerResponse(
            id=c.id,
            name=c.name,
            organization=c.organization,
            phone=c.phone,
            tier=c.tier,
            region=c.region,
        )
        for c in customers
    ]


@router.get("/products", response_model=list[ProductResponse])
async def list_products(db: AsyncSession = Depends(get_db)):
    """List all products."""
    result = await db.execute(select(Product).order_by(Product.category, Product.name))
    products = result.scalars().all()
    return [
        ProductResponse(
            id=p.id,
            name=p.name,
            category=p.category,
            unit=p.unit,
            price=p.price,
            in_stock=p.in_stock,
        )
        for p in products
    ]


@router.get("/samples", response_model=list[SampleMessage])
async def get_sample_messages():
    """Get sample messages for the gallery."""
    return SAMPLE_MESSAGES
