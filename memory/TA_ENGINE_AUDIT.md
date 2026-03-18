# Аудит Архитектуры TA Engine Backend

**Дата:** Декабрь 2025  
**Модуль:** `/app/backend/modules/ta_engine/`

---

## 1. Общая Архитектура

```
ta_engine/
├── setup/                      # Ядро технического анализа
│   ├── pattern_detector.py     # Детектор паттернов
│   ├── structure_engine.py     # Анализ рыночной структуры (HH/HL/LH/LL)
│   ├── level_engine.py         # Уровни поддержки/сопротивления + Fibonacci
│   ├── indicator_engine.py     # Индикаторы (EMA, RSI, MACD, BB, ATR, OBV)
│   ├── setup_builder.py        # Сборщик финального Setup объекта
│   ├── setup_types.py          # Dataclass-ы и Enum-ы
│   └── market_data_service.py  # Сервис получения свечных данных
├── ta_setup_api.py             # Упрощённый API-эндпоинт для фронтенда
├── hypothesis/                 # Модуль построения гипотез (не активен)
└── ideas/                      # Модуль сохранения идей (не активен)
```

### Pipeline данных

```
Coinbase API → candles[] → PatternDetector  ─┐
                        → IndicatorEngine    │
                        → StructureEngine    ├─→ SetupBuilder → Setup object → API Response
                        → LevelEngine       ─┘
```

---

## 2. Pattern Detector (`pattern_detector.py`)

### Поддерживаемые паттерны

| Тип паттерна | Enum | Описание |
|--------------|------|----------|
| Ascending Triangle | `ASCENDING_TRIANGLE` | Горизонтальное сопротивление + восходящая поддержка |
| Descending Triangle | `DESCENDING_TRIANGLE` | Нисходящее сопротивление + горизонтальная поддержка |
| Symmetrical Triangle | `SYMMETRICAL_TRIANGLE` | Сходящиеся линии тренда |
| Ascending Channel | `ASCENDING_CHANNEL` | Параллельные восходящие линии |
| Descending Channel | `DESCENDING_CHANNEL` | Параллельные нисходящие линии |
| Horizontal Channel | `HORIZONTAL_CHANNEL` | Боковой канал (range) |
| Double Top | `DOUBLE_TOP` | Два максимума на одном уровне |
| Double Bottom | `DOUBLE_BOTTOM` | Два минимума на одном уровне |
| Bull Flag | `BULL_FLAG` | Сильное движение вверх + консолидация |
| Bear Flag | `BEAR_FLAG` | Сильное движение вниз + консолидация |
| Compression | `COMPRESSION` | Сжатие волатильности (squeeze) |

### Алгоритм детекции

#### 2.1 Треугольники (`_detect_triangles`)

```python
lookback = min(50, len(candles))
swing_highs = _find_swing_points(highs, is_high=True)
swing_lows  = _find_swing_points(lows, is_high=False)

high_slope = _calculate_slope([highs[i] for i in swing_highs])
low_slope  = _calculate_slope([lows[i] for i in swing_lows])
```

**Логика классификации:**

| Условие | Тип паттерна | Направление |
|---------|--------------|-------------|
| `|high_slope| < 0.001` И `low_slope > 0.001` | Ascending Triangle | BULLISH |
| `high_slope < -0.001` И `|low_slope| < 0.001` | Descending Triangle | BEARISH |
| `high_slope < -0.0005` И `low_slope > 0.0005` | Symmetrical Triangle | NEUTRAL |

**Расчёт confidence:**
```python
confidence = 0.65 + min(slope * 10, 0.2)  # Базовый 0.65, макс 0.85
```

**Построение точек геометрии:**
```python
points = []
for i in swing_highs[-3:]:
    points.append({"time": timestamp, "price": highs[i], "type": "high"})
for i in swing_lows[-3:]:
    points.append({"time": timestamp, "price": lows[i], "type": "low"})
```

#### 2.2 Каналы (`_detect_channels`)

```python
lookback = min(40, len(candles))
high_slope = _linear_regression_slope(highs)
low_slope  = _linear_regression_slope(lows)
slope_diff = abs(high_slope - low_slope)

if slope_diff < 0.002:  # Линии параллельны
    avg_slope = (high_slope + low_slope) / 2
    if avg_slope > 0.001:   → ASCENDING_CHANNEL
    elif avg_slope < -0.001: → DESCENDING_CHANNEL
    else:                    → HORIZONTAL_CHANNEL
```

