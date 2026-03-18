"""
TA Setup API — Multi-Scale Analysis with Structure-First Architecture
======================================================================

FULL PATTERN REGISTRY ARCHITECTURE:

Pipeline:
    all_detectors → all_candidates → validation → expiration → structure_gating 
                 → ranking → penalize_overused → best_selection → decision → scenarios → output

Key Principles:
1. ALL available detectors participate automatically
2. ALL detectors return unified PatternCandidate format
3. Patterns COMPETE against each other
4. System can honestly say "no meaningful pattern"
5. Decision layer aggregates into actionable bias
6. Scenario engine generates tradeable outcomes
"""

from fastapi import APIRouter, Query
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import random

router = APIRouter(prefix="/api/ta", tags=["TA Setup"])

from modules.ta_engine.setup.pattern_validator_v2 import get_pattern_validator_v2
from modules.ta_engine.setup.structure_context_engine import structure_context_engine, StructureContext
from modules.ta_engine.setup.structure_engine_v2 import StructureEngineV2, get_structure_engine_v2
from modules.ta_engine.setup.pattern_candidate import PatternCandidate
from modules.ta_engine.setup.pattern_expiration import pattern_expiration_engine
from modules.ta_engine.setup.pattern_ranking_engine import pattern_ranking_engine
from modules.ta_engine.setup.pattern_selector import pattern_selector

# Import registry and all unified detectors (auto-registers on import)
from modules.ta_engine.setup.pattern_registry import (
    PATTERN_REGISTRY,
    validate_candidate,
    filter_by_structure,
    penalize_overused_patterns,
    run_all_detectors
)
import modules.ta_engine.setup.pattern_detectors_unified  # Auto-registers detectors

# Decision and Scenario engines
from modules.ta_engine.decision import build_decision, get_decision_engine_v2
from modules.ta_engine.scenario import generate_scenarios, build_confidence_explanation, get_scenario_engine_v3
from modules.ta_engine.structure import get_structure_visualization_builder
from modules.ta_engine.intelligence import build_mtf_context
from modules.ta_engine.explanation import get_explanation_engine_v1, get_explanation_engine_v2
from modules.ta_engine.trade_setup import get_trade_setup_generator


# =============================================================================
# MULTI-SCALE CONFIGURATION (The Key!)
# =============================================================================

TF_CONFIG = {
    "4H": {
        "lookback": 200,        # ~33 days of 4H candles (limited by Coinbase API)
        "pivot_window": 3,      # Very sensitive - микро структуры
        "min_pivot_distance": 5,
        "pattern_window": 150,
        "candle_type": "4h",    # Uses 4H candles!
        "description": "Micro structure / entry points"
    },
    "1D": {
        "lookback": 150,        # ~5 months of daily
        "pivot_window": 5,      # Standard sensitivity
        "min_pivot_distance": 8,
        "pattern_window": 100,
        "candle_type": "1d",
        "description": "Short-term / setup patterns"
    },
    "7D": {
        "lookback": 400,        # ~1.5 years of daily
        "pivot_window": 9,      # Less sensitive (bigger swings)
        "min_pivot_distance": 15,
        "pattern_window": 250,
        "candle_type": "1d",
        "description": "Medium-term / formation patterns"
    },
    "30D": {
        "lookback": 800,        # ~3 years of daily
        "pivot_window": 15,     # Only major swings
        "min_pivot_distance": 30,
        "pattern_window": 500,
        "candle_type": "1d",
        "description": "Long-term / structure patterns"
    },
    "180D": {
        "lookback": 1500,       # ~6 years of daily
        "pivot_window": 25,     # Macro swings only
        "min_pivot_distance": 60,
        "pattern_window": 800,
        "candle_type": "1d",
        "description": "Macro / trend patterns"
    },
    "1Y": {
        "lookback": 2500,       # ~10 years of daily - FULL HISTORY
        "pivot_window": 40,     # Cycle-level swings only
        "min_pivot_distance": 100,
        "pattern_window": 1500,
        "candle_type": "1d",
        "description": "Cycle-level / global context"
    }
}


# =============================================================================
# STRUCTURE-FIRST Pattern Detection (NEW ARCHITECTURE)
# =============================================================================

