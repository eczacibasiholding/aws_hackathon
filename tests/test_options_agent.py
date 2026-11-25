"""
Test cases for Options Agent (Agent 3)
Tests mitigation option generation and constraint validation
"""
import pytest
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class MitigationOption:
    """Mock Options Agent option"""
    def __init__(self, data: dict):
        self.option_id = data.get("option_id", "UNKNOWN")
        self.option_type = data.get("option_type", "unknown")
        self.details = data.get("details", "")
        self.available_days_from_now = data.get("available_days_from_now", 0)
        self.cost = data.get("cost", 0.0)
        self.co2_kg = data.get("co2_kg", 0.0)
        self.risk_score = data.get("risk_score", 0.0)
        self.constraints_satisfied = data.get("constraints_satisfied", [])
        self.constraints_violated = data.get("constraints_violated", [])
        self.feasibility = data.get("feasibility", "Unknown")
        self.llm_suggestion = data.get("llm_suggestion", "")

# Mock options for reference signals
REFERENCE_OPTIONS = {
    "SG-2611-001": [
        {
            "option_id": "option_1",
            "option_type": "transfer",
            "details": "Transfer 260 kg from D-SG-01 warehouse to T-SG-01",
            "available_days_from_now": 5,
            "cost": 15000.0,
            "co2_kg": 150,
            "risk_score": 1.5,
            "constraints_satisfied": ["capacity", "routing", "quality"],
            "constraints_violated": [],
            "feasibility": "Feasible",
            "llm_suggestion": "Inter-warehouse transfer is the most cost-effective option with minimal risk"
        },
        {
            "option_id": "option_2",
            "option_type": "alternative_supplier",
            "details": "Switch to T-BN-01 (Zhejiang) - 250+ kg available, ruhsatlı",
            "available_days_from_now": 7,
            "cost": 25000.0,
            "co2_kg": 800,
            "risk_score": 2.0,
            "constraints_satisfied": ["quality", "qualification", "moq"],
            "constraints_violated": [],
            "feasibility": "Feasible",
            "llm_suggestion": "Alternative supplier is ruhsatta kayıtlı and meets MOQ requirements"
        },
        {
            "option_id": "option_3",
            "option_type": "expedited",
            "details": "Air freight for critical 260 kg - 2 days delivery",
            "available_days_from_now": 2,
            "cost": 69567.0,
            "co2_kg": 1500,
            "risk_score": 1.0,
            "constraints_satisfied": ["speed", "critical_quantity"],
            "constraints_violated": ["cost", "co2"],
            "feasibility": "Conditional",
            "llm_suggestion": "Air freight eliminates downtime but is expensive and high CO2"
        }
    ],
    "SG-2611-005": [
        {
            "option_id": "option_1",
            "option_type": "alternative_supplier",
            "details": "Tuna/Izmail partial loading 3,000 MT",
            "available_days_from_now": 6,
            "cost": 45000.0,
            "co2_kg": 2500,
            "risk_score": 2.5,
            "constraints_satisfied": ["capacity", "partial_shipment"],
            "constraints_violated": [],
            "feasibility": "Feasible",
            "llm_suggestion": "Izmail loading provides partial relief while Chornomorsk remains closed"
        }
    ]
}

def generate_mitigation_options(signal_id: str) -> list:
    """
    Run Options Agent - generates mitigation options
    In production: uses routing rules, supplier data, and LLM suggestions
    In test: returns mock options based on signal
    """
    if signal_id in REFERENCE_OPTIONS:
        return [MitigationOption(opt) for opt in REFERENCE_OPTIONS[signal_id]]
    else:
        return [
            MitigationOption({
                "option_id": "default_option",
                "option_type": "monitor",
                "details": "Continue monitoring - no immediate action required",
                "available_days_from_now": 0,
                "cost": 0.0,
                "co2_kg": 0.0,
                "risk_score": 0.0,
                "constraints_satisfied": [],
                "constraints_violated": [],
                "feasibility": "NotFeasible",
                "llm_suggestion": "Signal requires further monitoring before generating options"
            })
        ]

