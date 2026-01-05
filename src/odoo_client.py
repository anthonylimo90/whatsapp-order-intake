"""
Odoo ERP integration client.

This module provides integration with Odoo's External API via XML-RPC.
Supports customer lookup, product matching, and sales order creation.

Note: Odoo External API requires Custom pricing plan (not available on Free/Standard).
Note: XML-RPC API is deprecated and will be removed in Odoo 20 (Fall 2026).
"""

from __future__ import annotations
import os
import xmlrpc.client
from typing import Optional
from dataclasses import dataclass
from difflib import SequenceMatcher

from .models import ERPOrderPayload


@dataclass
class OdooConfig:
    """Configuration for Odoo connection."""
    url: str
    database: str
    username: str
    password: str  # Can be password or API key (Odoo 14+)

    @classmethod
    def from_env(cls) -> "OdooConfig":
        """Load configuration from environment variables."""
        return cls(
            url=os.getenv("ODOO_URL", ""),
            database=os.getenv("ODOO_DATABASE", ""),
            username=os.getenv("ODOO_USERNAME", ""),
            password=os.getenv("ODOO_PASSWORD", ""),  # Or ODOO_API_KEY
        )


@dataclass
class CustomerMatch:
    """Result of customer lookup."""
    id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    confidence: float = 1.0


@dataclass
class ProductMatch:
    """Result of product lookup."""
    id: int
    name: str
    default_code: Optional[str] = None  # SKU
    list_price: float = 0.0
    uom_id: int = 1  # Unit of measure
    confidence: float = 1.0


@dataclass
class OdooOrderResult:
    """Result of order submission to Odoo."""
    success: bool
    order_id: Optional[int] = None
    order_name: Optional[str] = None  # e.g., "SO001"
    error: Optional[str] = None
    unmatched_products: list[str] = None

    def __post_init__(self):
        if self.unmatched_products is None:
            self.unmatched_products = []


