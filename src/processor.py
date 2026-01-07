"""Main order processing pipeline."""

from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from .models import ProcessingResult, OdooSubmissionResult
from .extractor import OrderExtractor
from .confirmation import ConfirmationGenerator
from .erp_payload import build_erp_payload

if TYPE_CHECKING:
    from .odoo_client import OdooClient


class OrderProcessor:
    """
    Main processor for WhatsApp order messages.

    Orchestrates extraction, ERP payload generation, and confirmation.
    Optionally submits orders to Odoo ERP.
    """

    def __init__(self, api_key: Optional[str] = None, odoo_client: Optional["OdooClient"] = None):
        """
        Initialize the processor.

        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
            odoo_client: Optional Odoo client for ERP submission
        """
        self.extractor = OrderExtractor(api_key)
        self.confirmation_generator = ConfirmationGenerator(api_key)
        self.odoo_client = odoo_client

    def process(
        self,
        message: str,
        use_simple_confirmation: bool = False,
        submit_to_odoo: bool = False,
        order_history_context: str = "",
    ) -> ProcessingResult:
        """
        Process a WhatsApp order message end-to-end.

        Args:
            message: Raw WhatsApp message text
            use_simple_confirmation: Use template-based confirmation (no LLM call)
            submit_to_odoo: Whether to submit the order to Odoo ERP
            order_history_context: Optional context about customer's past orders

        Returns:
            ProcessingResult with extraction, ERP payload, confirmation, and optional Odoo result
        """
        try:
            # Step 1: Extract order data from message (with history context if available)
            extracted_order = self.extractor.extract(message, order_history_context)

            # Step 2: Build ERP-ready payload
            erp_payload = build_erp_payload(extracted_order)

            # Step 3: Generate confirmation message
            if use_simple_confirmation:
                confirmation = self.confirmation_generator.generate_simple(extracted_order)
            else:
                confirmation = self.confirmation_generator.generate(extracted_order)

            # Step 4: Optionally submit to Odoo
            odoo_result = None
            if submit_to_odoo and self.odoo_client:
                odoo_response = self.odoo_client.submit_order(erp_payload)
                odoo_result = OdooSubmissionResult(
                    success=odoo_response.success,
                    order_id=odoo_response.order_id,
                    order_name=odoo_response.order_name,
                    error=odoo_response.error,
                    unmatched_products=odoo_response.unmatched_products or [],
                )

            return ProcessingResult(
                success=True,
                extracted_order=extracted_order,
                erp_payload=erp_payload,
                confirmation_message=confirmation,
                odoo_result=odoo_result,
            )

        except Exception as e:
            return ProcessingResult(
                success=False,
                error=str(e),
            )

    def extract_only(self, message: str):
        """
        Extract order data without generating confirmation.

        Useful for testing extraction logic.
        """
        return self.extractor.extract(message)
