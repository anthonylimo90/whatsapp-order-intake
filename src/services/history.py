"""Order history service for resolving ambiguous references."""

from typing import Optional, List, Dict, Any
from difflib import SequenceMatcher
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Order, OrderItem, Customer


async def get_customer_order_history(
    session: AsyncSession,
    customer_name: Optional[str] = None,
    organization: Optional[str] = None,
    limit: int = 5,
) -> list[dict]:
    """
    Get recent order history for a customer.

    Args:
        session: Database session
        customer_name: Customer contact name
        organization: Organization/lodge name
        limit: Maximum number of orders to return

    Returns:
        List of order summaries with items
    """
    # Build query to find matching orders
    query = select(Order).order_by(Order.created_at.desc())

    if organization:
        query = query.where(
            func.lower(Order.organization).contains(organization.lower())
        )
    elif customer_name:
        query = query.where(
            func.lower(Order.customer_name).contains(customer_name.lower())
        )
    else:
        return []

    query = query.limit(limit)

    result = await session.execute(query)
    orders = result.scalars().all()

    history = []
    for order in orders:
        if order.items_json and "items" in order.items_json:
            items_summary = [
                f"{item['quantity']} {item['unit']} {item['product_name']}"
                for item in order.items_json["items"]
            ]
            history.append({
                "date": order.created_at.strftime("%Y-%m-%d"),
                "items": items_summary,
            })

    return history