**Линейная регрессия:**
```python
def _linear_regression_slope(values):
    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    
    numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    
    return numerator / denominator / max(y_mean, 1e-8)
```

**Геометрия канала (4 точки):**
```python
points = [
    {"time": start_time, "price": highs[0], "type": "high_start"},
    {"time": end_time,   "price": highs[-1], "type": "high_end"},
    {"time": start_time, "price": lows[0],  "type": "low_start"},
    {"time": end_time,   "price": lows[-1], "type": "low_end"},
]
```

#### 2.3 Double Top/Bottom (`_detect_double_patterns`)

```python
lookback = min(60, len(candles))
swing_high_indices = _find_swing_points(highs, threshold=5)

idx1, idx2 = swing_high_indices[-2], swing_high_indices[-1]
high1, high2 = highs[idx1], highs[idx2]

tolerance = (max_high - min_low) * 0.03  # 3% от диапазона

if abs(high1 - high2) < tolerance and idx2 - idx1 > 5:
    → DOUBLE_TOP (bearish)
    neckline = min(lows[idx1:idx2+1])
    target = neckline - pattern_height
```

**Геометрия Double Top:**
```python
points = [
    {"time": t1, "price": high1, "type": "top1"},
    {"time": t2, "price": high2, "type": "top2"},
    {"time": t_mid, "price": neckline, "type": "neckline"},
]
```

#### 2.4 Compression (`_detect_compression`)

**Метод:** Сравнение текущего ATR с историческим.

```python
recent_atr = sum(ranges[-10:]) / 10
historical_atr = sum(ranges[-30:-10]) / 20
compression_ratio = recent_atr / historical_atr

if compression_ratio < 0.6:  # Волатильность упала на 40%+
    → COMPRESSION pattern detected
```

#### 2.5 Flags (`_detect_flags`)

**Метод:** Поиск сильного движения ("pole") + тесная консолидация ("flag").

```python
lookback = 30
pole_end = lookback // 3
pole_move = (closes[pole_end] - closes[0]) / closes[0]
flag_range = (max(flag_prices) - min(flag_prices)) / min(flag_prices)

if abs(pole_move) > 0.05 and flag_range < 0.03:
    → BULL_FLAG (if pole_move > 0)
    → BEAR_FLAG (if pole_move < 0)
```

### Валидация структурой

После детекции все паттерны проходят валидацию через `_validate_with_structure()`:

```python
hh = structure_meta.get("higher_highs", 0)
hl = structure_meta.get("higher_lows", 0)
lh = structure_meta.get("lower_highs", 0)
ll = structure_meta.get("lower_lows", 0)

bullish_structure = (hh >= 2 and hl >= 2)
bearish_structure = (lh >= 2 and ll >= 2)

# Ascending patterns требуют bullish structure
if pattern_type == ASCENDING_TRIANGLE:
    if bullish_structure:
        confidence *= 1.15  # Boost
    elif ll > 0:
        confidence *= 0.6   # Penalty
```

**Правила валидации:**

| Паттерн | Подтверждение структурой | Противоречие структуре |
|---------|--------------------------|------------------------|
| Ascending Triangle/Channel | HH≥2 И HL≥2 → +15% | LL>0 → -40% |
| Descending Triangle/Channel | LH≥2 И LL≥2 → +15% | HH>0 → -40% |
| Double Top | Сильный uptrend → +10% | Уже bearish → -30% |
| Double Bottom | Сильный downtrend → +10% | Уже bullish → -30% |

**Минимальный порог:** `confidence >= 0.3` для включения в результат.

---

## 3. Structure Engine (`structure_engine.py`)

### Определяемые структурные точки

| Тип | Enum | Определение |
|-----|------|-------------|
| Higher High | `HH` | Текущий swing high > предыдущего |
| Higher Low | `HL` | Текущий swing low > предыдущего |
| Lower High | `LH` | Текущий swing high < предыдущего |
| Lower Low | `LL` | Текущий swing low < предыдущего |
| Equal High | `EQH` | Swing high ≈ предыдущему |
| Equal Low | `EQL` | Swing low ≈ предыдущему |
| Break of Structure | `BOS` | Пробой предыдущего swing high/low |
| Change of Character | `CHOCH` | Смена тренда (bullish→bearish или наоборот) |

### Алгоритм поиска swing points

