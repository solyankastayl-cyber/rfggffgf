"""
Pattern Detectors - Unified Wrappers
=====================================

Wraps existing detectors to return List[PatternCandidate].
All registered detectors participate in unified candidate pool.
"""

from typing import List, Dict, Optional
from .pattern_candidate import PatternCandidate
from .pattern_registry import register_pattern, adapt_to_candidate, adapt_detected_pattern, PATTERN_REGISTRY


# =============================================================================
# HEAD & SHOULDERS DETECTOR WRAPPER
# =============================================================================

@register_pattern
def detect_head_shoulders_unified(
    candles: List[Dict],
    pivots_high: List = None,
    pivots_low: List = None,
    levels: List[Dict] = None,
    structure_ctx = None,
    timeframe: str = "1D",
    config: Dict = None
) -> List[PatternCandidate]:
    """
    Detect Head & Shoulders (bearish) and Inverse H&S (bullish).
    """
    from .detect_head_shoulders import get_head_shoulders_detector
    
    candidates = []
    
    try:
        detector = get_head_shoulders_detector(timeframe)
        patterns = detector.detect(
            candles=candles,
            pivots_high=pivots_high,
            pivots_low=pivots_low,
            levels=levels,
            structure_ctx=structure_ctx
        )
        
        for p in patterns:
            candidate = adapt_to_candidate(p, p.get("type"))
            if candidate:
                candidates.append(candidate)
                
    except Exception as e:
        pass  # Fail-safe
    
    return candidates


# =============================================================================
# TRIANGLE DETECTOR WRAPPER
# =============================================================================

@register_pattern
def detect_triangles_unified(
    candles: List[Dict],
    pivots_high: List = None,
    pivots_low: List = None,
    levels: List[Dict] = None,
    structure_ctx = None,
    timeframe: str = "1D",
    config: Dict = None
) -> List[PatternCandidate]:
    """
    Detect all triangle patterns using pattern_validator_v2.
    Returns List[PatternCandidate] for unified ranking.
    """
    from .pattern_validator_v2 import get_pattern_validator_v2
    
    candidates = []
    config = config or {}
    
    try:
        validator = get_pattern_validator_v2(timeframe, config)
        pattern = validator.detect_best_pattern(candles)
        
        if pattern and "triangle" in pattern.get("type", "").lower():
            # Add index info based on candles
            pattern["start_index"] = len(candles) // 3
            pattern["end_index"] = len(candles) - 1
            pattern["last_touch_index"] = len(candles) - 10
            
            candidate = adapt_to_candidate(pattern, pattern.get("type"))
            if candidate:
                candidates.append(candidate)
                
    except Exception as e:
        pass  # Fail-safe
    
    return candidates


# =============================================================================
# CHANNEL DETECTOR WRAPPER
# =============================================================================

@register_pattern
def detect_channels_unified(
    candles: List[Dict],
    pivots_high: List = None,
    pivots_low: List = None,
    levels: List[Dict] = None,
    structure_ctx = None,
    timeframe: str = "1D",
    config: Dict = None
) -> List[PatternCandidate]:
    """
    Detect channel patterns.
    """
    from .pattern_detector import get_pattern_detector
    
    candidates = []
    
    try:
        detector = get_pattern_detector()
        patterns = detector._detect_channels(candles)
        
        for p in patterns:
            candidate = adapt_detected_pattern(p)
            if candidate:
                candidate.start_index = len(candles) // 3
                candidate.end_index = len(candles) - 1
                candidate.last_touch_index = len(candles) - 10
                candidates.append(candidate)
                
    except Exception:
        pass
    
    return candidates


# =============================================================================
# DOUBLE TOP/BOTTOM DETECTOR WRAPPER
# =============================================================================

