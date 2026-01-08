"""Service for managing cumulative order state."""

from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db.models import CumulativeOrderState, OrderSnapshot, CumulativeOrderItem, Message
from ..models import ExtractedOrder, ExtractedItem
from .product_matching import ProductMatchingService


class OrderStateManager:
    """Manages cumulative order state and item merging."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.matcher = ProductMatchingService(session)

    async def get_or_create_state(self, conversation_id: int) -> CumulativeOrderState:
        """Get existing cumulative state or create new one."""
        query = select(CumulativeOrderState).where(
            CumulativeOrderState.conversation_id == conversation_id
        )
        result = await self.session.execute(query)
        state = result.scalar_one_or_none()

        if not state:
            state = CumulativeOrderState(
                conversation_id=conversation_id,
                items_json={"items": []},
                version=0,
            )
            self.session.add(state)
            await self.session.flush()

        return state

    def normalize_product_name(self, name: str) -> str:
        """Normalize product name for matching using enhanced matcher."""
        return self.matcher.normalize(name)

    def find_matching_item(
        self,
        new_item: ExtractedItem,
        existing_items: List[Dict[str, Any]],
    ) -> Tuple[Optional[Dict[str, Any]], float]:
        """
        Find matching item using enhanced fuzzy matching.

        Returns (matched_item, confidence_score).
        Uses ProductMatchingService for:
        - Alias lookup
        - Levenshtein distance
        - Combined scoring (SequenceMatcher + Levenshtein + Jaccard)
        """
        new_normalized = self.normalize_product_name(new_item.product_name)

        # First check if new item matches a known alias
        alias_match = self.matcher.find_alias(new_item.product_name)
        if alias_match:
            new_normalized = alias_match

        best_match = None
        best_score = 0.0

        # Get list of existing product names for fuzzy matching
        existing_names = [
            item.get("product_name", "") for item in existing_items
            if item.get("is_active", True)
        ]

        for item in existing_items:
            if not item.get("is_active", True):
                continue

            existing_normalized = item.get("normalized_name") or self.normalize_product_name(
                item.get("product_name", "")
            )

            # Check if existing item has an alias mapping
            existing_alias = self.matcher.find_alias(item.get("product_name", ""))
            if existing_alias:
                existing_normalized = existing_alias

            # Exact match (including after alias resolution)
            if new_normalized == existing_normalized:
                return item, 1.0

            # Use the enhanced fuzzy matcher
            match_result = self.matcher.match_sync(
                new_item.product_name,
                candidates=[item.get("product_name", "")],
                min_confidence=0.5
            )

            if match_result and match_result.confidence > best_score:
                best_match = item
                best_score = match_result.confidence

        return best_match, best_score

    async def merge_extraction(
        self,
        state: CumulativeOrderState,
        extraction: ExtractedOrder,
        message_id: int,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Merge new extraction into cumulative state.

        Returns dict with changes: {added: [], modified: [], unchanged: []}
        """
        existing_items = state.items_json.get("items", [])
        changes: Dict[str, List[Dict[str, Any]]] = {
            "added": [],
            "modified": [],
            "unchanged": [],
        }

        # Track which existing items were matched
        matched_indices = set()

        for new_item in extraction.items:
            match, confidence = self.find_matching_item(new_item, existing_items)

            if match and confidence >= 0.7:
                # Update existing item
                idx = existing_items.index(match)
                matched_indices.add(idx)

                old_qty = match.get("quantity")
                old_unit = match.get("unit")

                # Update the item
                match["quantity"] = new_item.quantity
                match["unit"] = new_item.unit
                match["confidence"] = new_item.confidence.value
                match["last_modified_message_id"] = message_id
                match["modification_count"] = match.get("modification_count", 0) + 1
                if new_item.notes:
                    match["notes"] = new_item.notes

                changes["modified"].append({
                    "product_name": match["product_name"],
                    "old_quantity": old_qty,
                    "new_quantity": new_item.quantity,
                    "old_unit": old_unit,
                    "unit": new_item.unit,
                })
            else:
                # Add new item
                new_entry = {
                    "product_name": new_item.product_name,
                    "normalized_name": self.normalize_product_name(new_item.product_name),
                    "quantity": new_item.quantity,
                    "unit": new_item.unit,
                    "confidence": new_item.confidence.value,
                    "original_text": new_item.original_text,
                    "notes": new_item.notes,
                    "first_mentioned_message_id": message_id,
                    "last_modified_message_id": message_id,
                    "modification_count": 0,
                    "is_active": True,
                }
                existing_items.append(new_entry)
                changes["added"].append(new_entry)

        # Mark unchanged items
        for idx, item in enumerate(existing_items):
            if idx not in matched_indices and item not in changes["added"]:
                if item.get("is_active", True):
                    changes["unchanged"].append({
                        "product_name": item.get("product_name"),
                        "quantity": item.get("quantity"),
                        "unit": item.get("unit"),
                    })

        # Update state
        state.items_json = {"items": existing_items}
        state.version += 1
        state.customer_name = extraction.customer_name or state.customer_name
        state.customer_organization = extraction.customer_organization or state.customer_organization
        state.delivery_date = extraction.requested_delivery_date or state.delivery_date
        state.urgency = extraction.delivery_urgency or state.urgency
        state.overall_confidence = extraction.overall_confidence.value
        state.requires_clarification = extraction.requires_clarification
        state.pending_clarifications = extraction.clarification_needed or []

        return changes

    async def create_snapshot(
        self,
        state: CumulativeOrderState,
        message_id: int,
        changes: Dict[str, List[Dict[str, Any]]],
        extraction: ExtractedOrder,
    ) -> OrderSnapshot:
        """Create a snapshot of current state."""
        snapshot = OrderSnapshot(
            cumulative_state_id=state.id,
            message_id=message_id,
            items_json=state.items_json,
            changes_json=changes,
            version=state.version,
            extraction_confidence=extraction.overall_confidence.value,
            requires_clarification=extraction.requires_clarification,
            clarification_items=extraction.clarification_needed,
        )
        self.session.add(snapshot)
        return snapshot

    def build_full_context(
        self,
        messages: List[Message],
        state: CumulativeOrderState,
    ) -> str:
        """Build full conversation context for LLM."""
        context_parts = []

        # Add current cumulative state
        items = state.items_json.get("items", [])
        if items:
            context_parts.append("CURRENT ORDER STATE:")
            for item in items:
                if item.get("is_active", True):
                    qty = item.get("quantity", "?")
                    unit = item.get("unit", "")
                    name = item.get("product_name", "unknown")
                    context_parts.append(f"  - {name}: {qty} {unit}")
            context_parts.append("")

        # Add customer info if available
        if state.customer_name or state.customer_organization:
            context_parts.append("CUSTOMER INFO:")
            if state.customer_name:
                context_parts.append(f"  Name: {state.customer_name}")
            if state.customer_organization:
                context_parts.append(f"  Organization: {state.customer_organization}")
            context_parts.append("")

        # Add delivery info if available
        if state.delivery_date or state.urgency:
            context_parts.append("DELIVERY INFO:")
            if state.delivery_date:
                context_parts.append(f"  Date: {state.delivery_date}")
            if state.urgency:
                context_parts.append(f"  Urgency: {state.urgency}")
            context_parts.append("")

        # Add all customer messages chronologically
        context_parts.append("CONVERSATION HISTORY:")
        for msg in messages:
            if msg.role == "customer":
                msg_type = "Clarification" if msg.message_type == "clarification" else "Order"
                context_parts.append(f"[{msg_type}]: {msg.content}")

        return "\n".join(context_parts)

    async def get_state_with_snapshots(
        self,
        conversation_id: int,
    ) -> Optional[CumulativeOrderState]:
        """Get cumulative state with all snapshots loaded."""
        from sqlalchemy.orm import selectinload

        query = (
            select(CumulativeOrderState)
            .options(selectinload(CumulativeOrderState.snapshots))
            .where(CumulativeOrderState.conversation_id == conversation_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
