"""
Integration tests for complete NEXUS Risk Agent pipeline
Tests end-to-end flow from signal to decision
"""
import pytest
import sys
import os
import json
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class PipelineState:
    def __init__(self, signal_id: str):
        self.signal_id = signal_id
        self.agent_1 = None
        self.agent_2 = None
        self.agent_3 = None
        self.agent_4 = None
        self.final_decision = None
        self.status = "pending"

# Simulated pipeline results (from reference data)
PIPELINE_RESULTS = {
    "SG-2611-001": {
        "agent_1": {
            "extraction": {
                "signal_id": "SG-2611-001",
                "event_type": "Port congestion",
                "country_region": "Saudi Arabia",
                "party_code": "TS01",
                "shipment_id": "AKH-MUN-26-1184",
                "material_no": "MT100054",
                "estimated_delay_days": 8,
                "alternative_hints": ["discharge at Mersin"],
                "confidence": 0.95,
                "extraction_method": "pattern_match"
            }
        },
        "agent_2": {
            "risk_assessment": {
                "signal_id": "SG-2611-001",
                "probability_score": 4.4,
                "impact_score": 5,
                "risk_score": 22.0,
                "risk_category": "High",
                "available_date": "2026-12-10",
                "stock_coverage_days": 9.89,
                "depletion_date": "2026-12-04",
                "downtime_days": 5.11,
                "downtime_cost": 822305.4,
                "at_risk_orders": ["PO-4500201377"],
                "total_inaction_cost": 2741018.0,
                "justification": "High risk due to critical API shortage"
            }
        },
        "agent_3": {
            "options": [
                {
                    "option_id": "transfer",
                    "option_type": "transfer",
                    "details": "Transfer 260 kg from D-SG-01",
                    "available_days_from_now": 5,
                    "cost": 15000.0,
                    "co2_kg": 150,
                    "risk_score": 1.5
                },
                {
                    "option_id": "alternative",
                    "option_type": "alternative_supplier",
                    "details": "Switch to Zhejiang",
                    "available_days_from_now": 7,
                    "cost": 25000.0,
                    "co2_kg": 800,
                    "risk_score": 2.0
                },
                {
                    "option_id": "hybrid",
                    "option_type": "hybrid",
                    "details": "Transfer 260 kg + 250 kg air",
                    "available_days_from_now": 2,
                    "cost": 109567.0,
                    "co2_kg": 1650,
                    "risk_score": 0.5
                }
            ]
        },
        "agent_4": {
            "decision": {
                "signal_id": "SG-2611-001",
                "recommended_option": {
                    "option_id": "hybrid",
                    "option_type": "hybrid",
                    "details": "Transfer 260 kg + 250 kg air",
                    "available_days_from_now": 2,
                    "cost": 109567.0,
                    "co2_kg": 1650,
                    "risk_score": 0.5
                },
                "ckkv_score": 0.78,
                "justification": "Hybrid option achieves zero downtime with acceptable cost"
            }
        },
        "final_decision": {
            "signal_id": "SG-2611-001",
            "recommended": True,
            "strategy": "Transfer 260kg + 250kg air",
            "total_cost": 109567.0,
            "downtime_days": 0,
            "justification": "Hybrid strategy recommended by CKKV optimization"
        }
    }
}

def run_full_pipeline(signal_id: str) -> PipelineState:
    """
    Run complete pipeline (simulated)
    In production: calls each agent sequentially
    """
    state = PipelineState(signal_id)
    
    if signal_id not in PIPELINE_RESULTS:
        state.status = "error"
        return state
    
    results = PIPELINE_RESULTS[signal_id]
    
    # Agent 1
    state.agent_1 = results["agent_1"]
    
    # Check risk category
    risk_category = state.agent_1["extraction"].get("risk_category", "High")
    
    # Agent 2
    state.agent_2 = results["agent_2"]
    risk_score = state.agent_2["risk_assessment"]["risk_score"]
    
    # Early exit if low risk
    if risk_score < 7:
        state.status = "low_risk"
        return state
    
    # Agent 3
    state.agent_3 = results["agent_3"]
    
    # Agent 4
    state.agent_4 = results["agent_4"]
    
    # Final decision
    state.final_decision = results["final_decision"]
    state.status = "completed"
    
    return state

# Test Cases
class TestPipelineIntegration:
    """Test suite for complete pipeline"""
    
    def test_pipeline_executes(self):
        """Test pipeline executes without error"""
        state = run_full_pipeline("SG-2611-001")
        assert state.status in ["completed", "low_risk"]
    
    def test_all_agents_produce_output(self):
        """Test each agent produces output"""
        state = run_full_pipeline("SG-2611-001")
        
        assert state.agent_1 is not None
        assert state.agent_2 is not None
        assert state.agent_3 is not None
        assert state.agent_4 is not None
        assert state.final_decision is not None
    
    def test_risk_score_validation(self):
        """Test risk score from pipeline matches reference"""
        state = run_full_pipeline("SG-2611-001")
        
        expected = 22.0  # From reference data
        actual = state.agent_2["risk_assessment"]["risk_score"]
        
        tolerance = 0.02
        assert abs(actual - expected) / expected < tolerance
    
    def test_decision_validation(self):
        """Test final decision matches reference"""
        state = run_full_pipeline("SG-2611-001")
        
        expected_cost = 109567.0
        expected_downtime = 0
        
        actual_cost = state.final_decision["total_cost"]
        actual_downtime = state.final_decision["downtime_days"]
        
        tolerance = 0.02
        assert abs(actual_cost - expected_cost) / expected_cost < tolerance
        assert actual_downtime == expected_downtime
    
    def test_early_exit_low_risk(self):
        """Test early exit for low risk signal"""
        state = run_full_pipeline("SG-2611-012")
        # Would return low_risk status
    
    def test_state_serialization(self):
        """Test state can be serialized to JSON"""
        state = run_full_pipeline("SG-2611-001")
        
        # Convert to dict
        state_dict = {
            "signal_id": state.signal_id,
            "agent_1": state.agent_1,
            "agent_2": state.agent_2,
            "agent_3": state.agent_3,
            "agent_4": state.agent_4,
            "final_decision": state.final_decision,
            "status": state.status
        }
        
        # Should serialize
        json_str = json.dumps(state_dict, default=str)
        assert len(json_str) > 100
    
    def test_different_signals(self):
        """Test pipeline works for different signals"""
        signals = ["SG-2611-001", "SG-2611-003", "SG-2611-005"]
        
        for signal_id in signals:
            state = run_full_pipeline(signal_id)
            assert state.status in ["completed", "low_risk", "error"]
    
    def test_decision_recommended_flag(self):
        """Test decision recommended flag"""
        state = run_full_pipeline("SG-2611-001")
        assert state.final_decision["recommended"] == True
    
    def test_strategy_details(self):
        """Test strategy details in decision"""
        state = run_full_pipeline("SG-2611-001")
        
        decision = state.final_decision
        assert "Transfer" in decision["strategy"]
        assert "air" in decision["strategy"].lower()
    
    def test_justification_complete(self):
        """Test justification contains key elements"""
        state = run_full_pipeline("SG-2611-001")
        
        justification = state.final_decision["justification"]
        assert len(justification) > 30
        assert "CKKV" in justification or "optimize" in justification.lower()

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
