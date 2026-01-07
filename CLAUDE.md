# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WhatsApp Order Intake Automation - An AI-powered prototype for extracting structured order data from WhatsApp messages for Kijani Supplies, a B2B distributor serving lodges and hotels in East Africa.

**Tech Stack:** Python 3.9+, Claude API (Sonnet 4), Pydantic, Anthropic SDK, FastAPI, React, TypeScript

## Commands

### Web Demo (Recommended)
```bash
# Install backend dependencies
pip3 install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..

# Start backend (in one terminal)
SEED_DATABASE=true python3 -m uvicorn app:app --reload --port 8000

# Start frontend (in another terminal)
cd frontend && npm run dev
```
Access the demo at http://localhost:5173

### CLI Mode

```bash
# Install dependencies
pip3 install -r requirements.txt

# Run tests
python3 -m pytest tests/ -v

# Run integration tests (requires ANTHROPIC_API_KEY)
python3 -m pytest tests/ -v -m integration

# Run application
python3 main.py                          # Interactive mode
python3 main.py --test                   # Run all sample messages
python3 main.py --message "..."          # Process single message
python3 main.py --test --odoo            # With Odoo integration
python3 main.py --message "..." --json   # JSON output
```

## Architecture

**Processing Pipeline:**
```
WhatsApp Message → OrderExtractor (LLM) → OrderProcessor → ProcessingResult
                                              │
                      ┌───────────────────────┼───────────────────────┐
                      ▼                       ▼                       ▼
                 ERP Payload          Confirmation Msg         Odoo Submission
                   Builder               Generator              (optional)
```

**Key Modules:**
- `src/extractor.py` - LLM-based order extraction using Claude Sonnet 4 with structured JSON output
- `src/processor.py` - Main pipeline orchestrator, coordinates extraction → payload → confirmation → optional Odoo
- `src/models.py` - Pydantic data models with confidence scoring (HIGH/MEDIUM/LOW)
- `src/confirmation.py` - WhatsApp confirmation message generation (LLM or template-based)
- `src/erp_payload.py` - Converts extracted orders to ERP-agnostic payload format
- `src/odoo_client.py` - Odoo ERP integration via XML-RPC with fuzzy product/customer matching
- `main.py` - CLI interface with interactive demo mode

**Web Demo Modules:**
- `app.py` - FastAPI application entry point
- `src/api/routes.py` - REST API endpoints for messages, conversations, orders, metrics
- `src/api/websocket.py` - WebSocket handlers for real-time updates
- `src/db/` - SQLAlchemy database models and seed data (SQLite)
- `frontend/` - React + TypeScript + Tailwind web interface

## Key Patterns

**Confidence Scoring:** Every extracted field has HIGH (0.95), MEDIUM (0.75), or LOW (0.50) confidence. Orders with confidence < 0.8 or clarification items are auto-flagged for human review.

**Dependency Injection:** OdooClient is optional and injected into OrderProcessor. Use MockOdooClient for development without Odoo instance.

**Fuzzy Matching:** Odoo client uses multi-strategy product matching (exact → contains → word-level → sequence similarity).

## Environment Variables

```
ANTHROPIC_API_KEY=sk-ant-...               # Required for Claude API
ODOO_URL=https://instance.odoo.com         # Optional
ODOO_DATABASE=database_name                # Optional
ODOO_USERNAME=api-user@company.com         # Optional
ODOO_PASSWORD=api-key-or-password          # Optional
```

## Git Workflow

Use feature branches for all new work:

```bash
# Create feature branch
git checkout -b feature/<feature-name>

# Work on feature, commit changes
git add .
git commit -m "Description of changes"

# Merge only after feature is working and tests pass
git checkout main
git merge feature/<feature-name>
```

Always verify tests pass before merging to main.

## Testing

Tests in `tests/test_extraction.py` cover:
- Confidence score mapping
- ERP payload generation
- Model validation
- High/low confidence routing

Use `@pytest.mark.integration` marker for tests requiring API key.
