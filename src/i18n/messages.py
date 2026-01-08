"""Internationalized message templates for confirmations and clarifications."""

from typing import Optional, Dict, Any

SUPPORTED_LANGUAGES = ["en", "sw"]  # English, Swahili

# Message templates for different scenarios
MESSAGES = {
    # Confirmation messages
    "order_received": {
        "en": "Thank you for your order! Here's what I understood:",
        "sw": "Asante kwa order yako! Hii ndio nilivyoelewa:",
    },
    "order_confirmed": {
        "en": "Your order has been confirmed and is being processed.",
        "sw": "Order yako imethibitishwa na inashughulikiwa.",
    },
    "order_summary_header": {
        "en": "Order Summary:",
        "sw": "Muhtasari wa Order:",
    },
    "items_header": {
        "en": "Items:",
        "sw": "Vitu:",
    },
    "delivery_date": {
        "en": "Delivery Date:",
        "sw": "Tarehe ya Uwasilishaji:",
    },
    "customer": {
        "en": "Customer:",
        "sw": "Mteja:",
    },

    # Clarification messages
    "clarification_needed": {
        "en": "I need some clarification on a few items:",
        "sw": "Ninahitaji ufafanuzi kuhusu vitu vichache:",
    },
    "which_product": {
        "en": "Which specific product did you mean by",
        "sw": "Bidhaa gani haswa ulimaanisha kwa",
    },
    "quantity_unclear": {
        "en": "Could you please specify the quantity for",
        "sw": "Tafadhali eleza kiasi cha",
    },
    "unit_unclear": {
        "en": "What unit would you like for",
        "sw": "Kipimo gani ungependa kwa",
    },

    # Status messages
    "processing": {
        "en": "Processing your order...",
        "sw": "Tunashughulikia order yako...",
    },
    "order_submitted": {
        "en": "Order submitted to the system!",
        "sw": "Order imetumwa kwenye mfumo!",
    },
    "order_pending_review": {
        "en": "Your order is pending review.",
        "sw": "Order yako inasubiri ukaguzi.",
    },

    # Error messages
    "error_general": {
        "en": "Sorry, there was an error processing your order. Please try again.",
        "sw": "Samahani, kulikuwa na hitilafu katika kushughulikia order yako. Tafadhali jaribu tena.",
    },
    "product_not_found": {
        "en": "Sorry, I couldn't find the product",
        "sw": "Samahani, sikupata bidhaa",
    },
    "out_of_stock": {
        "en": "Sorry, this item is currently out of stock",
        "sw": "Samahani, bidhaa hii haipo kwa sasa",
    },

    # Greeting/closing
    "greeting": {
        "en": "Hello! How can I help you with your order today?",
        "sw": "Habari! Ninawezaje kukusaidia na order yako leo?",
    },
    "goodbye": {
        "en": "Thank you for your order! Have a great day.",
        "sw": "Asante kwa order yako! Siku njema.",
    },

    # Common phrases
    "please_confirm": {
        "en": "Please confirm this is correct.",
        "sw": "Tafadhali thibitisha hii ni sahihi.",
    },
    "anything_else": {
        "en": "Is there anything else you'd like to add?",
        "sw": "Kuna kitu kingine ungependa kuongeza?",
    },
    "the_usual": {
        "en": "I've added your usual order items.",
        "sw": "Nimeongeza vitu vya order yako ya kawaida.",
    },
}

# Confirmation template
CONFIRMATION_TEMPLATE = {
    "en": """Thank you for your order, {customer_name}!

Here's what I understood:

{items_list}

{delivery_info}
{clarification_section}
{closing}""",

    "sw": """Asante kwa order yako, {customer_name}!

Hii ndio nilivyoelewa:

{items_list}

{delivery_info}
{clarification_section}
{closing}""",
}

# Clarification template
CLARIFICATION_TEMPLATE = {
    "en": """I need some clarification on your order:

{clarification_items}

Please reply with the details so I can process your order.""",

    "sw": """Ninahitaji ufafanuzi kuhusu order yako:

{clarification_items}

Tafadhali jibu na maelezo ili niweze kushughulikia order yako.""",
}


def get_message(key: str, language: str = "en", **kwargs) -> str:
    """
    Get a localized message by key.

    Args:
        key: Message key
        language: Language code ('en' or 'sw')
        **kwargs: Format arguments

    Returns:
        Localized message string
    """
    if key not in MESSAGES:
        return key

    lang = language if language in SUPPORTED_LANGUAGES else "en"
    message = MESSAGES[key].get(lang, MESSAGES[key].get("en", key))

    if kwargs:
        try:
            return message.format(**kwargs)
        except KeyError:
            return message

    return message


def get_confirmation_template(language: str = "en") -> str:
    """Get the confirmation message template for a language."""
    lang = language if language in SUPPORTED_LANGUAGES else "en"
    return CONFIRMATION_TEMPLATE.get(lang, CONFIRMATION_TEMPLATE["en"])


def get_clarification_template(language: str = "en") -> str:
    """Get the clarification message template for a language."""
    lang = language if language in SUPPORTED_LANGUAGES else "en"
    return CLARIFICATION_TEMPLATE.get(lang, CLARIFICATION_TEMPLATE["en"])


def format_items_list(items: list, language: str = "en") -> str:
    """
    Format a list of items for display.

    Args:
        items: List of item dicts with product_name, quantity, unit
        language: Language code

    Returns:
        Formatted string of items
    """
    lines = []
    for item in items:
        qty = item.get("quantity", "?")
        unit = item.get("unit", "")
        name = item.get("product_name", "Unknown")
        lines.append(f"  - {qty} {unit} {name}")

    return "\n".join(lines)


def format_confirmation_message(
    customer_name: str,
    items: list,
    delivery_date: Optional[str] = None,
    urgency: Optional[str] = None,
    clarifications: Optional[list] = None,
    language: str = "en",
) -> str:
    """
    Format a complete confirmation message.

    Args:
        customer_name: Customer name
        items: List of order items
        delivery_date: Requested delivery date
        urgency: Delivery urgency
        clarifications: List of items needing clarification
        language: Language code

    Returns:
        Formatted confirmation message
    """
    template = get_confirmation_template(language)

    items_list = format_items_list(items, language)

    # Delivery info
    delivery_info = ""
    if delivery_date or urgency:
        delivery_label = get_message("delivery_date", language)
        if delivery_date:
            delivery_info = f"{delivery_label} {delivery_date}"
        if urgency:
            delivery_info += f" ({urgency})" if delivery_info else urgency

    # Clarification section
    clarification_section = ""
    if clarifications:
        header = get_message("clarification_needed", language)
        items = "\n".join([f"  - {c}" for c in clarifications])
        clarification_section = f"\n{header}\n{items}"

    # Closing
    closing = get_message("please_confirm", language)

    return template.format(
        customer_name=customer_name,
        items_list=items_list,
        delivery_info=delivery_info,
        clarification_section=clarification_section,
        closing=closing,
    ).strip()
