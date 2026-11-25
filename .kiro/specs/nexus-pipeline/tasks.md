# Implementation Plan: NEXUS Pipeline

## Overview

This plan implements the NEXUS Pipeline, an automated risk intervention system for pharmaceutical supply chain disruption detection, assessment, and mitigation strategy generation. The implementation follows a bottom-up approach: data models → data loading → LLM abstraction → agent implementations → orchestration → UI. Each task includes validation against reference scenario S1 (signal SG-2611-001 / R-01) with ±2% tolerance for numerical assertions.

## Tasks

- [x] 1. Set up project structure and dependencies
  - Create `pyproject.toml` or `requirements.txt` with core dependencies: `pandas>=2.0.0`, `openpyxl>=3.1.0`, `pydantic>=2.0.0`, `streamlit>=1.28.0`, `pytest>=7.4.0`, `boto3>=1.28.0`, `python-dotenv>=1.0.0`, `hypothesis>=6.90.0`
  - Create `src/nexus/__init__.py` package directory
  - Create `src/nexus/agents/__init__.py` subdirectory
  - Create `decisions/` directory for JSON state persistence
  - Create `.env.example` file with environment variable templates (NEXUS_EXCEL_PATH, AWS_REGION, USE_MOCK_LLM)
  - _Requirements: 14.1, 14.5, 18.2_

- [x] 2. Implement data models in models.py
  - [x] 2.1 Create core Pydantic models for agent inputs and outputs
    - Implement `SignalInput` model (signal_id, signal_text, signal_date, signal_source)
    - Implement `SignalExtraction` model (event_type, country_region, party_code, shipment_id, material_no, estimated_delay_days, alternative_hints, confidence, extraction_method)
    - Implement `RiskInput` model (signal_id, extraction)
    - Implement `RiskAssessment` model (probability_score, impact_score, risk_score, risk_category, available_date, stock_coverage_days, depletion_date, downtime_days, remaining_buffer, downtime_cost, customer_penalty, total_inaction_cost, at_risk_orders, justification)
    - Implement `OptionsInput` model (signal_id, extraction, assessment)
    - Implement `Arrival` model (day, quantity)
    - Implement `MitigationOption` model (option_id, option_type, details, arrivals, action_cost, co2_kg, risk_score, downtime_days, total_cost, constraints_satisfied, constraints_violated, feasibility, llm_suggestion)
    - Implement `DecisionInput` model (signal_id, extraction, assessment, options)
    - Implement `RankedOption` model (option, normalized_cost, normalized_downtime, normalized_co2, normalized_risk, ckkv_score, rank)
    - Implement `DecisionResult` model (signal_id, all_options_ranked, recommended_option, justification)
    - _Requirements: 1.1, 2.1, 4.1, 6.1, 7.1, 9.1, 10.1_
  
  - [x] 2.2 Create data row models for Excel sheet mappings
    - Implement `SignalRow` model matching Risk_Sinyalleri sheet columns (sinyal_no, ham_metin, yayin_zamani, kaynak_kodu, kaynak_adi, kategori)
    - Implement `ShipmentRow` model matching Sevkiyatlar sheet (sevkiyat_no, takip_no, po_no, malzeme_no, miktar, birim, tedarikci_no, tasiyici_no, sevkiyat_tarihi, eta, gemi_adi)
    - Implement `MaterialRow` model matching Malzemeler sheet (malzeme_no, malzeme_adi, kategori, min_siparis_miktari, birim)
    - Implement `StockRow` model matching Stok_Durumu sheet (stok_anahtari, malzeme_no, tesis_kodu, mevcut_stok, gunluk_tuketim, emniyet_stoku)
    - Implement `SupplierRow` model matching Tedarikciler sheet (tedarikci_no, tedarikci_adi, ulke, finansal_not)
    - Implement `SupplySourceRow` model matching Tedarik_Kaynaklari sheet (kaynak_anahtari, malzeme_no, tedarikci_no, ana_kaynak_mi, kalifikasyon_durumu, kalifikasyon_suresi_gun, standart_tedarik_suresi_gun, birim_fiyat_usd, spot_moq)
    - Implement `ProductionLineRow` model matching Uretim_Hatlari sheet (hat_kodu, tesis_kodu, kritik_malzeme_no, gunluk_malzeme_ihtiyaci, gunluk_durus_maliyeti, yeniden_baslatma_maliyeti)
    - Implement `CustomerOrderRow` model matching Musteri_Siparisleri sheet (siparis_no, mamul_no, miktar, teslimat_tarihi, ceza_maddesi)
    - Implement `ParametersRow` model matching Parametreler sheet (analiz_referans_tarihi, usdtry, eurtry, eurusd, stok_tasima_orani, planlama_tamponu, koruma_ufku, qc_test_maliyeti, esik_yuksek, esik_orta, olasilik_agirlik_sinyal, olasilik_agirlik_performans, olasilik_agirlik_dis, olasilik_agirlik_finansal, ckkv_agirlik_maliyet, ckkv_agirlik_durusma, ckkv_agirlik_co2, ckkv_agirlik_risk)
    - _Requirements: 14.1, 14.5, 17.1_
  
  - [x] 2.3 Create pipeline state model
    - Implement `PipelineState` model (signal_id, agent_1_output, agent_2_output, agent_3_output, agent_4_output, status, approval_decision, approver_identity, error_message)
    - _Requirements: 18.1, 18.3, 18.4_

