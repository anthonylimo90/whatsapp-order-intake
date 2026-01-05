# WhatsApp Order Intake Automation

AI-powered order extraction prototype for Kijani Supplies - a B2B distributor serving lodges and hotels in East Africa.

## Overview

This prototype demonstrates automated extraction of structured order data from informal WhatsApp messages. It handles:
- Clear, well-formatted orders
- Ambiguous product references ("the usual soap")
- Voice note transcriptions with filler words
- Multi-item orders with mixed formats

## Quick Start

### Prerequisites
- Python 3.9+
- Anthropic API key

### Installation

```bash
# Clone/download the repository
cd whatsapp-order-intake

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip3 install -r requirements.txt

# Set your API key (copy .env.example and add your key)
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Running the Demo

```bash
# Interactive demo mode
python3 main.py

# Process a single message
python3 main.py --message "Hi, this is Mary from Saruni Mara. We need 50kg rice for Friday."

# Run all sample messages
python3 main.py --test

# Get JSON output
python3 main.py --message "Order for 50kg rice" --json
```

## Project Structure

```
├── main.py                 # CLI interface and demo runner
├── src/
│   ├── models.py           # Pydantic data models
│   ├── extractor.py        # LLM-based order extraction
│   ├── confirmation.py     # Confirmation message generation
│   ├── erp_payload.py      # ERP payload builder
│   └── processor.py        # Main processing pipeline
├── tests/
│   └── test_extraction.py  # Unit and integration tests
├── SOLUTION_DESIGN.md      # Solution design document
└── requirements.txt
```

## Architecture

```
WhatsApp Message
       │
       ▼
┌─────────────────┐
│  OrderExtractor │ ── Uses Claude API for structured extraction
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ExtractedOrder │ ── Pydantic model with confidence scores
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌──────────────┐
│ ERP   │ │ Confirmation │
│Payload│ │ Generator    │
└───────┘ └──────────────┘
```

## Key Features

### 1. Structured Output Parsing
- Uses Pydantic models for type-safe extraction
- JSON schema enforcement in prompts
- Validation at every stage

### 2. Confidence Scoring
Each extracted field has a confidence level:
- **HIGH**: Clear quantity and product name
- **MEDIUM**: Minor ambiguity (e.g., "probably 30")
- **LOW**: Vague references ("the usual", "some")

Orders with low confidence are flagged for human review.

### 3. Edge Case Handling
- **Ambiguous items**: Flagged with `requires_clarification=true`
- **Missing info**: Null fields with clarification prompts
- **Voice transcription**: Tolerant parsing of filler words
- **Relative dates**: "Friday", "tomorrow", "day after" → normalized

### 4. Modular Design
- `extractor.py`: LLM interaction isolated
- `erp_payload.py`: ERP format conversion (no LLM)
- `confirmation.py`: Both LLM and template-based options
- Easy to swap LLM providers or add new output formats

## Sample Output

**Input:**
```
Need 5 boxes of the usual soap and some flour. Also that cleaning
stuff we got last time. Can you deliver Tuesday? - Kilima Safari Lodge
```

**Extracted Order:**
```json
{
  "customer_name": "Kilima Safari Lodge",
  "customer_organization": "Kilima Safari Lodge",
  "items": [
    {
      "product_name": "Soap",
      "quantity": 5,
      "unit": "boxes",
      "confidence": "low",
      "notes": "Referenced as 'the usual soap' - brand/type unclear"
    },
    {
      "product_name": "Flour",
      "quantity": 1,
      "unit": "bag",
      "confidence": "low",
      "notes": "Quantity vague ('some')"
    },
    {
      "product_name": "Cleaning supplies",
      "quantity": 1,
      "unit": "order",
      "confidence": "low",
      "notes": "Referenced as 'that cleaning stuff we got last time'"
    }
  ],
  "requested_delivery_date": "Tuesday",
  "overall_confidence": "low",
  "requires_clarification": true
}
```

## Running Tests

```bash
# Unit tests only (no API calls)
python3 -m pytest tests/ -v

# Include integration tests (requires API key)
python3 -m pytest tests/ -v -m integration
```

## Configuration

The prototype loads environment variables from a `.env` file:

```bash
# .env
ANTHROPIC_API_KEY=your-api-key-here
```

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key | Required |

## Extending the Prototype

### Adding a New LLM Provider
1. Create a new extractor class implementing the same interface
2. Swap in `processor.py`

### Connecting to Odoo
The `ERPOrderPayload` model is designed for Odoo integration:
```python
# In production, add to erp_payload.py:
def submit_to_odoo(payload: ERPOrderPayload, odoo_client):
    # Map product names to SKUs
    # Apply customer pricing tier
    # Create sales order via XML-RPC
    pass
```

### Adding WhatsApp Integration
```python
# Webhook handler (FastAPI example)
@app.post("/webhook/whatsapp")
async def handle_whatsapp(request: Request):
    data = await request.json()
    message = extract_message_text(data)
    result = processor.process(message)
    await send_whatsapp_reply(data["from"], result.confirmation_message)
```

## Limitations

1. **No product catalog lookup**: Real system would validate against Odoo products
2. **No customer verification**: Would need phone→customer ID mapping
3. **No stock checking**: Would integrate with Odoo inventory
4. **Single language**: Tested primarily with English; Swahili needs testing
5. **No image/audio handling**: Text only in this prototype

## Future Improvements

- [ ] Product catalog fuzzy matching
- [ ] Customer order history for "the usual" resolution
- [ ] Multi-language support (Swahili)
- [ ] Voice note transcription integration
- [ ] Real-time stock availability check
- [ ] Pricing tier application

---

## License

MIT License - Built for PEV Studio AI Engineer Assessment
