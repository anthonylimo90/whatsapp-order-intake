"""Internationalization package for multi-language support."""

from .swahili_dictionary import (
    SWAHILI_TO_ENGLISH,
    ENGLISH_TO_SWAHILI,
    SWAHILI_QUANTITIES,
    SWAHILI_UNITS,
    translate_product_name,
    parse_swahili_quantity,
)
from .messages import (
    get_message,
    get_confirmation_template,
    get_clarification_template,
    SUPPORTED_LANGUAGES,
)

__all__ = [
    "SWAHILI_TO_ENGLISH",
    "ENGLISH_TO_SWAHILI",
    "SWAHILI_QUANTITIES",
    "SWAHILI_UNITS",
    "translate_product_name",
    "parse_swahili_quantity",
    "get_message",
    "get_confirmation_template",
    "get_clarification_template",
    "SUPPORTED_LANGUAGES",
]
