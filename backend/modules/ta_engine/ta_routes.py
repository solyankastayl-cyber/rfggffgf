"""
TA Engine Routes
=================
Phase 14.2 — API endpoints for TA Hypothesis Layer.
"""

from fastapi import APIRouter, Query
from datetime import datetime, timezone

from modules.ta_engine.hypothesis import get_hypothesis_builder

router = APIRouter(prefix="/api/ta-engine", tags=["ta-engine"])

_builder = get_hypothesis_builder()


# NOTE: Static routes MUST come before dynamic {symbol} routes

@router.get("/status")
async def get_ta_status():
    """Health check for TA Engine."""
    return {
        "ok": True,
        "module": "ta_engine",
        "version": "14.2",
        "phase": "Hypothesis Layer",
        "components": {
            "hypothesis_builder": "active",
            "trend_analyzer": "active",
            "momentum_analyzer": "active",
            "structure_analyzer": "active",
            "breakout_detector": "active",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/hypothesis/batch")
async def get_hypothesis_batch(
    symbols: str = Query("BTC,ETH,SOL", description="Comma-separated symbols"),
    timeframe: str = Query("1d", description="Candle timeframe")
):
    """Get hypothesis for multiple symbols."""
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    results = {}
    for sym in sym_list:
        hypo = _builder.build(sym, timeframe)
        results[sym] = hypo.to_dict()
    return {
        "ok": True,
        "count": len(results),
        "hypotheses": results,
    }


@router.get("/hypothesis/full/{symbol}")
async def get_hypothesis_full(
    symbol: str = "BTC",
    timeframe: str = Query("1d", description="Candle timeframe")
):
    """
    Get full TA hypothesis with detailed component signals.
    """
    hypo = _builder.build(symbol, timeframe)
    return {
        "ok": True,
        "hypothesis": hypo.to_full_dict(),
    }


@router.get("/hypothesis/{symbol}")
async def get_hypothesis(
    symbol: str = "BTC",
    timeframe: str = Query("1d", description="Candle timeframe")
):
    """
    Get unified TA hypothesis for a symbol.
    This is the primary endpoint for Trading Layer.
    
    Returns single direction/conviction after analyzing:
    - Trend (MA alignment)
    - Momentum (RSI, MACD)
    - Structure (HH/HL, BOS)
    - Breakout detection
    """
    hypo = _builder.build(symbol, timeframe)
    return {
        "ok": True,
        "hypothesis": hypo.to_dict(),
    }