- [ ] 3. Implement data loader with Excel integration
  - [-] 3.1 Create DataLoader class in data_loader.py
    - Implement `__init__(self, excel_path: str)` to load Excel file using pandas and openpyxl
    - Parse all required sheets: Risk_Sinyalleri, Sevkiyatlar, Malzemeler, Stok_Durumu, Tedarikciler, Tedarik_Kaynaklari, Uretim_Hatlari, Musteri_Siparisleri, Parametreler
    - Validate required sheets exist on startup (fail-fast with explicit error message)
    - Validate required columns exist in each sheet (log warning if optional columns missing)
    - _Requirements: 14.1, 14.2, 19.1_
  
  - [ ] 3.2 Implement typed accessor methods
    - Implement `get_signal(self, signal_id: str) -> SignalRow` with KeyError on not found
    - Implement `get_shipment(self, shipment_id: str) -> ShipmentRow`
    - Implement `get_material(self, material_no: str) -> MaterialRow`
    - Implement `get_supplier(self, supplier_code: str) -> SupplierRow`
    - Implement `get_stock_status(self, material_no: str, facility_code: str) -> StockRow`
    - Implement `get_production_lines(self, facility_code: str) -> List[ProductionLineRow]`
    - Implement `get_customer_orders(self, material_no: str) -> List[CustomerOrderRow]`
    - Implement `get_supply_sources(self, material_no: str) -> List[SupplySourceRow]`
    - Implement `get_parameters() -> ParametersRow`
    - _Requirements: 14.3, 14.4, 19.2_
  
  - [ ]* 3.3 Write unit tests for data loader
    - Test DataLoader successfully loads `data/NEXUS_Agent_Veri_Seti_TEKNIK.xlsx`
    - Test `get_signal("SG-2611-001")` returns valid SignalRow
    - Test `get_shipment("SV-26-1184")` returns valid ShipmentRow with material_no="M-1037"
    - Test `get_parameters()` returns ParametersRow with usdtry=45.9, esik_yuksek=15.0, esik_orta=7.0
    - Test missing signal_id raises KeyError with helpful message
    - Test missing Excel file raises DataLoadError on initialization
    - Verify analiz_referans_tarihi equals date(2026, 11, 25) (D0 = 25.11.2026)
    - _Requirements: 14.1, 14.3, 15.1, 17.2, 17.3, 19.1, 19.2_

- [ ] 4. Implement LLM client abstraction
  - [~] 4.1 Create LLMClient interface in llm_client.py
    - Define abstract base class `LLMClient` with `generate(self, prompt: str, json_mode: bool = False) -> str` method
    - _Requirements: 13.1_
  
  - [~] 4.2 Implement MockClient for testing
    - Create `MockClient(LLMClient)` class with recorded extractions dictionary
    - Preload mock data for signals S1 (SG-2611-001), S2, S3 with known extraction results
    - For S1: return extraction with shipment_id="SV-26-1184", estimated_delay_days=8, alternative_hints=["Mersin"], confidence=0.9, extraction_method="llm"
    - Implement `generate()` method to lookup signal_id in mock data and return JSON
    - Return error JSON if signal_id not in mock data
    - _Requirements: 13.2, 13.3_
  
  - [~] 4.3 Implement BedrockClient for AWS integration
    - Create `BedrockClient(LLMClient)` class with boto3 bedrock-runtime client
    - Use model_id from environment variable or default to "anthropic.claude-3-sonnet-20240229-v1:0"
    - Implement `generate()` method with proper error handling (timeout, malformed JSON)
    - Log LLM call failures with warning level
    - Raise exception on failure (to trigger fallback)
    - _Requirements: 13.1, 13.4, 19.3_
  
  - [~] 4.4 Implement FallbackLLMClient for graceful degradation
    - Create `FallbackLLMClient(LLMClient)` with primary and fallback clients
    - Try primary client first, catch exceptions and use fallback on failure
    - Log fallback usage with warning level
    - _Requirements: 13.1, 13.2, 13.3, 13.4_
  
  - [~] 4.5 Add environment variable configuration
    - Read USE_MOCK_LLM environment variable (default: "true" for tests)
    - Create factory function `create_llm_client()` that returns MockClient if USE_MOCK_LLM=true, else FallbackLLMClient(BedrockClient, MockClient)
    - _Requirements: 13.1, 13.4_

- [ ] 5. Implement Agent 1: Signal Agent
  - [~] 5.1 Create signal extraction function in agents/signal_agent.py
    - Implement `process_signal(input_data: SignalInput, llm_client: LLMClient, data_loader: DataLoader) -> SignalExtraction`
    - Construct LLM prompt with signal text and extraction schema (event_type, country_region, party_code, shipment_id, material_no, estimated_delay_days, alternative_hints)
    - Call llm_client.generate() with json_mode=True
    - Parse JSON response into SignalExtraction model
    - Set extraction_method="llm" and store confidence from LLM
    - _Requirements: 1.1, 1.2, 13.1_
  
  - [~] 5.2 Add pattern matching fallback
    - Implement regex pattern for shipment IDs: `[A-Z]{3}-[A-Z]{3}-\d{2}-\d{4}` (e.g., SV-26-1184)
    - Implement keyword matching for event types (port, closure, delay, quality, power)
    - Set extraction_method="pattern_match" when LLM fails
    - Set confidence based on match quality (0.5 for pattern match, 0.3 for partial)
    - _Requirements: 1.2, 1.4, 13.2, 13.3_
  
  - [~] 5.3 Add low confidence flagging
    - If confidence < 0.5, add flag to extraction indicating manual review required
    - Log warning for low confidence extractions
    - _Requirements: 1.5, 13.4_
  
  - [ ]* 5.4 Write unit tests for signal agent
    - Test `process_signal()` with mock LLM for signal SG-2611-001
    - Verify extraction contains shipment_id="SV-26-1184"
    - Verify estimated_delay_days=8
    - Verify alternative_hints contains "Mersin"
    - Verify confidence > 0.5
    - Verify extraction_method="llm"
    - Test pattern matching fallback when LLM returns error
    - Test low confidence flagging when confidence < 0.5
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 15.1, 16.2_