```python
swing_lookback = 5

def _find_swing_points(prices, is_high):
    for i in range(lookback, len(prices) - lookback):
        if is_high:
            if all(prices[i] >= prices[i-j] for j in range(1, lookback+1)) and \
               all(prices[i] >= prices[i+j] for j in range(1, lookback+1)):
                swings.append(i)
```

**Принцип:** Точка считается swing high/low, если она выше/ниже всех соседних точек в окне ±5 свечей.

### Детекция BOS и CHOCH

**Break of Structure (BOS):**
```python
# Bullish BOS: текущий high пробивает предыдущий swing high
if current_high > prev_swing_high and last_swing_high <= prev_swing_high:
    → BOS detected

# Bearish BOS: текущий low пробивает предыдущий swing low
if current_low < prev_swing_low and last_swing_low >= prev_swing_low:
    → BOS detected
```

**Change of Character (CHOCH):**
```python
recent_highs = [swing_highs[-3], swing_highs[-2], swing_highs[-1]]
recent_lows = [swing_lows[-3], swing_lows[-2], swing_lows[-1]]

# Was bullish (HH, HL) but now making LH
was_bullish = recent_highs[-3] < recent_highs[-2] and recent_lows[-3] < recent_lows[-2]
now_bearish = recent_highs[-1] < recent_highs[-2]

if was_bullish and now_bearish:
    → CHOCH detected (bearish reversal)
```

### Расчёт общего bias

```python
bullish_score = (hh_count + hl_count) * 2
bearish_score = (lh_count + ll_count) * 2

# Недавняя структура весит больше
for p in structure_points[-5:]:
    if p.type in [HH, HL]: bullish_score += 3
    if p.type in [LH, LL]: bearish_score += 3

if bullish_score > bearish_score * 1.3:
    bias = BULLISH
elif bearish_score > bullish_score * 1.3:
    bias = BEARISH
else:
    bias = NEUTRAL
```

---

## 4. Level Engine (`level_engine.py`)

### Типы уровней

| Тип | Enum | Источник |
|-----|------|----------|
| Support | `SUPPORT` | Swing lows |
| Resistance | `RESISTANCE` | Swing highs |
| Fib 23.6% | `FIB_236` | Fibonacci retracement |
| Fib 38.2% | `FIB_382` | Fibonacci retracement |
| Fib 50% | `FIB_500` | Fibonacci retracement |
| Fib 61.8% | `FIB_618` | Fibonacci retracement |
| Fib 78.6% | `FIB_786` | Fibonacci retracement |
| Liquidity High | `LIQUIDITY_HIGH` | Кластер равных хаёв |
| Liquidity Low | `LIQUIDITY_LOW` | Кластер равных лоу |

### Алгоритм Support/Resistance

```python
swing_highs = _find_swing_points(highs, is_high=True)

for idx in swing_highs:
    price = highs[idx]
    touches = _count_touches(highs, price, tolerance=0.5%)
    strength = min(0.5 + touches * 0.15, 1.0)
    
    → PriceLevel(type=RESISTANCE, price, strength, touches)
```

**Расчёт силы уровня:**
- Base: 0.5
- +0.15 за каждое касание
- Max: 1.0

### Fibonacci Retracements

```python
fib_ratios = [0.236, 0.382, 0.5, 0.618, 0.786]

lookback = min(100, len(candles))
recent_high = max(highs[-lookback:])
recent_low = min(lows[-lookback:])
swing_range = recent_high - recent_low

# Определение направления тренда
if high_idx > low_idx:  # Uptrend
    for ratio in fib_ratios:
        fib_price = recent_high - (swing_range * ratio)
        → PriceLevel(type=FIB_xxx, price=fib_price)
```

**Golden ratios (0.382, 0.618)** получают повышенную силу: 0.6 vs 0.5.

### Liquidity Zones

**Метод:** Поиск кластеров одинаковых цен (equal highs/lows).

```python
def _find_equal_levels(prices, tolerance=0.5%):
    price_counts = {}
    for price in prices[-50:]:
        rounded = round(price / tolerance) * tolerance
        price_counts[rounded] += 1
    
    most_common = max(price_counts, key=price_counts.get)
    if price_counts[most_common] >= 3:
        return most_common  # Liquidity zone
```

### Кластеризация уровней

