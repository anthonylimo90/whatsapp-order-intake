"""ERP payload generation for Odoo integration."""

from .models import ExtractedOrder, ERPOrderPayload, ConfidenceLevel


def confidence_to_score(level: ConfidenceLevel) -> float:
    """Convert confidence level to numeric score."""
    return {
        ConfidenceLevel.HIGH: 0.95,
        ConfidenceLevel.MEDIUM: 0.75,
        ConfidenceLevel.LOW: 0.50,
    }[level]


def build_erp_payload(order: ExtractedOrder) -> ERPOrderPayload:
    """
    Convert an extracted order to an ERP-ready payload.

    This creates a structure suitable for Odoo's sales order API.
    In production, this would include:
    - Product SKU lookup
    - Price calculation based on customer tier
    - Stock availability check

    Args:
        order: Extracted order data

    Returns:
        ERPOrderPayload ready for API submission
    """
    # Build order lines
    order_lines = []
    for item in order.items:
        line = {
            "product_name": item.product_name,
            "quantity": item.quantity,
            "unit": item.unit,
            "confidence": item.confidence.value,
            # In production, these would be populated from Odoo lookup:
            # "product_id": lookup_product_id(item.product_name),
            # "unit_price": get_customer_price(customer_id, product_id),
        }
        if item.notes:
            line["notes"] = item.notes
        order_lines.append(line)

    # Calculate overall confidence score
    item_scores = [confidence_to_score(item.confidence) for item in order.items]
    avg_confidence = sum(item_scores) / len(item_scores) if item_scores else 0.0

    # Adjust for overall order confidence
    overall_score = min(avg_confidence, confidence_to_score(order.overall_confidence))

    # Build notes for ERP
    notes_parts = []
    if order.delivery_urgency:
        notes_parts.append(f"Urgency: {order.delivery_urgency}")
    if order.clarification_needed:
        notes_parts.append(f"Needs clarification: {', '.join(order.clarification_needed)}")

    return ERPOrderPayload(
        customer_identifier=order.customer_organization or order.customer_name,
        order_lines=order_lines,
        requested_delivery_date=order.requested_delivery_date,
        notes="; ".join(notes_parts) if notes_parts else None,
        source_channel="whatsapp",
        confidence_score=round(overall_score, 2),
        requires_review=order.requires_clarification or overall_score < 0.8,
    )