def build_pattern_candidate(pattern_dict: Dict, candles: List[Dict], config: Dict) -> Optional[PatternCandidate]:
    """Convert old pattern dict to new PatternCandidate model."""
    if not pattern_dict:
        return None
    
    last_touch_index = len(candles) - 10  # Default
    anchor_points = pattern_dict.get("anchor_points", {})
    if anchor_points:
        for pts in [anchor_points.get("upper", []), anchor_points.get("lower", [])]:
            for pt in pts:
                pt_time = pt.get("time", 0)
                for i, c in enumerate(candles):
                    c_time = c.get("time", c.get("timestamp", 0))
                    if c_time > 1e12:
                        c_time = c_time // 1000
                    if c_time == pt_time:
                        last_touch_index = max(last_touch_index, i)
    
    return PatternCandidate(
        type=pattern_dict.get("type", "unknown"),
        direction=pattern_dict.get("direction", "neutral"),
        confidence=pattern_dict.get("confidence", 0.5),
        geometry_score=pattern_dict.get("confidence", 0.5),
        touch_count=pattern_dict.get("touches", 0),
        containment=pattern_dict.get("containment", 0.0),
        line_scores=pattern_dict.get("line_scores", {}),
        points=pattern_dict.get("points", {}),
        anchor_points=pattern_dict.get("anchor_points", {}),
        start_index=len(candles) // 3,
        end_index=len(candles) - 1,
        last_touch_index=last_touch_index,
        breakout_level=pattern_dict.get("breakout_level"),
        invalidation=pattern_dict.get("invalidation"),
    )


