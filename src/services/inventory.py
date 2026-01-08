"""Inventory service for stock availability checking."""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db.models import Product


class StockLevel(str, Enum):
    """Stock level categories."""
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    UNKNOWN = "unknown"


@dataclass
class StockStatus:
    """Stock status for a product."""
    product_name: str
    product_id: Optional[int]
    available_quantity: float
    unit: str
    requested_quantity: float
    is_available: bool
    stock_level: StockLevel
    can_fulfill: bool
    shortage: float  # How much is short (0 if can fulfill)
    alternatives: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None


@dataclass
class InventoryCheckResult:
    """Result of checking inventory for an order."""
    all_available: bool
    items: List[StockStatus]
    unavailable_items: List[StockStatus]
    low_stock_items: List[StockStatus]
    total_items: int
    fulfillable_items: int


# Default stock thresholds
DEFAULT_LOW_STOCK_THRESHOLD = 10.0


class InventoryService:
    """Service for checking and managing stock availability."""

    def __init__(
        self,
        session: Optional[AsyncSession] = None,
        low_stock_threshold: float = DEFAULT_LOW_STOCK_THRESHOLD,
    ):
        self.session = session
        self.low_stock_threshold = low_stock_threshold
        # In-memory stock for demo (would come from Odoo in production)
        self._mock_stock: Dict[str, Dict[str, Any]] = {}

    def set_mock_stock(self, product_name: str, quantity: float, unit: str = "kg"):
        """Set mock stock for testing."""
        self._mock_stock[product_name.lower()] = {
            "quantity": quantity,
            "unit": unit,
        }

    async def get_product_stock(
        self,
        product_name: str,
        product_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get stock information for a product.

        Args:
            product_name: Product name
            product_id: Optional product ID

        Returns:
            Dict with quantity and unit, or None if not found
        """
        # Check mock stock first
        if product_name.lower() in self._mock_stock:
            return self._mock_stock[product_name.lower()]

        # Check database
        if self.session:
            try:
                if product_id:
                    query = select(Product).where(Product.id == product_id)
                else:
                    query = select(Product).where(
                        Product.name.ilike(f"%{product_name}%")
                    )

                result = await self.session.execute(query)
                product = result.scalar_one_or_none()

                if product:
                    # Note: Product model has in_stock boolean, not quantity
                    # In production, this would query Odoo's stock.quant
                    return {
                        "quantity": 1000.0 if product.in_stock else 0.0,
                        "unit": product.unit or "kg",
                        "product_id": product.id,
                    }
            except Exception:
                pass

        return None

    def determine_stock_level(
        self,
        available: float,
        requested: float,
    ) -> StockLevel:
        """Determine the stock level category."""
        if available <= 0:
            return StockLevel.OUT_OF_STOCK
        if available < self.low_stock_threshold:
            return StockLevel.LOW_STOCK
        return StockLevel.IN_STOCK

    async def check_item_availability(
        self,
        product_name: str,
        quantity: float,
        unit: str,
        product_id: Optional[int] = None,
    ) -> StockStatus:
        """
        Check availability for a single item.

        Args:
            product_name: Product name
            quantity: Requested quantity
            unit: Unit of measure
            product_id: Optional product ID

        Returns:
            StockStatus with availability details
        """
        stock_info = await self.get_product_stock(product_name, product_id)

        if stock_info is None:
            return StockStatus(
                product_name=product_name,
                product_id=product_id,
                available_quantity=0.0,
                unit=unit,
                requested_quantity=quantity,
                is_available=False,
                stock_level=StockLevel.UNKNOWN,
                can_fulfill=False,
                shortage=quantity,
                notes="Product not found in inventory",
            )

        available = stock_info.get("quantity", 0.0)
        stock_unit = stock_info.get("unit", unit)
        db_product_id = stock_info.get("product_id", product_id)

        # Determine if we can fulfill the order
        can_fulfill = available >= quantity
        shortage = max(0, quantity - available) if not can_fulfill else 0

        stock_level = self.determine_stock_level(available, quantity)

        return StockStatus(
            product_name=product_name,
            product_id=db_product_id,
            available_quantity=available,
            unit=stock_unit,
            requested_quantity=quantity,
            is_available=available > 0,
            stock_level=stock_level,
            can_fulfill=can_fulfill,
            shortage=shortage,
        )

    async def check_order_availability(
        self,
        items: List[Dict[str, Any]],
    ) -> InventoryCheckResult:
        """
        Check availability for all items in an order.

        Args:
            items: List of items with product_name, quantity, unit

        Returns:
            InventoryCheckResult with complete status
        """
        item_statuses: List[StockStatus] = []
        unavailable: List[StockStatus] = []
        low_stock: List[StockStatus] = []

        for item in items:
            status = await self.check_item_availability(
                product_name=item.get("product_name", "Unknown"),
                quantity=item.get("quantity", 0),
                unit=item.get("unit", ""),
                product_id=item.get("product_id"),
            )
            item_statuses.append(status)

            if not status.can_fulfill:
                unavailable.append(status)
            elif status.stock_level == StockLevel.LOW_STOCK:
                low_stock.append(status)

        all_available = len(unavailable) == 0
        fulfillable = len(items) - len(unavailable)

        return InventoryCheckResult(
            all_available=all_available,
            items=item_statuses,
            unavailable_items=unavailable,
            low_stock_items=low_stock,
            total_items=len(items),
            fulfillable_items=fulfillable,
        )

    async def get_alternatives(
        self,
        product_name: str,
        category: Optional[str] = None,
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Get alternative products when an item is out of stock.

        Args:
            product_name: Original product name
            category: Product category for filtering
            limit: Maximum alternatives to return

        Returns:
            List of alternative products with stock info
        """
        if not self.session:
            return []

        try:
            # Find products in the same category that are in stock
            query = select(Product).where(Product.in_stock == True)

            if category:
                query = query.where(Product.category == category)

            query = query.limit(limit * 2)  # Get extra to filter

            result = await self.session.execute(query)
            products = result.scalars().all()

            alternatives = []
            for product in products:
                if product.name.lower() != product_name.lower():
                    alternatives.append({
                        "product_id": product.id,
                        "product_name": product.name,
                        "category": product.category,
                        "unit": product.unit,
                        "price": product.price,
                        "in_stock": product.in_stock,
                    })
                    if len(alternatives) >= limit:
                        break

            return alternatives
        except Exception:
            return []

    def format_availability_message(
        self,
        result: InventoryCheckResult,
        include_alternatives: bool = True,
    ) -> str:
        """
        Format inventory check result as a user-friendly message.

        Args:
            result: InventoryCheckResult
            include_alternatives: Whether to suggest alternatives

        Returns:
            Formatted message string
        """
        if result.all_available:
            if result.low_stock_items:
                return (
                    f"All {result.total_items} items are available. "
                    f"Note: {len(result.low_stock_items)} item(s) have low stock."
                )
            return f"All {result.total_items} items are available in stock."

        lines = [
            f"Stock Check: {result.fulfillable_items}/{result.total_items} items available."
        ]

        if result.unavailable_items:
            lines.append("\nUnavailable items:")
            for item in result.unavailable_items:
                if item.stock_level == StockLevel.OUT_OF_STOCK:
                    lines.append(f"  - {item.product_name}: OUT OF STOCK")
                else:
                    lines.append(
                        f"  - {item.product_name}: Only {item.available_quantity} "
                        f"{item.unit} available (need {item.requested_quantity})"
                    )

        if result.low_stock_items:
            lines.append("\nLow stock warnings:")
            for item in result.low_stock_items:
                lines.append(
                    f"  - {item.product_name}: {item.available_quantity} {item.unit} remaining"
                )

        return "\n".join(lines)
