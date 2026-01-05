# WhatsApp Order Intake Automation - Solution Design

## 1. Workflow Analysis

### Current Workflow
1. Customer sends order via WhatsApp
2. Ops team reads message and extracts: customer name, items, quantities, delivery date
3. Ops team looks up customer in Odoo (verify account, pricing tier)
4. Ops team creates order in Odoo ERP
5. Ops team sends confirmation to customer

### Automation Opportunities

| Step | Automation Potential | Rationale |
|------|---------------------|-----------|
| Message Reception | **Full automation** | WhatsApp Business API provides webhooks |
| Data Extraction | **Full automation** | LLM excels at parsing unstructured text |
| Customer Lookup | **Full automation** | Simple API call to Odoo |
| Order Creation | **Partial automation** | Auto-create for high-confidence orders; queue for review otherwise |
| Confirmation | **Full automation** | Template-based response generation |

### What Should Stay Manual

1. **Low-confidence orders** - When extraction confidence is below threshold (e.g., ambiguous items, new customers)
2. **New customer onboarding** - First-time customers need account setup and pricing tier assignment
3. **Exception handling** - Out-of-stock items, unusual quantities, credit limit issues
4. **Escalations** - Customer complaints or complex requests embedded in orders

## 2. Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                         WhatsApp Business API                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ Webhook
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Order Processing Service                        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐  │
│  │  Message    │───▶│   Order     │───▶│   Confidence            │  │
│  │  Receiver   │    │  Extractor  │    │   Evaluator             │  │
│  └─────────────┘    │  (LLM)      │    └───────────┬─────────────┘  │
│                     └─────────────┘                │                 │
│                                          ┌────────┴────────┐        │
│                                          ▼                 ▼        │
│                                   High Confidence    Low Confidence │
│                                          │                 │        │
│                                          ▼                 ▼        │
│                                   ┌───────────┐    ┌─────────────┐  │
│                                   │ Auto-     │    │ Human       │  │
│                                   │ Process   │    │ Review Queue│  │
│                                   └─────┬─────┘    └─────────────┘  │
└─────────────────────────────────────────┼───────────────────────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    ▼                     ▼                     ▼
            ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
            │ Odoo CRM    │      │ Odoo ERP    │      │ WhatsApp    │
            │ (Customer   │      │ (Order      │      │ (Send       │
            │  Lookup)    │      │  Creation)  │      │  Confirm)   │
            └─────────────┘      └─────────────┘      └─────────────┘
