# Requirements Document

## Introduction

The NEXUS Pipeline is an automated risk intervention system for supply chain disruption detection, assessment, and mitigation strategy generation. The pipeline processes risk signals from multiple sources, calculates deterministic risk scores, evaluates mitigation options, and generates strategic recommendations with human approval workflow. The system serves pharmaceutical and critical supply chain operations where production continuity and regulatory compliance are essential.

## Glossary

- **NEXUS Pipeline**: Automated risk detection and mitigation decision support system
- **Signal**: Raw risk notification from external or internal sources
- **Risk Score**: Probability-weighted impact measurement (0-25 scale)
- **Risk Categories**: Low (<7), Medium (7-15), High (≥15) risk classifications
- **Mitigation Option**: Available strategy to address supply chain disruption
- **CKKV Score**: Multi-criteria weighted score (Cost, Downtime, CO2, Risk)
- **Stock Coverage**: Number of days inventory will last at current consumption rate
- **Production Downtime**: Estimated days production line will stop due to shortage
- **Material No**: Unique identifier for raw materials or APIs
- **Shipment ID**: Tracking identifier for container shipments
- **Ruhsatta Kayıtlı**: Regulated materials requiring pharmaceutical qualification
- **Tesis**: Production facility code
- **Tedarikçi**: Supplier code
- **Taşıyıcı**: Carrier/transporter code
- **D0**: Analysis reference date (25.11.2026)
- **ETA**: Estimated Time of Arrival

## Requirements

### Requirement 1: Signal Processing and Extraction

**User Story:** As a risk analyst, I want the pipeline to extract structured information from raw risk signals, so that I can understand the nature, location, and impact of supply chain disruptions.

#### Acceptance Criteria

1. WHEN a risk signal is received, THE NEXUS Pipeline SHALL parse the signal metadata and raw text
2. WHEN signal text contains shipping information, THE NEXUS Pipeline SHALL extract shipment IDs using pattern matching
3. WHEN signal text references a specific port or facility, THE NEXUS Pipeline SHALL identify the affected geographical region
4. IF no LLM service is available, THE NEXUS Pipeline SHALL use pre-registered pattern matching as fallback
5. WHERE signal extraction confidence is below 50%, THE NEXUS Pipeline SHALL flag the signal for manual review

### Requirement 2: Probability Calculation

**User Story:** As a risk assessment agent, I want to calculate risk probability from weighted signal reliability scores, so that I can quantify the likelihood of disruption.

#### Acceptance Criteria

1. THE NEXUS Pipeline SHALL calculate probability using weighted sum: `Olasılık = 0.4×Signal + 0.3×Performance + 0.2×External + 0.1×Financial`
2. WHEN probability components are provided, THE NEXUS Pipeline SHALL apply exact weights from configuration parameters
3. IF component scores are missing, THE NEXUS Pipeline SHALL use zero value and log warning
4. WHILE signal is being assessed, THE NEXUS Pipeline SHALL store intermediate probability scores for audit trail
5. THE NEXUS Pipeline SHALL validate that probability weights sum to 1.0 during initialization

### Requirement 3: Stock Coverage Calculation

**User Story:** As a risk assessment agent, I want to calculate inventory coverage duration, so that I can determine when stock will be depleted.

#### Acceptance Criteria

1. THE NEXUS Pipeline SHALL calculate stock coverage using formula: `Stok_Günü = Mevcut_Stok / Günlük_Tüketim`
2. IF daily consumption is zero, THE NEXUS Pipeline SHALL report infinite coverage and log warning
3. WHEN stock coverage is calculated, THE NEXUS Pipeline SHALL store the value for downstream impact analysis
4. THE NEXUS Pipeline SHALL validate that current stock and daily consumption are non-negative values

### Requirement 4: Risk Scoring and Classification

**User Story:** As a risk management system, I want to compute final risk scores and assign categories, so that stakeholders can understand disruption severity.

#### Acceptance Criteria

1. THE NEXUS Pipeline SHALL compute risk score as: `Risk_Puanı = Olasılık × Etki`
2. WHEN risk score is below 7.0, THE NEXUS Pipeline SHALL classify as "Low"
3. WHEN risk score is between 7.0 and 15.0 (inclusive), THE NEXUS Pipeline SHALL classify as "Medium"
4. WHEN risk score is 15.0 or above, THE NEXUS Pipeline SHALL classify as "High"
5. IF risk score calculation results in negative value, THE NEXUS Pipeline SHALL return zero and log error

### Requirement 5: Downtime Gap and Buffer Calculation

**User Story:** As a supply chain planner, I want to calculate production downtime gap and remaining buffer, so that I can estimate when production will stop and assess safety margins.

#### Acceptance Criteria

