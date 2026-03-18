/**
 * ResearchChart — Technical Analysis Chart with Pattern Geometry
 * ==============================================================
 * 
 * Renders:
 * 1. Candles/Line price series
 * 2. Pattern geometry (channel/triangle lines)
 * 3. Support/Resistance levels
 * 4. Setup targets/trigger/invalidation
 * 
 * Layer priority:
 * - candles → pattern geometry → levels → targets
 */

import React, { useEffect, useRef } from 'react';
import styled from 'styled-components';
import { createChart, CandlestickSeries, LineSeries, createSeriesMarkers } from 'lightweight-charts';
import { MarketMechanicsRenderer } from '../../../components/chart-engine/MarketMechanicsLayer';

const ChartWrapper = styled.div`
  position: relative;
  width: 100%;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  font-family: 'Gilroy', 'Inter', -apple-system, sans-serif;
`;

const ChartContainer = styled.div`
  width: 100%;
  height: ${({ $height }) => $height || 400}px;
`;

// Pivot point markers — small, minimal, secondary layer
const PivotMarkersContainer = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  overflow: hidden;
`;

const PivotMarker = styled.div`
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  transform: translateX(-50%);
  font-family: 'Gilroy', 'Inter', -apple-system, sans-serif;
`;

const PivotDot = styled.div`
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: ${({ $color }) => $color};
  border: 1px solid white;
  box-shadow: 0 1px 2px rgba(0,0,0,0.2);
`;

const PivotLabel = styled.span`
  font-size: 9px;
  font-weight: 700;
  color: ${({ $color }) => $color};
  text-shadow: 0 0 2px white, 0 0 2px white;
  margin-top: ${({ $kind }) => $kind === 'high' ? '-16px' : '2px'};
`;

const BiasOverlay = styled.div`
  position: absolute;
  top: 12px;
  left: 200px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: ${({ $direction }) => 
    $direction === 'bullish' ? '#05A584' : 
    $direction === 'bearish' ? '#ef4444' : 
    '#64748b'};
  color: #ffffff;
  border-radius: 8px;
  font-weight: 700;
  font-size: 13px;
  font-family: 'Gilroy', 'Inter', -apple-system, sans-serif;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  z-index: 10;
  
  .arrow { font-size: 14px; }
  .confidence { font-size: 12px; opacity: 0.9; }
`;

const PatternLabel = styled.div`
  position: absolute;
  top: 12px;
  left: 12px;
  padding: 8px 12px;
  background: rgba(59, 130, 246, 0.95);
  border-radius: 8px;
  font-size: 12px;
  font-weight: 700;
  font-family: 'Gilroy', 'Inter', -apple-system, sans-serif;
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
  z-index: 10;
  text-transform: capitalize;
  
  .confidence { margin-left: 8px; opacity: 0.85; }
`;

// NEW: Primary Insight Overlay - the MAIN output on chart
const PrimaryInsightOverlay = styled.div`
  position: absolute;
  top: 16px;
  right: 16px;
  width: 220px;
  padding: 16px;
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(8px);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  font-family: 'Gilroy', 'Inter', -apple-system, sans-serif;
  color: #ffffff;
  z-index: 15;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
`;

const InsightTitle = styled.div`
  font-size: 16px;
  font-weight: 800;
  color: #ffffff;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
`;

const InsightDirection = styled.span`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: ${props => {
    if (props.$direction === 'bullish') return 'rgba(5, 165, 132, 0.2)';
    if (props.$direction === 'bearish') return 'rgba(239, 68, 68, 0.2)';
    return 'rgba(100, 116, 139, 0.2)';
  }};
  color: ${props => {
    if (props.$direction === 'bullish') return '#05A584';
    if (props.$direction === 'bearish') return '#ef4444';
    return '#94a3b8';
  }};
  font-size: 14px;
`;

const InsightSummary = styled.div`
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.4;
  margin-bottom: 12px;