- [~] 6. Checkpoint: Verify data pipeline and signal extraction
  - Ensure all tests pass for data_loader and signal_agent
  - Verify real Excel file loads successfully with correct parameters
  - Ask the user if questions arise

- [ ] 7. Implement Agent 2: Risk & Impact Agent
  - [~] 7.1 Implement probability calculation in agents/risk_impact_agent.py
    - Create `calculate_probability(signal_reliability: float, performance_score: float, external_factor_score: float, financial_score: float, parameters: ParametersRow) -> float`
    - Apply weighted sum formula: `probability = 0.4×signal + 0.3×performance + 0.2×external + 0.1×financial`
    - Use weights from parameters (olasilik_agirlik_sinyal, olasilik_agirlik_performans, olasilik_agirlik_dis, olasilik_agirlik_finansal)
    - Validate weights sum to 1.0 (within 0.001 tolerance)
    - _Requirements: 2.1, 2.2, 2.5, 17.4_
  
  - [~] 7.2 Implement stock coverage calculation
    - Create `calculate_stock_coverage(current_stock: float, daily_consumption: float) -> float`
    - Apply formula: `stock_coverage_days = current_stock / daily_consumption`
    - Handle zero consumption case: return float('inf') and log warning
    - Validate inputs are non-negative
    - _Requirements: 3.1, 3.2, 3.4, 19.4_
  
  - [~] 7.3 Implement risk score and classification
    - Create `calculate_risk_score(probability: float, impact: int) -> float`
    - Apply formula: `risk_score = probability × impact`
    - Implement `classify_risk_category(risk_score: float, parameters: ParametersRow) -> str`
    - Apply thresholds: score >= 15.0 → "High", 7.0 <= score < 15.0 → "Medium", score < 7.0 → "Low"
    - Use parameters.esik_yuksek and parameters.esik_orta for thresholds
    - Handle negative risk scores: return 0 and log error
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 17.3_
  
  - [~] 7.4 Implement available date and downtime gap calculation
    - Create `calculate_available_date(current_eta: date, customs_days: int, inland_transport_days: int, quality_approval_days: int, estimated_delay_days: int) -> date`
    - Create `calculate_depletion_date(d0: date, stock_coverage_days: float) -> date`
    - Create `calculate_downtime_and_buffer(available_date: date, depletion_date: date, d0: date) -> Tuple[float, float]`
    - Implement formulas: `remaining_buffer = max(0, stock_coverage_days - available_days_from_d0)`, `downtime_gap = max(0, available_days_from_d0 - stock_coverage_days)`
    - Ensure mutual exclusivity: at most one of remaining_buffer or downtime_gap is positive
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  
  - [~] 7.5 Implement financial impact calculation
    - Create `identify_at_risk_orders(material_no: str, depletion_date: date, available_date: date, data_loader: DataLoader) -> List[str]`
    - Query Musteri_Siparisleri sheet for material_no
    - For each order: calculate required_production_date = teslimat_tarihi - shipping_days
    - Mark order at-risk if depletion_date <= required_production_date <= available_date
    - Return list of siparis_no (order numbers)
    - Create `calculate_financial_impact(downtime_gap: float, daily_downtime_cost: float, restart_cost: float, at_risk_orders: List[CustomerOrderRow], no_action_downtime: float) -> Tuple[float, float, float]`
    - If downtime_gap > 0: downtime_cost = gap × daily_downtime_cost + restart_cost
    - Calculate customer_penalty_base = sum(order.ceza_maddesi for at-risk orders)
    - Prorate penalty: customer_penalty = customer_penalty_base × min(1.0, downtime_gap / no_action_downtime)
    - Calculate total_inaction_cost = downtime_cost + customer_penalty
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.9_
  
  - [~] 7.6 Implement impact score assignment
    - Create `calculate_impact_score(downtime_gap: float, no_action_cost: float, remaining_buffer: float, safety_stock_days: float) -> int`
    - Apply tiered rules: downtime_gap > 0 AND cost >= 2M TRY → 5; downtime_gap > 0 AND cost >= 500K TRY → 4; downtime_gap > 0 AND cost < 500K TRY → 3; downtime_gap == 0 AND buffer < safety_stock → 2; else → 1
    - _Requirements: 6.4, 6.5, 6.6, 6.7, 6.8_
  
  - [~] 7.7 Create main risk assessment function
    - Implement `calculate_risk_assessment(input_data: RiskInput, data_loader: DataLoader, parameters: ParametersRow) -> RiskAssessment`
    - Orchestrate all calculation functions above
    - Load shipment data, material data, stock data, production line data from data_loader
    - Calculate probability (lookup signal reliability, supplier performance, external factors, financial score)
    - Calculate stock coverage, available date, downtime gap, buffer
    - Identify at-risk orders
    - Calculate financial impact (daily_downtime_cost and restart_cost from Uretim_Hatlari sheet)
    - Calculate impact score
    - Calculate risk score and classify category
    - Return complete RiskAssessment model
    - _Requirements: 2.1, 3.1, 4.1, 5.1, 6.1, 14.3_
  
  - [ ]* 7.8 Write unit tests for risk agent
    - Test probability calculation with weights 0.4/0.3/0.2/0.1 sums correctly
    - Test stock coverage formula: 500kg / 50.5kg/day ≈ 9.89 days (±2%)
    - Test risk score calculation: 4.4 × 5 = 22.0
    - Test risk category: score 22.0 → "High" (threshold 15.0)
    - Test boundary case: score exactly 15.0 → "High"
    - Test zero consumption: returns float('inf') for coverage
    - Test mutual exclusivity: buffer > 0 ⇒ gap == 0, gap > 0 ⇒ buffer == 0
    - Test impact score tier 5: downtime > 0 AND cost >= 2M TRY
    - _Requirements: 2.1, 2.5, 3.1, 4.1, 4.2, 4.3, 5.3, 5.4, 6.4, 16.3_
  
  - [ ]* 7.9 Write integration test for S1 scenario
    - Test full `calculate_risk_assessment()` for signal SG-2611-001 with real Excel data
    - Verify probability_score ≈ 4.4 (±2%)
    - Verify impact_score = 5
    - Verify risk_score ≈ 22.0 (±2%)
    - Verify risk_category = "High"
    - Verify stock_coverage_days ≈ 9.89 (±2%)
    - Verify available day ≈ 15 days from D0 (±2%)
    - Verify downtime_days ≈ 5.11 (±2%)
    - Verify total_inaction_cost ≈ 2,741,018 TRY (±2%)
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 16.3_