1. WHEN calculating available day, THE NEXUS Pipeline SHALL use formula: `Available_Day = Current_ETA + Customs_Days + Inland_Transport_Days + Quality_Approval_Days + Delay_Days`
2. WHEN calculating depletion date, THE NEXUS Pipeline SHALL use formula: `Tükenme_Günü = D0 + Stok_Günü`
3. THE NEXUS Pipeline SHALL calculate remaining buffer as: `Remaining_Buffer = MAX(0, Stock_Coverage_Days - Available_Day)`
4. THE NEXUS Pipeline SHALL calculate downtime gap as: `Downtime_Gap = MAX(0, Available_Day - Stock_Coverage_Days)`
5. WHERE downtime gap is positive, THE NEXUS Pipeline SHALL report production downtime days equal to gap value

### Requirement 6: Financial Impact and Cost Analysis

**User Story:** As a finance manager, I want to estimate financial impact including downtime costs and no-action costs, so that I can justify mitigation investments and assign impact severity scores.

#### Acceptance Criteria

1. WHERE downtime gap is greater than zero, THE NEXUS Pipeline SHALL calculate downtime cost as: `Downtime_Cost = Gap_Days × Daily_Downtime_Cost + One_Time_Restart_Cost`
2. WHERE downtime gap is greater than zero, THE NEXUS Pipeline SHALL calculate customer penalty as: `Penalty = Base_Penalty × MIN(1, Strategy_Downtime / No_Action_Downtime)`
3. WHEN calculating no-action total cost, THE NEXUS Pipeline SHALL sum downtime cost and customer penalties
4. WHERE downtime gap is greater than zero AND no-action cost is at least 2,000,000 TRY, THE NEXUS Pipeline SHALL assign impact score 5
5. WHERE downtime gap is greater than zero AND no-action cost is at least 500,000 TRY, THE NEXUS Pipeline SHALL assign impact score 4
6. WHERE downtime gap is greater than zero AND no-action cost is below 500,000 TRY, THE NEXUS Pipeline SHALL assign impact score 3
7. WHERE downtime gap is zero AND remaining buffer is less than safety stock days, THE NEXUS Pipeline SHALL assign impact score 2
8. WHERE downtime gap is zero AND remaining buffer is at least safety stock days, THE NEXUS Pipeline SHALL assign impact score 1
9. THE NEXUS Pipeline SHALL break down total cost into downtime, customer penalty, and expedited shipping components

### Requirement 7: Mitigation Option Generation

**User Story:** As a logistics coordinator, I want the system to generate feasible mitigation options, so that decision-makers have actionable alternatives.

#### Acceptance Criteria

1. WHEN risk category is High or Medium, THE NEXUS Pipeline SHALL generate transfer options between warehouses
2. WHEN risk involves supplier constraints, THE NEXUS Pipeline SHALL identify alternative suppliers
3. WHERE pharma materials are involved, THE NEXUS Pipeline SHALL only suggest "Ruhsatta Kayıtlı" (registered) suppliers
4. WHEN route changes are possible, THE NEXUS Pipeline SHALL propose alternate shipping routes
5. WHERE expedited shipping reduces downtime, THE NEXUS Pipeline SHALL include air freight options
6. WHEN generating hybrid options, THE NEXUS Pipeline SHALL calculate air quantity as: `Hybrid_Air_Qty = (Main_Shipment_Available_Day + 2_Buffer_Days) × Daily_Consumption - Current_Stock - Transfer_Qty`, rounded up with minimum MOQ applied
7. IF option violates MOQ or capacity constraints, THE NEXUS Pipeline SHALL mark as "NotFeasible" and log violations

### Requirement 8: Option Validation and Constraints

**User Story:** As a quality assurance specialist, I want options validated against business constraints, so that recommendations are operationally viable.

#### Acceptance Criteria

1. WHERE material requires pharmaceutical qualification, THE NEXUS Pipeline SHALL verify "Ruhsatta Kayıtlı" status before suggesting supplier alternatives
2. WHEN supplier options are generated, THE NEXUS Pipeline SHALL check minimum order quantities
3. WHERE production capacity limits exist, THE NEXUS Pipeline SHALL validate option against facility capacity
4. IF option violates any constraint, THE NEXUS Pipeline SHALL list violated constraints and mark feasibility as "Conditional"
5. THE NEXUS Pipeline SHALL assign feasibility as "Feasible" only when all applicable constraints are satisfied

### Requirement 9: Multi-Criteria Strategy Evaluation

**User Story:** As a decision-maker, I want mitigation strategies evaluated using multi-criteria scoring with min-max normalization, so that I can balance cost, speed, sustainability, and risk across all options.

#### Acceptance Criteria