@register_pattern
def detect_double_patterns_unified(
    candles: List[Dict],
    pivots_high: List = None,
    pivots_low: List = None,
    levels: List[Dict] = None,
    structure_ctx = None,
    timeframe: str = "1D",
    config: Dict = None
) -> List[PatternCandidate]:
    """
    Detect double top and double bottom patterns.
    """
    from .pattern_detector import get_pattern_detector
    
    candidates = []
    
    try:
        detector = get_pattern_detector()
        patterns = detector._detect_double_patterns(candles)
        
        for p in patterns:
            candidate = adapt_detected_pattern(p)
            if candidate:
                candidate.start_index = len(candles) // 2
                candidate.end_index = len(candles) - 1
                candidate.last_touch_index = len(candles) - 5
                candidates.append(candidate)
                
    except Exception:
        pass
    
    return candidates


# =============================================================================
# COMPRESSION DETECTOR WRAPPER
# =============================================================================

@register_pattern
def detect_compression_unified(
    candles: List[Dict],
    pivots_high: List = None,
    pivots_low: List = None,
    levels: List[Dict] = None,
    structure_ctx = None,
    timeframe: str = "1D",
    config: Dict = None
) -> List[PatternCandidate]:
    """
    Detect compression/squeeze patterns.
    """
    from .pattern_detector import get_pattern_detector
    
    candidates = []
    
    try:
        detector = get_pattern_detector()
        patterns = detector._detect_compression(candles)
        
        for p in patterns:
            candidate = adapt_detected_pattern(p)
            if candidate:
                candidate.start_index = len(candles) - 30
                candidate.end_index = len(candles) - 1
                candidate.last_touch_index = len(candles) - 1
                candidates.append(candidate)
                
    except Exception:
        pass
    
    return candidates


# =============================================================================
# FLAGS/PENNANTS DETECTOR WRAPPER
# =============================================================================

@register_pattern
def detect_flags_unified(
    candles: List[Dict],
    pivots_high: List = None,
    pivots_low: List = None,
    levels: List[Dict] = None,
    structure_ctx = None,
    timeframe: str = "1D",
    config: Dict = None
) -> List[PatternCandidate]:
    """
    Detect flag and pennant patterns.
    """
    from .pattern_detector import get_pattern_detector
    
    candidates = []
    
    try:
        detector = get_pattern_detector()
        patterns = detector._detect_flags(candles)
        
        for p in patterns:
            candidate = adapt_detected_pattern(p)
            if candidate:
                candidate.start_index = len(candles) - 40
                candidate.end_index = len(candles) - 1
                candidate.last_touch_index = len(candles) - 5
                candidates.append(candidate)
                
    except Exception:
        pass
    
    return candidates


# =============================================================================
# RANGE DETECTOR (INLINE)
# =============================================================================

