"""
Tests for Pydantic models in src/nexus/models.py

This test suite validates that all agent I/O models:
- Can be instantiated with valid data
- Enforce type constraints
- Handle optional fields correctly
"""

import json
from datetime import date, datetime

import pytest

from src.nexus.models import (
    SignalInput,
    SignalExtraction,
    RiskInput,
    RiskAssessment,
    OptionsInput,
    Arrival,
    MitigationOption,
    DecisionInput,
    RankedOption,
    DecisionResult,
    PipelineState,
)


class TestSignalAgentModels:
    """Test Agent 1 (Signal Agent) models"""

    def test_signal_input_valid(self):
        """Test SignalInput with valid data"""
        signal_input = SignalInput(
            signal_id="SG-2611-001",
            signal_text="Port closure at Jeddah",
            signal_date=date(2026, 11, 24),
            signal_source="KY02",
        )
        assert signal_input.signal_id == "SG-2611-001"
        assert signal_input.signal_source == "KY02"

    def test_signal_extraction_valid(self):
        """Test SignalExtraction with all fields"""
        extraction = SignalExtraction(
            signal_id="SG-2611-001",
            event_type="Port congestion",
            country_region="Saudi Arabia",
            party_code="TS01",
            shipment_id="AKH-MUN-26-1184",
            material_no="MT100054",
            estimated_delay_days=8,
            alternative_hints=["Discharge at Mersin"],
            confidence=0.95,
            extraction_method="llm",
        )
        assert extraction.signal_id == "SG-2611-001"
        assert extraction.estimated_delay_days == 8
        assert extraction.extraction_method == "llm"

    def test_signal_extraction_optional_fields(self):
        """Test SignalExtraction with minimal required fields"""
        extraction = SignalExtraction(
            signal_id="SG-2611-002",
            event_type="Unknown",
            country_region="Unknown",
            estimated_delay_days=0,
            confidence=0.3,
            extraction_method="pattern_match",
        )
        assert extraction.party_code is None
        assert extraction.shipment_id is None
        assert extraction.material_no is None
        assert len(extraction.alternative_hints) == 0

    def test_signal_extraction_method_literal(self):
        """Test extraction_method accepts only valid literals"""
        with pytest.raises(ValueError):
            SignalExtraction(
                signal_id="SG-2611-003",
                event_type="Test",
                country_region="Test",
                estimated_delay_days=0,
                confidence=0.5,
                extraction_method="invalid_method",  # Should fail
            )


class TestRiskAgentModels:
    """Test Agent 2 (Risk & Impact Agent) models"""

    def test_risk_input_valid(self):
        """Test RiskInput with extraction"""
        extraction = SignalExtraction(
            signal_id="SG-2611-001",
            event_type="Port congestion",
            country_region="Saudi Arabia",
            estimated_delay_days=8,
            confidence=0.95,
            extraction_method="llm",
        )
        risk_input = RiskInput(signal_id="SG-2611-001", extraction=extraction)
        assert risk_input.signal_id == "SG-2611-001"
        assert risk_input.extraction.estimated_delay_days == 8

    def test_risk_assessment_valid(self):
        """Test RiskAssessment with all fields"""
        assessment = RiskAssessment(
            signal_id="SG-2611-001",
            probability_score=4.4,
            impact_score=5,
            risk_score=22.0,
            risk_category="High",
            available_date=date(2026, 12, 5),
            stock_coverage_days=9.9,
            depletion_date=date(2026, 12, 4),
            downtime_days=5.1,
            remaining_buffer=0.0,
            downtime_cost=229500.0,
            customer_penalty=350000.0,
            total_inaction_cost=579500.0,
            at_risk_orders=["SO-12345", "SO-12346"],
            justification="High risk due to production line stoppage",
        )
        assert assessment.risk_score == 22.0
        assert assessment.risk_category == "High"
        assert len(assessment.at_risk_orders) == 2

    def test_risk_category_literal(self):
        """Test risk_category accepts only valid literals"""
        with pytest.raises(ValueError):
            RiskAssessment(
                signal_id="SG-2611-001",
                probability_score=4.4,
                impact_score=5,
                risk_score=22.0,
                risk_category="Critical",  # Should fail - not in Literal
                available_date=date(2026, 12, 5),
                stock_coverage_days=9.9,
                depletion_date=date(2026, 12, 4),
                downtime_days=5.1,
                remaining_buffer=0.0,
                downtime_cost=229500.0,
                customer_penalty=0.0,
                total_inaction_cost=229500.0,
                at_risk_orders=[],
                justification="Test",
            )


