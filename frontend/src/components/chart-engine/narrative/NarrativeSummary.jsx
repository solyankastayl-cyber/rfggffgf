/**
 * NarrativeSummary — Display market story as text chain
 * ======================================================
 * 
 * Shows: BSL Swept → Bearish Impulse → VALID CHOCH → Supply Zone → SHORT Setup
 */

import React from 'react';
import styled from 'styled-components';

// Helper to check valid chain
function hasValidNarrativeChain(events) {
  const hasSweep = events.some(e => e.type === 'liquidity_sweep');
  const hasDisplacement = events.some(e => e.type === 'displacement');
  const hasCHOCH = events.some(e => e.type === 'choch' && e.isValid);
  const hasPOI = events.some(e => e.type === 'poi');
  return hasSweep && (hasDisplacement || hasCHOCH) && hasPOI;
}

const Container = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(30, 41, 59, 0.8);
  border-radius: 6px;
  font-size: 12px;
  margin-top: 8px;
`;

const Label = styled.span`
  color: #94a3b8;
  font-weight: 500;
`;

const Chain = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
`;

const Event = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
  background: ${props => props.$bg || 'rgba(100, 116, 139, 0.2)'};
  color: ${props => props.$color || '#e2e8f0'};
`;

const Arrow = styled.span`
  color: #64748b;
  font-size: 10px;
`;

const Direction = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
  background: ${props => props.$bearish ? 'rgba(239, 68, 68, 0.2)' : 'rgba(34, 197, 94, 0.2)'};
  color: ${props => props.$bearish ? '#ef4444' : '#22c55e'};
`;

const EVENT_STYLES = {
  liquidity_sweep: { bg: 'rgba(249, 115, 22, 0.2)', color: '#fb923c' },
  displacement: { bg: 'rgba(168, 85, 247, 0.2)', color: '#a855f7' },
  choch: { bg: 'rgba(34, 197, 94, 0.2)', color: '#22c55e' },
  choch_weak: { bg: 'rgba(245, 158, 11, 0.2)', color: '#f59e0b' },
  choch_fake: { bg: 'rgba(107, 114, 128, 0.2)', color: '#6b7280' },
  poi: { bg: 'rgba(59, 130, 246, 0.2)', color: '#3b82f6' },
  entry: { bg: 'rgba(239, 68, 68, 0.2)', color: '#ef4444' },
  entry_long: { bg: 'rgba(34, 197, 94, 0.2)', color: '#22c55e' },
};

const NarrativeSummary = ({ narrative, decision }) => {
  // Handle both array (from buildNarrative) and object (from renderNarrative)
  const events = Array.isArray(narrative) ? narrative : narrative?.events || [];
  
  if (!events || events.length === 0) {
    return null;
  }

  const hasChain = narrative?.hasChain ?? hasValidNarrativeChain(events);
  const bias = decision?.bias || 'neutral';
  const isBearish = bias === 'bearish';

  const getEventStyle = (event) => {
    if (event.type === 'choch') {
      if (!event.isValid) {
        return event.score >= 0.45 ? EVENT_STYLES.choch_weak : EVENT_STYLES.choch_fake;
      }
    }
    if (event.type === 'entry') {
      return event.subtype === 'long' ? EVENT_STYLES.entry_long : EVENT_STYLES.entry;
    }
    return EVENT_STYLES[event.type] || {};
  };

  const getShortLabel = (event) => {
    switch (event.type) {
      case 'liquidity_sweep':
        return event.subtype === 'buy_side_sweep' ? 'BSL Swept' : 'SSL Swept';
      case 'displacement':
        return event.direction === 'bearish' ? 'Bearish Impulse' : 'Bullish Impulse';
      case 'choch':
        if (event.isValid) return 'VALID CHOCH';
        return event.score >= 0.45 ? 'WEAK CHOCH' : 'FAKE CHOCH';
      case 'poi':
        return event.subtype === 'supply' ? 'Supply Zone' : 'Demand Zone';
      case 'entry':
        return event.subtype === 'short' ? 'SHORT Setup' : 'LONG Setup';
      default:
        return event.label;
    }
  };

  return (
    <Container>
      <Label>Story:</Label>
      <Chain>
        {events.map((event, idx) => {
          const style = getEventStyle(event);
          return (
            <React.Fragment key={idx}>
              <Event $bg={style.bg} $color={style.color}>
                {getShortLabel(event)}
              </Event>
              {idx < events.length - 1 && <Arrow>→</Arrow>}
            </React.Fragment>
          );
        })}
      </Chain>
      <Direction $bearish={isBearish}>
        {isBearish ? '↓ BEARISH' : '↑ BULLISH'}
      </Direction>
    </Container>
  );
};

export default NarrativeSummary;