```python
level_tolerance = 1%  # Уровни в пределах 1% объединяются

def _cluster_levels(levels, current_price):
    sorted_levels = sorted(levels, key=lambda l: l.price)
    
    for level in sorted_levels:
        cluster_price = avg(current_cluster)
        if abs(level.price - cluster_price) < cluster_price * tolerance:
            current_cluster.append(level)
        else:
            clustered.append(_merge_cluster(current_cluster))
            current_cluster = [level]
```

**При merge:**
- price = среднее значение
- strength = max + 0.05 за каждый уровень в кластере
- touches = сумма всех касаний

**Boost для близких уровней:** +0.1 к strength, если уровень в пределах 2% от текущей цены.

---

## 5. Indicator Engine (`indicator_engine.py`)

### Поддерживаемые индикаторы

| Индикатор | Параметры | Сигналы |
|-----------|-----------|---------|
| EMA | 20, 50, 200 | Stack alignment, Crossovers, Price position |
| RSI | 14 | Overbought (>70), Oversold (<30), Momentum |
| MACD | 12, 26, 9 | Crossovers, Histogram direction |
| Bollinger Bands | 20, 2σ | Squeeze, Upper/Lower breakout |
| Stochastic | 14 | Overbought (>80), Oversold (<20) |
| ATR | 14 | High/Low volatility |
| OBV | - | Divergence, Confirmation |

### EMA Analysis

#### Stack Alignment
```python
ema20 = _ema(closes, 20)
ema50 = _ema(closes, 50)
ema200 = _ema(closes, 200)

if ema20 > ema50 > ema200:
    → "EMA_STACK", BULLISH, strength=0.8
elif ema20 < ema50 < ema200:
    → "EMA_STACK", BEARISH, strength=0.8
```

#### Price Position
```python
above_count = sum([
    1 if price > ema20,
    1 if price > ema50,
    1 if price > ema200,
])

if above_count == 3: → BULLISH, strength=0.7
if above_count == 0: → BEARISH, strength=0.7
```

#### Crossovers
```python
if ema20_prev < ema50_prev and ema20 > ema50:
    → "EMA_CROSS", "golden_cross_20_50", BULLISH, strength=0.85
```

### RSI Analysis

```python
def _rsi(closes, period=14):
    gains = [max(change, 0) for change in changes]
    losses = [max(-change, 0) for change in changes]
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
```

| RSI | Сигнал | Direction | Strength |
|-----|--------|-----------|----------|
| >70 | Overbought | BEARISH | 0.6 + (rsi-70)/60 |
| <30 | Oversold | BULLISH | 0.6 + (30-rsi)/60 |
| 50-70 | Bullish momentum | BULLISH | 0.4 |
| 30-50 | Bearish momentum | BEARISH | 0.4 |

### MACD Analysis

```python
def _macd(closes):
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    macd_line = ema12 - ema26
    signal_line = _ema(macd_values, 9)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram
```

| Условие | Сигнал | Strength |
|---------|--------|----------|
| MACD crosses above Signal | Bullish cross | 0.75 |
| MACD crosses below Signal | Bearish cross | 0.75 |
| Histogram > 0 и растёт | Bullish histogram | 0.5 |
| Histogram < 0 и падает | Bearish histogram | 0.5 |

### Bollinger Bands

```python
middle = _sma(closes, 20)
std = _std(closes[-20:])
upper = middle + 2 * std
lower = middle - 2 * std
band_width = (upper - lower) / middle

# Squeeze detection
historical_widths = [calculate for last 50 candles]
squeeze_ratio = band_width / avg(historical_widths)

if squeeze_ratio < 0.7:
    → "BOLLINGER", "squeeze", NEUTRAL, strength=0.7
```

### OBV Divergence

```python
def _analyze_obv(closes, volumes):
    obv = [0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i-1]:
            obv.append(obv[-1] + volumes[i])
        elif closes[i] < closes[i-1]:
            obv.append(obv[-1] - volumes[i])
    
    price_change = (closes[-1] - closes[-20]) / closes[-20]
    obv_change = (obv[-1] - obv[-20]) / abs(obv[-20])
    
    # Bearish divergence: price up, volume down
    if price_change > 0.02 and obv_change < -0.1:
        → "OBV", "bearish_divergence", BEARISH, strength=0.6
    
    # Bullish divergence: price down, volume up
    if price_change < -0.02 and obv_change > 0.1:
        → "OBV", "bullish_divergence", BULLISH, strength=0.6
```

---

## 6. Setup Builder (`setup_builder.py`)

### Архитектура сборки