1. FOR each mitigation scenario, THE NEXUS Pipeline SHALL normalize cost using: `Normalized_Cost = (Worst_Cost - Option_Cost) / (Worst_Cost - Best_Cost)` across all options
2. FOR each mitigation scenario, THE NEXUS Pipeline SHALL normalize downtime using: `Normalized_Downtime = (Worst_Downtime - Option_Downtime) / (Worst_Downtime - Best_Downtime)` across all options
3. FOR each mitigation scenario, THE NEXUS Pipeline SHALL normalize CO2 emissions using: `Normalized_CO2 = (Worst_CO2 - Option_CO2) / (Worst_CO2 - Best_CO2)` across all options
4. FOR each mitigation scenario, THE NEXUS Pipeline SHALL normalize risk using: `Normalized_Risk = (Worst_Risk - Option_Risk) / (Worst_Risk - Best_Risk)` across all options
5. IF best and worst values are equal for any criterion, THE NEXUS Pipeline SHALL assign normalized score 1.0 for all options on that criterion
6. THE NEXUS Pipeline SHALL calculate weighted CKKV score as: `CKKV = 0.45 × Normalized_Cost + 0.30 × Normalized_Downtime + 0.10 × Normalized_CO2 + 0.15 × Normalized_Risk`
7. THE NEXUS Pipeline SHALL rank all options by CKKV score in descending order (higher is better)

### Requirement 10: Recommendation Generation

**User Story:** As a supply chain executive, I want the system to recommend optimal strategies with justification, so that stakeholders can approve actions with confidence.

#### Acceptance Criteria

1. WHEN options are ranked by CKKV score, THE NEXUS Pipeline SHALL select the highest scoring option as the final recommendation
2. THE NEXUS Pipeline SHALL generate LLM-based justification explaining recommendation rationale
3. WHERE recommended option achieves zero downtime, THE NEXUS Pipeline SHALL highlight "downtime_zero" constraint satisfaction
4. THE NEXUS Pipeline SHALL include all ranked options in output for stakeholder review
5. THE NEXUS Pipeline SHALL present cost breakdown and performance metrics for the recommended option

### Requirement 11: Human Approval Workflow

**User Story:** As a compliance officer, I want strategic decisions to require human approval, so that critical actions are verified before implementation.

#### Acceptance Criteria

1. WHEN final recommendation is ready, THE NEXUS Pipeline SHALL present options to approval UI
2. WHERE risk category is High, THE NEXUS Pipeline SHALL require explicit user approval before execution
3. IF user rejects recommendation, THE NEXUS Pipeline SHALL log rejection and store alternative preference
4. WHEN approval is granted, THE NEXUS Pipeline SHALL record timestamp and approver identity
5. THE NEXUS Pipeline SHALL store decision state in JSON format with full audit trail

### Requirement 12: Low-Risk Signal Handling

**User Story:** As an operations manager, I want low-risk signals to receive minimal intervention, so that resources focus on high-priority disruptions.

#### Acceptance Criteria

1. WHEN risk score is below 7.0, THE NEXUS Pipeline SHALL classify signal as Low Risk
2. FOR Low Risk signals, THE NEXUS Pipeline SHALL skip option generation and proceed directly to monitoring
3. WHERE signal is Low Risk, THE NEXUS Pipeline SHALL generate brief status update without strategic options
4. THE NEXUS Pipeline SHALL log Low Risk signals for periodic review without requiring approval
5. IF signal status changes to Higher Risk, THE NEXUS Pipeline SHALL re-trigger full analysis

### Requirement 13: LLM Integration and Fallback

**User Story:** As a technical lead, I want LLM integration with graceful fallback, so that the system remains operational during service outages.

#### Acceptance Criteria

1. WHEN LLM is available, THE NEXUS Pipeline SHALL use it for text generation and justification
2. IF LLM call fails, THE NEXUS Pipeline SHALL attempt mock data lookup for pre-registered signals
3. WHEN no mock data exists, THE NEXUS Pipeline SHALL use deterministic fallback explanations
4. THE NEXUS Pipeline SHALL log LLM usage status and fallback method for each signal
5. WHERE LLM provides risk explanation, THE NEXUS Pipeline SHALL verify consistency with calculated scores

### Requirement 14: Data Integration and Validation

**User Story:** As a data engineer, I want input data validated and integrated from Excel, so that the pipeline operates on accurate reference information.

#### Acceptance Criteria

1. THE NEXUS Pipeline SHALL read all required sheets from `data/NEXUS_Agent_Veri_Seti_TEKNIK.xlsx`
2. WHERE required data is missing, THE NEXUS Pipeline SHALL log specific missing fields
3. WHEN signal references shipment data, THE NEXUS Pipeline SHALL validate shipment exists in Sevkiyatlar sheet
4. IF material code does not exist in Malzemeler sheet, THE NEXUS Pipeline SHALL reject signal with error
5. THE NEXUS Pipeline SHALL load configuration parameters from Parametreler sheet on startup

