/**
 * MarketMechanicsLayer — Visualization for Market Mechanics Engine
 * ================================================================
 * 
 * Renders on chart:
 * 1. POI zones (demand/supply order blocks) — rectangles
 * 2. Liquidity lines (EQH/EQL) — thin dashed lines
 * 3. Sweep markers (BSL/SSL) — arrows
 * 4. CHOCH validation labels (VALID/FAKE)
 * 5. Displacement highlights (optional)
 * 
 * Rules:
 * - Maximum 5-7 elements on chart
 * - Each element must influence decision
 * - No visual noise
 * - POI visible immediately
 */

import { LineSeries, AreaSeries, createSeriesMarkers } from 'lightweight-charts';

// ═══════════════════════════════════════════════════════════════
// COLORS — Market Mechanics Palette
// ═══════════════════════════════════════════════════════════════

export const MM_COLORS = {
  // POI Zones
  demandActive: 'rgba(34, 197, 94, 0.20)',      // Green, visible
  demandMitigated: 'rgba(34, 197, 94, 0.06)',   // Green, faded
  supplyActive: 'rgba(239, 68, 68, 0.20)',      // Red, visible
  supplyMitigated: 'rgba(239, 68, 68, 0.06)',   // Red, faded
  demandBorder: '#22c55e',
  supplyBorder: '#ef4444',
  
  // Liquidity
  eqh: 'rgba(239, 68, 68, 0.35)',               // Red-orange for highs
  eql: 'rgba(34, 197, 94, 0.35)',               // Green for lows
  
  // Sweeps
  bslSweep: '#ef4444',                           // Red - bearish signal
  sslSweep: '#22c55e',                           // Green - bullish signal
  
  // CHOCH
  chochValid: '#22c55e',
  chochWeak: '#f59e0b',
  chochFake: '#6b7280',
  
  // Displacement
  bullishDisplacement: 'rgba(34, 197, 94, 0.04)',
  bearishDisplacement: 'rgba(239, 68, 68, 0.04)',
};

// ═══════════════════════════════════════════════════════════════
// MARKET MECHANICS RENDERER
// ═══════════════════════════════════════════════════════════════

export class MarketMechanicsRenderer {
  constructor(chart, priceSeries) {
    this.chart = chart;
    this.priceSeries = priceSeries;
    this.renderedSeries = [];
    this.renderedPriceLines = [];
    this.disposed = false;
  }

  /**
   * Check if chart is still valid
   */
  isValid() {
    return !this.disposed && this.chart && this.priceSeries;
  }

  /**
   * Clear all rendered market mechanics elements
   */
  clear() {
    this.disposed = true;
    
    // Remove series
    this.renderedSeries.forEach(series => {
      try {
        if (series && this.chart) {
          this.chart.removeSeries(series);
        }
      } catch (e) {
        // Ignore errors during cleanup
      }
    });
    this.renderedSeries = [];
    
    // Remove price lines
    this.renderedPriceLines.forEach(line => {
      try {
        if (line && this.priceSeries) {
          this.priceSeries.removePriceLine(line);
        }
      } catch (e) {
        // Ignore errors during cleanup
      }
    });
    this.renderedPriceLines = [];
    
    // Clear references
    this.chart = null;
    this.priceSeries = null;
  }

  /**
   * Render all market mechanics layers
   */
  render(data, options = {}) {
    // Check if chart is still valid
    if (!this.isValid()) {
      console.warn('MarketMechanicsRenderer: Chart is disposed, skipping render');
      return;
    }

    const {
      showPOI = true,
      showLiquidity = true,
      showSweeps = true,
      showCHOCH = true,
      maxPOIZones = 3,
      maxLiquidityLines = 4,
      maxSweeps = 2,
    } = options;

    const { poi, liquidity, chochValidation, displacement, candles } = data;

    // Get time range for zones
    const timeRange = this._getTimeRange(candles);

    // Render in correct z-order (back to front)
    if (showPOI && poi?.zones) {
      this.renderPOIZones(poi.zones, timeRange, maxPOIZones);
    }

    if (showLiquidity && liquidity) {
      this.renderLiquidityLines(liquidity, maxLiquidityLines);
    }

    // Collect markers for sweeps and CHOCH
    const markers = [];

    if (showSweeps && liquidity?.sweeps) {
      this._addSweepMarkers(markers, liquidity.sweeps, maxSweeps);
    }

    if (showCHOCH && chochValidation) {
      this._addCHOCHMarker(markers, chochValidation);
    }

    // Apply all markers
    if (markers.length > 0) {
      markers.sort((a, b) => a.time - b.time);
      this._setMarkers(markers);
    }
  }

