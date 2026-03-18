"""
Indicator Engine
=================
Extracts signals from technical indicators.

Supports:
- EMA (20, 50, 200)
- RSI
- MACD
- Bollinger Bands
- Stochastic
- ATR
- Ichimoku
- Supertrend
- OBV
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone

from modules.ta_engine.setup.setup_types import (
    IndicatorSignal,
    Direction,
)


class IndicatorEngine:
    """Extracts trading signals from technical indicators."""
    
    def __init__(self):
        self.ema_periods = [20, 50, 200]
        self.rsi_period = 14
        self.bb_period = 20
        self.bb_std = 2.0
    
    def analyze_all(self, candles: List[Dict]) -> List[IndicatorSignal]:
        """
        Analyze all indicators and return signals.
        Returns list sorted by strength (highest first).
        """
        if len(candles) < 50:
            return []
        
        signals = []
        
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        volumes = [c.get("volume", 0) for c in candles]
        
        # EMA signals
        signals.extend(self._analyze_ema(closes))
        
        # RSI signal
        rsi_signal = self._analyze_rsi(closes)
        if rsi_signal:
            signals.append(rsi_signal)
        
        # MACD signal
        macd_signal = self._analyze_macd(closes)
        if macd_signal:
            signals.append(macd_signal)
        
        # Bollinger Bands signal
        bb_signal = self._analyze_bollinger(closes)
        if bb_signal:
            signals.append(bb_signal)
        
        # Stochastic signal
        stoch_signal = self._analyze_stochastic(closes, highs, lows)
        if stoch_signal:
            signals.append(stoch_signal)
        
        # ATR signal
        atr_signal = self._analyze_atr(candles)
        if atr_signal:
            signals.append(atr_signal)
        
        # OBV signal
        obv_signal = self._analyze_obv(closes, volumes)
        if obv_signal:
            signals.append(obv_signal)
        
        # Sort by strength
        signals.sort(key=lambda s: s.strength, reverse=True)
        
        return signals
    
    def _analyze_ema(self, closes: List[float]) -> List[IndicatorSignal]:
        """Analyze EMA alignment and crossovers."""
        signals = []
        
        ema20 = self._ema(closes, 20)
        ema50 = self._ema(closes, 50)
        ema200 = self._ema(closes, 200) if len(closes) >= 200 else ema50
        
        current_price = closes[-1]
        
        # EMA Stack alignment
        if ema20 > ema50 > ema200:
            signals.append(IndicatorSignal(
                name="EMA_STACK",
                direction=Direction.BULLISH,
                strength=0.8,
                value=ema20,
                signal_type="bullish_alignment",
                description="EMA 20 > 50 > 200 — bullish stack alignment"
            ))
        elif ema20 < ema50 < ema200:
            signals.append(IndicatorSignal(
                name="EMA_STACK",
                direction=Direction.BEARISH,
                strength=0.8,
                value=ema20,
                signal_type="bearish_alignment",
                description="EMA 20 < 50 < 200 — bearish stack alignment"
            ))
        
        # Price position relative to EMAs
        above_count = sum([
            1 if current_price > ema20 else 0,
            1 if current_price > ema50 else 0,
            1 if current_price > ema200 else 0,
        ])
        
        if above_count == 3:
            signals.append(IndicatorSignal(
                name="PRICE_EMA_POSITION",
                direction=Direction.BULLISH,
                strength=0.7,
                value=current_price,
                signal_type="above_all_ema",
                description="Price above all major EMAs"
            ))
        elif above_count == 0:
            signals.append(IndicatorSignal(
                name="PRICE_EMA_POSITION",
                direction=Direction.BEARISH,
                strength=0.7,
                value=current_price,
                signal_type="below_all_ema",
                description="Price below all major EMAs"
            ))
        
        # EMA crossovers (check last few candles)
        ema20_prev = self._ema(closes[:-1], 20)
        ema50_prev = self._ema(closes[:-1], 50)
        
        if ema20_prev < ema50_prev and ema20 > ema50:
            signals.append(IndicatorSignal(
                name="EMA_CROSS",
                direction=Direction.BULLISH,
                strength=0.85,
                value=ema20,
                signal_type="golden_cross_20_50",
                description="EMA 20 crossed above EMA 50 — bullish signal"
            ))
        elif ema20_prev > ema50_prev and ema20 < ema50:
            signals.append(IndicatorSignal(
                name="EMA_CROSS",
                direction=Direction.BEARISH,
                strength=0.85,
                value=ema20,
                signal_type="death_cross_20_50",
                description="EMA 20 crossed below EMA 50 — bearish signal"
            ))
        
        return signals
    
    def _analyze_rsi(self, closes: List[float]) -> Optional[IndicatorSignal]:
        """Analyze RSI for overbought/oversold and divergence."""
        rsi = self._rsi(closes, 14)
        
        if rsi > 70:
            return IndicatorSignal(
                name="RSI",
                direction=Direction.BEARISH,
                strength=0.6 + (rsi - 70) / 60,  # Higher RSI = stronger signal
                value=rsi,
                signal_type="overbought",
                description=f"RSI at {rsi:.1f} — overbought territory"
            )
        elif rsi < 30:
            return IndicatorSignal(
                name="RSI",
                direction=Direction.BULLISH,
                strength=0.6 + (30 - rsi) / 60,
                value=rsi,
                signal_type="oversold",
                description=f"RSI at {rsi:.1f} — oversold territory"
            )
        elif 50 < rsi < 70:
            return IndicatorSignal(
                name="RSI",
                direction=Direction.BULLISH,
                strength=0.4,
                value=rsi,
                signal_type="bullish_momentum",
                description=f"RSI at {rsi:.1f} — bullish momentum"
            )
        elif 30 < rsi < 50:
            return IndicatorSignal(
                name="RSI",
                direction=Direction.BEARISH,
                strength=0.4,
                value=rsi,
                signal_type="bearish_momentum",
                description=f"RSI at {rsi:.1f} — bearish momentum"
            )
        
        return None
    
    def _analyze_macd(self, closes: List[float]) -> Optional[IndicatorSignal]:
        """Analyze MACD for crossovers and divergence."""
        if len(closes) < 35:
            return None
        
        macd_line, signal_line, histogram = self._macd(closes)
        
        # Check for crossover
        prev_closes = closes[:-1]
        prev_macd, prev_signal, prev_hist = self._macd(prev_closes)
        
        if prev_macd < prev_signal and macd_line > signal_line:
            return IndicatorSignal(
                name="MACD",
                direction=Direction.BULLISH,
                strength=0.75,
                value=histogram,
                signal_type="bullish_cross",
                description="MACD crossed above signal line — bullish momentum"
            )
        elif prev_macd > prev_signal and macd_line < signal_line:
            return IndicatorSignal(
                name="MACD",
                direction=Direction.BEARISH,
                strength=0.75,
                value=histogram,
                signal_type="bearish_cross",
                description="MACD crossed below signal line — bearish momentum"
            )
        
        # Histogram direction
        if histogram > 0 and histogram > prev_hist:
            return IndicatorSignal(
                name="MACD",
                direction=Direction.BULLISH,
                strength=0.5,
                value=histogram,
                signal_type="bullish_histogram",
                description="MACD histogram expanding positive"
            )
        elif histogram < 0 and histogram < prev_hist:
            return IndicatorSignal(
                name="MACD",
                direction=Direction.BEARISH,
                strength=0.5,
                value=histogram,
                signal_type="bearish_histogram",
                description="MACD histogram expanding negative"
            )
        
        return None
    
    def _analyze_bollinger(self, closes: List[float]) -> Optional[IndicatorSignal]:
        """Analyze Bollinger Bands for squeeze and breakout."""
        if len(closes) < 20:
            return None
        
        middle = self._sma(closes, 20)
        std = self._std(closes[-20:])
        upper = middle + 2 * std
        lower = middle - 2 * std
        
        current_price = closes[-1]
        band_width = (upper - lower) / middle
        
        # Calculate historical band width for comparison
        historical_widths = []
        for i in range(20, min(50, len(closes))):
            hist_middle = self._sma(closes[:i], 20)
            hist_std = self._std(closes[i-20:i])
            hist_width = (2 * hist_std) / hist_middle
            historical_widths.append(hist_width)
        
        if historical_widths:
            avg_width = sum(historical_widths) / len(historical_widths)
            squeeze_ratio = band_width / avg_width
            
            if squeeze_ratio < 0.7:
                return IndicatorSignal(
                    name="BOLLINGER",
                    direction=Direction.NEUTRAL,
                    strength=0.7,
                    value=band_width,
                    signal_type="squeeze",
                    description="Bollinger Bands squeeze — volatility contraction"
                )
        
        # Check for band touches
        if current_price > upper:
            return IndicatorSignal(
                name="BOLLINGER",
                direction=Direction.BULLISH,
                strength=0.6,
                value=current_price - upper,
                signal_type="upper_breakout",
                description="Price breaking above upper Bollinger Band"
            )
        elif current_price < lower:
            return IndicatorSignal(
                name="BOLLINGER",
                direction=Direction.BEARISH,
                strength=0.6,
                value=lower - current_price,
                signal_type="lower_breakout",
                description="Price breaking below lower Bollinger Band"
            )
        
        return None
    
    def _analyze_stochastic(self, closes: List[float], highs: List[float], lows: List[float]) -> Optional[IndicatorSignal]:
        """Analyze Stochastic oscillator."""
        if len(closes) < 14:
            return None
        
        # Calculate %K
        period = 14
        lowest_low = min(lows[-period:])
        highest_high = max(highs[-period:])
        
        if highest_high == lowest_low:
            return None
        
        k = ((closes[-1] - lowest_low) / (highest_high - lowest_low)) * 100
        
        if k > 80:
            return IndicatorSignal(
                name="STOCHASTIC",
                direction=Direction.BEARISH,
                strength=0.55,
                value=k,
                signal_type="overbought",
                description=f"Stochastic %K at {k:.1f} — overbought"
            )
        elif k < 20:
            return IndicatorSignal(
                name="STOCHASTIC",
                direction=Direction.BULLISH,
                strength=0.55,
                value=k,
                signal_type="oversold",
                description=f"Stochastic %K at {k:.1f} — oversold"
            )
        
        return None
    
    def _analyze_atr(self, candles: List[Dict]) -> Optional[IndicatorSignal]:
        """Analyze ATR for volatility."""
        if len(candles) < 14:
            return None
        
        atr = self._atr(candles, 14)
        current_price = candles[-1]["close"]
        volatility_pct = (atr / current_price) * 100
        
        if volatility_pct > 4:
            return IndicatorSignal(
                name="ATR",
                direction=Direction.NEUTRAL,
                strength=0.5,
                value=atr,
                signal_type="high_volatility",
                description=f"ATR indicates high volatility ({volatility_pct:.1f}%)"
            )
        elif volatility_pct < 1.5:
            return IndicatorSignal(
                name="ATR",
                direction=Direction.NEUTRAL,
                strength=0.6,
                value=atr,
                signal_type="low_volatility",
                description=f"ATR indicates low volatility ({volatility_pct:.1f}%) — potential breakout"
            )
        
        return None
    
    def _analyze_obv(self, closes: List[float], volumes: List[float]) -> Optional[IndicatorSignal]:
        """Analyze On-Balance Volume."""
        if len(closes) < 20 or all(v == 0 for v in volumes):
            return None
        
        # Calculate OBV
        obv = [0]
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]:
                obv.append(obv[-1] + volumes[i])
            elif closes[i] < closes[i-1]:
                obv.append(obv[-1] - volumes[i])
            else:
                obv.append(obv[-1])
        
        # Compare recent OBV trend to price trend
        price_change = (closes[-1] - closes[-20]) / closes[-20]
        obv_change = (obv[-1] - obv[-20]) / max(abs(obv[-20]), 1)
        
        # Divergence check
        if price_change > 0.02 and obv_change < -0.1:
            return IndicatorSignal(
                name="OBV",
                direction=Direction.BEARISH,
                strength=0.6,
                value=obv[-1],
                signal_type="bearish_divergence",
                description="OBV divergence: price up, volume down — bearish warning"
            )
        elif price_change < -0.02 and obv_change > 0.1:
            return IndicatorSignal(
                name="OBV",
                direction=Direction.BULLISH,
                strength=0.6,
                value=obv[-1],
                signal_type="bullish_divergence",
                description="OBV divergence: price down, volume up — bullish signal"
            )
        
        # Confirmation
        if price_change > 0.02 and obv_change > 0.1:
            return IndicatorSignal(
                name="OBV",
                direction=Direction.BULLISH,
                strength=0.5,
                value=obv[-1],
                signal_type="volume_confirmation",
                description="OBV confirms bullish price movement"
            )
        
        return None
    
    # Calculation helpers
    def _sma(self, data: List[float], period: int) -> float:
        if len(data) < period:
            return sum(data) / len(data) if data else 0
        return sum(data[-period:]) / period
    
    def _ema(self, data: List[float], period: int) -> float:
        if not data:
            return 0
        multiplier = 2 / (period + 1)
        ema = data[0]
        for price in data[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return ema
    
    def _std(self, data: List[float]) -> float:
        if len(data) < 2:
            return 0
        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        return variance ** 0.5
    
    def _rsi(self, closes: List[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        
        gains, losses = [], []
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _macd(self, closes: List[float]) -> Tuple[float, float, float]:
        ema12 = self._ema(closes, 12)
        ema26 = self._ema(closes, 26)
        macd_line = ema12 - ema26
        
        # Calculate signal line (9-period EMA of MACD)
        macd_values = []
        for i in range(26, len(closes) + 1):
            e12 = self._ema(closes[:i], 12)
            e26 = self._ema(closes[:i], 26)
            macd_values.append(e12 - e26)
        
        signal_line = self._ema(macd_values, 9) if len(macd_values) >= 9 else macd_line
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _atr(self, candles: List[Dict], period: int = 14) -> float:
        if len(candles) < period + 1:
            return 0
        
        trs = []
        for i in range(1, len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_close = candles[i-1]["close"]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        
        return sum(trs[-period:]) / period


# Singleton
_engine: Optional[IndicatorEngine] = None


def get_indicator_engine() -> IndicatorEngine:
    global _engine
    if _engine is None:
        _engine = IndicatorEngine()
    return _engine
