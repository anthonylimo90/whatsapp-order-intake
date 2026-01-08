"""Services package."""

from .history import (
    get_customer_order_history,
    get_customer_frequent_items,
    format_order_history_context,
    find_customer_fuzzy,
    resolve_usual_order,
    detect_usual_reference,
)
from .excel_parser import (
    parse_excel_order,
    excel_order_to_text,
    ExcelOrderResult,
    ExcelOrderSheet,
    ExcelOrderItem,
)
from .order_state import OrderStateManager
from .product_matching import ProductMatchingService, MatchResult, PRODUCT_ALIASES
from .pricing import PricingService, CustomerTier, PricedOrder, PricedItem, TIER_CONFIGS
from .inventory import InventoryService, StockStatus, StockLevel, InventoryCheckResult
from .transcription import (
    TranscriptionService,
    TranscriptionResult,
    TranscriptionProvider,
    OpenAITranscriptionService,
    MockTranscriptionService,
    get_transcription_service,
    adjust_extraction_confidence_for_voice,
)

__all__ = [
    # History
    "get_customer_order_history",
    "get_customer_frequent_items",
    "format_order_history_context",
    "find_customer_fuzzy",
    "resolve_usual_order",
    "detect_usual_reference",
    # Excel
    "parse_excel_order",
    "excel_order_to_text",
    "ExcelOrderResult",
    "ExcelOrderSheet",
    "ExcelOrderItem",
    # Order State
    "OrderStateManager",
    # Product Matching
    "ProductMatchingService",
    "MatchResult",
    "PRODUCT_ALIASES",
    # Pricing
    "PricingService",
    "CustomerTier",
    "PricedOrder",
    "PricedItem",
    "TIER_CONFIGS",
    # Inventory
    "InventoryService",
    "StockStatus",
    "StockLevel",
    "InventoryCheckResult",
    # Transcription
    "TranscriptionService",
    "TranscriptionResult",
    "TranscriptionProvider",
    "OpenAITranscriptionService",
    "MockTranscriptionService",
    "get_transcription_service",
    "adjust_extraction_confidence_for_voice",
]
