"""FastAPI route definitions."""

import time
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import (
    get_db,
    Conversation,
    Message,
    Order,
    OrderItem,
    Customer,
    Product,
    CumulativeOrderState,
    OrderSnapshot,
    CumulativeOrderItem,
)
from ..processor import OrderProcessor
from ..models import ConfidenceLevel
from ..services.history import (
    get_customer_order_history,
    get_customer_frequent_items,
    format_order_history_context,
)
from ..services.excel_parser import parse_excel_order, excel_order_to_text
from ..services.order_state import OrderStateManager
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
    ExcelOrderResponse,
    ExcelOrderSheetResponse,
    ExcelOrderItemResponse,
    CumulativeItemResponse,
    CumulativeStateResponse,
    ChangesResponse,
    ItemChangeResponse,
    SnapshotResponse,
    ConversationStateResponse,
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


def build_cumulative_state_response(state: CumulativeOrderState) -> CumulativeStateResponse:
    """Build CumulativeStateResponse from database model."""
    items = state.items_json.get("items", [])
    return CumulativeStateResponse(
        id=state.id,
        conversation_id=state.conversation_id,
        items=[
            CumulativeItemResponse(
                product_name=item.get("product_name", ""),
                normalized_name=item.get("normalized_name"),
                quantity=item.get("quantity", 0),
                unit=item.get("unit", ""),
                confidence=item.get("confidence", "medium"),
                original_text=item.get("original_text"),
                notes=item.get("notes"),
                modification_count=item.get("modification_count", 0),
                is_active=item.get("is_active", True),
                first_mentioned_message_id=item.get("first_mentioned_message_id"),
                last_modified_message_id=item.get("last_modified_message_id"),
            )
            for item in items
            if item.get("is_active", True)
        ],
        customer_name=state.customer_name,
        customer_organization=state.customer_organization,
        delivery_date=state.delivery_date,
        urgency=state.urgency,
        overall_confidence=state.overall_confidence or "medium",
        requires_clarification=state.requires_clarification,
        pending_clarifications=state.pending_clarifications or [],
        version=state.version,
        last_updated_at=state.last_updated_at,
    )


def build_changes_response(changes: dict) -> ChangesResponse:
    """Build ChangesResponse from changes dict."""
    return ChangesResponse(
        added=[
            CumulativeItemResponse(
                product_name=item.get("product_name", ""),
                normalized_name=item.get("normalized_name"),
                quantity=item.get("quantity", 0),
                unit=item.get("unit", ""),
                confidence=item.get("confidence", "medium"),
                original_text=item.get("original_text"),
                notes=item.get("notes"),
                modification_count=item.get("modification_count", 0),
                is_active=item.get("is_active", True),
            )
            for item in changes.get("added", [])
        ],
        modified=[
            ItemChangeResponse(
                product_name=item.get("product_name", ""),
                old_quantity=item.get("old_quantity"),
                new_quantity=item.get("new_quantity", 0),
                old_unit=item.get("old_unit"),
                unit=item.get("unit", ""),
            )
            for item in changes.get("modified", [])
        ],
        unchanged=changes.get("unchanged", []),
    )


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

    # Initialize cumulative order state
    state_manager = OrderStateManager(db)
    cumulative_state = await state_manager.get_or_create_state(conversation.id)

    # Merge extraction into cumulative state
    changes = await state_manager.merge_extraction(
        cumulative_state,
        extracted,
        customer_message.id,
    )

    # Create snapshot of current state
    await state_manager.create_snapshot(
        cumulative_state,
        customer_message.id,
        changes,
        extracted,
    )

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

    # Build cumulative state response
    cumulative_state_response = build_cumulative_state_response(cumulative_state)
    changes_response = build_changes_response(changes)

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
        cumulative_state=cumulative_state_response,
        changes=changes_response,
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