- [ ] 8. Implement Agent 3: Options Agent
  - [~] 8.1 Implement transfer option generation in agents/options_agent.py
    - Create `generate_transfer_options(material_no: str, facility_code: str, required_quantity: float, data_loader: DataLoader, parameters: ParametersRow) -> List[MitigationOption]`
    - Query Stok_Durumu sheet for material_no at other facilities
    - Filter facilities with mevcut_stok > min_siparis_miktari
    - Apply transfer protection constraint: reserve_qty = emniyet_stoku + (koruma_ufku × gunluk_tuketim)
    - Calculate transferable_qty = mevcut_stok - reserve_qty
    - Only generate option if transferable_qty > 0
    - Calculate cost: internal_transfer_rate × quantity × distance
    - Calculate arrivals: [Arrival(day=internal_transport_days, quantity=transferable_qty)]
    - Set co2_kg, risk_score (low), constraints_satisfied=["transfer_protection"]
    - _Requirements: 7.1, 8.3_
  
  - [~] 8.2 Implement alternative supplier option generation
    - Create `generate_supplier_options(material_no: str, current_supplier: str, required_quantity: float, data_loader: DataLoader, parameters: ParametersRow) -> List[MitigationOption]`
    - Query Tedarik_Kaynaklari sheet for material_no, filter out current supplier
    - CRITICAL: Only include suppliers with kalifikasyon_durumu == "Onaylı" (pharmaceutical qualification per material×supplier)
    - Calculate available_days = standart_tedarik_suresi_gun + route_transit_days + customs_days + quality_approval_days
    - If kalifikasyon_durumu != "Onaylı", add kalifikasyon_suresi_gun to available_days
    - Calculate action_cost = (birim_fiyat_usd × USDTRY × quantity) + shipping + QC_test_cost + inventory_carrying_cost
    - Calculate arrivals: [Arrival(day=available_days, quantity=order_quantity)]
    - Validate MOQ: quantity >= spot_moq (mark as "Conditional" if violated)
    - Set constraints_satisfied=["qualification"] if kalifikasyon_durumu == "Onaylı"
    - _Requirements: 7.2, 7.3, 8.1, 8.2, 8.4_
  
  - [~] 8.3 Implement expedited shipping option generation
    - Create `generate_expedited_options(shipment: ShipmentRow, data_loader: DataLoader, parameters: ParametersRow) -> List[MitigationOption]`
    - Calculate air freight option
    - Calculate action_cost = air_freight_rate × quantity × distance
    - Calculate available_days = 2 (air transit) + customs_expedited
    - Calculate arrivals: [Arrival(day=available_days, quantity=air_qty)]
    - Calculate co2_kg = air_emission_factor × distance × quantity (high emissions)
    - Set risk_score (low, fast and reliable)
    - Mark constraints_violated=["cost", "co2"] (expensive and high emissions)
    - Set feasibility="Conditional"
    - _Requirements: 7.5, 8.4_
  
  - [~] 8.4 Implement hybrid option generation
    - Create `generate_hybrid_options(transfer_option: MitigationOption, air_option: MitigationOption, main_shipment_available_day: int, current_stock: float, daily_consumption: float, parameters: ParametersRow) -> MitigationOption`
    - Calculate hybrid_air_qty = (main_shipment_available_day + 2) × daily_consumption - current_stock - transfer_qty
    - Round up to MOQ: hybrid_air_qty = ceil(hybrid_air_qty / moq) × moq
    - Calculate action_cost = transfer_cost + (air_qty × air_rate) + inventory_carrying + QC_tests
    - Calculate arrivals: [Arrival(day=transfer_days, quantity=transfer_qty), Arrival(day=air_days, quantity=air_qty), Arrival(day=main_shipment_days, quantity=main_qty)]
    - Calculate co2_kg = transfer_co2 + air_co2
    - Set downtime_days = 0 (by design, verified via simulation in Agent 4)
    - Set constraints_satisfied=["downtime_zero"]
    - _Requirements: 7.6, 8.5_
  
  - [~] 8.5 Implement no-action baseline option
    - Create `generate_no_action_option(assessment: RiskAssessment, original_eta: date, original_shipment_qty: float, parameters: ParametersRow) -> MitigationOption`
    - Calculate original_eta_days from D0
    - Create arrivals: [Arrival(day=original_eta_days, quantity=original_shipment_qty)]
    - Set action_cost = 0 (no mitigation action)
    - Set co2_kg = 0 (no additional emissions)
    - Set risk_score = assessment.risk_score (original risk)
    - Set downtime_days = assessment.downtime_days (original downtime from assessment)
    - CRITICAL: Set total_cost = assessment.total_inaction_cost (must equal ~2,741,018 TRY for S1, NOT zero)
    - Set feasibility = "Feasible"
    - _Requirements: 7.7, 8.5_
  
  - [~] 8.6 Implement feasibility classification
    - Create `classify_feasibility(option: MitigationOption) -> str`
    - If constraints_violated is empty → "Feasible"
    - If constraints_violated only contains ["cost"] or ["co2"] (soft constraints) → "Conditional"
    - If constraints_violated contains "qualification", "capacity", or other hard constraints → "NotFeasible"
    - _Requirements: 8.4, 8.5_
  
  - [~] 8.7 Create main options generation function
    - Implement `generate_mitigation_options(input_data: OptionsInput, llm_client: LLMClient, data_loader: DataLoader, parameters: ParametersRow) -> List[MitigationOption]`
    - Generate no-action baseline first
    - Generate transfer options (if applicable)
    - Generate alternative supplier options (filter by qualification status)
    - Generate expedited shipping options
    - Generate hybrid options (if transfer + air available)
    - For each option, call llm_client to generate llm_suggestion (1-2 sentence evaluation)
    - Use deterministic template if LLM unavailable
    - Return list of all generated options
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 8.1, 13.3_
  
  - [ ]* 8.8 Write unit tests for options agent
    - Test transfer option includes 260kg from facility with sufficient stock
    - Test transfer protection constraint: source retains emniyet_stoku + koruma_ufku × gunluk_tuketim
    - Test alternative supplier filtering: only "Onaylı" kalifikasyon_durumu for pharmaceutical materials
    - Test Zhejiang supplier available day = 8 (standart_tedarik_suresi_gun + customs + transit)
    - Test unqualified sources excluded from options list
    - Test hybrid option includes Mersin COD reference
    - Test no-action option has action_cost=0 but total_cost equals inaction cost
    - Test MOQ violation marks option as "Conditional"
    - _Requirements: 7.1, 7.2, 7.3, 7.6, 8.1, 8.2, 8.4, 16.4_
  
  - [ ]* 8.9 Write integration test for S1 scenario
    - Test full `generate_mitigation_options()` for signal SG-2611-001 with real Excel data
    - Verify at least 4 options generated (no_action, transfer, supplier alternatives, hybrid)
    - Verify transfer option exists with ~260kg quantity
    - Verify alternative supplier options only include "Onaylı" kalifikasyon_durumu
    - Verify hybrid option exists with constraints_satisfied=["downtime_zero"]
    - Verify no_action option total_cost ≈ 2,741,018 TRY (±2%)
    - _Requirements: 15.1, 15.5, 16.4_

