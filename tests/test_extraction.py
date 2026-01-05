"""Tests for order extraction functionality."""

import pytest
from unittest.mock import Mock, patch
import json

from src.models import ExtractedOrder, ExtractedItem, ConfidenceLevel, ERPOrderPayload
from src.erp_payload import build_erp_payload, confidence_to_score


class TestConfidenceScoring:
    """Test confidence score conversion."""

    def test_high_confidence_score(self):
        assert confidence_to_score(ConfidenceLevel.HIGH) == 0.95

    def test_medium_confidence_score(self):
        assert confidence_to_score(ConfidenceLevel.MEDIUM) == 0.75

    def test_low_confidence_score(self):
        assert confidence_to_score(ConfidenceLevel.LOW) == 0.50


class TestERPPayloadGeneration:
    """Test ERP payload generation from extracted orders."""

    def create_sample_order(self, **kwargs) -> ExtractedOrder:
        """Create a sample order for testing."""
        defaults = {
            "customer_name": "Mary",
            "customer_organization": "Saruni Mara",
            "items": [
                ExtractedItem(
                    product_name="Rice",
                    quantity=50,
                    unit="kg",
                    confidence=ConfidenceLevel.HIGH,
                    original_text="50kg rice",
                )
            ],
            "requested_delivery_date": "Friday",
            "delivery_urgency": None,
            "overall_confidence": ConfidenceLevel.HIGH,
            "requires_clarification": False,
            "clarification_needed": [],
            "raw_message": "Test message",
        }
        defaults.update(kwargs)
        return ExtractedOrder(**defaults)

    def test_basic_payload_generation(self):
        """Test basic ERP payload generation."""
        order = self.create_sample_order()
        payload = build_erp_payload(order)

        assert payload.customer_identifier == "Saruni Mara"
        assert payload.source_channel == "whatsapp"
        assert len(payload.order_lines) == 1
        assert payload.order_lines[0]["product_name"] == "Rice"
        assert payload.order_lines[0]["quantity"] == 50

    def test_payload_uses_customer_name_when_no_org(self):
        """Test fallback to customer name when no organization."""
        order = self.create_sample_order(customer_organization=None)
        payload = build_erp_payload(order)

        assert payload.customer_identifier == "Mary"

    def test_high_confidence_no_review(self):
        """Test high confidence orders don't require review."""
        order = self.create_sample_order()
        payload = build_erp_payload(order)

        assert payload.requires_review is False
        assert payload.confidence_score == 0.95

    def test_low_confidence_requires_review(self):
        """Test low confidence orders require review."""
        items = [
            ExtractedItem(
                product_name="Soap",
                quantity=5,
                unit="boxes",
                confidence=ConfidenceLevel.LOW,
                original_text="the usual soap",
                notes="Unclear which soap brand",
            )
        ]
        order = self.create_sample_order(
            items=items,
            overall_confidence=ConfidenceLevel.LOW,
            requires_clarification=True,
        )
        payload = build_erp_payload(order)

        assert payload.requires_review is True
        assert payload.confidence_score == 0.50

    def test_urgency_included_in_notes(self):
        """Test that delivery urgency is included in notes."""
        order = self.create_sample_order(delivery_urgency="ASAP")
        payload = build_erp_payload(order)

        assert payload.notes is not None
        assert "Urgency: ASAP" in payload.notes

    def test_clarification_items_in_notes(self):
        """Test that clarification items are in notes."""
        order = self.create_sample_order(
            requires_clarification=True,
            clarification_needed=["Which brand of soap?", "Quantity of flour?"],
        )
        payload = build_erp_payload(order)

        assert payload.notes is not None
        assert "Which brand of soap?" in payload.notes


class TestExtractedOrderModel:
    """Test the ExtractedOrder model validation."""

    def test_valid_order_creation(self):
        """Test creating a valid order."""
        order = ExtractedOrder(
            customer_name="Peter",
            customer_organization="Governors Camp",
            items=[
                ExtractedItem(
                    product_name="Milk",
                    quantity=40,
                    unit="L",
                    confidence=ConfidenceLevel.MEDIUM,
                    original_text="milk like maybe 40 liters",
                )
            ],
            requested_delivery_date="tomorrow",
            overall_confidence=ConfidenceLevel.MEDIUM,
            requires_clarification=False,
            raw_message="test",
        )

        assert order.customer_name == "Peter"
        assert len(order.items) == 1
        assert order.items[0].quantity == 40

    def test_order_with_multiple_items(self):
        """Test order with multiple items."""
        items = [
            ExtractedItem(
                product_name="Tomatoes",
                quantity=30,
                unit="kg",
                confidence=ConfidenceLevel.HIGH,
                original_text="Tomatoes 30kg",
            ),
            ExtractedItem(
                product_name="Onions",
                quantity=20,
                unit="kg",
                confidence=ConfidenceLevel.HIGH,
                original_text="Onions 20kg",
            ),
        ]

        order = ExtractedOrder(
            customer_name="Staff",
            customer_organization="Angama Mara",
            items=items,
            overall_confidence=ConfidenceLevel.HIGH,
            requires_clarification=False,
            raw_message="test",
        )

        assert len(order.items) == 2


class TestERPPayloadModel:
    """Test the ERPOrderPayload model."""

    def test_confidence_score_validation(self):
        """Test confidence score must be between 0 and 1."""
        payload = ERPOrderPayload(
            customer_identifier="Test",
            order_lines=[],
            confidence_score=0.85,
        )
        assert payload.confidence_score == 0.85

    def test_invalid_confidence_score_raises(self):
        """Test that invalid confidence score raises error."""
        with pytest.raises(ValueError):
            ERPOrderPayload(
                customer_identifier="Test",
                order_lines=[],
                confidence_score=1.5,  # Invalid: > 1.0
            )


# Integration test marker for tests that require API
@pytest.mark.integration
class TestLiveExtraction:
    """Integration tests that hit the actual API.

    Run with: pytest -m integration
    """

    def test_clear_order_extraction(self):
        """Test extraction of a clear order."""
        from src.processor import OrderProcessor

        processor = OrderProcessor()
        message = "Hi, this is Mary from Saruni Mara. We need 50kg rice, 20kg sugar, 10L cooking oil, and 30 eggs for Friday delivery. Thanks!"

        result = processor.process(message, use_simple_confirmation=True)

        assert result.success
        assert result.extracted_order is not None
        assert result.extracted_order.customer_organization == "Saruni Mara"
        assert len(result.extracted_order.items) == 4
        assert result.extracted_order.overall_confidence == ConfidenceLevel.HIGH
