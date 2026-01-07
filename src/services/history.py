"""Order history service for resolving ambiguous references."""

from typing import Optional
from sqlalchemy import select, func
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