- [~] 9. Checkpoint: Verify agent implementations
  - Ensure all tests pass for signal_agent, risk_agent, options_agent
  - Verify S1 scenario produces expected intermediate outputs
  - Ask the user if questions arise

- [ ] 10. Implement Agent 4: Decision Agent
  - [~] 10.1 Implement day-by-day downtime simulation in agents/decision_agent.py
    - Create `simulate_downtime(option: MitigationOption, current_stock: float, daily_consumption: float, main_shipment_available_day: int, parameters: ParametersRow) -> float`
    - Initialize inventory = current_stock
    - Sort option.arrivals by day
    - Simulate from day 0 to main_shipment_available_day (fixed evaluation horizon)
    - For each day: (1) add arrivals at start of day, (2) consume daily_consumption
    - If inventory >= consumption: subtract consumption, inventory continues
    - If inventory < consumption: calculate hours_operating = (inventory / consumption) × 24, downtime_hours += (24 - hours_operating), inventory = 0
    - Return downtime_hours / 24.0 (convert to days)
    - Handle multiple arrivals (transfer + air + main shipment for hybrid)
    - _Requirements: 5.5, 6.1_
  
  - [~] 10.2 Implement total cost calculation for each option
    - Create `calculate_total_cost(option: MitigationOption, daily_downtime_cost: float, restart_cost: float, customer_penalty_base: float, no_action_downtime: float) -> float`
    - If option.downtime_days > 0: downtime_cost = downtime_days × daily_downtime_cost, restart_cost_component = restart_cost
    - Else: downtime_cost = 0, restart_cost_component = 0
    - If no_action_downtime > 0: penalty = customer_penalty_base × min(1.0, option.downtime_days / no_action_downtime)
    - Else: penalty = 0
    - Calculate total_cost = downtime_cost + restart_cost_component + penalty + option.action_cost
    - VERIFICATION: For no_action option, total_cost must equal assessment.total_inaction_cost (~2,741,018 TRY for S1)
    - _Requirements: 6.1, 6.2, 6.3_
  
  - [~] 10.3 Implement min-max normalization
    - Create `normalize_criterion(values: List[float]) -> List[float]`
    - Find best_value = min(values) (lower is better for all criteria)
    - Find worst_value = max(values)
    - If worst_value == best_value: return [1.0] * len(values) (degenerate case)
    - For each value: normalized = (worst_value - value) / (worst_value - best_value)
    - Verify all normalized values in [0.0, 1.0]
    - Apply to cost (use total_cost, NOT action_cost), downtime, co2, risk across ALL options
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_
  
  - [~] 10.4 Implement CKKV score calculation
    - Create `calculate_ckkv_score(normalized_cost: float, normalized_downtime: float, normalized_co2: float, normalized_risk: float, parameters: ParametersRow) -> float`
    - Apply weighted sum: CKKV = 0.45×normalized_cost + 0.30×normalized_downtime + 0.10×normalized_co2 + 0.15×normalized_risk
    - Use weights from parameters (ckkv_agirlik_maliyet, ckkv_agirlik_durusma, ckkv_agirlik_co2, ckkv_agirlik_risk)
    - _Requirements: 9.6, 17.4_
  
  - [~] 10.5 Implement ranking and recommendation
    - Create `rank_options(options: List[MitigationOption], ckkv_scores: List[float]) -> List[RankedOption]`
    - Sort options by ckkv_score descending (higher is better)
    - Assign rank 1, 2, 3, ... to sorted list
    - Create RankedOption objects with normalized scores, ckkv_score, rank
    - Select rank 1 as recommended_option
    - _Requirements: 9.7, 10.1_
  
  - [~] 10.6 Implement justification generation
    - Create `generate_justification(recommended: RankedOption, total_options: int, llm_client: LLMClient) -> str`
    - Construct prompt with recommended option details (details, total_cost, downtime_days, co2_kg, risk_score, ckkv_score, rank)
    - Call llm_client.generate() to get 2-3 sentence justification
    - If LLM unavailable, use deterministic template: "Recommend {option_type} option: {details}. CKKV score {score:.3f} ranks highest, balancing total cost ({cost:,.0f} TRY), downtime ({downtime:.2f} days), CO2 ({co2:.0f} kg), and risk optimally."
    - _Requirements: 10.2, 10.3, 13.3_
  
  - [~] 10.7 Create main decision evaluation function
    - Implement `evaluate_and_recommend(input_data: DecisionInput, llm_client: LLMClient, parameters: ParametersRow) -> DecisionResult`
    - For each option: run simulate_downtime() to calculate precise downtime_days
    - For each option: run calculate_total_cost() to get full total_cost
    - Collect all costs, downtimes, co2, risks across options
    - Run min-max normalization for each criterion
    - Calculate CKKV score for each option
    - Rank options and select recommendation
    - Generate justification
    - Return DecisionResult with all_options_ranked, recommended_option, justification
    - _Requirements: 9.1, 9.6, 9.7, 10.1, 10.2_
  
  - [ ]* 10.8 Write unit tests for decision agent
    - Test day-by-day simulation with multiple arrivals (transfer day 2, air day 8, main day 15)
    - Test partial downtime calculation (fractional days)
    - Test total cost calculation includes all components (downtime + restart + penalty + action)
    - Test no_action total cost equals inaction cost (~2,741,018 TRY)
    - Test min-max normalization returns values in [0.0, 1.0]
    - Test degenerate normalization (all values equal) returns 1.0 for all
    - Test CKKV weighted sum with weights 0.45/0.30/0.10/0.15
    - Test ranking: highest CKKV score gets rank 1
    - _Requirements: 5.5, 6.1, 6.2, 6.3, 9.1, 9.5, 9.6, 9.7, 16.5_
  
  - [ ]* 10.9 Write integration test for S1 scenario
    - Test full `evaluate_and_recommend()` for signal SG-2611-001 with real options
    - Verify hybrid option recommended (rank 1)
    - Verify hybrid option total_cost ≈ 109,567 TRY (±2%)
    - Verify hybrid option downtime_days ≈ 0 (±0.1)
    - Verify hybrid option has constraints_satisfied containing "downtime_zero"
    - Verify no_action option total_cost ≈ 2,741,018 TRY (±2%)
    - Verify all options ranked with valid CKKV scores
    - Verify justification is non-empty string
    - _Requirements: 15.1, 15.5, 16.5_

