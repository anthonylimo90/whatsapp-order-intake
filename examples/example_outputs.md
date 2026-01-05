# Example Outputs

These are **actual outputs** from running the prototype with Claude API.

---

## Message 1: Clear Order

**Input:**
```
Hi, this is Mary from Saruni Mara. We need 50kg rice, 20kg sugar, 10L cooking oil, and 30 eggs for Friday delivery. Thanks!
```

**Result:** HIGH confidence, auto-processable

**Extracted Order:**
```json
{
  "customer_name": "Mary",
  "customer_organization": "Saruni Mara",
  "items": [
    {"product_name": "rice", "quantity": 50.0, "unit": "kg", "confidence": "high"},
    {"product_name": "sugar", "quantity": 20.0, "unit": "kg", "confidence": "high"},
    {"product_name": "cooking oil", "quantity": 10.0, "unit": "L", "confidence": "high"},
    {"product_name": "eggs", "quantity": 30.0, "unit": "pieces", "confidence": "high"}
  ],
  "requested_delivery_date": "Friday",
  "overall_confidence": "high",
  "requires_clarification": false
}
```

**ERP Payload:**
```json
{
  "customer_identifier": "Saruni Mara",
  "confidence_score": 0.95,
  "requires_review": false
}
```

**Confirmation Message:**
```
Hi Mary!

*Order confirmed* for Saruni Mara:

• 50kg rice
• 20kg sugar
• 10L cooking oil
• 30 eggs

*Delivery:* This Friday

Your order is being prepared and will arrive as scheduled.
```

---

## Message 2: Ambiguous Items

**Input:**
```
Need 5 boxes of the usual soap and some flour. Also that cleaning stuff we got last time. Can you deliver Tuesday? - Kilima Safari Lodge
```

**Result:** LOW confidence, requires human review

**Extracted Order:**
```json
{
  "customer_name": "Kilima Safari Lodge",
  "customer_organization": "Kilima Safari Lodge",
  "items": [
    {
      "product_name": "soap",
      "quantity": 5.0,
      "unit": "boxes",
      "confidence": "low",
      "notes": "Refers to 'the usual soap' - specific type/brand unclear"
    },
    {
      "product_name": "flour",
      "quantity": 1.0,
      "unit": "kg",
      "confidence": "low",
      "notes": "Vague quantity 'some' - estimated 1kg conservatively"
    },
    {
      "product_name": "cleaning stuff",
      "quantity": 1.0,
      "unit": "pieces",
      "confidence": "low",
      "notes": "Very vague reference to previous order - product unknown"
    }
  ],
  "requested_delivery_date": "Tuesday",
  "overall_confidence": "low",
  "requires_clarification": true,
  "clarification_needed": [
    "What specific type/brand of soap is 'the usual soap'?",
    "What quantity and unit of flour needed?",
    "What specific cleaning products from the previous order?",
    "What quantity of cleaning products needed?"
  ]
}
```

**ERP Payload:**
```json
{
  "customer_identifier": "Kilima Safari Lodge",
  "confidence_score": 0.5,
  "requires_review": true
}
```

**Confirmation Message:**
```
Hi Kilima Safari Lodge!

Thanks for your order for *Tuesday delivery*. I have:
• Soap - 5 boxes
• Flour - 1kg
• Cleaning products - 1 piece

I need a few quick details to confirm:

🧼 Which soap brand/type is your "usual"?
🌾 How much flour exactly do you need?
🧽 Which specific cleaning products from your previous order, and how many?

Please clarify so I can get your order exactly right!
```

---

## Message 3: Multiple Items, Informal

**Input:**
```
Order for Angama Mara:
- Tomatoes 30kg
- Onions 20kg
- Potatoes 50kg
- Carrots 15kg
- Green beans 10kg
Also 100 rolls toilet paper and hand sanitizer (big bottles x 20)
Need by Thursday latest
```

**Result:** MEDIUM confidence (one ambiguous item)

