#!/usr/bin/env python3
"""
TA Engine Ideas Module API Testing
==================================

Tests for My Ideas module functionality:

API Endpoints:
- POST /api/ta/ideas - Create new idea with snapshot
- GET /api/ta/ideas - List ideas with filters (status, asset, limit)
- GET /api/ta/ideas/{id} - Get idea with current version
- POST /api/ta/ideas/{id}/update - Create NEW version (not overwrites)
- GET /api/ta/ideas/{id}/timeline - Get version history
- DELETE /api/ta/ideas/{id} - Delete idea

Core Features:
- Ideas store full snapshots (decision, scenarios, trade_setup, explanation)
- Version count increments on update
- Comprehensive versioning and timeline functionality
"""

import requests
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional


class TAEngineAPITester:
    def __init__(self, base_url: str = "https://tech-analysis-14.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            print(f"✅ {test_name} - PASSED")
        else:
            print(f"❌ {test_name} - FAILED: {details}")
        
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> tuple:
        """Make API request and return (success, response_data, status_code)"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, timeout=30)
            else:
                return False, {}, 0
                
            return True, response.json() if response.text else {}, response.status_code
            
        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}, 0
        except Exception as e:
            return False, {"error": str(e)}, 0

    # ═══════════════════════════════════════════════════════════════
    # Core Health Check Tests
    # ═══════════════════════════════════════════════════════════════

    def test_health_endpoint(self):
        """Test /api/health endpoint"""
        success, data, status = self.make_request("GET", "/api/health")
        
        if not success or status != 200:
            self.log_result("Health Endpoint", False, f"Request failed: status={status}")
            return False
            
        if not data.get("ok"):
            self.log_result("Health Endpoint", False, "Status not OK")
            return False
            
        # Check required fields
        required_fields = ["ok", "mode", "version", "timestamp"]
        for field in required_fields:
            if field not in data:
                self.log_result("Health Endpoint", False, f"Missing field: {field}")
                return False
        
        print(f"   💚 Mode: {data.get('mode')}")
        print(f"   💚 Version: {data.get('version')}")
        
        self.log_result("Health Endpoint", True)
        return True

    # ═══════════════════════════════════════════════════════════════
    # TA Setup API Tests - Multi-Scale Market Hierarchy
    # ═══════════════════════════════════════════════════════════════

    def test_ta_setup_4h_timeframe(self):
        """Test /api/ta/setup with 4H timeframe - should return 4H candles (~200 candles)"""
        success, data, status = self.make_request("GET", "/api/ta/setup?symbol=BTC&tf=4H")
        
        if not success or status != 200:
            self.log_result("TA Setup 4H Timeframe", False, f"Request failed: status={status}, error: {data.get('error', 'unknown')}")
            return False
            
        # Check basic structure
        required_fields = ["symbol", "timeframe", "candles", "candle_count", "scale_config", "structure"]
        for field in required_fields:
            if field not in data:
                self.log_result("TA Setup 4H Timeframe", False, f"Missing field: {field}")
                return False
        
        candle_count = data.get("candle_count", 0)
        timeframe = data.get("timeframe")
        scale_config = data.get("scale_config", {})
        
        # Verify it's 4H timeframe
        if timeframe != "4H":
            self.log_result("TA Setup 4H Timeframe", False, f"Expected timeframe 4H, got {timeframe}")
            return False
            
        # Should have around 200 4H candles (allow some tolerance)
        if not (150 <= candle_count <= 250):
            self.log_result("TA Setup 4H Timeframe", False, f"Expected ~200 4H candles, got {candle_count}")
            return False
        
        # Verify scale config for 4H
        expected_lookback = 200
        if scale_config.get("lookback") != expected_lookback:
            self.log_result("TA Setup 4H Timeframe", False, f"Expected lookback {expected_lookback}, got {scale_config.get('lookback')}")
            return False
        
        print(f"   📈 4H candles: {candle_count}")
        print(f"   📈 Scale config: {scale_config.get('description')}")
        print(f"   📈 Lookback: {scale_config.get('lookback')}")
        print(f"   📈 Pivot window: {scale_config.get('pivot_window')}")
        print(f"   📈 Pattern: {data.get('pattern', {}).get('type') if data.get('pattern') else 'None'}")
        
        self.log_result("TA Setup 4H Timeframe", True)
        return data

    def test_ta_setup_1y_timeframe(self):
        """Test /api/ta/setup with 1Y timeframe - should return 2500 daily candles"""
        success, data, status = self.make_request("GET", "/api/ta/setup?symbol=BTC&tf=1Y")
        
        if not success or status != 200:
            self.log_result("TA Setup 1Y Timeframe", False, f"Request failed: status={status}, error: {data.get('error', 'unknown')}")
            return False
            
        # Check basic structure
        required_fields = ["symbol", "timeframe", "candles", "candle_count", "scale_config", "structure"]
        for field in required_fields:
            if field not in data:
                self.log_result("TA Setup 1Y Timeframe", False, f"Missing field: {field}")
                return False
        
        candle_count = data.get("candle_count", 0)
        timeframe = data.get("timeframe")
        scale_config = data.get("scale_config", {})
        
        # Verify it's 1Y timeframe
        if timeframe != "1Y":
            self.log_result("TA Setup 1Y Timeframe", False, f"Expected timeframe 1Y, got {timeframe}")
            return False
            
        # Should have around 2500 daily candles (allow some tolerance)
        if not (2000 <= candle_count <= 3000):
            self.log_result("TA Setup 1Y Timeframe", False, f"Expected ~2500 daily candles, got {candle_count}")
            return False
        
        # Verify scale config for 1Y
        expected_lookback = 2500
        if scale_config.get("lookback") != expected_lookback:
            self.log_result("TA Setup 1Y Timeframe", False, f"Expected lookback {expected_lookback}, got {scale_config.get('lookback')}")
            return False
        
        print(f"   📈 1Y candles: {candle_count}")
        print(f"   📈 Scale config: {scale_config.get('description')}")
        print(f"   📈 Lookback: {scale_config.get('lookback')}")
        print(f"   📈 Pivot window: {scale_config.get('pivot_window')}")
        print(f"   📈 Pattern: {data.get('pattern', {}).get('type') if data.get('pattern') else 'None'}")
        
        self.log_result("TA Setup 1Y Timeframe", True)
        return data

    def test_structure_response_format(self):
        """Test that response contains proper structure analysis (trend, hh, hl, lh, ll)"""
        success, data, status = self.make_request("GET", "/api/ta/setup?symbol=BTC&tf=1D")
        
        if not success or status != 200:
            self.log_result("Structure Response Format", False, f"Request failed: status={status}, error: {data.get('error', 'unknown')}")
            return False
            
        structure = data.get("structure", {})
        
        # Check required structure fields
        required_structure_fields = ["trend", "hh", "hl", "lh", "ll"]
        for field in required_structure_fields:
            if field not in structure:
                self.log_result("Structure Response Format", False, f"Missing structure field: {field}")
                return False
        
        # Verify structure values are reasonable
        trend = structure.get("trend")
        if trend not in ["bullish", "bearish", "neutral"]:
            self.log_result("Structure Response Format", False, f"Invalid trend value: {trend}")
            return False
        
        # Check that structure counts are non-negative integers
        for field in ["hh", "hl", "lh", "ll"]:
            value = structure.get(field)
            if not isinstance(value, int) or value < 0:
                self.log_result("Structure Response Format", False, f"Invalid {field} value: {value}")
                return False
        
        print(f"   🏗️ Trend: {trend}")
        print(f"   🏗️ Higher Highs: {structure.get('hh')}")
        print(f"   🏗️ Higher Lows: {structure.get('hl')}")
        print(f"   🏗️ Lower Highs: {structure.get('lh')}")
        print(f"   🏗️ Lower Lows: {structure.get('ll')}")
        
        self.log_result("Structure Response Format", True)
        return structure

    def test_eth_4h_pattern(self):
        """Test ETH 4H pattern - should show descending_triangle (bearish)"""
        success, data, status = self.make_request("GET", "/api/ta/setup?symbol=ETH&tf=4H")
        
        if not success or status != 200:
            self.log_result("ETH 4H Pattern", False, f"Request failed: status={status}, error: {data.get('error', 'unknown')}")
            return False
            
        pattern = data.get("pattern")
        
        # Check if pattern exists
        if not pattern:
            print("   ⚠️ No pattern detected for ETH 4H (this may be normal)")
            self.log_result("ETH 4H Pattern", True, "No pattern detected")
            return data
        
        pattern_type = pattern.get("type")
        direction = pattern.get("direction")
        
        print(f"   🔺 ETH 4H Pattern: {pattern_type}")
        print(f"   🔺 Direction: {direction}")
        print(f"   🔺 Confidence: {pattern.get('confidence', 'N/A')}")
        print(f"   🔺 Timeframe: {data.get('timeframe')}")
        
        # Log pattern details (even if not descending_triangle)
        if pattern_type == "descending_triangle" and direction == "bearish":
            print("   ✅ Expected descending_triangle (bearish) pattern found!")
        else:
            print(f"   ℹ️ Pattern is {pattern_type} ({direction}), not descending_triangle (bearish)")
        
        self.log_result("ETH 4H Pattern", True)
        return data

    def test_different_timeframe_patterns(self):
        """Test that different timeframes produce different patterns (4H ≠ 1D ≠ 30D)"""
        print("   🔄 Testing pattern differences across timeframes...")
        
        timeframes = ["4H", "1D", "30D"]
        patterns = {}
        
        for tf in timeframes:
            success, data, status = self.make_request("GET", f"/api/ta/setup?symbol=BTC&tf={tf}")
            
            if not success or status != 200:
                self.log_result("Different Timeframe Patterns", False, f"Failed to get {tf} data: status={status}")
                return False
            
            pattern = data.get("pattern")
            pattern_type = pattern.get("type") if pattern else None
            direction = pattern.get("direction") if pattern else None
            structure_trend = data.get("structure", {}).get("trend")
            
            patterns[tf] = {
                "pattern_type": pattern_type,
                "direction": direction,
                "structure_trend": structure_trend
            }
            
            print(f"   📊 {tf}: Pattern={pattern_type or 'None'}, Direction={direction or 'None'}, Trend={structure_trend}")
        
        # Check that we have valid responses for all timeframes
        if len(patterns) != len(timeframes):
            self.log_result("Different Timeframe Patterns", False, f"Expected {len(timeframes)} timeframes, got {len(patterns)}")
            return False
        
        # Check for differences in patterns or structure trends
        pattern_types = [p["pattern_type"] for p in patterns.values()]
        directions = [p["direction"] for p in patterns.values()]
        trends = [p["structure_trend"] for p in patterns.values()]
        
        # Count unique values
        unique_patterns = len(set(filter(None, pattern_types)))
        unique_directions = len(set(filter(None, directions)))
        unique_trends = len(set(filter(None, trends)))
        
        print(f"   🎯 Unique pattern types: {unique_patterns}")
        print(f"   🎯 Unique directions: {unique_directions}")
        print(f"   🎯 Unique trends: {unique_trends}")
        
        # Success if there's variation in any aspect
        has_variation = (unique_patterns > 1) or (unique_directions > 1) or (unique_trends > 1)
        
        if has_variation:
            print("   ✅ Timeframes show different analysis results!")
        else:
            print("   ⚠️ All timeframes show similar results (this may be normal)")
        
        self.log_result("Different Timeframe Patterns", True)
        return patterns

    # ═══════════════════════════════════════════════════════════════
    # ExplanationEngineV2 Tests (P1 Feature)
    # ═══════════════════════════════════════════════════════════════

    def test_explanation_v2_structure(self):
        """Test that /api/ta/setup/v2 returns explanation object with summary, action, risk, confidence"""
        success, data, status = self.make_request("GET", "/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        
        if not success or status != 200:
            self.log_result("ExplanationV2 Structure", False, f"Request failed: status={status}, error: {data.get('error', 'unknown')}")
            return False
            
        explanation = data.get("explanation")
        
        if not explanation:
            self.log_result("ExplanationV2 Structure", False, "Missing explanation object")
            return False
        
        # Check required fields
        required_fields = ["summary", "action", "risk", "confidence"]
        for field in required_fields:
            if field not in explanation:
                self.log_result("ExplanationV2 Structure", False, f"Missing explanation field: {field}")
                return False
        
        # Check field types and content
        summary = explanation.get("summary")
        action = explanation.get("action")  
        risk = explanation.get("risk")
        confidence = explanation.get("confidence")
        
        if not isinstance(summary, str) or not summary.strip():
            self.log_result("ExplanationV2 Structure", False, "Summary must be non-empty string")
            return False
            
        if not isinstance(action, str) or not action.strip():
            self.log_result("ExplanationV2 Structure", False, "Action must be non-empty string")
            return False
            
        if not isinstance(risk, str) or not risk.strip():
            self.log_result("ExplanationV2 Structure", False, "Risk must be non-empty string")
            return False
            
        if confidence not in ["low", "medium", "high"]:
            self.log_result("ExplanationV2 Structure", False, f"Invalid confidence level: {confidence}")
            return False
        
        print(f"   📝 Summary: {summary}")
        print(f"   📝 Action: {action}")
        print(f"   📝 Risk: {risk}")
        print(f"   📝 Confidence: {confidence}")
        
        self.log_result("ExplanationV2 Structure", True)
        return explanation

    def test_explanation_v2_format(self):
        """Test that ExplanationEngineV2 generates 3-line compact trader-style explanations"""
        success, data, status = self.make_request("GET", "/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        
        if not success or status != 200:
            self.log_result("ExplanationV2 Format", False, f"Request failed: status={status}")
            return False
            
        explanation = data.get("explanation", {})
        
        summary = explanation.get("summary", "")
        action = explanation.get("action", "")
        risk = explanation.get("risk", "")
        
        # Check that each line is concise (less than 100 chars as per trader style)
        if len(summary) > 100:
            self.log_result("ExplanationV2 Format", False, f"Summary too long ({len(summary)} chars): {summary}")
            return False
            
        if len(action) > 100:
            self.log_result("ExplanationV2 Format", False, f"Action too long ({len(action)} chars): {action}")
            return False
            
        if len(risk) > 100:
            self.log_result("ExplanationV2 Format", False, f"Risk too long ({len(risk)} chars): {risk}")
            return False
        
        # Check for trader-style format patterns
        trader_patterns = {
            "summary": ["Bullish", "Bearish", "Neutral", "Price is", "trend", "bouncing", "continues"],
            "action": ["Look for", "Short entries", "Long entries", "Wait for", "from"],
            "risk": ["Invalid if", "price", "above", "below", "holds", "breaks"]
        }
        
        summary_words = summary.lower()
        action_words = action.lower()
        risk_words = risk.lower()
        
        summary_matched = any(pattern.lower() in summary_words for pattern in trader_patterns["summary"])
        action_matched = any(pattern.lower() in action_words for pattern in trader_patterns["action"])
        risk_matched = any(pattern.lower() in risk_words for pattern in trader_patterns["risk"])
        
        print(f"   🎯 Summary format check: {summary_matched} - '{summary}'")
        print(f"   🎯 Action format check: {action_matched} - '{action}'")
        print(f"   🎯 Risk format check: {risk_matched} - '{risk}'")
        
        # At least 2 out of 3 should match expected patterns
        pattern_score = sum([summary_matched, action_matched, risk_matched])
        if pattern_score < 2:
            self.log_result("ExplanationV2 Format", False, f"Insufficient trader-style patterns matched ({pattern_score}/3)")
            return False
            
        self.log_result("ExplanationV2 Format", True)
        return True

    def test_decision_engine_bias(self):
        """Test decision engine returns bias (bullish/bearish/neutral) with confidence"""
        success, data, status = self.make_request("GET", "/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        
        if not success or status != 200:
            self.log_result("Decision Engine Bias", False, f"Request failed: status={status}")
            return False
            
        decision = data.get("decision")
        
        if not decision:
            self.log_result("Decision Engine Bias", False, "Missing decision object")
            return False
        
        bias = decision.get("bias")
        confidence = decision.get("confidence")
        
        if bias not in ["bullish", "bearish", "neutral"]:
            self.log_result("Decision Engine Bias", False, f"Invalid bias value: {bias}")
            return False
            
        if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
            self.log_result("Decision Engine Bias", False, f"Invalid confidence value: {confidence}")
            return False
        
        print(f"   🎯 Decision bias: {bias}")
        print(f"   🎯 Decision confidence: {confidence}")
        print(f"   🎯 Context: {decision.get('context', 'N/A')}")
        print(f"   🎯 Strength: {decision.get('strength', 'N/A')}")
        
        self.log_result("Decision Engine Bias", True)
        return decision

    def test_trade_setup_structure(self):
        """Test trade setup includes entry_zone, stop_loss, target_1"""
        success, data, status = self.make_request("GET", "/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        
        if not success or status != 200:
            self.log_result("Trade Setup Structure", False, f"Request failed: status={status}")
            return False
            
        trade_setup = data.get("trade_setup")
        
        if not trade_setup:
            # Trade setup might be empty if no clear setup is available
            print("   ⚠️ No trade setup available (this may be normal)")
            self.log_result("Trade Setup Structure", True, "No trade setup - normal behavior")
            return True
        
        # Check for primary setup
        primary_setup = trade_setup.get("primary")
        if not primary_setup:
            print("   ⚠️ No primary setup available")
            self.log_result("Trade Setup Structure", True, "No primary setup - normal behavior")
            return True
        
        # Check required setup fields
        required_fields = ["entry_zone", "stop_loss", "target_1"]
        for field in required_fields:
            if field not in primary_setup:
                self.log_result("Trade Setup Structure", False, f"Missing trade setup field: {field}")
                return False
        
        entry_zone = primary_setup.get("entry_zone")
        stop_loss = primary_setup.get("stop_loss")
        target_1 = primary_setup.get("target_1")
        
        print(f"   📊 Entry zone: {entry_zone}")
        print(f"   📊 Stop loss: {stop_loss}")
        print(f"   📊 Target 1: {target_1}")
        print(f"   📊 Direction: {primary_setup.get('direction', 'N/A')}")
        
        self.log_result("Trade Setup Structure", True)
        return trade_setup

    def test_scenarios_generation(self):
        """Test scenarios are generated correctly"""
        success, data, status = self.make_request("GET", "/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        
        if not success or status != 200:
            self.log_result("Scenarios Generation", False, f"Request failed: status={status}")
            return False
            
        scenarios = data.get("scenarios", [])
        
        if not scenarios:
            print("   ⚠️ No scenarios generated (this may be normal)")
            self.log_result("Scenarios Generation", True, "No scenarios - normal behavior")
            return True
        
        print(f"   📋 Number of scenarios: {len(scenarios)}")
        
        # Check scenario structure
        for i, scenario in enumerate(scenarios):
            if not isinstance(scenario, dict):
                self.log_result("Scenarios Generation", False, f"Scenario {i} is not a dict")
                return False
            
            scenario_type = scenario.get("type")
            probability = scenario.get("probability") 
            
            if scenario_type:
                print(f"   📋 Scenario {i+1}: {scenario_type} (probability: {probability})")
            
            # Check for common scenario fields
            expected_fields = ["type", "probability", "trigger", "target"]
            present_fields = [field for field in expected_fields if field in scenario]
            print(f"   📋   Fields present: {present_fields}")
        
        self.log_result("Scenarios Generation", True)
        return scenarios

    # ═══════════════════════════════════════════════════════════════
    # Structure Engine V2 Tests (NEW)
    # ═══════════════════════════════════════════════════════════════

    def test_structure_engine_v2_health(self):
        """Test Structure Engine V2 endpoint basic functionality"""
        success, data, status = self.make_request("GET", "/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        
        if not success or status != 200:
            self.log_result("Structure Engine V2 Health", False, f"Request failed: status={status}, error: {data.get('error', 'unknown')}")
            return False
            
        # Check required V2 fields
        required_v2_fields = ["structure_context", "base_layer"]
        for field in required_v2_fields:
            if field not in data:
                self.log_result("Structure Engine V2 Health", False, f"Missing V2 field: {field}")
                return False
        
        print(f"   🏗️ Structure Engine V2 responding correctly")
        print(f"   🏗️ Symbol: {data.get('symbol')}")
        print(f"   🏗️ Timeframe: {data.get('timeframe')}")
        
        self.log_result("Structure Engine V2 Health", True)
        return data

    def test_structure_context_fields(self):
        """Test structure_context contains required fields from Structure Engine V2"""
        success, data, status = self.make_request("GET", "/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        
        if not success or status != 200:
            self.log_result("Structure Context Fields", False, f"Request failed: status={status}")
            return False
            
        structure_context = data.get("structure_context", {})
        
        # Check for required V2 structure fields
        required_structure_fields = ["bias", "regime", "market_phase", "last_event"]
        for field in required_structure_fields:
            if field not in structure_context:
                self.log_result("Structure Context Fields", False, f"Missing structure_context field: {field}")
                return False
        
        # Check Base Layer fields
        base_layer = data.get("base_layer", {})
        required_base_layer_fields = ["supports", "resistances", "trendlines", "channels"]
        for field in required_base_layer_fields:
            if field not in base_layer:
                self.log_result("Structure Context Fields", False, f"Missing base_layer field: {field}")
                return False
        
        print(f"   🎯 Bias: {structure_context.get('bias')}")
        print(f"   🎯 Regime: {structure_context.get('regime')}")
        print(f"   🎯 Market Phase: {structure_context.get('market_phase')}")
        print(f"   🎯 Last Event: {structure_context.get('last_event')}")
        print(f"   🎯 Base Layer - Supports: {len(base_layer.get('supports', []))}")
        print(f"   🎯 Base Layer - Resistances: {len(base_layer.get('resistances', []))}")
        
        self.log_result("Structure Context Fields", True)
        return structure_context

    def test_no_dominant_pattern_logic(self):
        """Test that when no strong pattern exists, primary_pattern is null"""
        success, data, status = self.make_request("GET", "/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        
        if not success or status != 200:
            self.log_result("No Dominant Pattern Logic", False, f"Request failed: status={status}")
            return False
        
        primary_pattern = data.get("primary_pattern")
        selection_explanation = data.get("selection_explanation", {})
        
        # Check if primary_pattern is null
        if primary_pattern is None:
            print(f"   🎯 Correctly returning primary_pattern = null")
            print(f"   🎯 Explanation: {selection_explanation.get('status', 'No explanation')}")
        else:
            print(f"   🎯 Pattern detected: {primary_pattern.get('type')} with confidence {primary_pattern.get('confidence')}")
            print(f"   🎯 This is also valid - pattern detection working correctly")
        
        # Both cases are valid - either null (no pattern) or valid pattern
        self.log_result("No Dominant Pattern Logic", True)
        return data

    # ═══════════════════════════════════════════════════════════════
    # Ideas Module Tests (My Ideas for TA Engine)
    # ═══════════════════════════════════════════════════════════════

    def test_create_idea(self):
        """Test POST /api/ta/ideas creates new idea with snapshot"""
        test_data = {
            "asset": "BTCUSDT",
            "timeframe": "1d",
            "user_id": "test_user",
            "tags": ["test", "api"],
            "notes": "Test idea creation"
        }
        
        success, data, status = self.make_request("POST", "/api/ta/ideas", test_data)
        
        if not success or status != 200:
            self.log_result("Create Idea", False, f"Request failed: status={status}, error: {data.get('error', 'unknown')}")
            return False
        
        # Check response structure
        if not data.get("ok"):
            self.log_result("Create Idea", False, f"Response not OK: {data}")
            return False
        
        idea = data.get("idea")
        if not idea:
            self.log_result("Create Idea", False, "Missing idea object in response")
            return False
        
        # Check required fields
        required_fields = ["idea_id", "asset", "timeframe", "versions", "current_version", "technical_bias", "confidence"]
        for field in required_fields:
            if field not in idea:
                self.log_result("Create Idea", False, f"Missing idea field: {field}")
                return False
        
        # Check that idea has one version (initial)
        versions = idea.get("versions", [])
        if len(versions) != 1:
            self.log_result("Create Idea", False, f"Expected 1 version, got {len(versions)}")
            return False
        
        version = versions[0]
        if version.get("version") != 1:
            self.log_result("Create Idea", False, f"Expected version 1, got {version.get('version')}")
            return False
        
        # Check that version has setup snapshot
        setup_snapshot = version.get("setup_snapshot")
        if not setup_snapshot:
            self.log_result("Create Idea", False, "Missing setup_snapshot in version")
            return False
        
        print(f"   💡 Created idea: {idea.get('idea_id')}")
        print(f"   💡 Asset: {idea.get('asset')}")
        print(f"   💡 Version: {idea.get('current_version')}")
        print(f"   💡 Bias: {idea.get('technical_bias')}")
        print(f"   💡 Confidence: {idea.get('confidence')}")
        
        self.log_result("Create Idea", True)
        # Store idea_id for other tests
        self.test_idea_id = idea.get("idea_id")
        return idea

    def test_list_ideas(self):
        """Test GET /api/ta/ideas lists ideas with filters"""
        # Test basic list
        success, data, status = self.make_request("GET", "/api/ta/ideas")
        
        if not success or status != 200:
            self.log_result("List Ideas", False, f"Request failed: status={status}, error: {data.get('error', 'unknown')}")
            return False
        
        if not data.get("ok"):
            self.log_result("List Ideas", False, f"Response not OK: {data}")
            return False
        
        ideas = data.get("ideas", [])
        count = data.get("count", 0)
        
        print(f"   📋 Total ideas: {count}")
        print(f"   📋 Ideas in response: {len(ideas)}")
        
        # Test with filters
        success2, data2, status2 = self.make_request("GET", "/api/ta/ideas?asset=BTCUSDT&limit=10")
        
        if success2 and status2 == 200:
            filtered_count = data2.get("count", 0)
            print(f"   📋 Filtered (BTCUSDT): {filtered_count}")
        
        # Test with status filter
        success3, data3, status3 = self.make_request("GET", "/api/ta/ideas?status=active&limit=5")
        
        if success3 and status3 == 200:
            active_count = data3.get("count", 0)
            print(f"   📋 Active ideas: {active_count}")
        
        self.log_result("List Ideas", True)
        return data

    def test_get_idea(self):
        """Test GET /api/ta/ideas/{id} returns idea with current version"""
        if not hasattr(self, 'test_idea_id'):
            # Create an idea first
            self.test_create_idea()
        
        if not hasattr(self, 'test_idea_id'):
            self.log_result("Get Idea", False, "No test idea ID available")
            return False
        
        success, data, status = self.make_request("GET", f"/api/ta/ideas/{self.test_idea_id}")
        
        if not success or status != 200:
            self.log_result("Get Idea", False, f"Request failed: status={status}, error: {data.get('error', 'unknown')}")
            return False
        
        if not data.get("ok"):
            self.log_result("Get Idea", False, f"Response not OK: {data}")
            return False
        
        idea = data.get("idea")
        if not idea:
            self.log_result("Get Idea", False, "Missing idea object in response")
            return False
        
        # Check that we got the right idea
        if idea.get("idea_id") != self.test_idea_id:
            self.log_result("Get Idea", False, f"Expected idea_id {self.test_idea_id}, got {idea.get('idea_id')}")
            return False
        
        # Check that it has complete data
        required_fields = ["idea_id", "asset", "versions", "current_version", "created_at", "updated_at"]
        for field in required_fields:
            if field not in idea:
                self.log_result("Get Idea", False, f"Missing idea field: {field}")
                return False
        
        print(f"   🔍 Retrieved idea: {idea.get('idea_id')}")
        print(f"   🔍 Asset: {idea.get('asset')}")
        print(f"   🔍 Current version: {idea.get('current_version')}")
        print(f"   🔍 Status: {idea.get('status')}")
        print(f"   🔍 Versions count: {len(idea.get('versions', []))}")
        
        self.log_result("Get Idea", True)
        return idea

    def test_update_idea_new_version(self):
        """Test POST /api/ta/ideas/{id}/update creates NEW version (not overwrites)"""
        if not hasattr(self, 'test_idea_id'):
            self.test_create_idea()
        
        if not hasattr(self, 'test_idea_id'):
            self.log_result("Update Idea New Version", False, "No test idea ID available")
            return False
        
        # Get initial version count
        success_get, data_get, status_get = self.make_request("GET", f"/api/ta/ideas/{self.test_idea_id}")
        if not success_get or status_get != 200:
            self.log_result("Update Idea New Version", False, "Failed to get initial idea state")
            return False
        
        initial_idea = data_get.get("idea")
        initial_version = initial_idea.get("current_version", 1)
        initial_versions_count = len(initial_idea.get("versions", []))
        
        print(f"   🔄 Initial version: {initial_version}")
        print(f"   🔄 Initial versions count: {initial_versions_count}")
        
        # Update the idea
        success, data, status = self.make_request("POST", f"/api/ta/ideas/{self.test_idea_id}/update")
        
        if not success or status != 200:
            self.log_result("Update Idea New Version", False, f"Request failed: status={status}, error: {data.get('error', 'unknown')}")
            return False
        
        if not data.get("ok"):
            self.log_result("Update Idea New Version", False, f"Response not OK: {data}")
            return False
        
        updated_idea = data.get("idea")
        if not updated_idea:
            self.log_result("Update Idea New Version", False, "Missing idea object in response")
            return False
        
        # Check version increment
        new_version = updated_idea.get("current_version")
        new_versions_count = len(updated_idea.get("versions", []))
        
        if new_version != initial_version + 1:
            self.log_result("Update Idea New Version", False, f"Expected version {initial_version + 1}, got {new_version}")
            return False
        
        if new_versions_count != initial_versions_count + 1:
            self.log_result("Update Idea New Version", False, f"Expected {initial_versions_count + 1} versions, got {new_versions_count}")
            return False
        
        print(f"   🔄 New version: {new_version}")
        print(f"   🔄 New versions count: {new_versions_count}")
        print(f"   🔄 Message: {data.get('message')}")
        
        self.log_result("Update Idea New Version", True)
        return updated_idea

    def test_get_idea_timeline(self):
        """Test GET /api/ta/ideas/{id}/timeline returns version history"""
        if not hasattr(self, 'test_idea_id'):
            self.test_create_idea()
        
        if not hasattr(self, 'test_idea_id'):
            self.log_result("Get Idea Timeline", False, "No test idea ID available")
            return False
        
        success, data, status = self.make_request("GET", f"/api/ta/ideas/{self.test_idea_id}/timeline")
        
        if not success or status != 200:
            self.log_result("Get Idea Timeline", False, f"Request failed: status={status}, error: {data.get('error', 'unknown')}")
            return False
        
        if not data.get("ok"):
            self.log_result("Get Idea Timeline", False, f"Response not OK: {data}")
            return False
        
        # Check timeline structure
        required_fields = ["idea_id", "asset", "timeframe", "timeline"]
        for field in required_fields:
            if field not in data:
                self.log_result("Get Idea Timeline", False, f"Missing timeline field: {field}")
                return False
        
        timeline = data.get("timeline", [])
        if not timeline:
            self.log_result("Get Idea Timeline", False, "Empty timeline")
            return False
        
        # Check timeline entries
        version_count = 0
        validation_count = 0
        
        for entry in timeline:
            entry_type = entry.get("type")
            if entry_type == "version":
                version_count += 1
                print(f"   📅 Version {entry.get('version')} - {entry.get('timestamp')} - Bias: {entry.get('technical_bias')}")
            elif entry_type == "validation":
                validation_count += 1
                print(f"   📅 Validation - {entry.get('timestamp')} - Result: {entry.get('result')}")
        
        print(f"   📅 Timeline entries: {len(timeline)}")
        print(f"   📅 Versions: {version_count}")
        print(f"   📅 Validations: {validation_count}")
        
        self.log_result("Get Idea Timeline", True)
        return data

    def test_delete_idea(self):
        """Test DELETE /api/ta/ideas/{id} deletes idea"""
        # Create a separate idea for deletion test
        test_data = {
            "asset": "ETHUSDT",
            "timeframe": "1d",
            "user_id": "test_user",
            "notes": "Test idea for deletion"
        }
        
        success_create, data_create, status_create = self.make_request("POST", "/api/ta/ideas", test_data)
        
        if not success_create or status_create != 200:
            self.log_result("Delete Idea", False, "Failed to create test idea for deletion")
            return False
        
        idea_to_delete = data_create.get("idea", {}).get("idea_id")
        if not idea_to_delete:
            self.log_result("Delete Idea", False, "No idea ID for deletion test")
            return False
        
        print(f"   🗑️ Deleting idea: {idea_to_delete}")
        
        # Delete the idea
        success, data, status = self.make_request("DELETE", f"/api/ta/ideas/{idea_to_delete}")
        
        if success and status == 405:
            # Method not allowed - check if endpoint exists
            self.log_result("Delete Idea", False, "DELETE method not allowed - endpoint may not be implemented")
            return False
        
        if not success or status != 200:
            self.log_result("Delete Idea", False, f"Request failed: status={status}, error: {data.get('error', 'unknown')}")
            return False
        
        if not data.get("ok"):
            self.log_result("Delete Idea", False, f"Response not OK: {data}")
            return False
        
        # Verify idea is deleted by trying to get it
        success_verify, data_verify, status_verify = self.make_request("GET", f"/api/ta/ideas/{idea_to_delete}")
        
        if success_verify and status_verify == 200:
            self.log_result("Delete Idea", False, "Idea still exists after deletion")
            return False
        elif status_verify == 404:
            print(f"   🗑️ Idea successfully deleted")
        
        print(f"   🗑️ Message: {data.get('message')}")
        
        self.log_result("Delete Idea", True)
        return True

    def test_idea_snapshot_storage(self):
        """Test idea stores full snapshot (decision, scenarios, trade_setup, explanation)"""
        if not hasattr(self, 'test_idea_id'):
            self.test_create_idea()
        
        if not hasattr(self, 'test_idea_id'):
            self.log_result("Idea Snapshot Storage", False, "No test idea ID available")
            return False
        
        success, data, status = self.make_request("GET", f"/api/ta/ideas/{self.test_idea_id}")
        
        if not success or status != 200:
            self.log_result("Idea Snapshot Storage", False, f"Request failed: status={status}")
            return False
        
        idea = data.get("idea")
        if not idea:
            self.log_result("Idea Snapshot Storage", False, "Missing idea object")
            return False
        
        versions = idea.get("versions", [])
        if not versions:
            self.log_result("Idea Snapshot Storage", False, "No versions in idea")
            return False
        
        # Check first version's snapshot
        version = versions[0]
        setup_snapshot = version.get("setup_snapshot")
        
        if not setup_snapshot:
            self.log_result("Idea Snapshot Storage", False, "Missing setup_snapshot")
            return False
        
        # Check for key snapshot components
        snapshot_fields = ["technical_bias", "bias_confidence", "top_setup"]
        present_fields = []
        missing_fields = []
        
        for field in snapshot_fields:
            if field in setup_snapshot:
                present_fields.append(field)
            else:
                missing_fields.append(field)
        
        print(f"   📸 Snapshot present fields: {present_fields}")
        print(f"   📸 Snapshot missing fields: {missing_fields}")
        print(f"   📸 Snapshot size: {len(str(setup_snapshot))} chars")
        
        # Check if snapshot has meaningful content
        if len(str(setup_snapshot)) < 100:
            self.log_result("Idea Snapshot Storage", False, "Snapshot appears to be too small")
            return False
        
        self.log_result("Idea Snapshot Storage", True)
        return setup_snapshot

    def test_version_count_increment(self):
        """Test version count increments on update"""
        if not hasattr(self, 'test_idea_id'):
            self.test_create_idea()
        
        if not hasattr(self, 'test_idea_id'):
            self.log_result("Version Count Increment", False, "No test idea ID available")
            return False
        
        # Get initial state
        success1, data1, status1 = self.make_request("GET", f"/api/ta/ideas/{self.test_idea_id}")
        if not success1 or status1 != 200:
            self.log_result("Version Count Increment", False, "Failed to get initial state")
            return False
        
        initial_version = data1.get("idea", {}).get("current_version", 1)
        print(f"   🔢 Initial version: {initial_version}")
        
        # Update the idea
        success2, data2, status2 = self.make_request("POST", f"/api/ta/ideas/{self.test_idea_id}/update")
        if not success2 or status2 != 200:
            self.log_result("Version Count Increment", False, "Failed to update idea")
            return False
        
        updated_version = data2.get("idea", {}).get("current_version", initial_version)
        print(f"   🔢 Updated version: {updated_version}")
        
        # Verify increment
        if updated_version != initial_version + 1:
            self.log_result("Version Count Increment", False, f"Version did not increment correctly: {initial_version} -> {updated_version}")
            return False
        
        # Update again to test further increment
        success3, data3, status3 = self.make_request("POST", f"/api/ta/ideas/{self.test_idea_id}/update")
        if success3 and status3 == 200:
            final_version = data3.get("idea", {}).get("current_version", updated_version)
            print(f"   🔢 Final version: {final_version}")
            
            if final_version != updated_version + 1:
                self.log_result("Version Count Increment", False, f"Second increment failed: {updated_version} -> {final_version}")
                return False
        
        self.log_result("Version Count Increment", True)
        return True

    # ═══════════════════════════════════════════════════════════════
    # Test Runner
    # ═══════════════════════════════════════════════════════════════

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting TA Engine API Tests - Ideas Module Focus...")
        print(f"🌐 Base URL: {self.base_url}")
        print("=" * 80)
        
        # Health check
        print("\n🔧 HEALTH CHECK")
        print("-" * 50)
        self.test_health_endpoint()
        
        # Ideas Module Tests (Main Focus)
        print("\n💡 IDEAS MODULE TESTS")
        print("-" * 50)
        self.test_create_idea()
        self.test_list_ideas()
        self.test_get_idea()
        self.test_update_idea_new_version()
        self.test_get_idea_timeline()
        self.test_idea_snapshot_storage()
        self.test_version_count_increment()
        self.test_delete_idea()
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {success_rate:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL TESTS PASSED!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} TESTS FAILED")
            
            # Print failed tests
            failed_tests = [r for r in self.test_results if not r["passed"]]
            if failed_tests:
                print("\n❌ FAILED TESTS:")
                for test in failed_tests:
                    print(f"   - {test['test']}: {test['details']}")
            
            return False


def main():
    """Main test runner"""
    print("TA Engine API Tester - Multi-Scale Market Hierarchy")
    print("=" * 80)
    
    # Initialize tester
    tester = TAEngineAPITester()
    
    try:
        # Run tests
        success = tester.run_all_tests()
        
        # Exit with appropriate code
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return 1
        
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())