- [ ] 11. Implement Orchestrator
  - [~] 11.1 Create PipelineOrchestrator class in orchestrator.py
    - Implement `__init__(self, data_loader: DataLoader, llm_client: LLMClient, parameters: ParametersRow)`
    - Store data_loader, llm_client, parameters as instance variables
    - _Requirements: 18.1_
  
  - [~] 11.2 Implement run_pipeline method
    - Implement `run_pipeline(self, signal_id: str) -> PipelineState`
    - Initialize PipelineState with signal_id
    - Execute Agent 1: load signal data, call process_signal(), store agent_1_output
    - Execute Agent 2: call calculate_risk_assessment(), store agent_2_output
    - Check if risk_category == "Low": set status="low_risk", save state, return early
    - Execute Agent 3: call generate_mitigation_options(), store agent_3_output
    - Execute Agent 4: call evaluate_and_recommend(), store agent_4_output
    - Set status="completed"
    - Save state to JSON
    - Return PipelineState
    - _Requirements: 12.1, 12.2, 18.1, 18.3, 18.4_
  
  - [~] 11.3 Implement state persistence
    - Implement `_save_state(self, state: PipelineState)` private method
    - Create JSON filename: `decisions/{signal_id}_{timestamp}.json`
    - Convert PipelineState to dictionary with all agent outputs
    - Include timestamp, signal_id, status, approval_decision, approver_identity, error_message
    - Write JSON with indent=2, ensure_ascii=False, default=str (for dates)
    - Log state save success or failure
    - _Requirements: 18.1, 18.2, 18.3, 18.5_
  
  - [~] 11.4 Implement error handling
    - Wrap pipeline execution in try-except block
    - On exception: set status="error", store error_message, save partial state, re-raise
    - Log errors with appropriate level (warning for LLM failures, error for data failures)
    - _Requirements: 19.1, 19.2, 19.3, 19.5_
  
  - [ ]* 11.5 Write integration tests for orchestrator
    - Test full pipeline execution for signal SG-2611-001 (high risk scenario)
    - Verify all 4 agent outputs are populated in PipelineState
    - Verify status="completed"
    - Verify state saved to decisions/ directory with correct filename
    - Verify JSON file contains all expected fields
    - Test low-risk early exit: use signal with risk_score < 7, verify status="low_risk", verify agent_3_output and agent_4_output are None
    - Test error handling: use invalid signal_id, verify status="error", verify error_message populated
    - _Requirements: 12.1, 12.2, 12.3, 18.1, 18.2, 18.3, 18.4, 18.5, 19.2, 19.5, 16.6_

- [~] 12. Checkpoint: Verify full pipeline integration
  - Ensure all tests pass for decision_agent and orchestrator
  - Verify S1 scenario completes end-to-end with expected outputs
  - Verify state persistence to JSON works correctly
  - Ask the user if questions arise