**Extracted Order:**
```json
{
  "customer_name": "Angama Mara",
  "customer_organization": "Angama Mara",
  "items": [
    {"product_name": "Tomatoes", "quantity": 30.0, "unit": "kg", "confidence": "high"},
    {"product_name": "Onions", "quantity": 20.0, "unit": "kg", "confidence": "high"},
    {"product_name": "Potatoes", "quantity": 50.0, "unit": "kg", "confidence": "high"},
    {"product_name": "Carrots", "quantity": 15.0, "unit": "kg", "confidence": "high"},
    {"product_name": "Green beans", "quantity": 10.0, "unit": "kg", "confidence": "high"},
    {"product_name": "Toilet paper", "quantity": 100.0, "unit": "rolls", "confidence": "high"},
    {
      "product_name": "Hand sanitizer",
      "quantity": 20.0,
      "unit": "bottles",
      "confidence": "medium",
      "notes": "Size specified as 'big bottles' but exact volume not provided"
    }
  ],
  "requested_delivery_date": "Thursday",
  "delivery_urgency": "latest",
  "overall_confidence": "medium",
  "requires_clarification": true,
  "clarification_needed": ["Hand sanitizer bottle size/volume needs specification"]
}
```

**ERP Payload:**
```json
{
  "customer_identifier": "Angama Mara",
  "confidence_score": 0.75,
  "requires_review": true,
  "notes": "Urgency: latest; Needs clarification: Hand sanitizer bottle size/volume"
}
```

**Confirmation Message:**
```
Hi Angama Mara!

*Order Confirmation:*
• Tomatoes: 30kg
• Onions: 20kg
• Potatoes: 50kg
• Carrots: 15kg
• Green beans: 10kg
• Toilet paper: 100 rolls
• Hand sanitizer: 20 bottles

*Delivery:* Thursday (latest)

Quick question - what size bottles do you need for the hand sanitizer?
We have 250ml, 500ml, and 1L options available.
```

---

## Message 4: Voice Note Transcription (Messy)

**Input:**
```
hey its peter from governors camp um we're running low on a few things let me see uh we need milk like maybe 40 liters the fresh one not UHT and bread probably 30 loaves and um what else oh yeah butter like 5 kilos and cheese the cheddar one maybe 3 kilos can you do tomorrow or day after thanks
```

**Result:** MEDIUM confidence (approximate quantities)

**Extracted Order:**
```json
{
  "customer_name": "Peter",
  "customer_organization": "Governors Camp",
  "items": [
    {
      "product_name": "Fresh Milk",
      "quantity": 40.0,
      "unit": "L",
      "confidence": "medium",
      "notes": "Specifically requested fresh milk, not UHT"
    },
    {
      "product_name": "Bread",
      "quantity": 30.0,
      "unit": "loaves",
      "confidence": "medium",
      "notes": "Quantity expressed as 'probably 30'"
    },
    {
      "product_name": "Butter",
      "quantity": 5.0,
      "unit": "kg",
      "confidence": "medium",
      "notes": "Approximate quantity indicated by 'like 5 kilos'"
    },
    {
      "product_name": "Cheddar Cheese",
      "quantity": 3.0,
      "unit": "kg",
      "confidence": "medium",
      "notes": "Specifically cheddar cheese, approximate quantity"
    }
  ],
  "requested_delivery_date": "tomorrow or day after tomorrow",
  "overall_confidence": "medium",
  "requires_clarification": true,
  "clarification_needed": [
    "Confirm exact quantities for all items",
    "Confirm preferred delivery date - tomorrow or day after tomorrow"
  ]
}
```

**ERP Payload:**
```json
{
  "customer_identifier": "Governors Camp",
  "confidence_score": 0.75,
  "requires_review": true
}
```

**Confirmation Message:**
```
Hi Peter!

*Order Confirmation - Governors Camp*

- Fresh Milk: 40L
- Bread: 30 loaves
- Butter: 5kg
- Cheddar Cheese: 3kg

Quick clarification needed:
• Can you confirm the *exact quantities* for all items?
• Would you prefer delivery *tomorrow* or *day after tomorrow*?

Once confirmed, we'll have everything ready for you!
```

---

## Summary

| Message | Confidence | Review Required | Items | Auto-Process? |
|---------|-----------|-----------------|-------|---------------|
| 1. Clear Order | HIGH (0.95) | No | 4 | Yes |
| 2. Ambiguous Items | LOW (0.50) | Yes | 3 | No |
| 3. Multiple Items | MEDIUM (0.75) | Yes | 7 | No |
| 4. Voice Transcription | MEDIUM (0.75) | Yes | 4 | No |

### Key Observations

1. **Clear orders** are processed with HIGH confidence and can be auto-submitted to the ERP
2. **Ambiguous references** ("the usual", "some", "that stuff") are correctly flagged as LOW confidence
3. **Voice transcription filler words** (um, uh, like, maybe) are handled gracefully
4. **Partial ambiguity** (Message 3) correctly marks specific items as lower confidence while keeping others HIGH
5. **Clarification messages** are generated automatically when needed