@router.get("/conversations/{conversation_id}/state", response_model=ConversationStateResponse)
async def get_conversation_state(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get full conversation state including cumulative order and snapshots for frontend hydration."""
    # Get conversation with messages and cumulative state
    query = (
        select(Conversation)
        .options(
            selectinload(Conversation.messages),
            selectinload(Conversation.cumulative_state).selectinload(
                CumulativeOrderState.snapshots
            ),
        )
        .where(Conversation.id == conversation_id)
    )
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Build cumulative state response if exists
    cumulative_state_response = None
    snapshots_response = []

    if conversation.cumulative_state:
        cumulative_state_response = build_cumulative_state_response(conversation.cumulative_state)

        # Build snapshots response
        for snapshot in conversation.cumulative_state.snapshots:
            items = snapshot.items_json.get("items", [])
            changes = snapshot.changes_json or {}

            snapshots_response.append(
                SnapshotResponse(
                    id=snapshot.id,
                    version=snapshot.version,
                    items=[
                        CumulativeItemResponse(
                            product_name=item.get("product_name", ""),
                            normalized_name=item.get("normalized_name"),
                            quantity=item.get("quantity", 0),
                            unit=item.get("unit", ""),
                            confidence=item.get("confidence", "medium"),
                            original_text=item.get("original_text"),
                            notes=item.get("notes"),
                            modification_count=item.get("modification_count", 0),
                            is_active=item.get("is_active", True),
                        )
                        for item in items
                    ],
                    changes=ChangesResponse(
                        added=[
                            CumulativeItemResponse(
                                product_name=item.get("product_name", ""),
                                quantity=item.get("quantity", 0),
                                unit=item.get("unit", ""),
                                confidence=item.get("confidence", "medium"),
                            )
                            for item in changes.get("added", [])
                        ],
                        modified=[
                            ItemChangeResponse(
                                product_name=item.get("product_name", ""),
                                old_quantity=item.get("old_quantity"),
                                new_quantity=item.get("new_quantity", 0),
                                unit=item.get("unit", ""),
                            )
                            for item in changes.get("modified", [])
                        ],
                        unchanged=changes.get("unchanged", []),
                    ) if changes else None,
                    message_id=snapshot.message_id,
                    extraction_confidence=snapshot.extraction_confidence,
                    requires_clarification=snapshot.requires_clarification,
                    created_at=snapshot.created_at,
                )
            )

    return ConversationStateResponse(
        conversation_id=conversation.id,
        customer_name=conversation.customer_name,
        status=conversation.status,
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
        cumulative_state=cumulative_state_response,
        snapshots=snapshots_response,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
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

    # Get or create cumulative state
    state_manager = OrderStateManager(db)
    cumulative_state = await state_manager.get_or_create_state(conversation_id)

    # Add clarification message
    clarification_message = Message(
        conversation_id=conversation.id,
        role="customer",
        content=request.content,
        message_type="clarification",
    )
    db.add(clarification_message)
    await db.flush()

    # Build FULL context with current state and all messages
    full_context = state_manager.build_full_context(conversation.messages, cumulative_state)

    # Enhanced message with full context
    enhanced_message = f"""{full_context}

NEW CLARIFICATION FROM CUSTOMER:
{request.content}

Based on the current order state and this clarification, extract any updates.
If the customer is modifying an existing item (e.g., "change rice to 60kg"),
return that item with the updated quantity.
If adding new items, include them.
Preserve items from current state that aren't being modified."""

    # Reprocess with full context
    processor = OrderProcessor()
    try:
        result = processor.process(enhanced_message)
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

    # Merge extraction into cumulative state
    changes = await state_manager.merge_extraction(
        cumulative_state,
        extracted,
        clarification_message.id,
    )

    # Create snapshot of current state
    await state_manager.create_snapshot(
        cumulative_state,
        clarification_message.id,
        changes,
        extracted,
    )

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

    # Build cumulative state response
    cumulative_state_response = build_cumulative_state_response(cumulative_state)
    changes_response = build_changes_response(changes)

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
        cumulative_state=cumulative_state_response,
        changes=changes_response,
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


@router.post("/excel-order", response_model=ExcelOrderResponse)
async def process_excel_order(
    file: UploadFile = File(...),
    customer_name: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Process an Excel order file with multiple worksheets.

    Each worksheet is treated as a category (e.g., Dairy, Produce, Beverages).
    Expected columns: Subcategory, Product Name, Unit, Price, Opening Order (quantity).
    """
    start_time = time.time()

    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an Excel file (.xlsx or .xls)"
        )

    # Read file content
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    # Parse Excel file
    result = parse_excel_order(content, filename=file.filename, customer_name=customer_name)

    if not result.success:
        return ExcelOrderResponse(
            success=False,
            filename=file.filename,
            error=result.error,
        )

    # Convert to text for LLM processing
    order_text = excel_order_to_text(result)

    # Create conversation for this Excel order
    conversation = Conversation(
        customer_name=customer_name or result.customer_name or "Excel Order",
        status="active",
    )
    db.add(conversation)
    await db.flush()

    # Add the Excel order as a message
    excel_message = Message(
        conversation_id=conversation.id,
        role="customer",
        content=f"[Excel Order: {file.filename}]\n\n{order_text}",
        message_type="excel_order",
    )
    db.add(excel_message)
    await db.flush()

    # Process through the standard order processor for confirmation
    processor = OrderProcessor()
    try:
        process_result = processor.process(order_text)
    except Exception as e:
        await db.rollback()
        return ExcelOrderResponse(
            success=True,
            filename=file.filename,
            customer_name=customer_name,
            sheets=[
                ExcelOrderSheetResponse(
                    category=s.category,
                    items=[
                        ExcelOrderItemResponse(
                            category=i.category,
                            subcategory=i.subcategory,
                            product_name=i.product_name,
                            unit=i.unit,
                            price=i.price,
                            quantity=i.quantity,
                            row_number=i.row_number,
                        )
                        for i in s.items
                    ],
                    total_items=s.total_items,
                    total_value=s.total_value,
                )
                for s in result.sheets
            ],
            total_items=result.total_items,
            total_categories=result.total_categories,
            total_value=result.total_value,
            warnings=result.warnings + [f"LLM processing failed: {str(e)}"],
            error=None,
        )

    processing_time_ms = int((time.time() - start_time) * 1000)

    # Calculate confidence based on data quality
    # Check for missing prices, unclear units, etc.
    items_with_price = sum(1 for s in result.sheets for i in s.items if i.price is not None)
    total_items = result.total_items
    price_coverage = items_with_price / total_items if total_items > 0 else 0

    # Use LLM extraction result for confidence if available
    if process_result.success and process_result.extracted_order:
        extracted = process_result.extracted_order
        confidence_map = {"high": 0.95, "medium": 0.75, "low": 0.50}
        confidence_score = confidence_map.get(extracted.overall_confidence.value, 0.75)
        overall_confidence = extracted.overall_confidence.value
        requires_clarification = extracted.requires_clarification
    else:
        # Fallback: base confidence on data completeness
        if price_coverage >= 0.9 and total_items > 0:
            confidence_score = 0.95
            overall_confidence = "high"
        elif price_coverage >= 0.5:
            confidence_score = 0.80
            overall_confidence = "medium"
        else:
            confidence_score = 0.65
            overall_confidence = "medium"
        requires_clarification = False

    routing_decision = get_routing_decision(confidence_score, requires_clarification)

    order = Order(
        conversation_id=conversation.id,
        customer_name=customer_name or result.customer_name or "Excel Order",
        organization=customer_name,
        items_json={
            "source": "excel",
            "filename": file.filename,
            "categories": [s.category for s in result.sheets],
            "items": [
                {
                    "category": item.category,
                    "subcategory": item.subcategory,
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "price": item.price,
                }
                for sheet in result.sheets
                for item in sheet.items
            ],
        },
        confidence_score=confidence_score,
        overall_confidence=overall_confidence,
        requires_review=routing_decision == "review",
        requires_clarification=requires_clarification,
        status=routing_decision if routing_decision != "manual" else "pending",
        routing_decision=routing_decision,
        processing_time_ms=processing_time_ms,
    )
    db.add(order)
    await db.flush()

    # Create order items for history tracking
    for sheet in result.sheets:
        for item in sheet.items:
            order_item = OrderItem(
                order_id=order.id,
                product_name=item.product_name,
                quantity=item.quantity,
                unit=item.unit,
                confidence=overall_confidence,
            )
            db.add(order_item)

    # Initialize cumulative state from Excel items
    state_manager = OrderStateManager(db)
    cumulative_state = await state_manager.get_or_create_state(conversation.id)

    # Populate cumulative items from Excel
    added_items = []
    for sheet in result.sheets:
        for item in sheet.items:
            notes = f"Category: {item.category}"
            if item.subcategory:
                notes += f", Subcategory: {item.subcategory}"
            if item.price:
                notes += f", Price: KES {item.price:,.0f}"

            cum_item = CumulativeOrderItem(
                cumulative_state_id=cumulative_state.id,
                product_name=item.product_name,
                normalized_name=state_manager.normalize_product_name(item.product_name),
                quantity=item.quantity,
                unit=item.unit,
                confidence="high",  # Excel data is structured
                notes=notes,
                first_mentioned_message_id=excel_message.id,
                last_modified_message_id=excel_message.id,
                modification_count=0,
                is_active=True,
            )
            db.add(cum_item)
            added_items.append(cum_item)

    # Update cumulative state metadata and items_json
    cumulative_state.customer_name = customer_name or result.customer_name
    cumulative_state.overall_confidence = overall_confidence
    cumulative_state.version = 1
    cumulative_state.items_json = {
        "items": [
            {
                "product_name": item.product_name,
                "normalized_name": item.normalized_name,
                "quantity": item.quantity,
                "unit": item.unit,
                "confidence": "high",
                "notes": item.notes,
                "modification_count": 0,
                "is_active": True,
                "first_mentioned_message_id": excel_message.id,
                "last_modified_message_id": excel_message.id,
            }
            for item in added_items
        ]
    }
    await db.flush()

    # Create initial snapshot
    changes = {
        "added": [
            {
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit": item.unit,
                "confidence": "high",
            }
            for item in added_items
        ],
        "modified": [],
        "unchanged": [],
    }
    snapshot = OrderSnapshot(
        cumulative_state_id=cumulative_state.id,
        message_id=excel_message.id,
        items_json={"items": [
            {
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit": item.unit,
                "confidence": "high",
                "notes": item.notes,
            }
            for item in added_items
        ]},
        changes_json=changes,
        version=1,
        extraction_confidence=overall_confidence,
        requires_clarification=requires_clarification,
    )
    db.add(snapshot)

    # Generate detailed summary message
    summary_lines = [f"*Order Summary - {file.filename}*\n"]
    for sheet in result.sheets:
        summary_lines.append(f"\n*{sheet.category}* ({sheet.total_items} items)")
        for item in sheet.items:
            line = f"  • {item.product_name}: {item.quantity} {item.unit}"
            if item.price:
                line += f" @ KES {item.price:,.0f}"
            summary_lines.append(line)
        if sheet.total_value:
            summary_lines.append(f"  _Subtotal: KES {sheet.total_value:,.0f}_")

    summary_lines.append(f"\n*Total Items:* {result.total_items}")
    if result.total_value:
        summary_lines.append(f"*Total Value:* KES {result.total_value:,.0f}")
    summary_lines.append(f"\n*Confidence:* {overall_confidence.upper()} ({confidence_score*100:.0f}%)")
    summary_lines.append(f"*Routing:* {routing_decision.replace('_', ' ').title()}")

    summary_message = "\n".join(summary_lines)

    # Add summary message
    summary_msg = Message(
        conversation_id=conversation.id,
        role="system",
        content=summary_message,
        message_type="text",
    )
    db.add(summary_msg)

    # Add confirmation message from LLM or use fallback for large orders
    confirmation = process_result.confirmation_message if process_result.success else None
    if not confirmation:
        # Fallback confirmation for large Excel orders or LLM failures
        confirmation = (
            f"I've received your order from {file.filename}. "
            f"It contains {result.total_items} items across {result.total_categories} categories"
            + (f" with a total value of KES {result.total_value:,.0f}" if result.total_value else "")
            + ". You can review the full order details in the Extraction Results panel. "
            "Feel free to send me a message if you'd like to make any changes to the order!"
        )
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=confirmation,
        message_type="text",
    )
    db.add(assistant_message)

    conversation.status = "completed" if not requires_clarification else "needs_clarification"
    await db.commit()

    # Build cumulative state response
    cum_state_response = build_cumulative_state_response(cumulative_state)

    return ExcelOrderResponse(
        success=True,
        filename=file.filename,
        customer_name=customer_name or result.customer_name,
        sheets=[
            ExcelOrderSheetResponse(
                category=s.category,
                items=[
                    ExcelOrderItemResponse(
                        category=i.category,
                        subcategory=i.subcategory,
                        product_name=i.product_name,
                        unit=i.unit,
                        price=i.price,
                        quantity=i.quantity,
                        row_number=i.row_number,
                    )
                    for i in s.items
                ],
                total_items=s.total_items,
                total_value=s.total_value,
            )
            for s in result.sheets
        ],
        total_items=result.total_items,
        total_categories=result.total_categories,
        total_value=result.total_value,
        warnings=result.warnings,
        conversation_id=conversation.id,
        order_id=order.id,
        confirmation_message=confirmation,
        routing_decision=routing_decision,
        confidence_score=confidence_score,
        overall_confidence=overall_confidence,
        cumulative_state=cum_state_response,
    )
