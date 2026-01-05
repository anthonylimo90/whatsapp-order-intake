#!/usr/bin/env python3
"""
WhatsApp Order Intake Automation - CLI Interface

Usage:
    python3 main.py                    # Run interactive demo
    python3 main.py --message "..."    # Process a single message
    python3 main.py --test             # Run all sample messages
"""

import argparse
import json
from dotenv import load_dotenv
from src.processor import OrderProcessor

# Load environment variables from .env file
load_dotenv()


# Sample messages from the assessment
SAMPLE_MESSAGES = {
    "clear_order": {
        "name": "Message 1: Clear Order",
        "message": "Hi, this is Mary from Saruni Mara. We need 50kg rice, 20kg sugar, 10L cooking oil, and 30 eggs for Friday delivery. Thanks!",
    },
    "ambiguous_items": {
        "name": "Message 2: Ambiguous Items",
        "message": 'Need 5 boxes of the usual soap and some flour. Also that cleaning stuff we got last time. Can you deliver Tuesday? - Kilima Safari Lodge',
    },
    "multiple_items": {
        "name": "Message 3: Multiple Items, Informal",
        "message": """Order for Angama Mara:
- Tomatoes 30kg
- Onions 20kg
- Potatoes 50kg
- Carrots 15kg
- Green beans 10kg
Also 100 rolls toilet paper and hand sanitizer (big bottles x 20)
Need by Thursday latest""",
    },
    "voice_transcription": {
        "name": "Message 4: Voice Note Transcription (Messy)",
        "message": "hey its peter from governors camp um we're running low on a few things let me see uh we need milk like maybe 40 liters the fresh one not UHT and bread probably 30 loaves and um what else oh yeah butter like 5 kilos and cheese the cheddar one maybe 3 kilos can you do tomorrow or day after thanks",
    },
}


def print_divider(char="=", length=60):
    print(char * length)


def print_result(result, show_json=True):
    """Pretty print a processing result."""
    if not result.success:
        print(f"\n❌ Processing failed: {result.error}")
        return

    order = result.extracted_order
    erp = result.erp_payload

    print("\n📋 EXTRACTED ORDER")
    print_divider("-")
    print(f"Customer: {order.customer_name}")
    if order.customer_organization:
        print(f"Organization: {order.customer_organization}")
    print(f"Delivery: {order.requested_delivery_date or 'Not specified'}", end="")
    if order.delivery_urgency:
        print(f" ({order.delivery_urgency})")
    else:
        print()
    print(f"Overall Confidence: {order.overall_confidence.value.upper()}")
    print(f"Requires Clarification: {'Yes' if order.requires_clarification else 'No'}")

    print("\n📦 ITEMS")
    print_divider("-")
    for item in order.items:
        conf_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}[item.confidence.value]
        print(f"  {conf_icon} {item.product_name}: {item.quantity} {item.unit}")
        if item.notes:
            print(f"     ⚠️  {item.notes}")

    if order.clarification_needed:
        print("\n⚠️  CLARIFICATION NEEDED")
        print_divider("-")
        for item in order.clarification_needed:
            print(f"  • {item}")

    if show_json:
        print("\n📤 ERP PAYLOAD (JSON)")
        print_divider("-")
        print(json.dumps(erp.model_dump(), indent=2))

    print("\n💬 CONFIRMATION MESSAGE")
    print_divider("-")
    print(result.confirmation_message)


def run_interactive():
    """Run interactive demo mode."""
    print("\n" + "=" * 60)
    print("  WhatsApp Order Intake Automation - Demo")
    print("  Kijani Supplies B2B Order Processing")
    print("=" * 60)

    processor = OrderProcessor()

    while True:
        print("\nSelect an option:")
        print("  1. Process sample message 1 (Clear Order)")
        print("  2. Process sample message 2 (Ambiguous Items)")
        print("  3. Process sample message 3 (Multiple Items)")
        print("  4. Process sample message 4 (Voice Transcription)")
        print("  5. Enter custom message")
        print("  6. Run all samples")
        print("  q. Quit")

        choice = input("\nChoice: ").strip().lower()

        if choice == "q":
            print("\nGoodbye!")
            break
        elif choice == "1":
            process_sample(processor, "clear_order")
        elif choice == "2":
            process_sample(processor, "ambiguous_items")
        elif choice == "3":
            process_sample(processor, "multiple_items")
        elif choice == "4":
            process_sample(processor, "voice_transcription")
        elif choice == "5":
            print("\nEnter your WhatsApp message (press Enter twice to submit):")
            lines = []
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
            if lines:
                message = "\n".join(lines)
                print("\nProcessing...")
                result = processor.process(message)
                print_result(result)
        elif choice == "6":
            run_all_samples(processor)
        else:
            print("Invalid choice, please try again.")


def process_sample(processor, sample_key):
    """Process a specific sample message."""
    sample = SAMPLE_MESSAGES[sample_key]
    print(f"\n{'=' * 60}")
    print(f"  {sample['name']}")
    print("=" * 60)
    print(f"\n📱 INPUT MESSAGE:\n{sample['message']}")
    print("\nProcessing...")
    result = processor.process(sample["message"])
    print_result(result)


def run_all_samples(processor):
    """Run all sample messages."""
    for key in SAMPLE_MESSAGES:
        process_sample(processor, key)
        print("\n" + "=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="WhatsApp Order Intake Automation Prototype"
    )
    parser.add_argument(
        "--message", "-m", type=str, help="Process a single message"
    )
    parser.add_argument(
        "--test", "-t", action="store_true", help="Run all sample messages"
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output JSON only"
    )

    args = parser.parse_args()

    processor = OrderProcessor()

    if args.message:
        result = processor.process(args.message)
        if args.json:
            print(json.dumps({
                "extracted_order": result.extracted_order.model_dump() if result.extracted_order else None,
                "erp_payload": result.erp_payload.model_dump() if result.erp_payload else None,
                "confirmation_message": result.confirmation_message,
                "success": result.success,
                "error": result.error,
            }, indent=2))
        else:
            print_result(result)
    elif args.test:
        run_all_samples(processor)
    else:
        run_interactive()


if __name__ == "__main__":
    main()
