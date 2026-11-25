# Project Steering Document - NEXUS Supply Chain Risk Agent

## Project Overview

**Project Name**: NEXUS Supply Chain Risk Agent  
**Domain**: Supply Chain Risk Management  
**Analysis Reference Date**: 25.11.2026  
**Purpose**: Automated risk detection, scoring, impact analysis, and mitigation strategy generation for supply chain disruptions

---

## Data Inputs

### Primary Input File: `NEXUS_Agent_Veri_Seti_TEKNIK.xlsx`
- **Purpose**: Raw signal data for agent processing
- **Content**: 
  - Risk signals (SG-2611-XXX series)
  - Source codes and metadata
  - Signal text (English/Turkish)
  - Categorization and status
- **Key Sheets**:
  - `Risk_Sinyalleri`: 25 risk signals with metadata
  - `Risk_Kaynaklari`: Source definitions and reliability weights
  - `Sevkiyatlar`: Shipment records
  - `Acik_Siparisler`: Open orders
  - `Stok_Durumu`: Inventory levels
  - `Uretim_Hatlari`: Production lines
  - `Musteri_Siparisleri`: Customer orders
  - `Malzemeler`: Material/master data
  - `Tedarikciler`: Supplier data
  - `Tasiyicilar`: Carrier data
  - `Tesisler`: Facility data
  - `Tedarik_Kaynaklari`: Alternative source options
  - `Rota_Secenekleri`: Route alternatives
  - `Parametreler`: Configuration parameters
  - `Esik_Tablolari`: Threshold values

### Answer Key: `NEXUS_Hackathon_Veri_Seti_AnaVeri.xlsx`
- **Purpose**: Ground truth for validation
- **Key Sheets**:
  - `Risk_Skorlama`: Risk scores and impact analysis
  - `Parametreler`: Analysis parameters (overlaps with input)
  - `Risk_Kaynaklari`: Source definitions
  - `Risk_Sinyalleri`: Signal reference data

---

## Analysis Methodology

### Risk Scoring Formula

```
Olasılık = Σ(w_i × p_i)
where:
  w_Sinyal = 0.4 (Signal reliability weight)
  w_Performans = 0.3 (Party performance weight)
  w_DisKosul = 0.2 (External condition weight)
  w_Finansal = 0.1 (Financial health weight)

Risk_Puanı = Olasılık × Etki
```

### Probability Weights
| Weight Type | Value | Description |
|-------------|-------|-------------|
| Signal Reliability | 0.4 | Source credibility (1-5) |
| Party Performance | 0.3 | Supplier/carrier OTIF |
| External Condition | 0.2 | Geopolitical, weather, congestion |
| Financial Health | 0.1 | Credit rating/financial score |

### Impact Estimation
Based on:
1. Financial loss threshold
2. Production disruption days
3. Customer service impact
4. Inventory coverage days

### Risk Categories
| Risk Score | Category | Agent Action |
|------------|----------|--------------|
| <7 | Low | Monitor only |
| 7-15 | Medium | Alert + options prepared |
| ≥15 | High | Full analysis + strategic options |

---

## Agent Architecture

### Deterministic Processing (Python)
1. Signal parsing and validation
2. Probability calculation (weighted sum)
3. Impact estimation (threshold-based)
4. Strategy evaluation (multi-criteria decision)
5. Optimization (MILP-based routing)

### LLM Processing (Text Generation Only)
1. Risk explanation generation
2. Justification writing
3. Strategy rationale
4. Agent action recommendations

---

## Key Metrics

### Risk Metrics
- **Risk Scale**: 1-25 (probability × impact)
- **Risk Levels**: Low (<7), Medium (7-15), High (≥15)
- **Time Horizon**: D0 = 25.11.2026

