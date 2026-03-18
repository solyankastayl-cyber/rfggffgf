"""
Pattern Selector
================

Final selection: Choose the best pattern (or none).

Key rule: Better to show NOTHING than show garbage.

If the best pattern doesn't meet minimum threshold → return None.
Also returns alternatives for user to see other possibilities.
"""

from typing import List, Optional, Tuple
from .pattern_candidate import PatternCandidate


class PatternSelector:
    """
    Selects the best pattern from ranked candidates.
    
    Rules:
    1. Primary must exceed MIN_SCORE threshold
    2. Alternatives must exceed lower threshold
    3. If nothing qualifies → return None
    """
    
    MIN_PRIMARY_SCORE = 0.55    # Primary pattern must score at least this
    MIN_ALTERNATIVE_SCORE = 0.45  # Alternatives can be slightly lower
    MAX_ALTERNATIVES = 2         # Show up to 2 alternatives
    
    def __init__(self):
        pass

    def select(
        self, 
        ranked_candidates: List[PatternCandidate]
    ) -> Tuple[Optional[PatternCandidate], List[PatternCandidate]]:
        """
        Select primary pattern and alternatives.
        
        Args:
            ranked_candidates: Candidates sorted by total_score (highest first)
            
        Returns:
            (primary, alternatives) tuple
            primary is None if nothing qualifies
        """
        if not ranked_candidates:
            return None, []

        primary = ranked_candidates[0]

        # Hard filter: primary must meet minimum threshold
        if primary.total_score < self.MIN_PRIMARY_SCORE:
            return None, []

        # Get alternatives (next best patterns that also qualify)
        alternatives = []
        for c in ranked_candidates[1:]:
            if c.total_score >= self.MIN_ALTERNATIVE_SCORE:
                alternatives.append(c)
            if len(alternatives) >= self.MAX_ALTERNATIVES:
                break
        
        return primary, alternatives
    
    def explain_selection(
        self, 
        primary: Optional[PatternCandidate],
        alternatives: List[PatternCandidate]
    ) -> dict:
        """Generate explanation for the selection."""
        if primary is None:
            return {
                "status": "no_pattern",
                "reason": "No pattern met minimum quality threshold",
                "suggestion": "Market may be in unclear/choppy state"
            }
        
        # Build explanation
        explanation = {
            "status": "pattern_found",
            "primary": {
                "type": primary.type,
                "score": round(primary.total_score, 2),
                "strengths": [],
                "weaknesses": []
            }
        }
        
        # Identify strengths
        if primary.structure_score > 0.7:
            explanation["primary"]["strengths"].append("Aligns with market structure")
        if primary.recency_score > 0.7:
            explanation["primary"]["strengths"].append("Recently tested")
        if primary.geometry_score > 0.7:
            explanation["primary"]["strengths"].append("Clean geometry")
        
        # Identify weaknesses
        if primary.structure_score < 0.4:
            explanation["primary"]["weaknesses"].append("Conflicts with market regime")
        if primary.recency_score < 0.4:
            explanation["primary"]["weaknesses"].append("Last touch was long ago")
        if primary.level_score < 0.4:
            explanation["primary"]["weaknesses"].append("Far from key levels")
        
        if alternatives:
            explanation["alternatives_count"] = len(alternatives)
            explanation["alternatives"] = [
                {"type": a.type, "score": round(a.total_score, 2)}
                for a in alternatives
            ]
        
        return explanation


# Singleton instance
pattern_selector = PatternSelector()