```
SetupBuilder.build(symbol, timeframe)
    │
    ├─→ _get_candles()           → List[Dict]
    ├─→ pattern_detector.detect_all() → List[DetectedPattern]
    ├─→ indicator_engine.analyze_all() → List[IndicatorSignal]
    ├─→ level_engine.analyze_all()    → List[PriceLevel]
    ├─→ structure_engine.analyze_all() → (points, bias, meta)
    │
    ├─→ _detect_regime()         → "TREND_UP" | "TREND_DOWN" | "RANGE" | etc.
    │
    ├─→ _build_setup_from_pattern()   ─┐
    │   или                            │
    ├─→ _build_setup_from_structure() ─┼─→ List[Setup]
    │
    ├─→ setups.sort(by confluence_score)
    │
    └─→ SetupAnalysisResult(top_setup, alternatives, bias, confidence)
```

### Маппинг Pattern → Setup Type

```python
pattern_to_setup = {
    ASCENDING_TRIANGLE:  ASCENDING_TRIANGLE_BREAKOUT,
    DESCENDING_TRIANGLE: DESCENDING_TRIANGLE_BREAKOUT,
    SYMMETRICAL_TRIANGLE: SYMMETRICAL_TRIANGLE_BREAKOUT,
    ASCENDING_CHANNEL:   CHANNEL_BREAKOUT,
    DESCENDING_CHANNEL:  CHANNEL_BREAKOUT,
    HORIZONTAL_CHANNEL:  RANGE_BREAKOUT,
    DOUBLE_TOP:          DOUBLE_TOP_REVERSAL,
    DOUBLE_BOTTOM:       DOUBLE_BOTTOM_REVERSAL,
    BULL_FLAG:           FLAG_CONTINUATION,
    BEAR_FLAG:           FLAG_CONTINUATION,
    COMPRESSION:         COMPRESSION_BREAKOUT,
}
```

### Расчёт Confluence Score

```python
def _compute_confluence(pattern, indicators, levels, structure_points):
    score = 0.0
    
    # Pattern contribution (35%)
    score += pattern.confidence * 0.35
    
    # Indicator alignment (15-25%)
    aligned_count = count(ind.direction == pattern.direction)
    if aligned_count >= 3: score += 0.25
    elif aligned_count >= 1: score += 0.15
    
    # Level support (15%)
    if bullish and support_cluster >= 2: score += 0.15
    if bearish and resistance_cluster >= 2: score += 0.15
    
    # Structure confirmation (15%)
    if bullish and HH+HL > LH+LL: score += 0.15
    if bearish and LH+LL > HH+HL: score += 0.15
    
    # Fibonacci confluence (10%)
    if fib_levels_present: score += 0.1
    
    return min(score, 1.0)
```

### Расчёт Setup Confidence

```python
def _calculate_setup_confidence(pattern, indicators, confluence, conflicts):
    confidence = confluence.score * 0.6
    confidence += pattern.confidence * 0.3
    
    # Indicator boost
    avg_indicator_strength = sum(i.strength) / len(indicators)
    confidence += avg_indicator_strength * 0.1
    
    # Conflict penalty
    for conflict in conflicts:
        confidence += conflict.impact  # Negative value
    
    return clamp(confidence, 0.0, 1.0)
```

### Детекция Market Regime

```python
def _detect_regime(candles, indicators):
    sma20 = avg(closes[-20:])
    sma50 = avg(closes[-50:])
    current_price = closes[-1]
    
    if current_price > sma20 > sma50:
        return "TREND_UP"
    elif current_price < sma20 < sma50:
        return "TREND_DOWN"
    elif atr_signal.type == "low_volatility":
        return "COMPRESSION"
    elif atr_signal.type == "high_volatility":
        return "EXPANSION"
    else:
        return "RANGE"
```

---

## 7. API Layer (`ta_setup_api.py`)

### Текущая реализация

В текущей версии используется **упрощённый inline-алгоритм** вместо полноценного `SetupBuilder`. Это сделано для быстрой интеграции с фронтендом.

#### Endpoint: `GET /api/ta/setup`

**Параметры:**
- `symbol`: Trading pair (default: "BTCUSDT")
- `tf`: Timeframe (4H, 1D, 7D, 30D, 180D, 1Y)