```

### Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Runtime | Python 3.11+ | Ecosystem for LLM integrations, team familiarity |
| LLM | Claude 3.5 Sonnet | Excellent instruction-following, structured output support |
| Message Queue | Redis/Celery | Handle async processing, retries |
| API Framework | FastAPI | Async support, automatic OpenAPI docs |
| Validation | Pydantic | Type-safe structured outputs |
| WhatsApp | Meta Cloud API | Official API, reliable |
| ERP | Odoo XML-RPC API | Native Odoo integration |

### Data Flow

1. **Incoming Message** → WhatsApp webhook delivers message JSON
2. **Extraction** → LLM parses message into structured `OrderRequest`
3. **Enrichment** → Customer lookup adds account ID, pricing tier
4. **Validation** → Check stock, credit limits, delivery feasibility
5. **Routing** → High-confidence → auto-process; Low-confidence → human queue
6. **Execution** → Create Odoo sales order via API
7. **Confirmation** → Generate and send WhatsApp confirmation

## 3. Edge Cases & Handling

### Ambiguous Product References
**Example:** "the usual soap", "that cleaning stuff from last time"

**Handling:**
- Query customer's order history from Odoo
- Use LLM to match vague references to past orders
- If still ambiguous, flag for human review with suggestions
- Build customer-specific product alias database over time

### Missing Information
**Example:** No delivery date specified, quantity unclear

**Handling:**
- Apply sensible defaults (e.g., "next available delivery")
- Generate clarifying question in confirmation: "We'll deliver on [date]. Reply to change."
- For critical missing info (no items, no customer ID), request clarification before proceeding

### New/Unknown Customers
**Handling:**
- Check if phone number exists in Odoo
- If new: Queue for manual onboarding, send acknowledgment
- If existing but name mismatch: Use phone number as primary identifier

### Out-of-Stock Items
**Handling:**
- Real-time stock check before order creation
- If item unavailable: Include in confirmation with alternatives or ETA
- Partial orders: Process available items, flag rest for follow-up

### Unclear Quantities
**Example:** "some flour", "a few boxes"

**Handling:**
- Flag fields with low confidence scores
- Use customer's typical order quantities as reference
- Route to human review if variance is high

### Voice Note Transcription Errors
**Handling:**
- Transcription quality metadata (if available) affects confidence
- Extra tolerance for phonetically similar product names
- Lower confidence threshold triggers review

## 4. Rollout Plan

### Phase 1: Shadow Mode (Weeks 1-2)
- System processes all WhatsApp orders in parallel
- **No** orders auto-created; all go to human review
- Ops team verifies extractions and provides corrections
- Metrics: Extraction accuracy, false positive/negative rates

### Phase 2: Assisted Mode (Weeks 3-4)
- High-confidence orders (>90%) pre-fill Odoo forms
- Ops team reviews and confirms with one click
- System learns from corrections
- Metrics: Time savings, correction rate

### Phase 3: Semi-Automated (Weeks 5-8)
- Very high-confidence orders (>95%) auto-created
- Confirmation sent with "Reply CANCEL within 5 min to stop"
- Human reviews low-confidence orders
- Metrics: Auto-processing rate, error rate, customer complaints

### Phase 4: Full Automation (Week 9+)
- All high-confidence orders auto-processed
- Ops team focuses on exceptions and customer service
- Continuous monitoring and threshold adjustment

### Human-in-the-Loop Strategy

| Confidence Level | Action |
|-----------------|--------|
| >95% | Auto-process, notify ops team |
| 80-95% | Pre-fill form, require human confirmation |
| <80% | Route to human queue with extraction suggestions |

### Key Metrics to Track

- **Accuracy Rate**: % of orders processed without correction
- **Auto-Processing Rate**: % of orders handled without human intervention
- **Processing Time**: Average time from message to order creation
- **Error Rate**: % of orders with post-creation corrections
- **Customer Satisfaction**: Response time, complaint rate
- **Cost per Order**: Including API costs, human time

## 5. Expected Impact

### Quantified Benefits

| Metric | Current | Projected | Improvement |
|--------|---------|-----------|-------------|
| Processing time | 3 min/order | 30 sec/order | **85% reduction** |
| Error rate | 5% | <1% | **80% reduction** |
| Daily capacity | 50 orders | 200+ orders | **4x increase** |
| Staff time on data entry | 5 hrs/day | <1 hr/day | **80% reduction** |

### Cost Analysis (WhatsApp channel only)

**Current Cost:**
- 20 orders/day × 3 min × $0.50/min labor = $30/day
- Monthly: ~$650

**Projected Cost:**
- LLM API: ~$0.01/order × 20 = $0.20/day
- Human review (20% of orders): 4 orders × 1 min × $0.50 = $2/day
- Monthly: ~$65

**Savings: ~$585/month (90% reduction) for WhatsApp channel alone**

### Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM hallucination | Medium | High | Confidence scoring, validation against product catalog |
| Customer resistance | Low | Medium | Maintain human fallback, clear escalation path |
| API downtime | Low | High | Fallback to manual queue, retry logic |
| Data privacy concerns | Medium | High | Process data in-region, don't log full messages |

### Limitations

1. **Voice notes** - Requires reliable transcription service; quality varies
2. **Images** - Product photos need vision model; not in initial scope
3. **Complex negotiations** - Price discussions, bulk discounts need human
4. **Multi-language** - Swahili/English code-switching needs testing
5. **Product catalog sync** - Requires up-to-date Odoo product data

---

## 6. Odoo Integration Details

### API Overview

Odoo provides an External API via XML-RPC (and JSON-RPC) for programmatic access:

| Endpoint | Purpose |
|----------|---------|
| `/xmlrpc/2/common` | Authentication |
| `/xmlrpc/2/object` | Model operations (CRUD) |

**Important Notes:**
- External API only available on **Custom pricing plans** (not Free/Standard)
- XML-RPC/JSON-RPC APIs are **deprecated** and will be removed in Odoo 20 (Fall 2026)
- Consider migrating to newer REST API when available

### Authentication

```python
import xmlrpc.client