  // ═══════════════════════════════════════════════════════════════
  // POI ZONES — Order Blocks / Supply / Demand
  // ═══════════════════════════════════════════════════════════════

  renderPOIZones(zones, timeRange, maxZones = 3) {
    if (!zones || zones.length === 0) return;

    // Prioritize active zones, then by strength
    const sortedZones = [...zones]
      .sort((a, b) => {
        // Active zones first
        if (!a.mitigated && b.mitigated) return -1;
        if (a.mitigated && !b.mitigated) return 1;
        // Then by strength
        return (b.strength || 0) - (a.strength || 0);
      })
      .slice(0, maxZones);

    sortedZones.forEach(zone => {
      this._renderPOIZone(zone, timeRange);
    });
  }

  _renderPOIZone(zone, timeRange) {
    // Safety check
    if (!this.isValid()) return;
    
    const isDemand = zone.type === 'demand';
    const isActive = !zone.mitigated;
    
    const color = isDemand
      ? (isActive ? MM_COLORS.demandActive : MM_COLORS.demandMitigated)
      : (isActive ? MM_COLORS.supplyActive : MM_COLORS.supplyMitigated);
    
    const borderColor = isDemand ? MM_COLORS.demandBorder : MM_COLORS.supplyBorder;

    // Calculate zone time bounds
    const startTime = zone.origin_time || timeRange.start;
    const endTime = timeRange.end;

    // Render zone as area series (workaround for lightweight-charts)
    // Top boundary line
    const topSeries = this.chart.addSeries(LineSeries, {
      color: isActive ? borderColor : 'transparent',
      lineWidth: isActive ? 1 : 0,
      lineStyle: 2, // Dashed
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });

    // Create data points spanning the zone
    const zoneData = [
      { time: startTime, value: zone.price_high },
      { time: endTime, value: zone.price_high },
    ];
    
    topSeries.setData(zoneData);
    this.renderedSeries.push(topSeries);

    // Bottom boundary
    const bottomSeries = this.chart.addSeries(LineSeries, {
      color: isActive ? borderColor : 'transparent',
      lineWidth: isActive ? 1 : 0,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });

    bottomSeries.setData([
      { time: startTime, value: zone.price_low },
      { time: endTime, value: zone.price_low },
    ]);
    this.renderedSeries.push(bottomSeries);

    // Fill area between lines
    const areaSeries = this.chart.addSeries(AreaSeries, {
      lineColor: 'transparent',
      topColor: color,
      bottomColor: color,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });

    areaSeries.setData([
      { time: startTime, value: zone.price_high },
      { time: endTime, value: zone.price_high },
    ]);
    this.renderedSeries.push(areaSeries);

    // Add label as price line
    if (isActive) {
      const label = this.priceSeries.createPriceLine({
        price: zone.price_mid || (zone.price_high + zone.price_low) / 2,
        color: borderColor,
        lineWidth: 0,
        lineStyle: 2,
        axisLabelVisible: true,
        title: zone.label || (isDemand ? 'DEMAND' : 'SUPPLY'),
      });
      this.renderedPriceLines.push(label);
    }
  }

  // ═══════════════════════════════════════════════════════════════
  // LIQUIDITY LINES — EQH / EQL
  // ═══════════════════════════════════════════════════════════════