### Performance Indicators
| KPI | Target | Description |
|-----|--------|-------------|
| Detection Time | ≤4 hours | Time from signal to initial assessment |
| Decision Time | ≤30 minutes | Time from assessment to recommendation |
| False Alarm Rate | ≤15% | Incorrect risk signals |
| Recommendation Acceptance | ≥75% | Stakeholder approval rate |
| Preventive Action | ≥80% | Actions before risk occurrence |
| OTIF (Critical Suppliers) | ≥92% | On-time in-full delivery |
| On-Time Arrival | ≥90% | Carrier performance |

---

## Implementation Phases

### Phase 1: Data Ingestion
- Parse all input sheets
- Load reference data
- Establish data relationships

### Phase 2: Risk Scoring
- Calculate signal probabilities
- Estimate impact
- Generate risk scores

### Phase 3: Impact Analysis
- Production line disruption
- Inventory coverage
- Financial exposure
- Customer impact

### Phase 4: Strategy Generation
- Alternative sourcing
- Route optimization
- Inventory reallocation
- Cost-benefit analysis

### Phase 5: LLM Integration
- Generate explanations
- Create justifications
- Format recommendations

---

## Testing Strategy

### Validation Approach
1. Compare calculated risk scores against `Risk_Skorlama` sheet
2. Verify probability calculations match formula
3. Check impact estimations against reference data
4. Validate strategy options against `Rota_Secenekleri`

### Test Cases
- Signal SG-2611-001: Red Sea diversion → Cidde delay
- Signal SG-2611-005: Chornomorsk port closure
- Signal SG-2611-008: Power rationing in Shenzhen
- Signal SG-2611-003: OOS quality issue (lower impact)

---

## Key Dependencies

### Data Files
- `data/NEXUS_Agent_Veri_Seti_TEKNIK.xlsx` (input)
- `data/NEXUS_Hackathon_Veri_Seti_AnaVeri.xlsx` (reference)

### Python Libraries
- pandas (data processing)
- openpyxl (Excel handling)
- scipy (optimization, if needed)

### External Systems
- ERP (for real-time order data)
- TMS (for shipment tracking)
- Supplier portals

---

## Risk Signal Categories
1. **Lojistik & Liman**: Vessel delays, port congestion
2. **Jeopolitik**: War zones, sanctions, port closures
3. **Tedarikçi**: Quality issues, production delays
4. **Enerji**: Power outages, rationing
5. **Piyasa**: Freight index changes
6. **İşgücü**: Strikes, labor disputes
7. **Hava & Afet**: Weather disruptions
8. **Sosyal**: Rumors, social media alerts

---

## Agent Decision Flow

```
Signal Received
     ↓
Parse & Validate
     ↓
Calculate Probability (weighted sum)
     ↓
Estimate Impact (threshold-based)
     ↓
Calculate Risk Score (Prob × Impact)
     ↓
Categorize (Low/Medium/High)
     ↓
Generate Options (if Medium/High)
     ↓
Evaluate Strategies (multi-criteria)
     ↓
Generate Recommendations (LLM)
     ↓
Output Risk Report
```

---

## Output Format

### Risk Report Structure
1. **Signal Summary**: ID, time, source, category
2. **Risk Assessment**: Score, level, confidence
3. **Impact Analysis**: Financial, operational, customer
4. **Mitigation Options**: Sourcing, routing, inventory
5. **Recommendation**: LLM-generated with justification
6. **Rationale**: Probabilistic reasoning chain

---

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| AnalizTarihi | 2026-11-25 | Analysis reference date |
| StokTasimaOrani | 0.3 | Annual inventory holding cost |
| PlanlamaTambonu | 2 days | Planning uncertainty buffer |
| W_Sinyal | 0.4 | Signal reliability weight |
| W_Performans | 0.3 | Party performance weight |
| W_DisKosul | 0.2 | External condition weight |
| W_Finansal | 0.1 | Financial health weight |
| EsikYuksek | 15 | High risk threshold |
| EsikOrta | 7 | Medium risk threshold |

---

## Next Steps

1. Build data ingestion module
2. Implement risk scoring engine
3. Develop impact analysis
4. Create strategy generation
5. Integrate LLM for text generation
6. Implement validation testing
7. Generate final report
