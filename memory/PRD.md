# TA Engine - Technical Analysis Module

## Original Problem Statement
Модуль теханализа по GitHub для анализа рыночных данных с архитектурой Structure-First.

## Architecture

### Completed Layers (Roadmap)
1. **Structure Engine** ✅ - Market structure analysis (HH/HL/LH/LL)
2. **Structure Visualization** ✅ - Visual explanation layer (BOS/CHOCH events)
3. **MTF Context Engine** ✅ - Multi-timeframe market intelligence
4. **Decision Engine V2** ✅ (Jan 2026) - Final system verdict
5. **Scenario Engine V3** ✅ (Jan 2026) - Decision-driven scenarios
6. **AI Explanation Layer** ✅ (Jan 2026) - Human-readable analysis
7. **Idea Engine V1** ✅ (Jan 2026) - Versioned idea management
8. **Trade Setup Generator** ✅ (Jan 2026) - Execution-ready setups
9. **Graph Cleanup + Execution Overlay** ✅ (Jan 2026) - Visual entry/stop/target

### Decision Engine V2 Contract
```json
{
  "decision": {
    "bias": "bearish",
    "confidence": 0.71,
    "context": "relief_bounce",
    "alignment": "mixed",
    "strength": "medium",
    "dominant_tf": "30D",
    "tradeability": "conditional",
    "summary": "Short-term bounce inside bearish higher timeframe structure"
  }
}
```

### Explanation Engine V1 Contract
```json
{
  "explanation": {
    "summary": "Market shows high-conviction bearish bias...",
    "technical_reasoning": "Current market structure indicates...",
    "scenario_explanation": "**Primary scenario:** Bearish continuation (80%)...",
    "risk_factors": "Mixed alignment | Low confidence",
    "invalidation_explanation": "Scenario becomes invalid if...",
    "short_text": "BEARISH setup (80%) — watching trigger at 89,200",
    "confidence": 0.80
  }
}
```

### Idea Engine V1 Contract
```json
{
  "idea": {
    "id": "uuid",
    "asset": "BTCUSDT",
    "timeframe": "1D",
    "version_count": 2,
    "current_version_id": "uuid"
  },
  "version": {
    "version_number": 2,
    "bias": "bearish",
    "confidence": 0.75,
    "scenario_title": "Bearish continuation",
    "trigger": "89200",
    "invalidation": "92000",
    "status": "ACTIVE"
  }
}
```

### Trade Setup Generator Contract
```json
{
  "trade_setup": {
    "primary": {
      "direction": "short",
      "entry_zone": [88800, 89200],
      "stop_loss": 90500,
      "target_1": 78500,
      "target_2": 68200,
      "invalidation": 90500,
      "rr": 2.1,
      "valid": true,
      "reason": "bearish context + relief bounce into resistance"
    },
    "alternative": {...}
  }
}
```

Hard rules:
- If no usable levels → no setup (null)
- If RR < 1.5 → valid = false
- Primary setup from primary scenario
- Entry depends on context (relief_bounce → sell near resistance, pullback → buy near support)
- Stop always behind invalidation level (structural)

## Core Requirements
- Pattern CANNOT override MTF + Structure consensus
- Decision stable across TF switches
- Confidence thresholds: >=0.75 → strong, >=0.55 → medium, <0.55 → weak
- Scenarios built from decision (not bare levels)
- Explanation is deterministic (not AI-generated)
- Old idea versions NOT deleted (version chain)

## What's Been Implemented

### Jan 2026
- ✅ Decision Engine V2 (`/app/backend/modules/ta_engine/decision/decision_engine_v2.py`)
- ✅ Scenario Engine V3 (`/app/backend/modules/ta_engine/scenario/scenario_engine_v3.py`)
- ✅ Explanation Engine V1 (`/app/backend/modules/ta_engine/explanation/explanation_engine_v1.py`)
- ✅ Idea Engine V1 (`/app/backend/modules/idea/`)
- ✅ Integration into `/api/ta/setup/v2` endpoint
- ✅ Idea API (`/api/ideas`, `/api/favorites`)

## API Endpoints

### TA Analysis
- `GET /api/ta/setup/v2?symbol=BTC&tf=1D` - Full TA setup with Decision V2 + Scenarios V3 + Explanation

### Ideas
- `POST /api/ideas` - Create idea from analysis
- `GET /api/ideas/:id` - Get idea with version history
- `PUT /api/ideas/:id/update` - Update idea (new version)
- `POST /api/ideas/:id/favorite` - Add to favorites
- `DELETE /api/ideas/:id/favorite?user_id=xxx` - Remove from favorites
- `GET /api/ideas/user/:user_id` - Get user's ideas
- `GET /api/ideas/asset/:asset` - Get ideas for asset
- `GET /api/favorites/:user_id` - Get user's favorites

## Prioritized Backlog

### P0 - Next (AI Explanation polish)
- Compress text to trader-thinking style
- Make explanation more actionable

### P1 - After Explanation polish
- My Ideas page in frontend
- Telegram / content automation

### P2 - Future
- Idea Outcome Tracking (VALIDATED/INVALIDATED)
- Auto Update Recommendations

## What's Been Implemented (Frontend)

### Jan 2026
- ✅ ExplanationPanel component (`/app/frontend/src/modules/cockpit/components/ExplanationPanel.jsx`)
- ✅ Integration into Tech Analysis page
- ✅ Summary, Technical Reasoning, Scenario, Risk Factors, Invalidation sections
- ✅ Confidence meter (80% with progress bar)
- ✅ Quick Share Text with Copy/Share buttons
- ✅ ScenariosBlock with trigger/invalidation from Scenario Engine V3

## Tech Stack
- Backend: FastAPI + Python
- Frontend: React + Tailwind
- Data: Coinbase public API
- DB: MongoDB (Ideas currently in-memory, ready for MongoDB)

## Files Structure
```
/app/backend/modules/
├── ta_engine/
│   ├── decision/
│   │   ├── decision_engine.py      # V1 legacy
│   │   └── decision_engine_v2.py   # V2 ✅
│   ├── scenario/
│   │   ├── scenario_engine.py      # V1 legacy
│   │   ├── scenario_engine_v2.py   # V2 structure-aware
│   │   └── scenario_engine_v3.py   # V3 decision-driven ✅
│   ├── explanation/
│   │   └── explanation_engine_v1.py # Human-readable ✅
│   ├── intelligence/
│   │   └── mtf_context_engine.py
│   └── ta_setup_api.py
├── idea/
│   ├── models.py                   # Idea, IdeaVersion, Favorite
│   ├── repository.py               # Data access layer
│   ├── idea_engine_v1.py           # Create, update, track
│   └── idea_routes.py              # REST API ✅
```