  renderLiquidityLines(liquidity, maxLines = 4) {
    // Safety check
    if (!this.isValid()) return;
    
    const pools = liquidity.pools || [];
    
    // Filter to strongest pools only
    const strongPools = pools
      .filter(p => (p.strength || 0) >= 2.0 && p.status === 'active')
      .sort((a, b) => (b.strength || 0) - (a.strength || 0))
      .slice(0, maxLines);

    strongPools.forEach(pool => {
      const isHigh = pool.side === 'high';
      const color = isHigh ? MM_COLORS.eqh : MM_COLORS.eql;
      const label = isHigh ? 'EQH' : 'EQL';

      const priceLine = this.priceSeries.createPriceLine({
        price: pool.price,
        color: color,
        lineWidth: 1,
        lineStyle: 2, // Dashed
        axisLabelVisible: true,
        title: `${label} (${pool.touches || '?'})`,
      });
      
      this.renderedPriceLines.push(priceLine);
    });
  }

  // ═══════════════════════════════════════════════════════════════
  // SWEEP MARKERS — BSL / SSL
  // ═══════════════════════════════════════════════════════════════

  _addSweepMarkers(markers, sweeps, maxSweeps = 2) {
    if (!sweeps || sweeps.length === 0) return;

    // Get strongest sweeps only
    const strongSweeps = [...sweeps]
      .sort((a, b) => (b.strength || 0) - (a.strength || 0))
      .slice(0, maxSweeps);

    strongSweeps.forEach(sweep => {
      const isBSL = sweep.type === 'buy_side_sweep';
      
      markers.push({
        time: sweep.time,
        position: isBSL ? 'aboveBar' : 'belowBar',
        color: isBSL ? MM_COLORS.bslSweep : MM_COLORS.sslSweep,
        shape: isBSL ? 'arrowDown' : 'arrowUp',
        text: isBSL ? 'BSL' : 'SSL',
      });
    });
  }

  // ═══════════════════════════════════════════════════════════════
  // CHOCH VALIDATION MARKER
  // ═══════════════════════════════════════════════════════════════

  _addCHOCHMarker(markers, chochValidation) {
    if (!chochValidation || !chochValidation.event_time) return;

    const { is_valid, label, direction, score } = chochValidation;
    
    // Determine color based on validation
    let color;
    let text;
    
    if (is_valid) {
      color = MM_COLORS.chochValid;
      text = 'CHOCH ✓';
    } else if (score >= 0.45) {
      color = MM_COLORS.chochWeak;
      text = 'CHOCH?';
    } else {
      color = MM_COLORS.chochFake;
      text = 'CHOCH ✗';
    }

    const isBullish = direction === 'bullish';

    markers.push({
      time: chochValidation.event_time,
      position: isBullish ? 'belowBar' : 'aboveBar',
      color: color,
      shape: isBullish ? 'arrowUp' : 'arrowDown',
      text: text,
    });
  }

  // ═══════════════════════════════════════════════════════════════
  // HELPERS
  // ═══════════════════════════════════════════════════════════════

  _getTimeRange(candles) {
    if (!candles || candles.length === 0) {
      return { start: 0, end: 0 };
    }
    const times = candles.map(c => c.time).filter(t => t > 0);
    return {
      start: Math.min(...times),
      end: Math.max(...times),
    };
  }

  _setMarkers(markers) {
    try {
      // Import already available at top of file
      createSeriesMarkers(this.priceSeries, markers);
    } catch (e) {
      console.warn('Failed to set markers:', e);
    }
  }
}

// ═══════════════════════════════════════════════════════════════
// EXPORT HELPER FUNCTION
// ═══════════════════════════════════════════════════════════════

/**
 * Render market mechanics on existing chart
 * 
 * @param {Object} chart - lightweight-charts instance
 * @param {Object} priceSeries - main price series
 * @param {Object} data - { poi, liquidity, chochValidation, displacement, candles }
 * @param {Object} options - rendering options
 * @returns {MarketMechanicsRenderer} renderer instance for cleanup
 */
export function renderMarketMechanics(chart, priceSeries, data, options = {}) {
  const renderer = new MarketMechanicsRenderer(chart, priceSeries);
  renderer.render(data, options);
  return renderer;
}

export default MarketMechanicsRenderer;