`;

const InsightMeta = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
`;

const InsightConfidence = styled.div`
  font-size: 20px;
  font-weight: 800;
  color: ${props => {
    if (props.$value >= 70) return '#05A584';
    if (props.$value >= 50) return '#f59e0b';
    return '#94a3b8';
  }};
`;

const InsightLabel = styled.span`
  font-size: 10px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
`;

const COLORS = {
  bullish: '#05A584',
  bearish: '#ef4444',
  support: '#05A584',
  resistance: '#ef4444',
  trigger: '#8b5cf6',
  invalidation: '#f59e0b',
  target: '#3b82f6',
  patternUpper: '#3b82f6',
  patternLower: '#3b82f6',
  trendlineBullish: '#22c55e',
  trendlineBearish: '#f97316',
  channelUpper: '#a78bfa',
  channelLower: '#a78bfa',
  // Structure visualization colors
  pivotHH: '#16a34a',    // Strong green - higher high
  pivotHL: '#4ade80',    // Light green - higher low
  pivotLH: '#f97316',    // Orange - lower high
  pivotLL: '#ef4444',    // Red - lower low
  pivotDefault: '#94a3b8',
  bosUp: '#22c55e',
  bosDown: '#ef4444',
  chochUp: '#22c55e',
  chochDown: '#ef4444',
  // EXECUTION OVERLAY colors
  entryLong: 'rgba(34, 197, 94, 0.25)',     // Green zone for long
  entryShort: 'rgba(239, 68, 68, 0.25)',    // Red zone for short
  stopLoss: '#ef4444',                       // Red line
  targetPrimary: '#22c55e',                  // Green line
  targetSecondary: '#34d399',                // Light green
};

