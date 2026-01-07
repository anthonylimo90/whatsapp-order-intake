"""Confirmation message generation."""

from __future__ import annotations
from typing import Optional
from anthropic import Anthropic
from .models import ExtractedOrder, ConfidenceLevel, DetectedLanguage


CONFIRMATION_SYSTEM_PROMPT = """You are a friendly customer service assistant for Kijani Supplies, a B2B distributor serving lodges and hotels in East Africa.

Generate WhatsApp confirmation messages that are:
- Warm but professional
- Concise (customers are busy)
- Clear about what was ordered
- Explicit about delivery date
- Include any clarification requests naturally

Format guidelines:
- Use simple formatting (WhatsApp supports *bold* and _italic_)
- Keep messages under 500 characters when possible
- List items clearly
- End with a way to make changes or ask questions

LANGUAGE: You MUST respond in the same language the customer used.
- If the customer wrote in Swahili, respond in Swahili
- If the customer wrote in English, respond in English
- If the customer used mixed languages, respond in the dominant language

Common Swahili phrases for confirmations:
- "Asante sana" = Thank you very much
- "Oda yako" = Your order
- "Tutawasilisha" = We will deliver
- "Tafadhali jibu" = Please reply
- "Swali" = Question

If clarification is needed:
- Politely ask for the specific missing information
- Suggest options when possible
- Don't make assumptions about vague items"""


class ConfirmationGenerator:
    """Generates customer-facing confirmation messages."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with Anthropic client."""
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()

    def generate(self, order: ExtractedOrder) -> str:
        """
        Generate a confirmation message for an extracted order.

        Args:
            order: The extracted order data

        Returns:
            WhatsApp-formatted confirmation message
        """
        # Build context for the LLM
        items_summary = "\n".join(
            f"- {item.product_name}: {item.quantity} {item.unit}"
            + (f" (needs clarification: {item.notes})" if item.confidence == ConfidenceLevel.LOW else "")
            for item in order.items
        )

        # Get detected language (default to English)
        language = getattr(order, 'detected_language', DetectedLanguage.ENGLISH)
        if isinstance(language, DetectedLanguage):
            language_str = language.value
        else:
            language_str = str(language)

        prompt = f"""Generate a WhatsApp confirmation message for this order:

Customer: {order.customer_name}
Organization: {order.customer_organization or 'Not specified'}
Delivery: {order.requested_delivery_date or 'Not specified'} {f'({order.delivery_urgency})' if order.delivery_urgency else ''}

Items:
{items_summary}

Needs clarification: {order.requires_clarification}
Clarification items: {', '.join(order.clarification_needed) if order.clarification_needed else 'None'}

IMPORTANT: The customer's message was in {language_str.upper()}. You MUST respond in {language_str.upper()}.

Generate a confirmation message. If clarification is needed, ask for it naturally in the message."""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=CONFIRMATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    def generate_simple(self, order: ExtractedOrder) -> str:
        """
        Generate a simple template-based confirmation (no LLM call).

        Useful for high-confidence orders or when minimizing API calls.

        Args:
            order: The extracted order data

        Returns:
            Simple confirmation message
        """
        customer = order.customer_organization or order.customer_name
        items_list = "\n".join(
            f"  - {item.product_name}: {item.quantity} {item.unit}"
            for item in order.items
        )

        delivery = order.requested_delivery_date or "to be confirmed"

        # Get detected language
        language = getattr(order, 'detected_language', DetectedLanguage.ENGLISH)

        # Generate message based on language
        if language == DetectedLanguage.SWAHILI:
            delivery_sw = delivery if delivery != "to be confirmed" else "itahibitishwa"
            message = f"""Habari {order.customer_name}!

Asante sana kwa oda yako kutoka *{customer}*.

*Muhtasari wa Oda:*
{items_list}

*Uwasilishaji:* {delivery_sw}

Tutahibitisha upatikanaji na kuwasiliana nawe hivi karibuni. Jibu ujumbe huu ikiwa unahitaji kufanya mabadiliko yoyote.

- Timu ya Kijani Supplies"""

            if order.requires_clarification and order.clarification_needed:
                clarifications = "\n".join(f"  - {c}" for c in order.clarification_needed)
                message += f"""

*Swali:*
Tunahitaji maelezo zaidi kuhusu:
{clarifications}

Tafadhali jibu na maelezo ili tukamilishe oda yako."""

        else:
            # English (default)
            message = f"""Hi {order.customer_name}!

Thank you for your order from *{customer}*.

*Order Summary:*
{items_list}

*Delivery:* {delivery}

We'll confirm availability and get back to you shortly. Reply to this message if you need to make any changes.

- Kijani Supplies Team"""

            if order.requires_clarification and order.clarification_needed:
                clarifications = "\n".join(f"  - {c}" for c in order.clarification_needed)
                message += f"""

*Quick question:*
We need a bit more info on:
{clarifications}

Please reply with details so we can complete your order."""

        return message