@register_pattern
def detect_range_unified(
    candles: List[Dict],
    pivots_high: List = None,
    pivots_low: List = None,
    levels: List[Dict] = None,
    structure_ctx = None,
    timeframe: str = "1D",
    config: Dict = None
) -> List[PatternCandidate]:
    """
    Detect horizontal range patterns.
    
    Range is often MORE VALID than triangle!
    """
    candidates = []
    
    if len(candles) < 30:
        return candidates
    
    config = config or {}
    lookback = min(config.get("pattern_window", 100), len(candles))
    recent = candles[-lookback:]
    
    highs = [c["high"] for c in recent]
    lows = [c["low"] for c in recent]
    
    range_high = max(highs)
    range_low = min(lows)
    range_width = (range_high - range_low) / range_low if range_low > 0 else 0
    
    # Valid range: 2% - 20% width
    if range_width < 0.02 or range_width > 0.20:
        return candidates
    
    # Count boundary touches
    tolerance = range_width * 0.1
    upper_touches = sum(1 for c in recent if c["high"] >= range_high * (1 - tolerance))
    lower_touches = sum(1 for c in recent if c["low"] <= range_low * (1 + tolerance))
    
    # Need at least 3 touches on each boundary
    if upper_touches < 3 or lower_touches < 3:
        return candidates
    
    # Check no strong trend (linear regression)
    closes = [c["close"] for c in recent]
    n = len(closes)
    x_mean = (n - 1) / 2
    y_mean = sum(closes) / n
    numerator = sum((i - x_mean) * (closes[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    slope = numerator / denominator / max(y_mean, 1e-8) if denominator > 0 else 0
    
    # Slope should be near zero for range
    if abs(slope) > 0.0003:
        return candidates
    
    # Calculate scores
    total_touches = upper_touches + lower_touches
    touch_score = min(1.0, total_touches / 10)
    confidence = round(min(0.85, 0.5 + touch_score * 0.25), 2)
    
    if confidence < 0.55:
        return candidates
    
    # Get timestamps
    start_time = recent[0].get("time", recent[0].get("timestamp", 0))
    end_time = recent[-1].get("time", recent[-1].get("timestamp", 0))
    if start_time > 1e12:
        start_time = start_time // 1000
    if end_time > 1e12:
        end_time = end_time // 1000
    
    candidates.append(PatternCandidate(
        type="range",
        direction="neutral",
        confidence=confidence,
        geometry_score=confidence,
        touch_count=total_touches,
        containment=0.9,
        line_scores={"upper": touch_score * 10, "lower": touch_score * 10},
        points={
            "upper": [{"time": start_time, "value": round(range_high, 2)}, {"time": end_time, "value": round(range_high, 2)}],
            "lower": [{"time": start_time, "value": round(range_low, 2)}, {"time": end_time, "value": round(range_low, 2)}],
        },
        anchor_points={},
        start_index=len(candles) - lookback,
        end_index=len(candles) - 1,
        last_touch_index=len(candles) - 5,
        breakout_level=round(range_high, 2),
        invalidation=round(range_low, 2),
    ))
    
    return candidates


# =============================================================================
# WEDGE DETECTOR
# =============================================================================

@register_pattern
def detect_wedge_unified(
    candles: List[Dict],
    pivots_high: List = None,
    pivots_low: List = None,
    levels: List[Dict] = None,
    structure_ctx = None,
    timeframe: str = "1D",
    config: Dict = None
) -> List[PatternCandidate]:
    """
    Detect rising and falling wedge patterns.
    
    Wedge = both lines slope same direction but converge.
    """
    candidates = []
    
    if len(candles) < 40:
        return candidates
    
    config = config or {}
    lookback = min(config.get("pattern_window", 80), len(candles))
    recent = candles[-lookback:]
    
    highs = [c["high"] for c in recent]
    lows = [c["low"] for c in recent]
    
    # Find swing points
    swing_highs = []
    swing_lows = []
    window = 3
    
    for i in range(window, len(recent) - window):
        if all(highs[i] >= highs[i-j] for j in range(1, window+1)) and \
           all(highs[i] >= highs[i+j] for j in range(1, window+1)):
            swing_highs.append((i, highs[i]))
        if all(lows[i] <= lows[i-j] for j in range(1, window+1)) and \
           all(lows[i] <= lows[i+j] for j in range(1, window+1)):
            swing_lows.append((i, lows[i]))
    
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return candidates
    
    # Calculate slopes
    if swing_highs[-1][0] != swing_highs[0][0]:
        high_slope = (swing_highs[-1][1] - swing_highs[0][1]) / (swing_highs[-1][0] - swing_highs[0][0])
    else:
        high_slope = 0
    
    if swing_lows[-1][0] != swing_lows[0][0]:
        low_slope = (swing_lows[-1][1] - swing_lows[0][1]) / (swing_lows[-1][0] - swing_lows[0][0])
    else:
        low_slope = 0
    
    # Normalize slopes
    avg_price = sum(c["close"] for c in recent) / len(recent)
    high_slope_norm = high_slope / avg_price if avg_price else 0
    low_slope_norm = low_slope / avg_price if avg_price else 0
    
    # Wedge criteria: both slopes same direction, converging
    wedge_type = None
    direction = "neutral"
    
    # Rising wedge (both up, but converging) - bearish
    if high_slope_norm > 0.0001 and low_slope_norm > 0.0001:
        if low_slope_norm > high_slope_norm:  # Lower line rising faster = converging
            wedge_type = "rising_wedge"
            direction = "bearish"
    
    # Falling wedge (both down, but converging) - bullish
    elif high_slope_norm < -0.0001 and low_slope_norm < -0.0001:
        if high_slope_norm > low_slope_norm:  # Upper line falling slower = converging
            wedge_type = "falling_wedge"
            direction = "bullish"
    
    if wedge_type:
        confidence = 0.65
        
        start_time = recent[0].get("time", 0)
        end_time = recent[-1].get("time", 0)
        if start_time > 1e12:
            start_time = start_time // 1000
        if end_time > 1e12:
            end_time = end_time // 1000
        
        candidates.append(PatternCandidate(
            type=wedge_type,
            direction=direction,
            confidence=confidence,
            geometry_score=confidence,
            touch_count=len(swing_highs) + len(swing_lows),
            containment=0.8,
            line_scores={"upper": 8.0, "lower": 8.0},
            points={
                "upper": [{"time": start_time, "value": swing_highs[0][1]}, {"time": end_time, "value": swing_highs[-1][1]}],
                "lower": [{"time": start_time, "value": swing_lows[0][1]}, {"time": end_time, "value": swing_lows[-1][1]}],
            },
            anchor_points={},
            start_index=len(candles) - lookback,
            end_index=len(candles) - 1,
            last_touch_index=len(candles) - 5,
            breakout_level=swing_highs[-1][1] if direction == "bullish" else swing_lows[-1][1],
            invalidation=swing_lows[-1][1] if direction == "bullish" else swing_highs[-1][1],
        ))
    
    return candidates


# =============================================================================
# BREAKOUT DETECTOR
# =============================================================================

@register_pattern
def detect_breakout_unified(
    candles: List[Dict],
    pivots_high: List = None,
    pivots_low: List = None,
    levels: List[Dict] = None,
    structure_ctx = None,
    timeframe: str = "1D",
    config: Dict = None
) -> List[PatternCandidate]:
    """
    Detect breakout patterns (price breaking key levels).
    """
    candidates = []
    
    if len(candles) < 30 or not levels:
        return candidates
    
    current_price = candles[-1]["close"]
    prev_close = candles[-2]["close"] if len(candles) > 1 else current_price
    
    for level in levels[:5]:  # Top 5 levels
        level_price = level.get("price", 0)
        level_type = level.get("type", "")
        level_strength = level.get("strength", 50)
        
        if not level_price:
            continue
        
        # Breakout above resistance
        if level_type == "resistance" and prev_close < level_price and current_price > level_price:
            confidence = min(0.8, 0.5 + level_strength / 200)
            
            candidates.append(PatternCandidate(
                type="breakout_up",
                direction="bullish",
                confidence=confidence,
                geometry_score=confidence,
                touch_count=level.get("touches", 3),
                containment=0.9,
                line_scores={"level": level_strength / 10},
                points={"level": level_price, "breakout_price": current_price},
                anchor_points={},
                start_index=len(candles) - 5,
                end_index=len(candles) - 1,
                last_touch_index=len(candles) - 1,
                breakout_level=level_price,
                invalidation=level_price * 0.98,
            ))
        
        # Breakdown below support
        elif level_type == "support" and prev_close > level_price and current_price < level_price:
            confidence = min(0.8, 0.5 + level_strength / 200)
            
            candidates.append(PatternCandidate(
                type="breakdown",
                direction="bearish",
                confidence=confidence,
                geometry_score=confidence,
                touch_count=level.get("touches", 3),
                containment=0.9,
                line_scores={"level": level_strength / 10},
                points={"level": level_price, "breakdown_price": current_price},
                anchor_points={},
                start_index=len(candles) - 5,
                end_index=len(candles) - 1,
                last_touch_index=len(candles) - 1,
                breakout_level=level_price,
                invalidation=level_price * 1.02,
            ))
    
    return candidates


# Print registered detectors on import
print(f"[PatternRegistry] Registered {len(PATTERN_REGISTRY)} pattern detectors")