class TestOptionsAgentModels:
    """Test Agent 3 (Options Agent) models"""

    def test_arrival_valid(self):
        """Test Arrival model"""
        arrival = Arrival(day=5, quantity=260.0)
        assert arrival.day == 5
        assert arrival.quantity == 260.0

    def test_mitigation_option_valid(self):
        """Test MitigationOption with all fields"""
        option = MitigationOption(
            option_id="opt_transfer_001",
            option_type="transfer",
            details="Transfer 260kg from T-AKH-01",
            arrivals=[Arrival(day=2, quantity=260.0)],
            action_cost=15000.0,
            co2_kg=120.0,
            risk_score=5.0,
            downtime_days=3.5,
            total_cost=172500.0,
            constraints_satisfied=["transfer_protection", "capacity"],
            constraints_violated=[],
            feasibility="Feasible",
            llm_suggestion="Recommended for quick response",
        )
        assert option.option_type == "transfer"
        assert len(option.arrivals) == 1
        assert option.feasibility == "Feasible"

    def test_mitigation_option_no_action(self):
        """Test no_action option type"""
        option = MitigationOption(
            option_id="no_action",
            option_type="no_action",
            details="Wait for original shipment",
            arrivals=[Arrival(day=15, quantity=2000.0)],
            action_cost=0.0,
            co2_kg=0.0,
            risk_score=22.0,
            downtime_days=5.1,
            total_cost=579500.0,
            constraints_satisfied=[],
            constraints_violated=[],
            feasibility="Feasible",
        )
        assert option.option_type == "no_action"
        assert option.action_cost == 0.0

    def test_option_type_literal(self):
        """Test option_type accepts only valid literals"""
        with pytest.raises(ValueError):
            MitigationOption(
                option_id="opt_invalid",
                option_type="emergency_purchase",  # Should fail
                details="Invalid option",
                arrivals=[Arrival(day=1, quantity=100.0)],
                action_cost=1000.0,
                co2_kg=50.0,
                risk_score=10.0,
                downtime_days=0.0,
                total_cost=1000.0,
                constraints_satisfied=[],
                constraints_violated=[],
                feasibility="Feasible",
            )

    def test_options_input_valid(self):
        """Test OptionsInput with extraction and assessment"""
        extraction = SignalExtraction(
            signal_id="SG-2611-001",
            event_type="Port congestion",
            country_region="Saudi Arabia",
            estimated_delay_days=8,
            confidence=0.95,
            extraction_method="llm",
        )
        assessment = RiskAssessment(
            signal_id="SG-2611-001",
            probability_score=4.4,
            impact_score=5,
            risk_score=22.0,
            risk_category="High",
            available_date=date(2026, 12, 5),
            stock_coverage_days=9.9,
            depletion_date=date(2026, 12, 4),
            downtime_days=5.1,
            remaining_buffer=0.0,
            downtime_cost=229500.0,
            customer_penalty=0.0,
            total_inaction_cost=229500.0,
            at_risk_orders=[],
            justification="High risk",
        )
        options_input = OptionsInput(
            signal_id="SG-2611-001", extraction=extraction, assessment=assessment
        )
        assert options_input.signal_id == "SG-2611-001"


class TestDecisionAgentModels:
    """Test Agent 4 (Decision Agent) models"""

    def test_ranked_option_valid(self):
        """Test RankedOption with normalized scores"""
        option = MitigationOption(
            option_id="opt_transfer_001",
            option_type="transfer",
            details="Transfer option",
            arrivals=[Arrival(day=2, quantity=260.0)],
            action_cost=15000.0,
            co2_kg=120.0,
            risk_score=5.0,
            downtime_days=3.5,
            total_cost=172500.0,
            constraints_satisfied=[],
            constraints_violated=[],
            feasibility="Feasible",
        )
        ranked = RankedOption(
            option=option,
            normalized_cost=0.85,
            normalized_downtime=0.70,
            normalized_co2=0.90,
            normalized_risk=0.80,
            ckkv_score=0.81,
            rank=1,
        )
        assert ranked.rank == 1
        assert 0.0 <= ranked.ckkv_score <= 1.0

    def test_decision_result_valid(self):
        """Test DecisionResult with ranked options"""
        option1 = MitigationOption(
            option_id="opt_transfer_001",
            option_type="transfer",
            details="Transfer option",
            arrivals=[Arrival(day=2, quantity=260.0)],
            action_cost=15000.0,
            co2_kg=120.0,
            risk_score=5.0,
            downtime_days=3.5,
            total_cost=172500.0,
            constraints_satisfied=[],
            constraints_violated=[],
            feasibility="Feasible",
        )
        ranked1 = RankedOption(
            option=option1,
            normalized_cost=0.85,
            normalized_downtime=0.70,
            normalized_co2=0.90,
            normalized_risk=0.80,
            ckkv_score=0.81,
            rank=1,
        )
        
        decision = DecisionResult(
            signal_id="SG-2611-001",
            all_options_ranked=[ranked1],
            recommended_option=ranked1,
            justification="Transfer option provides best balance of cost and time",
        )
        assert decision.signal_id == "SG-2611-001"
        assert decision.recommended_option.rank == 1
        assert len(decision.all_options_ranked) == 1


