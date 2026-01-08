"""Pricing service with customer tier-based discounts."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db.models import Customer


class CustomerTier(str, Enum):
    """Customer pricing tier levels."""
    STANDARD = "standard"
    PREMIUM = "premium"
    VIP = "vip"


@dataclass
class TierConfig:
    """Configuration for a pricing tier."""
    tier: CustomerTier
    discount_percentage: float
    min_order_value: float = 0.0
    free_delivery_threshold: float = 0.0
    description: str = ""


# Default tier configurations
TIER_CONFIGS: Dict[CustomerTier, TierConfig] = {
    CustomerTier.STANDARD: TierConfig(
        tier=CustomerTier.STANDARD,
        discount_percentage=0.0,
        min_order_value=0.0,
        free_delivery_threshold=50000.0,  # KES
        description="Standard customer pricing",
    ),
    CustomerTier.PREMIUM: TierConfig(
        tier=CustomerTier.PREMIUM,
        discount_percentage=10.0,  # 10% discount
        min_order_value=0.0,
        free_delivery_threshold=30000.0,
        description="Premium customer - 10% discount",
    ),
    CustomerTier.VIP: TierConfig(
        tier=CustomerTier.VIP,
        discount_percentage=20.0,  # 20% discount
        min_order_value=0.0,
        free_delivery_threshold=0.0,  # Always free
        description="VIP customer - 20% discount, free delivery",
    ),
}


@dataclass
class PricedItem:
    """An item with pricing information."""
    product_name: str
    quantity: float
    unit: str
    base_price: float
    discount_percentage: float
    discounted_price: float
    line_total: float
    notes: Optional[str] = None


@dataclass
class PricedOrder:
    """An order with complete pricing breakdown."""
    customer_name: str
    customer_tier: CustomerTier
    items: List[PricedItem]
    subtotal: float
    discount_amount: float
    delivery_fee: float
    total: float
    currency: str = "KES"


class PricingService:
    """Service for applying tier-based pricing to orders."""

    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session
        self.default_currency = "KES"

    async def get_customer_tier(
        self,
        customer_name: Optional[str] = None,
        organization: Optional[str] = None,
        customer_id: Optional[int] = None,
    ) -> CustomerTier:
        """
        Get the pricing tier for a customer.

        Args:
            customer_name: Customer contact name
            organization: Organization/lodge name
            customer_id: Direct customer ID

        Returns:
            CustomerTier enum value
        """
        if not self.session:
            return CustomerTier.STANDARD

        try:
            if customer_id:
                query = select(Customer).where(Customer.id == customer_id)
            elif organization:
                query = select(Customer).where(
                    Customer.organization.ilike(f"%{organization}%")
                )
            elif customer_name:
                query = select(Customer).where(
                    Customer.name.ilike(f"%{customer_name}%")
                )
            else:
                return CustomerTier.STANDARD

            result = await self.session.execute(query)
            customer = result.scalar_one_or_none()

            if customer and customer.tier:
                try:
                    return CustomerTier(customer.tier.lower())
                except ValueError:
                    return CustomerTier.STANDARD

        except Exception:
            pass

        return CustomerTier.STANDARD

    def get_tier_config(self, tier: CustomerTier) -> TierConfig:
        """Get the configuration for a tier."""
        return TIER_CONFIGS.get(tier, TIER_CONFIGS[CustomerTier.STANDARD])

    def calculate_discount(self, base_price: float, tier: CustomerTier) -> float:
        """
        Calculate the discounted price for a tier.

        Args:
            base_price: Original price
            tier: Customer tier

        Returns:
            Discounted price
        """
        config = self.get_tier_config(tier)
        discount = base_price * (config.discount_percentage / 100)
        return base_price - discount

    def calculate_delivery_fee(
        self,
        subtotal: float,
        tier: CustomerTier,
        base_delivery_fee: float = 500.0,
    ) -> float:
        """
        Calculate delivery fee based on order total and tier.

        Args:
            subtotal: Order subtotal
            tier: Customer tier
            base_delivery_fee: Default delivery fee

        Returns:
            Delivery fee (0 if threshold met)
        """
        config = self.get_tier_config(tier)

        # VIP gets free delivery always
        if config.free_delivery_threshold == 0.0:
            return 0.0

        # Check if subtotal meets threshold
        if subtotal >= config.free_delivery_threshold:
            return 0.0

        return base_delivery_fee

    def price_item(
        self,
        product_name: str,
        quantity: float,
        unit: str,
        base_price: float,
        tier: CustomerTier,
        notes: Optional[str] = None,
    ) -> PricedItem:
        """
        Apply tier pricing to a single item.

        Args:
            product_name: Product name
            quantity: Quantity ordered
            unit: Unit of measure
            base_price: Base unit price
            tier: Customer tier

        Returns:
            PricedItem with all pricing details
        """
        config = self.get_tier_config(tier)
        discounted_price = self.calculate_discount(base_price, tier)
        line_total = discounted_price * quantity

        return PricedItem(
            product_name=product_name,
            quantity=quantity,
            unit=unit,
            base_price=base_price,
            discount_percentage=config.discount_percentage,
            discounted_price=discounted_price,
            line_total=line_total,
            notes=notes,
        )

    async def price_order(
        self,
        customer_name: str,
        items: List[Dict[str, Any]],
        base_prices: Dict[str, float],
        organization: Optional[str] = None,
        base_delivery_fee: float = 500.0,
    ) -> PricedOrder:
        """
        Apply tier pricing to an entire order.

        Args:
            customer_name: Customer name
            items: List of items with product_name, quantity, unit
            base_prices: Dict mapping product names to base prices
            organization: Customer organization
            base_delivery_fee: Default delivery fee

        Returns:
            PricedOrder with complete breakdown
        """
        # Get customer tier
        tier = await self.get_customer_tier(
            customer_name=customer_name,
            organization=organization,
        )

        # Price each item
        priced_items = []
        subtotal = 0.0

        for item in items:
            product_name = item.get("product_name", "Unknown")
            quantity = item.get("quantity", 0)
            unit = item.get("unit", "")
            notes = item.get("notes")

            # Get base price (default to 0 if not found)
            base_price = base_prices.get(product_name.lower(), 0.0)

            priced_item = self.price_item(
                product_name=product_name,
                quantity=quantity,
                unit=unit,
                base_price=base_price,
                tier=tier,
                notes=notes,
            )
            priced_items.append(priced_item)
            subtotal += priced_item.line_total

        # Calculate discount amount
        config = self.get_tier_config(tier)
        discount_amount = subtotal * (config.discount_percentage / 100)
        discounted_subtotal = subtotal - discount_amount

        # Calculate delivery fee
        delivery_fee = self.calculate_delivery_fee(
            discounted_subtotal, tier, base_delivery_fee
        )

        # Calculate total
        total = discounted_subtotal + delivery_fee

        return PricedOrder(
            customer_name=customer_name,
            customer_tier=tier,
            items=priced_items,
            subtotal=subtotal,
            discount_amount=discount_amount,
            delivery_fee=delivery_fee,
            total=total,
            currency=self.default_currency,
        )

    def format_price(self, amount: float, currency: str = "KES") -> str:
        """Format a price for display."""
        return f"{currency} {amount:,.2f}"

    def format_order_summary(self, order: PricedOrder) -> str:
        """
        Format a priced order for display.

        Args:
            order: PricedOrder object

        Returns:
            Formatted string summary
        """
        lines = [
            f"Customer: {order.customer_name} ({order.customer_tier.value.upper()})",
            "",
            "Items:",
        ]

        for item in order.items:
            base = self.format_price(item.base_price)
            if item.discount_percentage > 0:
                lines.append(
                    f"  {item.quantity} {item.unit} {item.product_name}: "
                    f"{base} → {self.format_price(item.discounted_price)} "
                    f"(-{item.discount_percentage:.0f}%)"
                )
            else:
                lines.append(
                    f"  {item.quantity} {item.unit} {item.product_name}: {base}"
                )

        lines.extend([
            "",
            f"Subtotal: {self.format_price(order.subtotal)}",
        ])

        if order.discount_amount > 0:
            lines.append(
                f"Discount ({order.customer_tier.value}): "
                f"-{self.format_price(order.discount_amount)}"
            )

        if order.delivery_fee > 0:
            lines.append(f"Delivery: {self.format_price(order.delivery_fee)}")
        else:
            lines.append("Delivery: FREE")

        lines.append(f"Total: {self.format_price(order.total)}")

        return "\n".join(lines)