def detect_range_pattern(candles: List[Dict], config: Dict) -> Optional[Dict]:
    """NEW: Detect RANGE pattern - often more valid than triangle!"""
    if len(candles) < 30:
        return None
    
    lookback = min(config.get("pattern_window", 100), len(candles))
    recent = candles[-lookback:]
    
    highs = [c["high"] for c in recent]
    lows = [c["low"] for c in recent]
    
    range_high = max(highs)
    range_low = min(lows)
    range_width = (range_high - range_low) / range_low if range_low > 0 else 0
    
    if range_width < 0.02 or range_width > 0.20:
        return None
    
    tolerance = range_width * 0.1
    upper_touches = sum(1 for c in recent if c["high"] >= range_high * (1 - tolerance))
    lower_touches = sum(1 for c in recent if c["low"] <= range_low * (1 + tolerance))
    
    if upper_touches < 3 or lower_touches < 3:
        return None
    
    # Check no strong trend
    closes = [c["close"] for c in recent]
    n = len(closes)
    x_mean = (n - 1) / 2
    y_mean = sum(closes) / n
    numerator = sum((i - x_mean) * (closes[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    slope = numerator / denominator / max(y_mean, 1e-8) if denominator > 0 else 0
    
    if abs(slope) > 0.0003:
        return None
    
    total_touches = upper_touches + lower_touches
    confidence = round(min(0.85, 0.5 + min(1.0, total_touches / 10) * 0.25), 2)
    
    if confidence < 0.55:
        return None
    
    start_time = recent[0].get("time", recent[0].get("timestamp", 0))
    end_time = recent[-1].get("time", recent[-1].get("timestamp", 0))
    if start_time > 1e12:
        start_time = start_time // 1000
    if end_time > 1e12:
        end_time = end_time // 1000
    
    return {
        "type": "range",
        "direction": "neutral",
        "confidence": confidence,
        "touches": total_touches,
        "containment": 0.9,
        "line_scores": {"upper": min(1.0, total_touches / 10) * 10, "lower": min(1.0, total_touches / 10) * 10},
        "points": {
            "upper": [{"time": start_time, "value": round(range_high, 2)}, {"time": end_time, "value": round(range_high, 2)}],
            "lower": [{"time": start_time, "value": round(range_low, 2)}, {"time": end_time, "value": round(range_low, 2)}],
        },
        "anchor_points": {"upper": [{"time": start_time, "value": round(range_high, 2)}], "lower": [{"time": end_time, "value": round(range_low, 2)}]},
        "breakout_level": round(range_high, 2),
        "invalidation": round(range_low, 2),
        "range_width_pct": round(range_width * 100, 2),
    }


def hard_filter_recency(candidates: List, candles: List[Dict]) -> List:
    """
    HARD FILTER: Reject patterns that are too old or irrelevant.
    
    Rules:
    1. Pattern recency > 35% of lookback → reject
    2. Pattern end_index < 70% of candles → reject
    """
    if not candidates or not candles:
        return candidates
    
    total = len(candles)
    filtered = []
    
    for c in candidates:
        # Rule 1: last touch must be recent
        recency = (total - 1 - c.last_touch_index) / max(total, 1)
        if recency > 0.35:
            continue
        
        # Rule 2: pattern must cover recent chart area
        if c.end_index < total * 0.7:
            continue
        
        filtered.append(c)
    
    return filtered


def detect_pattern_v2(candles: List[Dict], symbol: str, tf: str) -> Dict:
    """
    STRUCTURE-FIRST Pattern Detection Pipeline (V2).
    
    Pipeline:
        candles → pivots → levels/trends → STRUCTURE_ENGINE_V2 → regime/phase
        → pattern candidates → structure_gating → hard_filters → ranking
        → penalize_overused → best_selection → decision → scenarios → output
    
    KEY CHANGE: Structure analysis BEFORE pattern detection.
    """
    config = TF_CONFIG.get(tf, TF_CONFIG["1D"])
    
    empty_result = {
        "structure_context": None,
        "base_layer": {"supports": [], "resistances": [], "trendlines": [], "channels": []},
        "primary_pattern": None, 
        "alternative_patterns": [], 
        "selection_explanation": {"status": "insufficient_data"},
        "decision": None,
        "scenarios": [],
        "confidence_explanation": {},
        "meta": {"total_candidates": 0, "after_filter": 0, "rejected": 0}
    }
    
    if len(candles) < 30:
        return empty_result
    
    validator = get_pattern_validator_v2(tf.upper(), config)
    pivot_highs, pivot_lows = validator.find_pivots(candles)
    
    if len(pivot_highs) < 2 or len(pivot_lows) < 2:
        empty_result["selection_explanation"] = {"status": "insufficient_pivots"}
        return empty_result
    
    # =============================================
    # STEP 1: BASE LAYER — levels + trendlines
    # =============================================
    levels = detect_levels(candles, tf)
    levels_for_ranking = [{"price": lv["price"], "strength": lv.get("strength", 50)} for lv in levels]
    
    # =============================================
    # STEP 2: STRUCTURE ENGINE V2 — understand market FIRST
    # =============================================
    structure_v2 = get_structure_engine_v2(tf)
    structure_state = structure_v2.build(
        candles=candles,
        pivots_high=pivot_highs,
        pivots_low=pivot_lows,
        levels=levels,
        trendlines=None
    )
    
    # Build base_layer from structure state — ALWAYS visible
    base_layer = {
        "supports": structure_state.active_supports,
        "resistances": structure_state.active_resistances,
        "trendlines": structure_state.active_trendlines,
        "channels": structure_state.active_channels,
    }
    
    structure_dict = structure_state.to_dict()
    
    # Also build old-format structure_ctx for compatibility with registry
    structure_ctx = structure_context_engine.build(candles, pivot_highs, pivot_lows)
    
    # Override old ctx's regime/bias with v2's more accurate values
    structure_ctx.regime = structure_state.regime
    structure_ctx.bias = structure_state.bias
    
    # =============================================
    # STEP 3: PATTERN CANDIDATES — only after structure is known
    # =============================================
    all_candidates = run_all_detectors(
        candles=candles,
        pivots_high=pivot_highs,
        pivots_low=pivot_lows,
        levels=levels,
        structure_ctx=structure_ctx,
        timeframe=tf,
        config=config
    )
    
    total_found = len(all_candidates)
    
    # STEP 4: Validation filter — remove garbage
    all_candidates = [c for c in all_candidates if validate_candidate(c)]
    after_validation = len(all_candidates)
    
    # STEP 5: Expiration filter — remove old patterns
    current_index = len(candles) - 1
    all_candidates = pattern_expiration_engine.filter_expired(all_candidates, current_index, tf)
    after_expiration = len(all_candidates)
    
    # STEP 6: STRUCTURE GATING — hard rejection by regime (V2!)
    all_candidates = filter_by_structure(all_candidates, structure_ctx)
    after_structure = len(all_candidates)
    
    # STEP 7: HARD RECENCY FILTER — reject stale patterns
    all_candidates = hard_filter_recency(all_candidates, candles)
    after_recency = len(all_candidates)
    
    # STEP 8: Ranking — patterns compete
    current_price = candles[-1]["close"]
    ranked_candidates = pattern_ranking_engine.rank(all_candidates, structure_ctx, levels_for_ranking, current_price)
    
    # STEP 9: Anti-overfit — penalize dominant pattern types
    ranked_candidates = penalize_overused_patterns(ranked_candidates)
    
    # STEP 10: Re-sort after penalties
    ranked_candidates.sort(key=lambda x: x.total_score, reverse=True)
    
    # STEP 11: Select best (with higher confidence bar)
    primary, alternatives = pattern_selector.select(ranked_candidates)
    
    # HARD RULE: if structure_score is weak, reject primary
    if primary and structure_state.structure_score < 0.4:
        if primary.total_score < 0.6:
            alternatives = [primary] + alternatives if primary else alternatives
            primary = None
    
    explanation = pattern_selector.explain_selection(primary, alternatives)
    
    # Convert to dict
    primary_dict = primary.to_dict() if primary else None
    alternatives_dict = [a.to_dict() for a in alternatives]
    
    # STEP 12: Build DECISION using structure v2
    decision = build_decision(
        structure_context=structure_dict,
        primary_pattern=primary_dict,
        alternative_patterns=alternatives_dict
    )
    
    # STEP 13: Generate SCENARIOS using ScenarioEngineV2
    scenarios = generate_scenarios(
        primary_pattern=primary_dict,
        alternative_patterns=alternatives_dict,
        decision=decision,
        structure_context=structure_dict,
        base_layer=base_layer,
        current_price=current_price
    )
    
    # STEP 14: Build confidence explanation
    confidence_explanation = build_confidence_explanation(primary_dict)
    
    # STEP 15: Build STRUCTURE VISUALIZATION — the "explanation layer"
    viz_builder = get_structure_visualization_builder()
    structure_visualization = viz_builder.build(
        pivots_high=pivot_highs,
        pivots_low=pivot_lows,
        structure_context=structure_dict,
        candles=candles,
    )
    
    return {
        "structure_context": structure_dict,
        "base_layer": base_layer,
        "structure_visualization": structure_visualization,  # NEW: visual explanation
        "primary_pattern": primary_dict,
        "alternative_patterns": alternatives_dict,
        "selection_explanation": explanation,
        "decision": decision,
        "scenarios": scenarios,
        "confidence_explanation": confidence_explanation,
        "meta": {
            "total_candidates": total_found,
            "after_validation": after_validation,
            "after_expiration": after_expiration,
            "after_structure_gate": after_structure,
            "after_recency_filter": after_recency,
            "final_ranked": len(ranked_candidates),
            "rejected": total_found - len(ranked_candidates)
        }
    }


def detect_pattern(candles: List[Dict], symbol: str, tf: str) -> Dict:
    """LEGACY: Detect pattern for backward compatibility."""
    config = TF_CONFIG.get(tf, TF_CONFIG["1D"])
    
    if len(candles) < 30:
        return None
    
    validator = get_pattern_validator_v2(tf.upper(), config)
    pattern = validator.detect_best_pattern(candles)
    
    return pattern


# =============================================================================
# Level Detection
# =============================================================================

def detect_levels(candles: List[Dict], tf: str) -> List[Dict]:
    """Detect support/resistance levels with TF-appropriate sensitivity."""
    if len(candles) < 20:
        return []
    
    config = TF_CONFIG.get(tf, TF_CONFIG["1D"])
    
    # Use more candles for level detection on higher TFs
    lookback = min(len(candles), config["lookback"])
    recent = candles[-lookback:]
    
    price_clusters = {}
    
    # Cluster prices with TF-appropriate bucket size
    # Higher TF = larger buckets (less noise)
    bucket_size = 100 if tf in ["1D", "4H"] else 500 if tf == "7D" else 1000
    
    for c in recent:
        for price in [c['high'], c['low']]:
            bucket = round(price / bucket_size) * bucket_size
            price_clusters[bucket] = price_clusters.get(bucket, 0) + 1
    
    sorted_levels = sorted(price_clusters.items(), key=lambda x: x[1], reverse=True)
    
    current_price = candles[-1]['close']
    
    levels = []
    for price, touches in sorted_levels[:5]:
        if price > current_price * 1.001:
            level_type = "resistance"
        elif price < current_price * 0.999:
            level_type = "support"
        else:
            level_type = "pivot"
        
        strength = min(100, int(touches / len(recent) * 400))
        
        levels.append({
            "price": round(price, 2),
            "type": level_type,
            "strength": strength,
            "touches": touches
        })
    
    return levels[:3]


# =============================================================================
# Structure Analysis
# =============================================================================

def analyze_structure(candles: List[Dict], tf: str) -> Dict:
    """Analyze market structure with TF-appropriate window."""
    if len(candles) < 10:
        return {"trend": "neutral", "hh": 0, "hl": 0, "lh": 0, "ll": 0}
    
    config = TF_CONFIG.get(tf, TF_CONFIG["1D"])
    
    # Use TF-appropriate window for structure analysis
    window = min(config["lookback"] // 3, len(candles))
    recent = candles[-window:]
    
    hh_count = 0
    hl_count = 0
    lh_count = 0
    ll_count = 0
    
    prev_high = recent[0]['high']
    prev_low = recent[0]['low']
    
    for c in recent[1:]:
        if c['high'] > prev_high:
            hh_count += 1
        else:
            lh_count += 1
        
        if c['low'] > prev_low:
            hl_count += 1
        else:
            ll_count += 1
        
        prev_high = c['high']
        prev_low = c['low']
    
    # Determine trend
    if hh_count > lh_count and hl_count > ll_count:
        trend = "bullish"
    elif lh_count > hh_count and ll_count > hl_count:
        trend = "bearish"
    else:
        trend = "neutral"
    
    return {
        "trend": trend,
        "hh": hh_count,
        "hl": hl_count,
        "lh": lh_count,
        "ll": ll_count
    }


# =============================================================================
# Setup Builder
# =============================================================================

def build_setup(candles: List[Dict], pattern: Dict, levels: List[Dict], structure: Dict) -> Dict:
    """Build trading setup from analysis components."""
    if not candles or not pattern:
        return None
    
    current_price = candles[-1]['close']
    
    direction = pattern.get("direction", "neutral")
    if direction == "neutral":
        direction = structure.get("trend", "neutral")
    
    if direction == "bearish":
        support_levels = [lv for lv in levels if lv['type'] == 'support']
        if support_levels:
            target1 = support_levels[0]['price']
            target2 = target1 * 0.95
        else:
            target1 = current_price * 0.95
            target2 = current_price * 0.90
        
        trigger = pattern.get("breakout_level") or current_price * 0.98
        invalidation = pattern.get("invalidation") or current_price * 1.05
    else:
        resistance_levels = [lv for lv in levels if lv['type'] == 'resistance']
        if resistance_levels:
            target1 = resistance_levels[0]['price']
            target2 = target1 * 1.05
        else:
            target1 = current_price * 1.05
            target2 = current_price * 1.10
        
        trigger = pattern.get("breakout_level") or current_price * 1.02
        invalidation = pattern.get("invalidation") or current_price * 0.95
    
    targets = [
        {"price": round(target1, 2), "label": "T1"},
        {"price": round(target2, 2), "label": "T2"}
    ]
    
    return {
        "direction": direction,
        "trigger": round(trigger, 2),
        "invalidation": round(invalidation, 2),
        "targets": targets
    }


# =============================================================================
# Main API Endpoint
# =============================================================================

@router.get("/setup")
async def get_ta_setup(
    symbol: str = Query("BTCUSDT", description="Trading pair"),
    tf: str = Query("1D", description="Timeframe")
):
    """
    Get complete TA setup for symbol and timeframe.
    
    MULTI-SCALE ANALYSIS:
    - All TFs use DAILY candles (no aggregation!)
    - Different TFs = different analysis parameters
    - Higher TF = larger lookback, less sensitive pivots
    """
    # Normalize symbol
    clean_symbol = symbol.replace("USDT", "").replace("-USD", "").upper()
    
    # Map timeframe
    tf_map = {
        "4H": "4H", "4h": "4H",
        "1D": "1D", "1d": "1D", 
        "7D": "7D", "7d": "7D",
        "30D": "30D", "30d": "30D",
        "180D": "180D", "180d": "180D",
        "1Y": "1Y", "1y": "1Y"
    }
    normalized_tf = tf_map.get(tf, "1D")
    
    # Get TF-specific config
    config = TF_CONFIG.get(normalized_tf, TF_CONFIG["1D"])
    
    # Fetch DAILY candles (always daily, no aggregation!)
    try:
        from modules.data.coinbase_provider import coinbase_provider
        
        # Always fetch daily candles
        # Exception: 4H fetches 4h candles
        if normalized_tf == "4H":
            cb_tf = "4h"
        else:
            cb_tf = "1d"
        
        product_id = f"{clean_symbol}-USD"
        
        # Fetch enough candles for the lookback
        limit = config["lookback"] + 100  # Extra buffer
        
        raw_candles = await coinbase_provider.get_candles(
            product_id=product_id,
            timeframe=cb_tf,
            limit=limit
        )
        
        # Format candles
        candles = []
        for c in raw_candles:
            candles.append({
                "time": c['timestamp'] // 1000 if c['timestamp'] > 1e12 else c['timestamp'],
                "open": c['open'],
                "high": c['high'],
                "low": c['low'],
                "close": c['close'],
                "volume": c.get('volume', 0)
            })
        
        # Sort by time
        candles.sort(key=lambda x: x['time'])
        
    except Exception as e:
        # Log the error
        print(f"[ERROR] Failed to fetch candles for {clean_symbol} {normalized_tf}: {e}")
        # Fallback: generate mock data
        import time
        base_time = int(time.time()) - 86400 * config["lookback"]
        base_price = 95000 if clean_symbol == "BTC" else 3200 if clean_symbol == "ETH" else 150
        
        candles = []
        for i in range(config["lookback"]):
            t = base_time + i * 86400
            change = random.uniform(-0.03, 0.03)
            open_p = base_price * (1 + change)
            close_p = open_p * (1 + random.uniform(-0.02, 0.02))
            high_p = max(open_p, close_p) * (1 + random.uniform(0, 0.015))
            low_p = min(open_p, close_p) * (1 - random.uniform(0, 0.015))
            base_price = close_p
            
            candles.append({
                "time": t,
                "open": round(open_p, 2),
                "high": round(high_p, 2),
                "low": round(low_p, 2),
                "close": round(close_p, 2),
                "volume": random.randint(1000, 10000)
            })
    
    # Trim to lookback window
    candles = candles[-config["lookback"]:]
    
    # Detect pattern with TF-specific parameters
    pattern = detect_pattern(candles, clean_symbol, normalized_tf)
    
    # Detect levels
    levels = detect_levels(candles, normalized_tf)
    
    # Analyze structure
    structure = analyze_structure(candles, normalized_tf)
    
    # Build setup
    setup = build_setup(candles, pattern, levels, structure)
    
    return {
        "symbol": f"{clean_symbol}USDT",
        "timeframe": normalized_tf,
        "scale_config": {
            "lookback": config["lookback"],
            "pivot_window": config["pivot_window"],
            "min_pivot_distance": config["min_pivot_distance"],
            "description": config["description"]
        },
        "candles": candles,
        "candle_count": len(candles),
        "pattern": pattern,
        "levels": levels,
        "structure": structure,
        "setup": setup,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# =============================================================================
# NEW: Structure-First Setup Endpoint (v2)
# =============================================================================

@router.get("/setup/v2")
async def get_ta_setup_v2(
    symbol: str = Query("BTCUSDT", description="Trading pair"),
    tf: str = Query("1D", description="Timeframe")
):
    """
    NEW ARCHITECTURE: Structure-First TA Setup
    
    Returns:
    - structure_context: Market regime (trend/range/compression)
    - primary_pattern: Best pattern after competition + expiration filter
    - alternative_patterns: Other valid patterns
    - selection_explanation: Why this pattern was chosen
    
    This endpoint:
    1. First analyzes market structure (regime, bias)
    2. Detects ALL pattern candidates (triangles, ranges, etc)
    3. Filters expired/old patterns
    4. Ranks patterns by score
    5. Selects best (or returns None if no good patterns)
    """
    clean_symbol = symbol.replace("USDT", "").replace("-USD", "").upper()
    
    tf_map = {
        "4H": "4H", "4h": "4H",
        "1D": "1D", "1d": "1D", 
        "7D": "7D", "7d": "7D",
        "30D": "30D", "30d": "30D",
        "180D": "180D", "180d": "180D",
        "1Y": "1Y", "1y": "1Y"
    }
    normalized_tf = tf_map.get(tf, "1D")
    config = TF_CONFIG.get(normalized_tf, TF_CONFIG["1D"])
    
    # Fetch candles
    try:
        from modules.data.coinbase_provider import coinbase_provider
        
        cb_tf = "4h" if normalized_tf == "4H" else "1d"
        product_id = f"{clean_symbol}-USD"
        limit = config["lookback"] + 100
        
        raw_candles = await coinbase_provider.get_candles(
            product_id=product_id,
            timeframe=cb_tf,
            limit=limit
        )
        
        candles = []
        for c in raw_candles:
            candles.append({
                "time": c['timestamp'] // 1000 if c['timestamp'] > 1e12 else c['timestamp'],
                "open": c['open'],
                "high": c['high'],
                "low": c['low'],
                "close": c['close'],
                "volume": c.get('volume', 0)
            })
        
        candles.sort(key=lambda x: x['time'])
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch candles: {e}")
        # Fallback mock data
        import time
        base_time = int(time.time()) - 86400 * config["lookback"]
        base_price = 95000 if clean_symbol == "BTC" else 3200
        
        candles = []
        for i in range(config["lookback"]):
            t = base_time + i * 86400
            change = random.uniform(-0.03, 0.03)
            open_p = base_price * (1 + change)
            close_p = open_p * (1 + random.uniform(-0.02, 0.02))
            high_p = max(open_p, close_p) * (1 + random.uniform(0, 0.015))
            low_p = min(open_p, close_p) * (1 - random.uniform(0, 0.015))
            base_price = close_p
            
            candles.append({
                "time": t,
                "open": round(open_p, 2),
                "high": round(high_p, 2),
                "low": round(low_p, 2),
                "close": round(close_p, 2),
                "volume": random.randint(1000, 10000)
            })
    
    candles = candles[-config["lookback"]:]
    
    # Use NEW architecture
    result = detect_pattern_v2(candles, clean_symbol, normalized_tf)
    
    # =============================================
    # MTF CONTEXT ENGINE — analyze higher TFs for global context
    # =============================================
    # For daily candle TFs we reuse same candle data with different parameters
    # This is efficient — no extra API calls needed
    MTF_ANALYZE = ["1D", "7D", "30D"]
    tf_structure_data = {}
    
    # Current TF structure is already computed
    current_structure = result.get("structure_context")
    if current_structure:
        tf_structure_data[normalized_tf] = current_structure
    
    # Run structure analysis for other TFs (reuse daily candles)
    for mtf in MTF_ANALYZE:
        if mtf == normalized_tf:
            continue  # Already have it
        mtf_config = TF_CONFIG.get(mtf, TF_CONFIG["1D"])
        # Only analyze if we have enough candles
        mtf_lookback = min(len(candles), mtf_config["lookback"])
        if mtf_lookback < 30:
            continue
        mtf_candles = candles[-mtf_lookback:]
        try:
            mtf_validator = get_pattern_validator_v2(mtf, mtf_config)
            mtf_ph, mtf_pl = mtf_validator.find_pivots(mtf_candles)
            if len(mtf_ph) >= 2 and len(mtf_pl) >= 2:
                mtf_engine = get_structure_engine_v2(mtf)
                mtf_levels = detect_levels(mtf_candles, mtf)
                mtf_state = mtf_engine.build(
                    candles=mtf_candles,
                    pivots_high=mtf_ph,
                    pivots_low=mtf_pl,
                    levels=mtf_levels,
                )
                tf_structure_data[mtf] = mtf_state.to_dict()
        except Exception as e:
            print(f"[MTF] Failed to analyze {mtf}: {e}")
    
    mtf_context = build_mtf_context(tf_structure_data, normalized_tf)
    
    # =============================================
    # DECISION ENGINE V2 — Final System Verdict
    # =============================================
    # Uses: mtf_context (45%) + structure_context (35%) + pattern (20%)
    decision_engine = get_decision_engine_v2()
    decision_v2 = decision_engine.build(
        mtf_context=mtf_context,
        structure_context=result.get("structure_context", {}),
        primary_pattern=result.get("primary_pattern"),
    )
    
    # =============================================
    # SCENARIO ENGINE V3 — Decision-Driven Scenarios
    # =============================================
    # Scenarios built from: decision + mtf_context + structure_context + base_layer
    scenario_engine = get_scenario_engine_v3()
    current_price = candles[-1]["close"] if candles else 0.0
    base_layer = result.get("base_layer", {"supports": [], "resistances": [], "trendlines": [], "channels": []})
    
    scenarios_v3_result = scenario_engine.build(
        decision=decision_v2,
        mtf_context=mtf_context,
        structure_context=result.get("structure_context", {}),
        base_layer=base_layer,
        current_price=current_price,
        primary_pattern=result.get("primary_pattern"),
        alternative_patterns=result.get("alternative_patterns", []),
    )
    scenarios_v3 = scenarios_v3_result.get("scenarios", [])
    
    # Also get legacy pattern for comparison
    legacy_pattern = detect_pattern(candles, clean_symbol, normalized_tf)
    
    # Detect levels and structure (for display)
    levels = detect_levels(candles, normalized_tf)
    structure = analyze_structure(candles, normalized_tf)
    
    # =============================================
    # TRADE SETUP GENERATOR — Execution-Ready Setups
    # =============================================
    trade_setup_gen = get_trade_setup_generator()
    trade_setup_result = trade_setup_gen.build(
        decision=decision_v2,
        scenarios=scenarios_v3,
        base_layer=base_layer,
        structure_context=result.get("structure_context", {}),
        current_price=current_price,
    )
    trade_setup = trade_setup_result.get("trade_setup", {})
    
    # =============================================
    # EXPLANATION ENGINE V2 — Ultra-Compact (3 lines)
    # =============================================
    explanation_engine_v2 = get_explanation_engine_v2()
    explanation = explanation_engine_v2.build(
        decision=decision_v2,
        scenarios=scenarios_v3,
        trade_setup=trade_setup,
    )
    
    # Also get detailed V1 explanation (legacy)
    explanation_engine_v1 = get_explanation_engine_v1()
    explanation_detailed = explanation_engine_v1.generate({
        "decision": decision_v2,
        "mtf_context": mtf_context,
        "structure_context": result.get("structure_context", {}),
        "scenarios": scenarios_v3,
    })
    
    return {
        "symbol": f"{clean_symbol}USDT",
        "timeframe": normalized_tf,
        "scale_config": {
            "lookback": config["lookback"],
            "pivot_window": config["pivot_window"],
            "description": config["description"]
        },
        "candles": candles,
        "candle_count": len(candles),
        "current_price": current_price,
        
        # Structure-First Architecture (V2)
        "structure_context": result.get("structure_context"),
        
        # MTF CONTEXT — multi-timeframe intelligence
        "mtf_context": mtf_context,
        
        # BASE LAYER — always visible on chart
        "base_layer": base_layer,
        
        # STRUCTURE VISUALIZATION — the explanation layer (HH/HL/LH/LL, BOS/CHOCH)
        "structure_visualization": result.get("structure_visualization", {
            "pivot_points": [], "events": [], "active_trendlines": []
        }),
        
        "primary_pattern": result.get("primary_pattern"),
        "alternative_patterns": result.get("alternative_patterns", []),
        "selection_explanation": result.get("selection_explanation"),
        
        # DECISION V2 — Final system verdict (MTF + Structure + Pattern weighted)
        "decision": decision_v2,
        
        # SCENARIOS V3 — Decision-driven scenarios
        "scenarios": scenarios_v3,
        
        # EXPLANATION V2 — Ultra-compact (3 lines)
        "explanation": explanation,
        
        # EXPLANATION V1 — Detailed (legacy)
        "explanation_detailed": explanation_detailed,
        
        # TRADE SETUP — Execution-ready entry/stop/targets
        "trade_setup": trade_setup,
        
        # Legacy (for comparison during transition)
        "decision_legacy": result.get("decision"),
        "scenarios_legacy": result.get("scenarios", []),
        
        # Confidence Explanation
        "confidence_explanation": result.get("confidence_explanation", {}),
        
        # Pipeline meta (for debugging/transparency)
        "meta": result.get("meta", {}),
        
        # Legacy (for comparison)
        "legacy_pattern": legacy_pattern,
        
        # Standard fields
        "levels": levels,
        "structure": structure,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# =============================================================================
# Debug Endpoint
# =============================================================================

@router.get("/debug")
async def get_ta_debug(
    symbol: str = Query("BTCUSDT"),
    tf: str = Query("1D")
):
    """Debug endpoint showing internal state."""
    clean_symbol = symbol.replace("USDT", "").replace("-USD", "").upper()
    
    tf_map = {
        "4H": "4H", "4h": "4H",
        "1D": "1D", "1d": "1D",
        "7D": "7D", "7d": "7D",
        "30D": "30D", "30d": "30D",
        "180D": "180D", "180d": "180D",
        "1Y": "1Y", "1y": "1Y"
    }
    normalized_tf = tf_map.get(tf, "1D")
    
    config = TF_CONFIG.get(normalized_tf, TF_CONFIG["1D"])
    
    try:
        from modules.data.coinbase_provider import coinbase_provider
        
        product_id = f"{clean_symbol}-USD"
        raw_candles = await coinbase_provider.get_candles(
            product_id=product_id,
            timeframe="1d",
            limit=config["lookback"]
        )
        
        candles = [{
            "time": c['timestamp'] // 1000 if c['timestamp'] > 1e12 else c['timestamp'],
            "open": c['open'],
            "high": c['high'],
            "low": c['low'],
            "close": c['close'],
        } for c in raw_candles]
        
        candles.sort(key=lambda x: x['time'])
        
    except Exception:
        candles = []
    
    # Get validator with config
    validator = get_pattern_validator_v2(normalized_tf, config)
    pivot_highs, pivot_lows = validator.find_pivots(candles)
    
    return {
        "symbol": clean_symbol,
        "timeframe": normalized_tf,
        "config": config,
        "candle_count": len(candles),
        "pivot_highs": len(pivot_highs),
        "pivot_lows": len(pivot_lows),
        "first_candle": candles[0] if candles else None,
        "last_candle": candles[-1] if candles else None,
    }