- [ ] 13. Implement Streamlit UI
  - [~] 13.1 Create app.py with basic structure
    - Import streamlit, initialize session state
    - Create page title: "NEXUS Risk Intervention Pipeline"
    - Add page configuration with wide layout
    - _Requirements: 11.1_
  
  - [~] 13.2 Implement signal selection
    - Create data_loader initialization function (cached with @st.cache_resource)
    - Load all signal IDs from Risk_Sinyalleri sheet
    - Create dropdown selector: `st.selectbox("Select Signal", signal_ids)`
    - Add "Analyze Signal" button
    - _Requirements: 11.1_
  
  - [~] 13.3 Implement pipeline execution UI
    - On button click: initialize orchestrator with data_loader, llm_client, parameters
    - Show spinner with "Processing signal..." message
    - Call orchestrator.run_pipeline(selected_signal)
    - Store result in session state
    - _Requirements: 11.1_
  
  - [~] 13.4 Implement Agent 1 display card
    - Create expander: "Agent 1: Signal Extraction"
    - Display extraction results: event_type, country_region, shipment_id, material_no, estimated_delay_days, alternative_hints
    - Show confidence score and extraction_method
    - Use color coding: green for confidence > 0.7, yellow for 0.5-0.7, red for < 0.5
    - _Requirements: 11.1_
  
  - [~] 13.5 Implement Agent 2 display card
    - Create expander: "Agent 2: Risk Assessment"
    - Display metrics: risk_score, risk_category, probability_score, impact_score
    - Display stock metrics: stock_coverage_days, downtime_days, remaining_buffer
    - Display financial metrics: downtime_cost, customer_penalty, total_inaction_cost
    - Use color coding for risk_category: red for High, yellow for Medium, green for Low
    - Show at_risk_orders list if any
    - _Requirements: 11.1_
  
  - [~] 13.6 Implement low-risk early exit display
    - If status == "low_risk": show info message "Low risk signal - monitoring only"
    - Display brief summary with risk_score and stock_coverage_days
    - Do not show Agent 3 and Agent 4 sections
    - _Requirements: 12.3_
  
  - [~] 13.7 Implement Agent 3 display card
    - Create expander: "Agent 3: Mitigation Options"
    - For each option: display option_type, details, feasibility
    - Show key metrics: total_cost, downtime_days, co2_kg, risk_score
    - Display arrivals schedule as timeline or table
    - Show constraints_satisfied and constraints_violated as badges
    - Display llm_suggestion as quote
    - _Requirements: 11.1_
  
  - [~] 13.8 Implement Agent 4 display card
    - Create expander: "Agent 4: Decision & Recommendation" (expanded by default)
    - Create comparison table with all ranked options
    - Columns: Rank, Option Type, Total Cost (TRY), Downtime (days), CO2 (kg), Risk Score, CKKV Score
    - Highlight recommended option (rank 1) with green background
    - Display justification in success banner
    - Show normalized scores as progress bars or small charts
    - _Requirements: 10.4, 10.5, 11.1_
  
  - [~] 13.9 Implement approval workflow
    - Create two-column layout for approval buttons
    - Add "✅ Approve" button (primary style) in left column
    - Add "❌ Reject" button in right column
    - On approve: call orchestrator to update state with approval_decision="approved", approver_identity=st.session_state.user, timestamp
    - On reject: call orchestrator to update state with approval_decision="rejected", approver_identity=st.session_state.user
    - Save updated state to JSON
    - Show success/warning message based on action
    - Disable buttons after action to prevent duplicate submissions
    - _Requirements: 11.2, 11.3, 11.4, 18.3_
  
  - [~] 13.10 Add error handling and logging
    - Wrap pipeline execution in try-except
    - Display error messages in st.error() box
    - Log all UI actions (signal selection, pipeline execution, approval decisions)
    - Add debug mode toggle in sidebar to show raw JSON outputs
    - _Requirements: 19.1, 19.2, 19.3_

- [ ] 14. Reconcile existing tests with implementation
  - [~] 14.1 Update test_signal_agent.py
    - Replace mock imports with real `src.nexus.agents.signal_agent` module
    - Update test assertions to match actual SignalExtraction model fields
    - Verify tests use MockClient (no AWS calls)
    - Remove any self-referential mock-only assertions that don't test real code logic
    - Ensure tests validate against expected S1 scenario values
    - Run tests and fix any import or assertion errors
    - _Requirements: 16.2_
  
  - [~] 14.2 Update test_risk_agent.py
    - Replace mock imports with real `src.nexus.agents.risk_impact_agent` module
    - Update test assertions to match actual RiskAssessment model fields
    - Verify numerical assertions use ±2% tolerance (pytest.approx with rel=0.02)
    - Ensure tests validate against expected S1 scenario values (risk_score ≈ 22.0, coverage ≈ 9.89, downtime ≈ 5.11, cost ≈ 2,741,018)
    - Run tests and fix any calculation or assertion errors
    - _Requirements: 16.3_
  
  - [~] 14.3 Update test_options_agent.py
    - Replace mock imports with real `src.nexus.agents.options_agent` module
    - Update test assertions to match actual MitigationOption model fields
    - Verify tests check qualification filtering (only "Onaylı" suppliers)
    - Verify tests check transfer protection constraint
    - Verify tests check no_action total_cost equals inaction_cost
    - Run tests and fix any logic or assertion errors
    - _Requirements: 16.4_
  
  - [~] 14.4 Update test_decision_agent.py
    - Replace mock imports with real `src.nexus.agents.decision_agent` module
    - Update test assertions to match actual DecisionResult model fields
    - Verify tests check day-by-day simulation logic
    - Verify tests check total cost calculation (all components)
    - Verify tests check CKKV scoring and ranking
    - Ensure tests validate against expected S1 scenario values (hybrid recommended, cost ≈ 109,567, downtime ≈ 0)
    - Run tests and fix any calculation or assertion errors
    - _Requirements: 16.5_
  
  - [~] 14.5 Update test_integration.py
    - Replace mock imports with real `src.nexus.orchestrator` module
    - Update test assertions to match actual PipelineState model fields
    - Add end-to-end test for S1 scenario (SG-2611-001) with all agent outputs validated
    - Add test for low-risk early exit scenario
    - Verify tests use real Excel data from `data/NEXUS_Agent_Veri_Seti_TEKNIK.xlsx`
    - Run tests and fix any integration errors
    - _Requirements: 16.6_

