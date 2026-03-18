"""
Decision Engine V2 - Final Decision Layer
==========================================

decision = f(mtf_context, structure_context, primary_pattern)

Priority weights:
  MTF Context        45%
  Structure Context  35%
  Pattern Evidence   20%

This is the MAIN verdict of the system.
Pattern no longer drives decision - it only confirms or weakens it.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class DecisionEngineV2:
    """
    Final decision layer:
    decision = f(mtf_context, structure_context, primary_pattern)

    Priority:
      1. MTF context — highest weight (45%)
      2. Structure context — confirmation (35%)
      3. Pattern evidence — secondary only (20%)
    
    Pattern cannot override MTF + Structure consensus.
    """

    MTF_WEIGHT = 0.45
    STRUCTURE_WEIGHT = 0.35
    PATTERN_WEIGHT = 0.20

    def build(
        self,
        mtf_context: Dict[str, Any],
        structure_context: Dict[str, Any],
        primary_pattern: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build final decision from MTF, structure, and pattern.
        
        Returns:
            {
                "bias": "bearish",
                "confidence": 0.71,
                "context": "relief_bounce",
                "alignment": "mixed",
                "strength": "medium",
                "dominant_tf": "30D",
                "tradeability": "conditional",
                "summary": "Short-term bounce inside bearish higher timeframe structure"
            }
        """
        # Extract MTF context data
        mtf_bias = mtf_context.get("global_bias", "neutral")
        mtf_conf = float(mtf_context.get("confidence", 0.5) or 0.5)
        local_context = mtf_context.get("local_context", "trend_continuation")
        alignment = mtf_context.get("alignment", "mixed")
        dominant_tf = mtf_context.get("dominant_tf", "1D")
        mtf_summary = mtf_context.get("summary", "")

        # Extract structure context data
        structure_bias = structure_context.get("bias", "neutral")
        structure_score = float(structure_context.get("structure_score", 0.5) or 0.5)
        regime = structure_context.get("regime", "range")
        market_phase = structure_context.get("market_phase", "range")

        # Extract pattern evidence
        pattern_bias, pattern_conf = self._extract_pattern_evidence(primary_pattern)

        # =============================================
        # BIAS SCORING — weighted combination
        # =============================================
        mtf_score = self._bias_to_score(mtf_bias) * mtf_conf
        structure_score_signed = self._bias_to_score(structure_bias) * structure_score
        pattern_score = self._bias_to_score(pattern_bias) * pattern_conf

        final_score = (
            mtf_score * self.MTF_WEIGHT +
            structure_score_signed * self.STRUCTURE_WEIGHT +
            pattern_score * self.PATTERN_WEIGHT
        )

        # =============================================
        # PENALTIES / MODIFIERS
        # =============================================
        final_score = self._apply_alignment_penalty(final_score, alignment)
        final_score = self._apply_pattern_conflict_penalty(
            final_score=final_score,
            mtf_bias=mtf_bias,
            structure_bias=structure_bias,
            pattern_bias=pattern_bias,
        )
        final_score = self._apply_regime_modifier(final_score, regime, local_context)

        # =============================================
        # FINAL CLASSIFICATION
        # =============================================
        final_bias = self._score_to_bias(final_score)
        confidence = self._compute_confidence(
            final_score=final_score,
            mtf_conf=mtf_conf,
            structure_score=structure_score,
            pattern_conf=pattern_conf,
            alignment=alignment,
        )

        strength = self._classify_strength(confidence)
        tradeability = self._classify_tradeability(
            confidence=confidence,
            alignment=alignment,
            regime=regime,
            bias=final_bias,
            pattern_exists=primary_pattern is not None,
        )

        summary = self._build_summary(
            final_bias=final_bias,
            local_context=local_context,
            dominant_tf=dominant_tf,
            alignment=alignment,
            regime=regime,
            market_phase=market_phase,
            fallback=mtf_summary,
        )

        return {
            "bias": final_bias,
            "confidence": round(confidence, 2),
            "context": local_context,
            "alignment": alignment,
            "strength": strength,
            "dominant_tf": dominant_tf,
            "tradeability": tradeability,
            "summary": summary,
        }

    # ---------------------------------------------------------
    # Pattern Evidence Extraction
    # ---------------------------------------------------------
    def _extract_pattern_evidence(self, primary_pattern: Optional[Dict[str, Any]]) -> tuple[str, float]:
        """Extract bias and confidence from pattern."""
        if not primary_pattern:
            return "neutral", 0.0
        direction = primary_pattern.get("direction", "neutral")
        confidence = float(primary_pattern.get("confidence", 0.0) or 0.0)
        return direction, min(max(confidence, 0.0), 1.0)

    # ---------------------------------------------------------
    # Bias <-> Score Conversion
    # ---------------------------------------------------------
    def _bias_to_score(self, bias: str) -> float:
        """Convert bias to numeric score."""
        if bias == "bullish":
            return 1.0
        if bias == "bearish":
            return -1.0
        return 0.0

    def _score_to_bias(self, score: float) -> str:
        """Convert numeric score to bias."""
        if score >= 0.15:
            return "bullish"
        if score <= -0.15:
            return "bearish"
        return "neutral"

    # ---------------------------------------------------------
    # Penalty / Modifier Functions
    # ---------------------------------------------------------
    def _apply_alignment_penalty(self, score: float, alignment: str) -> float:
        """
        Alignment penalty:
        - mixed → reduce confidence (-15%)
        - full alignment → bonus (+5%)
        """
        if alignment == "mixed":
            return score * 0.85
        if alignment in ["full_bullish", "full_bearish", "aligned"]:
            return score * 1.05
        return score

    def _apply_pattern_conflict_penalty(
        self,
        final_score: float,
        mtf_bias: str,
        structure_bias: str,
        pattern_bias: str,
    ) -> float:
        """
        Pattern conflict penalty:
        If pattern contradicts BOTH mtf and structure → heavy penalty (-20%)
        Pattern cannot override consensus.
        """
        if pattern_bias == "neutral":
            return final_score

        # If pattern contradicts both mtf and structure, penalize hard
        if pattern_bias != mtf_bias and pattern_bias != structure_bias:
            if mtf_bias != "neutral" and structure_bias != "neutral":
                return final_score * 0.8

        return final_score

    def _apply_regime_modifier(self, score: float, regime: str, local_context: str) -> float:
        """
        Regime modifier:
        - compression / range → reduce directional confidence (-15%)
        - relief_bounce / pullback → reduce certainty (-10%)
        """
        # Compression / range = less directional certainty
        if regime in ["range", "compression"]:
            return score * 0.85

        # Relief bounce / pullback = counter-trend move
        if local_context in ["relief_bounce", "pullback"]:
            return score * 0.9

        return score

    # ---------------------------------------------------------
    # Confidence Calculation
    # ---------------------------------------------------------
    def _compute_confidence(
        self,
        final_score: float,
        mtf_conf: float,
        structure_score: float,
        pattern_conf: float,
        alignment: str,
    ) -> float:
        """
        Compute overall confidence.
        
        Combines:
        - Directional strength (how strong is the final score)
        - Blended input confidences (weighted by importance)
        - Alignment bonus/penalty
        """
        # Directional strength: how far from neutral
        directional_strength = min(1.0, abs(final_score) / 0.6)

        # Blended input confidence
        blended = (
            mtf_conf * 0.45 +
            structure_score * 0.35 +
            pattern_conf * 0.20
        )

        # Final confidence = blend of directional strength and input confidence
        confidence = blended * 0.6 + directional_strength * 0.4

        # Alignment modifier
        if alignment == "mixed":
            confidence *= 0.9

        return min(max(confidence, 0.0), 1.0)

    # ---------------------------------------------------------
    # Strength Classification
    # ---------------------------------------------------------
    def _classify_strength(self, confidence: float) -> str:
        """
        Classify strength from confidence:
        - confidence >= 0.75 → strong
        - 0.55 <= confidence < 0.75 → medium
        - confidence < 0.55 → weak
        """
        if confidence >= 0.75:
            return "strong"
        if confidence >= 0.55:
            return "medium"
        return "weak"

    # ---------------------------------------------------------
    # Tradeability Classification
    # ---------------------------------------------------------
    def _classify_tradeability(
        self,
        confidence: float,
        alignment: str,
        regime: str,
        bias: str,
        pattern_exists: bool,
    ) -> str:
        """
        Classify tradeability:
        - aligned + strong → good
        - mixed + medium → conditional
        - weak + no pattern → low
        """
        # Neutral bias = not tradeable
        if bias == "neutral":
            return "low"

        # Low confidence = low tradeability
        if confidence < 0.55:
            return "low"

        # Range/compression without pattern = conditional
        if regime in ["range", "compression"] and not pattern_exists:
            return "conditional"

        # Mixed alignment = conditional
        if alignment == "mixed":
            return "conditional"

        return "good"

    # ---------------------------------------------------------
    # Summary Generation
    # ---------------------------------------------------------
    def _build_summary(
        self,
        final_bias: str,
        local_context: str,
        dominant_tf: str,
        alignment: str,
        regime: str,
        market_phase: str,
        fallback: str,
    ) -> str:
        """Build human-readable one-line summary."""
        
        if final_bias == "bearish":
            if local_context == "relief_bounce":
                return f"Short-term bounce inside bearish {dominant_tf} higher-timeframe structure."
            if local_context == "trend_continuation":
                return f"Bearish trend continuation led by {dominant_tf} structure."
            if local_context == "pullback":
                return f"Bearish pullback within {dominant_tf} downtrend structure."
            return f"Bearish context inside {market_phase or regime} conditions."

        if final_bias == "bullish":
            if local_context == "pullback":
                return f"Pullback inside bullish {dominant_tf} higher-timeframe structure."
            if local_context == "trend_continuation":
                return f"Bullish trend continuation led by {dominant_tf} structure."
            if local_context == "relief_bounce":
                return f"Bullish relief bounce within {dominant_tf} context."
            return f"Bullish context inside {market_phase or regime} conditions."

        # Neutral
        if fallback:
            return fallback

        return f"Mixed market context inside {market_phase or regime} conditions."


# ---------------------------------------------------------
# Factory / Singleton
# ---------------------------------------------------------
_decision_engine_v2_instance: Optional[DecisionEngineV2] = None


def get_decision_engine_v2() -> DecisionEngineV2:
    """Get singleton instance of DecisionEngineV2."""
    global _decision_engine_v2_instance
    if _decision_engine_v2_instance is None:
        _decision_engine_v2_instance = DecisionEngineV2()
    return _decision_engine_v2_instance


# Singleton for direct import
decision_engine_v2 = DecisionEngineV2()
