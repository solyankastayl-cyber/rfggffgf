"""
Pattern Candidate Model
=======================

Unified model for all pattern types with scoring fields.
This allows fair comparison between triangles, channels, ranges, etc.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class PatternCandidate:
    """
    Universal pattern candidate with all scoring fields.
    
    Every pattern type (triangle, channel, range, H&S) uses this model.
    This enables fair ranking between different pattern types.
    """
    # Core identification
    type: str                           # symmetrical_triangle, ascending_triangle, range, etc.
    direction: str                      # bullish / bearish / neutral
    
    # Geometry scores (from validator)
    confidence: float                   # Base confidence from validator
    geometry_score: float               # How well the geometry fits
    touch_count: int                    # Number of line touches
    containment: float                  # % of candles inside pattern
    line_scores: Dict[str, float]       # Per-line quality scores
    
    # Points for rendering
    points: Dict[str, Any]              # Extended lines for rendering
    anchor_points: Dict[str, Any]       # Original pivot points
    
    # Position info (for expiration)
    start_index: int                    # Where pattern starts
    end_index: int                      # Where pattern ends
    last_touch_index: int               # Last time price touched boundary
    
    # Ranking scores (filled by ranking engine)
    structure_score: float = 0.0        # Alignment with market structure
    level_score: float = 0.0            # Alignment with S/R levels
    recency_score: float = 0.0          # How fresh/relevant is it
    cleanliness_score: float = 0.0      # Overall quality
    total_score: float = 0.0            # Final ranking score
    
    # Trading levels
    breakout_level: Optional[float] = None
    invalidation: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convert to API response format."""
        return {
            "type": self.type,
            "direction": self.direction,
            "confidence": round(self.confidence, 2),
            "total_score": round(self.total_score, 2),
            "scores": {
                "geometry": round(self.geometry_score, 2),
                "structure": round(self.structure_score, 2),
                "level": round(self.level_score, 2),
                "recency": round(self.recency_score, 2),
                "cleanliness": round(self.cleanliness_score, 2),
            },
            "touches": self.touch_count,
            "containment": round(self.containment, 2),
            "line_scores": {k: round(v, 1) for k, v in self.line_scores.items()},
            "points": self.points,
            "anchor_points": self.anchor_points,
            "breakout_level": round(self.breakout_level, 2) if self.breakout_level else None,
            "invalidation": round(self.invalidation, 2) if self.invalidation else None,
        }