async def get_customer_frequent_items(
    session: AsyncSession,
    customer_name: Optional[str] = None,
    organization: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """
    Get frequently ordered items for a customer.

    Args:
        session: Database session
        customer_name: Customer contact name
        organization: Organization/lodge name
        limit: Maximum number of items to return

    Returns:
        List of frequently ordered products with typical quantities
    """
    # Get customer's orders
    query = select(Order)

    if organization:
        query = query.where(
            func.lower(Order.organization).contains(organization.lower())
        )
    elif customer_name:
        query = query.where(
            func.lower(Order.customer_name).contains(customer_name.lower())
        )
    else:
        return []

    result = await session.execute(query)
    orders = result.scalars().all()

    # Aggregate item frequencies and typical quantities
    item_stats: dict[str, dict] = {}

    for order in orders:
        if order.items_json and "items" in order.items_json:
            for item in order.items_json["items"]:
                name = item["product_name"].lower()
                if name not in item_stats:
                    item_stats[name] = {
                        "product_name": item["product_name"],
                        "count": 0,
                        "quantities": [],
                        "unit": item["unit"],
                    }
                item_stats[name]["count"] += 1
                item_stats[name]["quantities"].append(item["quantity"])

    # Calculate typical quantities and sort by frequency
    frequent_items = []
    for stats in sorted(item_stats.values(), key=lambda x: x["count"], reverse=True)[:limit]:
        avg_qty = sum(stats["quantities"]) / len(stats["quantities"])
        frequent_items.append({
            "product_name": stats["product_name"],
            "typical_quantity": round(avg_qty, 1),
            "unit": stats["unit"],
            "order_count": stats["count"],
        })

    return frequent_items


def format_order_history_context(
    history: list[dict],
    frequent_items: list[dict],
) -> str:
    """
    Format order history as context for the LLM prompt.

    Args:
        history: Recent order history
        frequent_items: Frequently ordered items

    Returns:
        Formatted string for LLM context
    """
    if not history and not frequent_items:
        return ""

    lines = ["CUSTOMER ORDER HISTORY:"]

    if history:
        lines.append("\nRecent Orders:")
        for i, order in enumerate(history[:5], 1):
            items_str = ", ".join(order["items"][:5])
            if len(order["items"]) > 5:
                items_str += f" (+{len(order['items']) - 5} more)"
            lines.append(f"  {i}. {order['date']}: {items_str}")

    if frequent_items:
        lines.append("\nFrequently Ordered Items ('the usual' likely refers to these):")
        for item in frequent_items[:7]:
            lines.append(
                f"  - {item['product_name']}: typically {item['typical_quantity']} {item['unit']} "
                f"(ordered {item['order_count']} times)"
            )

    lines.append(
        "\nWhen the customer says 'the usual', 'same as last time', or similar, "
        "use this history to resolve the reference and increase confidence accordingly."
    )

    return "\n".join(lines)


async def find_customer_fuzzy(
    session: AsyncSession,
    customer_name: Optional[str] = None,
    organization: Optional[str] = None,
    phone: Optional[str] = None,
    min_confidence: float = 0.6,
) -> Optional[Customer]:
    """
    Find customer using fuzzy matching on name/organization.

    Args:
        session: Database session
        customer_name: Customer contact name
        organization: Organization/lodge name
        phone: Phone number (exact match)
        min_confidence: Minimum similarity threshold

    Returns:
        Best matching Customer or None
    """
    # Try exact phone match first (most reliable)
    if phone:
        query = select(Customer).where(
            or_(Customer.phone == phone, Customer.phone == phone.replace(" ", ""))
        )
        result = await session.execute(query)
        customer = result.scalar_one_or_none()
        if customer:
            return customer

    # Get all customers for fuzzy matching
    query = select(Customer)
    result = await session.execute(query)
    customers = result.scalars().all()

    if not customers:
        return None

    best_match = None
    best_score = 0.0

    search_term = (organization or customer_name or "").lower()
    if not search_term:
        return None

    for customer in customers:
        # Match against organization
        if customer.organization:
            org_score = SequenceMatcher(
                None, search_term, customer.organization.lower()
            ).ratio()
            if org_score > best_score:
                best_score = org_score
                best_match = customer

        # Match against name
        if customer.name:
            name_score = SequenceMatcher(
                None, search_term, customer.name.lower()
            ).ratio()
            if name_score > best_score:
                best_score = name_score
                best_match = customer

    if best_score >= min_confidence:
        return best_match

    return None


async def resolve_usual_order(
    session: AsyncSession,
    customer_name: Optional[str] = None,
    organization: Optional[str] = None,
    resolve_type: str = "frequent",
) -> Optional[List[Dict[str, Any]]]:
    """
    Resolve 'the usual' to actual order items.

    Args:
        session: Database session
        customer_name: Customer contact name
        organization: Organization/lodge name
        resolve_type: 'frequent' for top items, 'last' for most recent order

    Returns:
        List of items with product_name, quantity, unit, or None if no history
    """
    if resolve_type == "last":
        # Get most recent order items
        history = await get_customer_order_history(
            session, customer_name, organization, limit=1
        )
        if not history:
            return None

        # Parse items from the most recent order
        query = select(Order).order_by(Order.created_at.desc())

        if organization:
            query = query.where(
                func.lower(Order.organization).contains(organization.lower())
            )
        elif customer_name:
            query = query.where(
                func.lower(Order.customer_name).contains(customer_name.lower())
            )
        else:
            return None

        query = query.limit(1)
        result = await session.execute(query)
        order = result.scalar_one_or_none()

        if order and order.items_json and "items" in order.items_json:
            return [
                {
                    "product_name": item["product_name"],
                    "quantity": item["quantity"],
                    "unit": item["unit"],
                    "resolved_from": "last_order",
                }
                for item in order.items_json["items"]
            ]

        return None

    else:  # frequent
        # Get frequently ordered items with typical quantities
        frequent = await get_customer_frequent_items(
            session, customer_name, organization, limit=10
        )

        if not frequent:
            return None

        # Return items that have been ordered at least 2 times
        return [
            {
                "product_name": item["product_name"],
                "quantity": item["typical_quantity"],
                "unit": item["unit"],
                "resolved_from": "frequent_items",
                "order_count": item["order_count"],
            }
            for item in frequent
            if item["order_count"] >= 2
        ]


def detect_usual_reference(message: str) -> bool:
    """
    Detect if a message contains references to 'the usual' or similar.

    Args:
        message: The customer message

    Returns:
        True if message references usual/previous orders
    """
    message_lower = message.lower()

    # Common phrases indicating 'the usual'
    usual_phrases = [
        "the usual",
        "my usual",
        "our usual",
        "same as before",
        "same as last time",
        "same order",
        "regular order",
        "same as yesterday",
        "same as always",
        "what we always get",
        "what i always order",
        "repeat order",
        "reorder",
        "same thing",
        "usual order",
        # Swahili equivalents
        "kama kawaida",
        "order ya kawaida",
        "vile tunavyoagiza",
    ]

    for phrase in usual_phrases:
        if phrase in message_lower:
            return True

    return False