const ResearchChart = ({
  candles = [],
  pattern = null,
  levels = [],
  setup = null,
  structure = null,
  baseLayer = null,
  structureVisualization = null,  // HH/HL/LH/LL, BOS/CHOCH, trendlines
  tradeSetup = null,  // EXECUTION OVERLAY: entry_zone, stop_loss, targets
  // NEW: Market Mechanics props
  poi = null,
  liquidity = null,
  chochValidation = null,
  displacement = null,
  chartType = 'candles',
  height = 400,
  showLevels = true,
  showPattern = true,
  showBaseLayer = true,
  showStructure = true,
  showTargets = true,
  showExecutionOverlay = true,
  // NEW: Market Mechanics toggles
  showMarketMechanics = true,
  showPOI = true,
  showLiquidity = true,
  showSweeps = true,
  showCHOCH = true,
}) => {
  const chartRef = useRef(null);
  const chartInstanceRef = useRef(null);
  const mmRendererRef = useRef(null);

  useEffect(() => {
    if (!chartRef.current || candles.length === 0) return;

    // Cleanup
    if (chartInstanceRef.current) {
      chartInstanceRef.current.remove();
      chartInstanceRef.current = null;
    }

    const rect = chartRef.current.getBoundingClientRect();
    
    // Create chart
    const chart = createChart(chartRef.current, {
      width: rect.width,
      height: height,
      layout: {
        background: { type: 'solid', color: '#ffffff' },
        textColor: '#64748b',
        fontFamily: "Gilroy, Inter, -apple-system, sans-serif",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: '#f1f5f9' },
        horzLines: { color: '#f1f5f9' },
      },
      crosshair: {
        mode: 1,
        vertLine: { color: '#94a3b8', style: 2, width: 1 },
        horzLine: { color: '#94a3b8', style: 2, width: 1 },
      },
      rightPriceScale: {
        borderColor: '#e2e8f0',
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: '#e2e8f0',
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 80,
      },
    });

    chartInstanceRef.current = chart;

    // 1. Add price series (candles/line)
    let priceSeries;
    if (chartType === 'line') {
      priceSeries = chart.addSeries(LineSeries, {
        color: COLORS.bullish,
        lineWidth: 2,
        lastValueVisible: true,
        priceLineVisible: true,
        priceLineWidth: 1,
        priceLineStyle: 2,
      });
    } else {
      priceSeries = chart.addSeries(CandlestickSeries, {
        upColor: COLORS.bullish,
        downColor: COLORS.bearish,
        borderUpColor: COLORS.bullish,
        borderDownColor: COLORS.bearish,
        wickUpColor: COLORS.bullish,
        wickDownColor: COLORS.bearish,
        lastValueVisible: true,
        priceLineVisible: true,
        priceLineWidth: 1,
        priceLineStyle: 2,
      });
    }

    // Format and set candle data
    const seen = new Set();
    const mapped = candles
      .map(c => ({
        time: c.time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
        value: c.close,
      }))
      .filter(c => c.time > 0)
      .sort((a, b) => a.time - b.time)
      .filter(c => {
        if (seen.has(c.time)) return false;
        seen.add(c.time);
        return true;
      });

    priceSeries.setData(mapped);

    // ═══════════════════════════════════════════════════════════════
    // MARKET MECHANICS LAYER (POI, Liquidity, Sweeps, CHOCH)
    // ═══════════════════════════════════════════════════════════════
    if (showMarketMechanics && (poi || liquidity || chochValidation)) {
      // Clean up previous renderer
      if (mmRendererRef.current) {
        mmRendererRef.current.clear();
      }
      
      // Create new renderer
      const mmRenderer = new MarketMechanicsRenderer(chart, priceSeries);
      mmRenderer.render(
        { poi, liquidity, chochValidation, displacement, candles },
        { 
          showPOI, 
          showLiquidity, 
          showSweeps, 
          showCHOCH,
          maxPOIZones: 3,      // max 3 zones
          maxLiquidityLines: 4, // max 4 EQH/EQL lines
          maxSweeps: 2,        // max 2 sweep markers
        }
      );
      mmRendererRef.current = mmRenderer;
    }

    // 2. RENDER STRUCTURE MARKERS (HH/HL/LH/LL + CHOCH/BOS) — native chart markers
    // NOTE: Disabled when Market Mechanics is enabled (CHOCH is rendered there)
    if (showStructure && structureVisualization && !showMarketMechanics) {
      const markers = [];
      const eventTimes = new Set();

      // Events (CHOCH/BOS) take priority over pivot labels
      (structureVisualization.events || []).forEach(event => {
        eventTimes.add(event.time);
        const isUp = event.direction === 'up';
        markers.push({
          time: event.time,
          position: isUp ? 'aboveBar' : 'belowBar',
          color: isUp ? COLORS.chochUp : COLORS.chochDown,
          shape: isUp ? 'arrowUp' : 'arrowDown',
          text: event.label,
        });
      });

      // Pivot points — skip if event already placed at same time
      (structureVisualization.pivot_points || []).forEach(pivot => {
        if (eventTimes.has(pivot.time)) return;
        const isHigh = pivot.kind === 'high';
        const colorMap = { HH: COLORS.pivotHH, HL: COLORS.pivotHL, LH: COLORS.pivotLH, LL: COLORS.pivotLL };
        markers.push({
          time: pivot.time,
          position: isHigh ? 'aboveBar' : 'belowBar',
          color: colorMap[pivot.label] || COLORS.pivotDefault,
          shape: 'circle',
          text: pivot.label,
        });
      });

      // lightweight-charts requires markers sorted by time
      markers.sort((a, b) => a.time - b.time);
      if (markers.length > 0) {
        createSeriesMarkers(priceSeries, markers);
      }
    }

    // 3. RENDER PATTERN GEOMETRY (channel/triangle lines)
    // RULE: Render EXACTLY 2 points per line, no broken segments
    if (showPattern && pattern?.points) {
      const { upper, lower } = pattern.points;
      
      // Helper to parse point (handles both array [time, value] and object {time, value})
      const parsePoint = (pt) => {
        if (Array.isArray(pt)) {
          return {
            time: typeof pt[0] === 'number' ? pt[0] : parseInt(pt[0]),
            value: typeof pt[1] === 'number' ? pt[1] : parseFloat(pt[1]),
          };
        } else if (pt && typeof pt === 'object') {
          return {
            time: typeof pt.time === 'number' ? pt.time : parseInt(pt.time),
            value: typeof pt.value === 'number' ? pt.value : parseFloat(pt.value),
          };
        }
        return null;
      };
      
      // Upper trendline - EXACTLY 2 points
      if (upper && upper.length >= 2) {
        const upperSeries = chart.addSeries(LineSeries, {
          color: COLORS.patternUpper,
          lineWidth: 2,
          lineStyle: 0,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        });
        
        // Parse only first 2 points
        const p1 = parsePoint(upper[0]);
        const p2 = parsePoint(upper[upper.length > 1 ? 1 : 0]);
        
        if (p1 && p2 && p1.time > 0 && p2.time > 0 && p1.value > 0 && p2.value > 0) {
          // Use exactly 2 points - NO extension that could create broken segments
          const upperData = [p1, p2].sort((a, b) => a.time - b.time);
          upperSeries.setData(upperData);
        }
      }
      
      // Lower trendline - EXACTLY 2 points
      if (lower && lower.length >= 2) {
        const lowerSeries = chart.addSeries(LineSeries, {
          color: COLORS.patternLower,
          lineWidth: 2,
          lineStyle: 0,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        });
        
        // Parse only first 2 points
        const p1 = parsePoint(lower[0]);
        const p2 = parsePoint(lower[lower.length > 1 ? 1 : 0]);
        
        if (p1 && p2 && p1.time > 0 && p2.time > 0 && p1.value > 0 && p2.value > 0) {
          // Use exactly 2 points - NO extension
          const lowerData = [p1, p2].sort((a, b) => a.time - b.time);
          lowerSeries.setData(lowerData);
        }
      }
    }

    // 3. RENDER BASE LAYER — ALWAYS visible (trendlines + channels from StructureEngineV2)
    if (showBaseLayer && baseLayer) {
      const parsePoint = (pt) => {
        if (!pt) return null;
        return {
          time: typeof pt.time === 'number' ? pt.time : parseInt(pt.time),
          value: typeof pt.value === 'number' ? pt.value : parseFloat(pt.value),
        };
      };

      // Render trendlines — DISABLED, now using active_trendlines from structure_visualization
      // Old base_layer trendlines were not structure-aware
      // (baseLayer.trendlines || []).forEach(...)

      // Render channels
      (baseLayer.channels || []).forEach((ch, idx) => {
        const upperStart = parsePoint(ch.upper?.start);
        const upperEnd = parsePoint(ch.upper?.end);
        const lowerStart = parsePoint(ch.lower?.start);
        const lowerEnd = parsePoint(ch.lower?.end);

        if (upperStart && upperEnd && upperStart.time > 0 && upperEnd.time > 0 && upperStart.value > 0 && upperEnd.value > 0) {
          const chUpperSeries = chart.addSeries(LineSeries, {
            color: COLORS.channelUpper,
            lineWidth: 1,
            lineStyle: 2,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: false,
          });
          chUpperSeries.setData([upperStart, upperEnd].sort((a, b) => a.time - b.time));
        }

        if (lowerStart && lowerEnd && lowerStart.time > 0 && lowerEnd.time > 0 && lowerStart.value > 0 && lowerEnd.value > 0) {
          const chLowerSeries = chart.addSeries(LineSeries, {
            color: COLORS.channelLower,
            lineWidth: 1,
            lineStyle: 2,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: false,
          });
          chLowerSeries.setData([lowerStart, lowerEnd].sort((a, b) => a.time - b.time));
        }
      });

      // Render base layer S/R levels - thin, dashed, label on line only (price on scale auto)
      const priceRange = mapped.length > 0 ? Math.max(...mapped.map(c => c.high)) - Math.min(...mapped.map(c => c.low)) : 0;
      const threshold = priceRange * 0.02;
      const drawnBasePrices = [];

      (baseLayer.supports || []).forEach(level => {
        const tooClose = drawnBasePrices.some(p => Math.abs(p - level.price) < threshold);
        if (tooClose) return;
        drawnBasePrices.push(level.price);
        priceSeries.createPriceLine({
          price: level.price,
          color: 'rgba(34, 197, 94, 0.6)',
          lineWidth: 1,
          lineStyle: 1,
          axisLabelVisible: true,  // Shows price on scale
          title: 'Support',        // Label on line (no price, no %)
        });
      });

      (baseLayer.resistances || []).forEach(level => {
        const tooClose = drawnBasePrices.some(p => Math.abs(p - level.price) < threshold);
        if (tooClose) return;
        drawnBasePrices.push(level.price);
        priceSeries.createPriceLine({
          price: level.price,
          color: 'rgba(239, 68, 68, 0.6)',
          lineWidth: 1,
          lineStyle: 1,
          axisLabelVisible: true,  // Shows price on scale
          title: 'Resistance',     // Label on line (no price, no %)
        });
      });
    }

    // 4. RENDER LEVELS - DISABLED (already rendered from baseLayer above to avoid duplication)
    // Base layer S/R is the single source of truth for support/resistance levels

    // 4. RENDER TARGETS (secondary, thin lines)
    if (showTargets && setup) {
      const targetLines = [];
      
      if (setup.trigger) {
        targetLines.push({ price: setup.trigger, color: COLORS.trigger, label: 'Trigger' });
      }
      if (setup.invalidation) {
        targetLines.push({ price: setup.invalidation, color: COLORS.invalidation, label: 'Invalidation' });
      }
      // targets is array of {price, label} objects
      if (setup.targets?.[0]?.price) {
        targetLines.push({ price: setup.targets[0].price, color: COLORS.target, label: setup.targets[0].label || 'T1' });
      }
      if (setup.targets?.[1]?.price) {
        targetLines.push({ price: setup.targets[1].price, color: COLORS.target, label: setup.targets[1].label || 'T2' });
      }
      
      targetLines.forEach(line => {
        priceSeries.createPriceLine({
          price: line.price,
          color: line.color,
          lineWidth: 1,
          lineStyle: 1, // Dotted (less prominent than pattern)
          axisLabelVisible: true,
          title: line.label,
        });
      });
    }

    // =========================================================
    // 5. EXECUTION OVERLAY — Entry Zone, Stop Loss, Targets
    // =========================================================
    // Only render if valid setup exists
    const primarySetup = tradeSetup?.primary;
    if (showExecutionOverlay && primarySetup && primarySetup.valid) {
      const { direction, entry_zone, stop_loss, target_1, target_2 } = primarySetup;
      const isShort = direction === 'short';
      
      // === ENTRY ZONE (most prominent) ===
      if (entry_zone && entry_zone.length === 2) {
        // Entry high line
        priceSeries.createPriceLine({
          price: entry_zone[1],
          color: isShort ? '#ef4444' : '#22c55e',
          lineWidth: 2,
          lineStyle: 0, // Solid
          axisLabelVisible: true,
          title: 'ENTRY ↓',
        });
        
        // Entry low line
        priceSeries.createPriceLine({
          price: entry_zone[0],
          color: isShort ? '#ef4444' : '#22c55e',
          lineWidth: 2,
          lineStyle: 0,
          axisLabelVisible: false,
          title: '',
        });
      }
      
      // === STOP LOSS (critical level) ===
      if (stop_loss) {
        priceSeries.createPriceLine({
          price: stop_loss,
          color: COLORS.stopLoss,
          lineWidth: 2,
          lineStyle: 2, // Dashed
          axisLabelVisible: true,
          title: 'STOP',
        });
      }
      
      // === TARGET 1 (primary target) ===
      if (target_1) {
        priceSeries.createPriceLine({
          price: target_1,
          color: COLORS.targetPrimary,
          lineWidth: 2,
          lineStyle: 0, // Solid
          axisLabelVisible: true,
          title: 'TP1',
        });
      }
      
      // === TARGET 2 (secondary target, optional) ===
      if (target_2) {
        priceSeries.createPriceLine({
          price: target_2,
          color: COLORS.targetSecondary,
          lineWidth: 1,
          lineStyle: 1, // Dotted
          axisLabelVisible: true,
          title: 'TP2',
        });
      }
    }
    
    // Fit content
    chart.timeScale().fitContent();

    // Resize observer
    const ro = new ResizeObserver(() => {
      if (chartRef.current && chartInstanceRef.current) {
        const w = chartRef.current.clientWidth;
        if (w > 0) {
          chartInstanceRef.current.applyOptions({ width: w });
        }
      }
    });
    ro.observe(chartRef.current);

    return () => {
      ro.disconnect();
      if (chartInstanceRef.current) {
        chartInstanceRef.current.remove();
        chartInstanceRef.current = null;
      }
    };
  }, [candles, chartType, height, levels, setup, pattern, baseLayer, structureVisualization, tradeSetup, showLevels, showPattern, showBaseLayer, showStructure, showTargets, showExecutionOverlay]);

  const direction = pattern?.direction || setup?.direction || 'neutral';
  const confidence = pattern?.total_score || pattern?.confidence || setup?.confidence || 0;
  const confPercent = Math.round(confidence * 100);
  
  // Format pattern name
  const formatPatternName = (type) => {
    if (!type) return 'Analyzing...';
    return type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  };
  
  // Get direction arrow
  const getArrow = (dir) => {
    if (dir === 'bullish') return '↑';
    if (dir === 'bearish') return '↓';
    return '→';
  };
  
  // Get insight summary based on pattern and direction
  const getInsightSummary = () => {
    const patternType = pattern?.type?.toLowerCase() || '';
    
    if (patternType.includes('triangle')) {
      if (direction === 'bullish') return 'Compression structure with bullish bias. Watch for breakout above resistance.';
      if (direction === 'bearish') return 'Compression structure with bearish bias. Watch for breakdown below support.';
      return 'Symmetrical compression. Breakout direction uncertain.';
    }
    if (patternType.includes('wedge')) {
      if (direction === 'bullish') return 'Falling wedge detected. Bullish reversal likely.';
      if (direction === 'bearish') return 'Rising wedge detected. Bearish reversal likely.';
      return 'Wedge pattern forming.';
    }
    if (patternType.includes('channel')) {
      return 'Trending channel structure detected.';
    }
    if (patternType.includes('range')) {
      return 'Horizontal range. Trade the boundaries.';
    }
    if (patternType.includes('head') || patternType.includes('shoulder')) {
      if (direction === 'bullish') return 'Inverse H&S. Bullish reversal pattern.';
      return 'Head & Shoulders. Bearish reversal pattern.';
    }
    return 'Pattern detected. Analyzing structure.';
  };

  // Structure-first insight when no pattern
  const getStructureInsight = () => {
    if (!structure) return null;
    const regime = structure.regime || structure.trend || 'unknown';
    const bias = structure.bias || 'neutral';
    return {
      title: regime.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
      summary: `Market structure: ${regime}. Bias: ${bias}. No dominant pattern detected.`,
    };
  };

  return (
    <ChartWrapper>
      <ChartContainer ref={chartRef} $height={height} />
      {/* Insight overlays removed - information shown in top bar instead */}
    </ChartWrapper>
  );
};

export default ResearchChart;