### Requirement 15: Output Format and Validation

**User Story:** As a developer, I want consistent output format matching test expectations, so that integration tests validate behavior correctly.

#### Acceptance Criteria

1. FOR signal SG-2611-001 (R-01), THE NEXUS Pipeline SHALL produce risk score approximately 22.0
2. FOR signal SG-2611-001 (R-01), THE NEXUS Pipeline SHALL report stock coverage approximately 9.89 days
3. FOR signal SG-2611-001 (R-01), THE NEXUS Pipeline SHALL calculate downtime approximately 5.11 days
4. FOR signal SG-2611-001 (R-01), THE NEXUS Pipeline SHALL estimate no-action cost approximately 2,741,018 TRY
5. FOR signal SG-2611-001 (R-01), WHERE recommended strategy is hybrid, THE NEXUS Pipeline SHALL suggest transfer 260kg + 250kg air cargo at approximately 109,567 TRY with zero downtime

### Requirement 16: Testing Integration

**User Story:** As a QA engineer, I want existing tests integrated with new pipeline implementation, so that all components work together correctly.

#### Acceptance Criteria

1. THE NEXUS Pipeline SHALL expose interfaces compatible with existing test files in `tests/` directory
2. WHEN Agent 1 (Signal Agent) is invoked, THE NEXUS Pipeline SHALL produce output compatible with `test_signal_agent.py` expectations
3. WHEN Agent 2 (Risk Agent) is invoked, THE NEXUS Pipeline SHALL produce output compatible with `test_risk_agent.py` expectations
4. WHEN Agent 3 (Options Agent) is invoked, THE NEXUS Pipeline SHALL produce output compatible with `test_options_agent.py` expectations
5. WHEN Agent 4 (Decision Agent) is invoked, THE NEXUS Pipeline SHALL produce output compatible with `test_decision_agent.py` expectations
6. THE NEXUS Pipeline SHALL support end-to-end integration testing as defined in `test_integration.py`

### Requirement 17: Configuration Parameters

**User Story:** As a system administrator, I want parameters configurable without code changes, so that the system can adapt to changing business rules.

#### Acceptance Criteria

1. WHEN NEXUS Pipeline starts, THE NEXUS Pipeline SHALL load configuration from `data/NEXUS_Agent_Veri_Seti_TEKNIK.xlsx` Parametreler sheet
2. THE NEXUS Pipeline SHALL use analysis reference date (D0) = 25.11.2026 for all time calculations
3. WHERE risk thresholds are configured, THE NEXUS Pipeline SHALL use EsikYuksek = 15 and EsikOrta = 7
4. THE NEXUS Pipeline SHALL use probability weights: Signal (0.4), Performance (0.3), External (0.2), Financial (0.1)
5. IF configuration parameters conflict, THE NEXUS Pipeline SHALL fail on startup with explicit error message

### Requirement 18: State Management

**User Story:** As a system operator, I want pipeline state persisted for audit and replay, so that decisions are traceable and reproducible.

#### Acceptance Criteria

1. WHEN pipeline processes signal, THE NEXUS Pipeline SHALL create state record with agent outputs
2. THE NEXUS Pipeline SHALL store state in JSON format with full agent step data
3. WHEN state is saved, THE NEXUS Pipeline SHALL include timestamp, signal ID, and processing status
4. FOR completed pipeline runs, THE NEXUS Pipeline SHALL mark status as "completed" or "low_risk"
5. WHEN pipeline fails, THE NEXUS Pipeline SHALL save partial state and error details

### Requirement 19: Error Handling

**User Story:** As a system maintainer, I want comprehensive error handling, so that failures don't cascade and diagnostic information is clear.

#### Acceptance Criteria

1. WHEN data file is missing, THE NEXUS Pipeline SHALL fail on startup with explicit file path error
2. IF signal ID is not found in input data, THE NEXUS Pipeline SHALL return error with available signal list
3. WHERE LLM returns malformed JSON, THE NEXUS Pipeline SHALL revert to deterministic extraction and log warning
4. IF intermediate calculation results in division by zero, THE NEXUS Pipeline SHALL return infinity or error code
5. THE NEXUS Pipeline SHALL maintain pipeline state during partial failures to enable recovery

### Requirement 20: Performance and Scalability

**User Story:** As a performance engineer, I want pipeline processing within acceptable time bounds, so that analysts receive timely recommendations.

#### Acceptance Criteria

1. WHEN processing a single signal, THE NEXUS Pipeline SHALL complete within 30 seconds for 100 options
2. THE NEXUS Pipeline SHALL process low-risk signals in under 5 seconds
3. FOR high-risk signals requiring full analysis, THE NEXUS Pipeline SHALL complete within 60 seconds
4. THE NEXUS Pipeline SHALL log processing time metrics for monitoring