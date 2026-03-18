# TA Engine — Product Requirements Document

## Project Overview
Crypto Technical Analysis Engine with multi-timeframe analysis, decision engine, and trade setup generation.

## Original Problem Statement
Работа с модулем теханализа (ta_engine). Реализация AI Explanation Polish (P1) — сделать explanation ультракомпактным (3 строки) как думает трейдер.

## Architecture
```
Analysis → Decision → Scenario → Execution → Visualization
```

### Core Components
- **Structure Engine V2**: Market structure analysis (regime, bias, phase)
- **Decision Engine V2**: Weighted decision (MTF 45% + Structure 35% + Pattern 20%)
- **Scenario Engine V3**: Primary/Alternative scenarios with triggers
- **Trade Setup Generator**: Entry zone, stop loss, targets
- **Explanation Engine V2**: Ultra-compact 3-line explanation

## What's Been Implemented

### 2026-03-18: AI Explanation Polish (P1) ✅
- ExplanationEngineV2 generates 3-line compact explanations:
  - `summary`: "Bearish. Price is bouncing into resistance."
  - `action`: "Look for rejection from 89200."
  - `risk`: "Invalid if price holds above 90300."
- ExplanationPanel (frontend) updated for V2 format
- All 11 backend tests passed (100%)

### 2026-03-18: My Ideas Module ✅
- Full CRUD API: create, list, get, update, delete, timeline
- Versioning: each update creates NEW version (не перезаписывает)
- Snapshot stores: decision, scenarios, trade_setup, explanation
- Validation system: track accuracy, target hits, invalidations
- Timeline endpoint shows version history
- All 9 backend tests passed (100%)

## API Endpoints
- `GET /api/ta/setup/v2?symbol=BTCUSDT&tf=1D` — Full analysis pipeline
- `GET /api/health` — Health check
- `GET /api/ta/registry` — Strategy registry
- `GET /api/provider/coinbase/ticker/{symbol}` — Live prices

## User Personas
- **Active Trader**: Needs instant understanding of market state
- **Algo Developer**: Uses API for automated analysis

## Backlog

### P0 (Critical)
- [x] ExplanationEngineV2 (3-line format) ✅

### P1 (Next)
- [ ] My Ideas (save setups, history, share)
- [ ] Telegram Engine (auto-posting)

### P2 (Future)
- [ ] Copy-trading integration
- [ ] Twitter-ready content generation

## Technical Stack
- Backend: FastAPI + MongoDB
- Frontend: React + styled-components
- Data: Coinbase API (live market data)