class TestPipelineState:
    """Test Orchestrator PipelineState model"""

    def test_pipeline_state_minimal(self):
        """Test PipelineState with minimal required fields"""
        state = PipelineState(
            signal_id="SG-2611-001",
            timestamp=datetime(2026, 11, 25, 10, 30, 0),
            status="in_progress",
        )
        assert state.signal_id == "SG-2611-001"
        assert state.status == "in_progress"
        assert state.agent_1_output is None
        assert state.agent_2_output is None
        assert state.agent_3_output is None
        assert state.agent_4_output is None
        assert state.approval_decision is None
        assert state.approver_identity is None
        assert state.error_message is None

    def test_pipeline_state_with_agent_outputs(self):
        """Test PipelineState with all agent outputs populated"""
        # Create Agent 1 output
        extraction = SignalExtraction(
            signal_id="SG-2611-001",
            event_type="Port congestion",
            country_region="Saudi Arabia",
            party_code="TS01",
            shipment_id="AKH-MUN-26-1184",
            material_no="MT100054",
            estimated_delay_days=8,
            alternative_hints=["Discharge at Mersin"],
            confidence=0.95,
            extraction_method="llm",
        )

        # Create Agent 2 output
        assessment = RiskAssessment(
            signal_id="SG-2611-001",
            probability_score=4.4,
            impact_score=5,
            risk_score=22.0,
            risk_category="High",
            available_date=date(2026, 12, 5),
            stock_coverage_days=9.9,
            depletion_date=date(2026, 12, 4),
            downtime_days=5.1,
            remaining_buffer=0.0,
            downtime_cost=229500.0,
            customer_penalty=350000.0,
            total_inaction_cost=579500.0,
            at_risk_orders=["SO-12345"],
            justification="High risk due to production line stoppage",
        )

        # Create Agent 3 output
        option = MitigationOption(
            option_id="opt_transfer_001",
            option_type="transfer",
            details="Transfer 260kg from T-AKH-01",
            arrivals=[Arrival(day=2, quantity=260.0)],
            action_cost=15000.0,
            co2_kg=120.0,
            risk_score=5.0,
            downtime_days=3.5,
            total_cost=172500.0,
            constraints_satisfied=["transfer_protection"],
            constraints_violated=[],
            feasibility="Feasible",
        )

        # Create Agent 4 output
        ranked = RankedOption(
            option=option,
            normalized_cost=0.85,
            normalized_downtime=0.70,
            normalized_co2=0.90,
            normalized_risk=0.80,
            ckkv_score=0.81,
            rank=1,
        )
        decision = DecisionResult(
            signal_id="SG-2611-001",
            all_options_ranked=[ranked],
            recommended_option=ranked,
            justification="Transfer option provides best balance",
        )

        # Create pipeline state
        state = PipelineState(
            signal_id="SG-2611-001",
            timestamp=datetime(2026, 11, 25, 10, 30, 0),
            status="completed",
            agent_1_output=extraction,
            agent_2_output=assessment,
            agent_3_output=[option],
            agent_4_output=decision,
            approval_decision="approved",
            approver_identity="user@example.com",
        )

        assert state.signal_id == "SG-2611-001"
        assert state.status == "completed"
        assert state.agent_1_output.extraction_method == "llm"
        assert state.agent_2_output.risk_category == "High"
        assert len(state.agent_3_output) == 1
        assert state.agent_4_output.recommended_option.rank == 1
        assert state.approval_decision == "approved"
        assert state.approver_identity == "user@example.com"

    def test_pipeline_state_low_risk(self):
        """Test PipelineState for low-risk signal (stops after Agent 2)"""
        extraction = SignalExtraction(
            signal_id="SG-2611-012",
            event_type="Rumor",
            country_region="USA",
            estimated_delay_days=0,
            confidence=0.3,
            extraction_method="pattern_match",
        )
        assessment = RiskAssessment(
            signal_id="SG-2611-012",
            probability_score=1.5,
            impact_score=1,
            risk_score=1.5,
            risk_category="Low",
            available_date=date(2026, 11, 27),
            stock_coverage_days=30.0,
            depletion_date=date(2026, 12, 25),
            downtime_days=0.0,
            remaining_buffer=20.0,
            downtime_cost=0.0,
            customer_penalty=0.0,
            total_inaction_cost=0.0,
            at_risk_orders=[],
            justification="Low risk - monitor only",
        )

        state = PipelineState(
            signal_id="SG-2611-012",
            timestamp=datetime(2026, 11, 25, 11, 0, 0),
            status="low_risk",
            agent_1_output=extraction,
            agent_2_output=assessment,
            # Agent 3 and 4 not executed for low-risk signals
        )

        assert state.status == "low_risk"
        assert state.agent_2_output.risk_category == "Low"
        assert state.agent_3_output is None
        assert state.agent_4_output is None

    def test_pipeline_state_error(self):
        """Test PipelineState with error status"""
        state = PipelineState(
            signal_id="SG-2611-999",
            timestamp=datetime(2026, 11, 25, 12, 0, 0),
            status="error",
            error_message="Failed to load shipment data for signal SG-2611-999",
        )

        assert state.status == "error"
        assert state.error_message is not None
        assert "Failed to load" in state.error_message
        assert state.agent_1_output is None

    def test_pipeline_state_status_literal(self):
        """Test status field accepts only valid literals"""
        with pytest.raises(ValueError):
            PipelineState(
                signal_id="SG-2611-001",
                timestamp=datetime(2026, 11, 25, 10, 30, 0),
                status="pending",  # Should fail - not in Literal
            )

    def test_pipeline_state_approval_decision_literal(self):
        """Test approval_decision field accepts only valid literals"""
        with pytest.raises(ValueError):
            PipelineState(
                signal_id="SG-2611-001",
                timestamp=datetime(2026, 11, 25, 10, 30, 0),
                status="completed",
                approval_decision="maybe",  # Should fail - not in Literal
            )

    def test_pipeline_state_json_serialization(self):
        """Test PipelineState can be serialized to JSON"""
        extraction = SignalExtraction(
            signal_id="SG-2611-001",
            event_type="Port congestion",
            country_region="Saudi Arabia",
            estimated_delay_days=8,
            confidence=0.95,
            extraction_method="llm",
        )

        state = PipelineState(
            signal_id="SG-2611-001",
            timestamp=datetime(2026, 11, 25, 10, 30, 0),
            status="in_progress",
            agent_1_output=extraction,
        )

        # Serialize to JSON
        json_str = state.model_dump_json(indent=2)
        assert json_str is not None
        
        # Verify it's valid JSON
        json_dict = json.loads(json_str)
        assert json_dict["signal_id"] == "SG-2611-001"
        assert json_dict["status"] == "in_progress"
        assert json_dict["agent_1_output"]["event_type"] == "Port congestion"

    def test_pipeline_state_json_deserialization(self):
        """Test PipelineState can be deserialized from JSON"""
        json_data = {
            "signal_id": "SG-2611-001",
            "timestamp": "2026-11-25T10:30:00",
            "status": "completed",
            "agent_1_output": {
                "signal_id": "SG-2611-001",
                "event_type": "Port congestion",
                "country_region": "Saudi Arabia",
                "party_code": None,
                "shipment_id": None,
                "material_no": None,
                "estimated_delay_days": 8,
                "alternative_hints": [],
                "confidence": 0.95,
                "extraction_method": "llm",
            },
            "agent_2_output": None,
            "agent_3_output": None,
            "agent_4_output": None,
            "approval_decision": None,
            "approver_identity": None,
            "error_message": None,
        }

        # Deserialize from dict
        state = PipelineState(**json_data)
        assert state.signal_id == "SG-2611-001"
        assert state.status == "completed"
        assert state.agent_1_output.extraction_method == "llm"
        assert state.agent_2_output is None