url = "https://your-odoo-instance.com"
db = "database-name"
username = "user@example.com"
password = "password-or-api-key"  # API keys supported in Odoo 14+

common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
```

### Key Operations

#### Customer Lookup (res.partner)
```python
# Search by phone number (most reliable)
customers = models.execute_kw(db, uid, password, 'res.partner', 'search_read',
    [["|", ("phone", "=", phone), ("mobile", "=", phone)]],
    {"fields": ["id", "name", "phone", "email"], "limit": 5}
)

# Search by name (fuzzy)
customers = models.execute_kw(db, uid, password, 'res.partner', 'search_read',
    [[("name", "ilike", customer_name)]],
    {"fields": ["id", "name"], "limit": 5}
)
```

#### Product Lookup (product.product)
```python
products = models.execute_kw(db, uid, password, 'product.product', 'search_read',
    [[("name", "ilike", product_name), ("sale_ok", "=", True)]],
    {"fields": ["id", "name", "default_code", "list_price", "uom_id"], "limit": 10}
)
```

#### Create Sales Order (sale.order)
```python
order_id = models.execute_kw(db, uid, password, 'sale.order', 'create', [{
    'partner_id': customer_id,  # Required: Odoo customer ID
    'order_line': [
        (0, 0, {'product_id': 101, 'product_uom_qty': 50, 'price_unit': 2500.0}),
        (0, 0, {'product_id': 102, 'product_uom_qty': 20, 'price_unit': 1800.0}),
    ],
    'note': 'Source: WhatsApp\nRequested delivery: Friday',
}])

# Optionally confirm the order
models.execute_kw(db, uid, password, 'sale.order', 'action_confirm', [[order_id]])
```

### Integration Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Order Extractor │────▶│   Odoo Client    │────▶│   Odoo ERP       │
│  (LLM)           │     │                  │     │                  │
└──────────────────┘     │  1. Find customer│     │  - res.partner   │
                         │  2. Match products│     │  - product.product│
                         │  3. Create order │     │  - sale.order    │
                         └──────────────────┘     └──────────────────┘
```

### Product Matching Strategy

Since extracted product names won't exactly match Odoo product names, we implement fuzzy matching:

1. **Exact match** - Try direct name lookup first
2. **Contains match** - Check if extracted name is contained in product name
3. **Word match** - Match individual words (e.g., "rice" matches "Rice (Basmati) 25kg")
4. **Fuzzy similarity** - Use sequence matching for typos/variations

Products that can't be matched are flagged in the order notes for manual resolution.

### Environment Variables for Odoo

```bash
# .env
ODOO_URL=https://your-instance.odoo.com
ODOO_DATABASE=your-database
ODOO_USERNAME=api-user@company.com
ODOO_PASSWORD=your-api-key
```

### Error Handling

| Error | Handling |
|-------|----------|
| Customer not found | Create order in review queue, flag for customer creation |
| Product not matched | Include in order notes, create with available products |
| Connection timeout | Retry with exponential backoff, fallback to queue |
| Authentication failure | Alert ops team, log for investigation |

---

## Questions I Would Ask the Client

1. What's the structure of product SKUs/names in Odoo? How standardized?
2. Do customers have consistent WhatsApp numbers, or do multiple staff order?
3. What's the current Odoo API access situation? Any rate limits?
4. Are there seasonal patterns in order volume or product demand?
5. What languages do customers use? (English, Swahili, mixed?)
6. How are partial deliveries handled today?
7. What's the tolerance for delayed confirmations during rollout?
