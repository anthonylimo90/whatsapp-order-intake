"""Order extraction using LLM with structured outputs."""

from __future__ import annotations
import json
from typing import Optional
from anthropic import Anthropic
from .models import ExtractedOrder, ConfidenceLevel, ExtractedItem, DetectedLanguage


EXTRACTION_SYSTEM_PROMPT = """You are an order extraction assistant for Kijani Supplies, a B2B distributor serving lodges and hotels in East Africa.

Your task is to extract structured order information from WhatsApp messages. These messages may be:
- Clearly written orders with specific quantities
- Informal messages with vague quantities ("some", "a few", "the usual")
- Voice note transcriptions with filler words and unclear speech
- Messages referencing past orders ("the same as last time")

EXTRACTION RULES:

1. CUSTOMER IDENTIFICATION:
   - Extract both contact person name AND organization name if available
   - The organization (lodge/hotel name) is the primary customer identifier
   - Common patterns: "from [Organization]", "Order for [Organization]", "- [Organization]"
   - IMPORTANT: If no personal name is given, use the organization name as customer_name
   - customer_name must NEVER be null - always provide a value

2. ITEMS:
   - Extract product name, quantity, and unit
   - Standardize units: kg, L (liters), pieces, boxes, rolls, bottles
   - For eggs, default unit is "pieces" unless "trays" specified (1 tray = 30 eggs)
   - If quantity is vague ("some", "a few"), estimate conservatively and mark LOW confidence

3. DELIVERY DATE:
   - Parse relative dates: "Friday", "tomorrow", "day after tomorrow", "Tuesday"
   - Note urgency indicators: "latest", "ASAP", "urgent"
   - If no date specified, leave as null

4. CONFIDENCE SCORING:
   - HIGH: Clear quantity, unambiguous product name, explicit details
   - MEDIUM: Minor ambiguity (e.g., "probably 30", brand not specified)
   - LOW: Vague quantity, unclear product reference, transcription issues

5. AMBIGUOUS REFERENCES:
   - "the usual", "same as last time", "that thing" → Mark as LOW confidence, note in clarification_needed
   - Unknown product names → Include as-is, mark MEDIUM confidence
   - Brand preferences mentioned → Include in notes

6. LANGUAGE SUPPORT:
   - Messages may be in English, Swahili, or mixed (code-switching)
   - Extract data regardless of language
   - Common Swahili terms:
     * "tunahitaji" = "we need"
     * "tafadhali" = "please"
     * "kesho" = "tomorrow"
     * "asubuhi" = "morning"
     * "mchele" = "rice"
     * "sukari" = "sugar"
     * "mafuta" = "oil"
     * "mayai" = "eggs"
     * "maziwa" = "milk"
     * "mkate" = "bread"
   - Detect the primary language used and include it in your response
   - Generate any clarification questions in the same language as the input

7. OVERALL CONFIDENCE:
   - HIGH: All items HIGH confidence, customer clearly identified
   - MEDIUM: Some items MEDIUM confidence, or minor clarifications needed
   - LOW: Any item LOW confidence, or critical info missing

Always set requires_clarification=true if ANY item needs follow-up."""


def create_extraction_prompt(message: str, order_history_context: str = "") -> str:
    """Create the extraction prompt for a WhatsApp message."""
    history_section = ""
    if order_history_context:
        history_section = f"""
{order_history_context}

"""

    return f"""{history_section}Extract the order information from this WhatsApp message:

<message>
{message}
</message>

Return a JSON object with this exact structure:
{{
    "customer_name": "string - contact person name (REQUIRED - use organization name if no person named)",
    "customer_organization": "string or null - lodge/hotel name",
    "items": [
        {{
            "product_name": "string",
            "quantity": number,
            "unit": "string",
            "confidence": "high" | "medium" | "low",
            "original_text": "string - the part of message this came from",
            "notes": "string or null - any ambiguity"
        }}
    ],
    "requested_delivery_date": "string or null",
    "delivery_urgency": "string or null",
    "overall_confidence": "high" | "medium" | "low",
    "requires_clarification": boolean,
    "clarification_needed": ["string"] - list of things needing follow-up,
    "detected_language": "english" | "swahili" | "mixed" - primary language detected,
    "raw_message": "string - copy of original message"
}}"""


class OrderExtractor:
    """Extracts structured order data from WhatsApp messages using Claude."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the extractor with Anthropic client."""
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()

    def extract(self, message: str, order_history_context: str = "") -> ExtractedOrder:
        """
        Extract order information from a WhatsApp message.

        Args:
            message: The raw WhatsApp message text
            order_history_context: Optional context about customer's order history

        Returns:
            ExtractedOrder with structured data and confidence scores
        """
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": create_extraction_prompt(message, order_history_context)}
            ],
        )

        # Parse the response
        response_text = response.content[0].text

        # Extract JSON from response (handle potential markdown wrapping)
        json_str = response_text
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0]

        data = json.loads(json_str.strip())

        # Handle customer_name fallback - use organization if name is null
        customer_name = data.get("customer_name")
        customer_org = data.get("customer_organization")
        if not customer_name:
            customer_name = customer_org or "Unknown Customer"

        # Convert to Pydantic model
        items = [
            ExtractedItem(
                product_name=item["product_name"],
                quantity=item["quantity"],
                unit=item["unit"],
                confidence=ConfidenceLevel(item["confidence"]),
                original_text=item["original_text"],
                notes=item.get("notes"),
            )
            for item in data["items"]
        ]

        # Parse detected language (default to English if not provided)
        detected_lang = data.get("detected_language", "english")
        try:
            detected_language = DetectedLanguage(detected_lang)
        except ValueError:
            detected_language = DetectedLanguage.ENGLISH

        return ExtractedOrder(
            customer_name=customer_name,
            customer_organization=customer_org,
            items=items,
            requested_delivery_date=data.get("requested_delivery_date"),
            delivery_urgency=data.get("delivery_urgency"),
            overall_confidence=ConfidenceLevel(data["overall_confidence"]),
            requires_clarification=data["requires_clarification"],
            clarification_needed=data.get("clarification_needed", []),
            detected_language=detected_language,
            raw_message=message,
        )