- [ ] 15. Final validation and testing
  - [~] 15.1 Run full pytest suite
    - Execute `pytest tests/ -v --hypothesis-show-statistics`
    - Verify all unit tests pass (signal, risk, options, decision agents)
    - Verify all integration tests pass (orchestrator, full pipeline)
    - Verify property-based tests pass (if implemented)
    - Fix any failing tests
    - _Requirements: 20.1, 20.2, 20.3_
  
  - [~] 15.2 Validate S1 scenario end-to-end
    - Run orchestrator.run_pipeline("SG-2611-001") programmatically
    - Verify Agent 1 output: shipment_id="SV-26-1184", delay=8 days
    - Verify Agent 2 output: risk_score ≈ 22.0, coverage ≈ 9.89, downtime ≈ 5.11, cost ≈ 2,741,018 TRY
    - Verify Agent 3 output: transfer 260kg, Zhejiang option day 8, no unqualified suppliers
    - Verify Agent 4 output: hybrid recommended, cost ≈ 109,567 TRY, downtime ≈ 0
    - Verify JSON state saved to decisions/ directory
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_
  
  - [~] 15.3 Validate Streamlit UI manually
    - Start Streamlit app: `streamlit run src/nexus/app.py`
    - Select signal SG-2611-001 from dropdown
    - Click "Analyze Signal" and verify all 4 agent cards display correctly
    - Verify comparison table shows all options ranked by CKKV score
    - Verify hybrid option highlighted as recommended
    - Test approve/reject buttons and verify state saved to JSON
    - Test low-risk signal scenario (early exit)
    - _Requirements: 11.1, 11.2, 11.3, 11.4_
  
  - [~] 15.4 Performance validation
    - Measure pipeline execution time for low-risk signal (target: < 5 seconds)
    - Measure pipeline execution time for high-risk signal (target: < 60 seconds)
    - Log processing time metrics for each agent
    - Optimize bottlenecks if targets not met (cache data, vectorize calculations)
    - _Requirements: 20.1, 20.2, 20.3, 20.4_
  
  - [~] 15.5 Documentation and cleanup
    - Create README.md with installation instructions, usage examples, testing commands
    - Document environment variables in .env.example
    - Add docstrings to all public functions and classes
    - Remove any debug print statements or commented-out code
    - Verify all files follow Python style conventions (PEP 8)
    - _Requirements: 17.1, 17.2, 17.3, 17.4_

- [~] 16. Final checkpoint: Complete validation
  - All tests pass (unit, integration, property-based)
  - S1 scenario validated end-to-end with expected outputs (±2% tolerance)
  - Streamlit UI functional with approval workflow
  - Performance targets met (low-risk < 5s, high-risk < 60s)
  - Ask the user if questions arise

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP (all test-related sub-tasks)
- Each task references specific requirements for traceability (e.g., _Requirements: 1.1, 1.2_)
- Numerical assertions use ±2% tolerance: `pytest.approx(expected, rel=0.02)`
- All tests use MockClient to avoid AWS Bedrock calls during CI/testing
- S1 scenario (SG-2611-001 / R-01) is the reference test case with known expected outputs
- Validation tolerance ensures tests pass with real Excel data variations
- Tests must pass before proceeding to next task to ensure incremental correctness
- Pre-existing test files in tests/ directory need imports updated to real src/nexus modules
- Configuration parameters loaded from Excel Parametreler sheet (D0=25.11.2026, USDTRY=45.9, thresholds 15/7)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1", "2.2", "2.3"] },
    { "id": 2, "tasks": ["3.1", "3.2"] },
    { "id": 3, "tasks": ["3.3"] },
    { "id": 4, "tasks": ["4.1", "4.2", "4.3", "4.4", "4.5"] },
    { "id": 5, "tasks": ["5.1", "5.2", "5.3"] },
    { "id": 6, "tasks": ["5.4"] },
    { "id": 7, "tasks": ["6"] },
    { "id": 8, "tasks": ["7.1", "7.2", "7.3", "7.4", "7.5", "7.6", "7.7"] },
    { "id": 9, "tasks": ["7.8", "7.9"] },
    { "id": 10, "tasks": ["8.1", "8.2", "8.3", "8.4", "8.5", "8.6", "8.7"] },
    { "id": 11, "tasks": ["8.8", "8.9"] },
    { "id": 12, "tasks": ["9"] },
    { "id": 13, "tasks": ["10.1", "10.2", "10.3", "10.4", "10.5", "10.6", "10.7"] },
    { "id": 14, "tasks": ["10.8", "10.9"] },
    { "id": 15, "tasks": ["11.1", "11.2", "11.3", "11.4"] },
    { "id": 16, "tasks": ["11.5"] },
    { "id": 17, "tasks": ["12"] },
    { "id": 18, "tasks": ["13.1", "13.2", "13.3", "13.4", "13.5", "13.6", "13.7", "13.8", "13.9", "13.10"] },
    { "id": 19, "tasks": ["14.1", "14.2", "14.3", "14.4", "14.5"] },
    { "id": 20, "tasks": ["15.1"] },
    { "id": 21, "tasks": ["15.2", "15.3", "15.4", "15.5"] },
    { "id": 22, "tasks": ["16"] }
  ]
}
```