**Response:**
```json
{
  "symbol": "BTCUSDT",
  "timeframe": "1D",
  "candles": [...],
  "pattern": {
    "type": "ascending_channel",
    "confidence": 0.78,
    "points": {
      "upper": [[timestamp, price], [timestamp, price]],
      "lower": [[timestamp, price], [timestamp, price]]
    }
  },
  "levels": [
    {"type": "resistance", "price": 98500.0, "strength": 0.85},
    {"type": "support", "price": 92100.0, "strength": 0.82}
  ],
  "structure": {
    "trend": "bullish",
    "hh": 5, "hl": 4, "lh": 2, "ll": 1
  },
  "setup": {
    "direction": "bullish",
    "confidence": 0.73,
    "trigger": 98500.0,
    "invalidation": 92100.0,
    "targets": [101500.0, 105000.0]
  },
  "timestamp": "2025-12-01T..."
}
```

### Построение геометрии паттерна

```python
# Window selection
window = min(100, len(candles))
recent = candles[-window:]

# Slope calculation
n = len(highs)
half = n // 2

upper_slope = avg(
    (highs[half] - highs[0]) / half,
    (highs[-1] - highs[half]) / half
)

# Pattern classification
if upper_slope > 0 and lower_slope > 0:
    type = "ascending_channel"
elif upper_slope < 0 and lower_slope < 0:
    type = "descending_channel"
# ... etc

# Geometry points (2 lines, 4 points total)
upper_start = highs[0]
upper_end = highs[0] + upper_slope * (n - 1)

points = {
    "upper": [[times[0], upper_start], [times[-1], upper_end]],
    "lower": [[times[0], lower_start], [times[-1], lower_end]]
}
```

---

## 8. Data Types (`setup_types.py`)

### Setup Object

```python
@dataclass
class Setup:
    # Identity
    setup_id: str
    asset: str
    timeframe: str
    
    # Classification
    setup_type: SetupType
    direction: Direction
    
    # Scores
    confidence: float      # 0-1
    confluence_score: float  # 0-1
    
    # Components
    patterns: List[DetectedPattern]
    indicators: List[IndicatorSignal]
    levels: List[PriceLevel]
    structure: List[StructurePoint]
    
    # Confluence analysis
    primary_confluence: Confluence
    secondary_confluence: List[Confluence]
    conflicts: List[ConflictSignal]
    
    # Trade parameters
    entry_zone: Dict[str, float]  # {low, high}
    invalidation: float
    targets: List[float]
    
    # Context
    current_price: float
    market_regime: str
    explanation: str
    timestamp: datetime
```

### DetectedPattern

```python
@dataclass
class DetectedPattern:
    pattern_type: PatternType
    direction: Direction
    confidence: float
    start_time: datetime
    end_time: datetime
    points: List[Dict[str, float]]  # Geometry for chart
    breakout_level: float
    target_price: float
    invalidation: float
    notes: str  # Structure validation notes
```

---

## 9. Итоги

### Сильные стороны архитектуры

1. **Модульность**: Каждый движок (pattern, structure, level, indicator) изолирован и может развиваться независимо.

2. **Confluence-based scoring**: Финальный score учитывает подтверждение из нескольких источников.

3. **Structure validation**: Паттерны валидируются через рыночную структуру, что снижает false positives.

4. **Полная геометрия**: Для каждого паттерна возвращаются точки для отрисовки на графике.

### Возможности для улучшения

1. **API слой**: Текущий `ta_setup_api.py` использует упрощённую inline-логику. Полный `SetupBuilder` доступен, но не подключён.

2. **Volume analysis**: OBV присутствует, но нет volume profile или VWAP.

3. **Multi-timeframe analysis**: Каждый таймфрейм анализируется изолированно.

4. **Machine learning**: Нет ML-компонентов для адаптивной детекции.

---

## 10. Глоссарий

| Термин | Определение |
|--------|-------------|
| Swing High/Low | Локальный максимум/минимум, выше/ниже соседних точек |
| HH (Higher High) | Новый swing high выше предыдущего |
| HL (Higher Low) | Новый swing low выше предыдущего |
| LH (Lower High) | Новый swing high ниже предыдущего |
| LL (Lower Low) | Новый swing low ниже предыдущего |
| BOS (Break of Structure) | Пробой предыдущего swing point |
| CHOCH (Change of Character) | Смена направления тренда |
| Confluence | Совпадение нескольких сигналов в одной точке |
| ATR (Average True Range) | Средний истинный диапазон, мера волатильности |
| Neckline | Линия поддержки/сопротивления в паттернах Double Top/Bottom |