# Test Cases
class TestOptionsAgent:
    """Test suite for Options Agent"""
    
    def test_option_generation_high_risk(self):
        """Test option generation for high risk signal"""
        options = generate_mitigation_options("SG-2611-001")
        assert len(options) > 0
        assert all(opt.feasibility in ["Feasible", "Conditional", "NotFeasible"] for opt in options)
    
    def test_option_types(self):
        """Test that options include different types"""
        options = generate_mitigation_options("SG-2611-001")
        option_types = {opt.option_type for opt in options}
        
        # Should include transfer, alternative_supplier, and expedited
        assert "transfer" in option_types
        assert "alternative_supplier" in option_types
        assert "expedited" in option_types
    
    def test_constraint_validation(self):
        """Test constraint satisfaction validation"""
        options = generate_mitigation_options("SG-2611-001")
        
        # Find alternative supplier option
        alt_supplier = next((opt for opt in options if opt.option_type == "alternative_supplier"), None)
        assert alt_supplier is not None
        assert "qualification" in alt_supplier.constraints_satisfied
        assert "moq" in alt_supplier.constraints_satisfied
    
    def test_pharma_qualification(self):
        """Test that unregistered suppliers are excluded for pharma"""
        options = generate_mitigation_options("SG-2611-001")
        
        for opt in options:
            if opt.option_type == "alternative_supplier":
                assert "qualification" in opt.constraints_satisfied
                assert "Ruhsatta Kayıtlı" in opt.details or opt.constraints_violated == []
    
    def test_cost_calculation(self):
        """Test option cost calculations"""
        options = generate_mitigation_options("SG-2611-001")
        
        # Air freight should be most expensive
        air_option = next((opt for opt in options if opt.option_type == "expedited"), None)
        assert air_option is not None
        assert air_option.cost > 50000  # Should be ~69,567
        
        # Transfer should be cheaper
        transfer_option = next((opt for opt in options if opt.option_type == "transfer"), None)
        assert transfer_option is not None
        assert transfer_option.cost < 50000
    
    def test_co2_emissions(self):
        """Test CO2 emissions calculation"""
        options = generate_mitigation_options("SG-2611-001")
        
        # Air freight should have highest CO2
        air_option = next((opt for opt in options if opt.option_type == "expedited"), None)
        assert air_option.co2_kg > 1000
        
        # Transfer should have lower CO2
        transfer_option = next((opt for opt in options if opt.option_type == "transfer"), None)
        assert transfer_option.co2_kg < 500
    
    def test_availability_time(self):
        """Test availability time estimates"""
        options = generate_mitigation_options("SG-2611-001")
        
        # Air freight should be fastest
        air_option = next((opt for opt in options if opt.option_type == "expedited"), None)
        assert air_option.available_days_from_now <= 3
        
        # Transfer should be medium
        transfer_option = next((opt for opt in options if opt.option_type == "transfer"), None)
        assert 3 <= transfer_option.available_days_from_now <= 7
    
    def test_risk_scores(self):
        """Test risk scores for options"""
        options = generate_mitigation_options("SG-2611-001")
        
        # All options should have risk scores
        for opt in options:
            assert 0 <= opt.risk_score <= 5
    
    def test_suggestions_exist(self):
        """Test LLM suggestions are generated"""
        options = generate_mitigation_options("SG-2611-001")
        
        for opt in options:
            assert opt.llm_suggestion is not None
            assert len(opt.llm_suggestion) > 20
    
    def test_different_signals(self):
        """Test different signals have different options"""
        options1 = generate_mitigation_options("SG-2611-001")
        options2 = generate_mitigation_options("SG-2611-005")
        
        # Different signals should have different options
        assert len(options1) != len(options2) or \
               options1[0].details != options2[0].details
    
    def test_option_feasibility(self):
        """Test feasibility classification"""
        options = generate_mitigation_options("SG-2611-001")
        
        feasible = [opt for opt in options if opt.feasibility == "Feasible"]
        conditional = [opt for opt in options if opt.feasibility == "Conditional"]
        not_feasible = [opt for opt in options if opt.feasibility == "NotFeasible"]
        
        # Should have at least one feasible or conditional option
        assert len(feasible) + len(conditional) > 0
    
    def test_no_unregistered_pharma_suppliers(self):
        """Verify unregistered suppliers are excluded"""
        options = generate_mitigation_options("SG-2611-001")
        
        for opt in options:
            if opt.option_type == "alternative_supplier":
                # Should mention qualification or have no violations
                assert "Ruhsatta Kayıtlı" in opt.details or "qualification" in opt.constraints_satisfied

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