class OdooClient:
    """
    Client for Odoo External API integration.

    Uses XML-RPC to communicate with Odoo's external API endpoints:
    - /xmlrpc/2/common - Authentication
    - /xmlrpc/2/object - Model operations (CRUD)
    """

    def __init__(self, config: OdooConfig):
        """
        Initialize the Odoo client.

        Args:
            config: Odoo connection configuration
        """
        self.config = config
        self._uid: Optional[int] = None
        self._common: Optional[xmlrpc.client.ServerProxy] = None
        self._models: Optional[xmlrpc.client.ServerProxy] = None

    def connect(self) -> bool:
        """
        Establish connection and authenticate with Odoo.

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            self._common = xmlrpc.client.ServerProxy(
                f"{self.config.url}/xmlrpc/2/common"
            )
            self._uid = self._common.authenticate(
                self.config.database,
                self.config.username,
                self.config.password,
                {}
            )
            if self._uid:
                self._models = xmlrpc.client.ServerProxy(
                    f"{self.config.url}/xmlrpc/2/object"
                )
                return True
            return False
        except Exception as e:
            print(f"Odoo connection failed: {e}")
            return False

    def _execute(self, model: str, method: str, *args):
        """Execute a method on an Odoo model."""
        if not self._uid or not self._models:
            raise RuntimeError("Not connected to Odoo. Call connect() first.")
        return self._models.execute_kw(
            self.config.database,
            self._uid,
            self.config.password,
            model,
            method,
            *args
        )

    def search_customer(
        self,
        name: Optional[str] = None,
        phone: Optional[str] = None
    ) -> Optional[CustomerMatch]:
        """
        Search for a customer (res.partner) by name or phone.

        Args:
            name: Customer or organization name
            phone: Phone number

        Returns:
            CustomerMatch if found, None otherwise
        """
        domain = []
        if phone:
            # Try exact phone match first (most reliable)
            domain = ["|", ("phone", "=", phone), ("mobile", "=", phone)]
        elif name:
            # Fuzzy name search
            domain = [("name", "ilike", name)]

        if not domain:
            return None

        results = self._execute(
            "res.partner",
            "search_read",
            [domain],
            {"fields": ["id", "name", "phone", "mobile", "email"], "limit": 5}
        )

        if not results:
            return None

        # If multiple results, find best match
        if name and len(results) > 1:
            best_match = max(
                results,
                key=lambda r: SequenceMatcher(None, name.lower(), r["name"].lower()).ratio()
            )
            confidence = SequenceMatcher(None, name.lower(), best_match["name"].lower()).ratio()
        else:
            best_match = results[0]
            confidence = 1.0 if phone else 0.9

        return CustomerMatch(
            id=best_match["id"],
            name=best_match["name"],
            phone=best_match.get("phone") or best_match.get("mobile"),
            email=best_match.get("email"),
            confidence=confidence,
        )

    def search_product(self, name: str) -> Optional[ProductMatch]:
        """
        Search for a product by name with fuzzy matching.

        Args:
            name: Product name to search for

        Returns:
            ProductMatch if found, None otherwise
        """
        # Search for products matching the name
        results = self._execute(
            "product.product",
            "search_read",
            [[("name", "ilike", name), ("sale_ok", "=", True)]],
            {"fields": ["id", "name", "default_code", "list_price", "uom_id"], "limit": 10}
        )

        if not results:
            # Try broader search with individual words
            words = name.split()
            if len(words) > 1:
                for word in words:
                    if len(word) > 2:  # Skip short words
                        results = self._execute(
                            "product.product",
                            "search_read",
                            [[("name", "ilike", word), ("sale_ok", "=", True)]],
                            {"fields": ["id", "name", "default_code", "list_price", "uom_id"], "limit": 10}
                        )
                        if results:
                            break

        if not results:
            return None

        # Find best match using fuzzy matching
        best_match = max(
            results,
            key=lambda r: SequenceMatcher(None, name.lower(), r["name"].lower()).ratio()
        )
        confidence = SequenceMatcher(None, name.lower(), best_match["name"].lower()).ratio()

        return ProductMatch(
            id=best_match["id"],
            name=best_match["name"],
            default_code=best_match.get("default_code"),
            list_price=best_match.get("list_price", 0.0),
            uom_id=best_match.get("uom_id", [1])[0] if best_match.get("uom_id") else 1,
            confidence=confidence,
        )

    def create_sale_order(
        self,
        partner_id: int,
        order_lines: list[dict],
        notes: Optional[str] = None,
    ) -> OdooOrderResult:
        """
        Create a sales order in Odoo.

        Args:
            partner_id: Odoo customer ID
            order_lines: List of {"product_id": int, "quantity": float, "price_unit": float}
            notes: Optional order notes

        Returns:
            OdooOrderResult with order details or error
        """
        try:
            # Build order line tuples: (0, 0, {values}) for create
            odoo_lines = [
                (0, 0, {
                    "product_id": line["product_id"],
                    "product_uom_qty": line["quantity"],
                    "price_unit": line.get("price_unit", 0.0),
                })
                for line in order_lines
            ]

            order_vals = {
                "partner_id": partner_id,
                "order_line": odoo_lines,
            }
            if notes:
                order_vals["note"] = notes

            # Create the order
            order_id = self._execute("sale.order", "create", [order_vals])

            # Get order name
            order_data = self._execute(
                "sale.order",
                "read",
                [[order_id]],
                {"fields": ["name"]}
            )
            order_name = order_data[0]["name"] if order_data else None

            return OdooOrderResult(
                success=True,
                order_id=order_id,
                order_name=order_name,
            )

        except Exception as e:
            return OdooOrderResult(
                success=False,
                error=str(e),
            )

    def submit_order(self, payload: ERPOrderPayload) -> OdooOrderResult:
        """
        Submit an extracted order payload to Odoo.

        This is the main integration point - takes our ERPOrderPayload
        and creates a corresponding sale.order in Odoo.

        Args:
            payload: The ERP payload from order extraction

        Returns:
            OdooOrderResult with success/failure details
        """
        # Step 1: Find customer
        customer = self.search_customer(name=payload.customer_identifier)
        if not customer:
            return OdooOrderResult(
                success=False,
                error=f"Customer not found: {payload.customer_identifier}",
            )

        # Step 2: Match products
        order_lines = []
        unmatched = []

        for line in payload.order_lines:
            product = self.search_product(line["product_name"])
            if product:
                order_lines.append({
                    "product_id": product.id,
                    "quantity": line["quantity"],
                    "price_unit": product.list_price,
                })
            else:
                unmatched.append(line["product_name"])

        if not order_lines:
            return OdooOrderResult(
                success=False,
                error="No products could be matched",
                unmatched_products=unmatched,
            )

        # Step 3: Create order
        notes_parts = []
        if payload.notes:
            notes_parts.append(payload.notes)
        if payload.requested_delivery_date:
            notes_parts.append(f"Requested delivery: {payload.requested_delivery_date}")
        if unmatched:
            notes_parts.append(f"Unmatched items (need manual add): {', '.join(unmatched)}")
        notes_parts.append(f"Source: {payload.source_channel}")

        result = self.create_sale_order(
            partner_id=customer.id,
            order_lines=order_lines,
            notes="\n".join(notes_parts) if notes_parts else None,
        )
        result.unmatched_products = unmatched

        return result


class MockOdooClient(OdooClient):
    """
    Mock Odoo client for testing without a real Odoo instance.

    Simulates customer and product lookups with sample data.
    """

    # Sample customers (simulating Odoo res.partner)
    MOCK_CUSTOMERS = [
        {"id": 1, "name": "Saruni Mara", "phone": "+254700000001", "email": "orders@sarunimara.com"},
        {"id": 2, "name": "Kilima Safari Lodge", "phone": "+254700000002", "email": "orders@kilimasafari.com"},
        {"id": 3, "name": "Angama Mara", "phone": "+254700000003", "email": "orders@angama.com"},
        {"id": 4, "name": "Governors Camp", "phone": "+254700000004", "email": "orders@governorscamp.com"},
    ]

    # Sample products (simulating Odoo product.product)
    MOCK_PRODUCTS = [
        {"id": 101, "name": "Rice (Basmati) 25kg", "default_code": "RICE-BAS-25", "list_price": 2500.0},
        {"id": 102, "name": "Sugar 25kg", "default_code": "SUG-25", "list_price": 1800.0},
        {"id": 103, "name": "Cooking Oil 20L", "default_code": "OIL-20L", "list_price": 3200.0},
        {"id": 104, "name": "Eggs (Tray of 30)", "default_code": "EGG-30", "list_price": 450.0},
        {"id": 105, "name": "Fresh Milk 1L", "default_code": "MILK-1L", "list_price": 120.0},
        {"id": 106, "name": "Bread (White Loaf)", "default_code": "BREAD-WHT", "list_price": 55.0},
        {"id": 107, "name": "Butter 500g", "default_code": "BTR-500", "list_price": 350.0},
        {"id": 108, "name": "Cheddar Cheese 1kg", "default_code": "CHS-CHD-1", "list_price": 1200.0},
        {"id": 109, "name": "Tomatoes Fresh 1kg", "default_code": "TOM-1KG", "list_price": 80.0},
        {"id": 110, "name": "Onions 1kg", "default_code": "ONI-1KG", "list_price": 60.0},
        {"id": 111, "name": "Potatoes 1kg", "default_code": "POT-1KG", "list_price": 50.0},
        {"id": 112, "name": "Carrots 1kg", "default_code": "CAR-1KG", "list_price": 70.0},
        {"id": 113, "name": "Green Beans 1kg", "default_code": "GRB-1KG", "list_price": 150.0},
        {"id": 114, "name": "Toilet Paper (100 rolls)", "default_code": "TP-100", "list_price": 4500.0},
        {"id": 115, "name": "Hand Sanitizer 500ml", "default_code": "SAN-500", "list_price": 350.0},
        {"id": 116, "name": "Bar Soap (Box of 12)", "default_code": "SOAP-12", "list_price": 600.0},
        {"id": 117, "name": "Flour (All Purpose) 25kg", "default_code": "FLR-25", "list_price": 1500.0},
    ]

    _order_counter = 0

    def __init__(self, config: Optional[OdooConfig] = None):
        """Initialize mock client (config not required)."""
        self.config = config or OdooConfig("", "", "", "")
        self._uid = 1  # Fake user ID

    def connect(self) -> bool:
        """Mock connection always succeeds."""
        return True

    def search_customer(
        self,
        name: Optional[str] = None,
        phone: Optional[str] = None
    ) -> Optional[CustomerMatch]:
        """Search mock customers."""
        if phone:
            for c in self.MOCK_CUSTOMERS:
                if c["phone"] == phone:
                    return CustomerMatch(
                        id=c["id"],
                        name=c["name"],
                        phone=c["phone"],
                        email=c["email"],
                        confidence=1.0,
                    )

        if name:
            # Fuzzy match on name
            best_match = None
            best_score = 0.0
            for c in self.MOCK_CUSTOMERS:
                score = SequenceMatcher(None, name.lower(), c["name"].lower()).ratio()
                if score > best_score and score > 0.4:  # Minimum threshold
                    best_score = score
                    best_match = c

            if best_match:
                return CustomerMatch(
                    id=best_match["id"],
                    name=best_match["name"],
                    phone=best_match["phone"],
                    email=best_match["email"],
                    confidence=best_score,
                )

        return None

    def search_product(self, name: str) -> Optional[ProductMatch]:
        """Search mock products with fuzzy matching."""
        best_match = None
        best_score = 0.0

        name_lower = name.lower()
        for p in self.MOCK_PRODUCTS:
            # Check product name
            score = SequenceMatcher(None, name_lower, p["name"].lower()).ratio()

            # Also check if search term is contained in product name
            if name_lower in p["name"].lower():
                score = max(score, 0.8)

            # Check individual words
            for word in name_lower.split():
                if len(word) > 2 and word in p["name"].lower():
                    score = max(score, 0.7)

            if score > best_score and score > 0.3:
                best_score = score
                best_match = p

        if best_match:
            return ProductMatch(
                id=best_match["id"],
                name=best_match["name"],
                default_code=best_match["default_code"],
                list_price=best_match["list_price"],
                confidence=best_score,
            )

        return None

    def create_sale_order(
        self,
        partner_id: int,
        order_lines: list[dict],
        notes: Optional[str] = None,
    ) -> OdooOrderResult:
        """Create a mock sales order."""
        MockOdooClient._order_counter += 1
        order_id = 1000 + MockOdooClient._order_counter
        order_name = f"SO{order_id:04d}"

        return OdooOrderResult(
            success=True,
            order_id=order_id,
            order_name=order_name,
        )
