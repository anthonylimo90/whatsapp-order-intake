"""Main order processing pipeline."""

from __future__ import annotations
from typing import Optional
from .models import ProcessingResult
from .extractor import OrderExtractor
from .confirmation import ConfirmationGenerator
from .erp_payload import build_erp_payload


class OrderProcessor:
    """
    Main processor for WhatsApp order messages.

    Orchestrates extraction, ERP payload generation, and confirmation.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the processor.

        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
        """
        self.extractor = OrderExtractor(api_key)
        self.confirmation_generator = ConfirmationGenerator(api_key)

    def process(self, message: str, use_simple_confirmation: bool = False) -> ProcessingResult:
        """
        Process a WhatsApp order message end-to-end.

        Args:
            message: Raw WhatsApp message text
            use_simple_confirmation: Use template-based confirmation (no LLM call)

        Returns:
            ProcessingResult with extraction, ERP payload, and confirmation
        """
        try:
            # Step 1: Extract order data from message
            extracted_order = self.extractor.extract(message)

            # Step 2: Build ERP-ready payload
            erp_payload = build_erp_payload(extracted_order)

            # Step 3: Generate confirmation message
            if use_simple_confirmation:
                confirmation = self.confirmation_generator.generate_simple(extracted_order)
            else:
                confirmation = self.confirmation_generator.generate(extracted_order)

            return ProcessingResult(
                success=True,
                extracted_order=extracted_order,
                erp_payload=erp_payload,
                confirmation_message=confirmation,
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
