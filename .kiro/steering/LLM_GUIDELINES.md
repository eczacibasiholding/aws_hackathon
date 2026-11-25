# LLM Usage Guidelines - NEXUS Risk Agent

## Scope of LLM Usage

**Important**: The LLM is used **ONLY** for:
1. **Text Generation** (explanation, justification, rationale)
2. **Natural Language Reasoning** (clear articulation of logic)
3. **Recommendation Formatting** (professional presentation)

**LLM is NOT used for**:
- Risk score calculations (deterministic)
- Probability computations (weighted sums)
- Impact estimations (threshold-based)
- Strategy optimization (MILP algorithms)

---

## Output Structure

### Risk Report Template

```markdown
## Risk Report: {Risk ID}

### Signal Summary
- **Signal No**: {Sinyal No}
- **Category**: {Kategori}
- **Source**: {Kaynak Adı}
- **Detection Time**: {Tespit Zamanı}
- **Signal Text**: {Ham Metin}

### Risk Assessment
- **Probability**: {Olasılık} ({Puan}/5)
- **Impact**: {Etki} ({Puan}/5)
- **Risk Score**: {Risk_Puanı} ({Kategori})
- **Confidence**: {Güvenilirlik}

### Impact Analysis
1. **Financial Impact**
   - Potential Cost: {Tahmini_Maliyet} TRY
   - Stock Holding Cost: {Stok_Maliyeti} TRY
   - Production Loss: {Durmuş_Maliyeti} TRY

2. **Operational Impact**
   - Production Line: {HAT-SG-03}
   - Stock Coverage: {Stok_Günü} days
   - Downtime Risk: {Risk_Seviyesi}

3. **Customer Impact**
   - Affected Orders: {Sipariş_No}
   - Delivery Delay: {Gecikme_Günü} days
   - Customer Priority: {Öncelik}

### Mitigation Options
{LLM_üretir: 2-3 practical options with reasoning}

Option 1: Source Switch to T-BN-01
- Cost: {Maliyet} TRY
- Lead Time: {Tedarik_Zamani} days
- Risk: {Risk_Seviyesi}

Option 2: Expedited Air Freight
- Cost: {Maliyet} TRY
- Lead Time: {Tedarik_Zamani} days
- Risk: {Risk_Seviyesi}

### Recommendation
{LLM_üretir: Clear recommendation with full justification}

### Rationale Chain
1. Signal reliability: {Güvenilirlik}/5 - {Açıklama}
2. Party performance: {Performans}/5 - {Açıklama}
3. External conditions: {Dış_Koşul}/5 - {Açıklama}
4. Financial health: {Finansal}/5 - {Açıklama}
5. Stock coverage: {Stok_Günü} days - {Etki_Açıklaması}
6. Production risk: {Düşüş_Riski} - {Sonuç}
```

---

## LLM Tasks

### Task 1: Signal Explanation
**Input**: Raw signal text + metadata  
**Output**: Natural language summary

```
"Signal SG-2611-001 indicates a critical disruption at Jeddah Islamic Port. 
The MV AEGEAN STAR carrier has been rescheduled due to Red Sea diversions 
and port congestion, causing an 8-day delay for the AKH-MUN-26-1184 shipment 
of 2,000 kg Clarithromycin API. This affects the T-SG-01 facility stock, 
which has only ~9.9 days of coverage remaining."
```

### Task 2: Risk Justification
**Input**: Probability and impact scores  
**Output**: Detailed reasoning chain

```
"The risk score of 22.0 (High) is justified by:
1. High signal reliability (5/5) - Carrier advisory verified via AIS
2. Critical external conditions (5/5) - Active Red Sea conflict zone
3. Adequate party performance (4/5) - Carrier OTIF history
4. Low financial risk (2/5) - Carrier financial health
5. Severe impact (5/5) - Production line stop risk in ~5 days
6. Significant financial exposure (>2M TRY) - Critical API material"
```

### Task 3: Strategy Rationale
**Input**: Mitigation options + scores  
**Output**: Comparative analysis

```
"The recommended option is switching to T-BN-01 alternative supplier 
because:
1. Cost: 25,000 TRY (lower than air freight 45,000 TRY)
2. Risk: Medium (15 days vs 18 days lead time)
3. Quality: Already approved source, minimal regulatory risk
4. Stock: 2,000 pcs available in HK warehouse immediately

Alternative air freight option is 80% more expensive and 
increases carbon footprint by 30x, making it less sustainable."
```

### Task 4: Agent Action Selection
**Input**: Risk score + category  
**Output**: Appropriate action description

```
"For high-risk signals (≥15), the agent performs:
1. Full analysis of all mitigation options
2. Multi-criteria evaluation (cost, time, CO2, risk)
3. Optimization-based route selection
4. Strategic recommendation to stakeholders
5. Implementation roadmap with milestones

This comprehensive approach ensures minimal disruption 
while maintaining cost-efficiency and sustainability goals."
```

---

## Output Quality Standards

### Clarity Requirements
1. **Plain Language**: Avoid technical jargon where possible
2. **Logical Flow**: Cause → Effect → Action
3. **Data-Driven**: Every claim backed by numbers
4. **Action-Oriented**: Clear next steps for each stakeholder

### Tone Requirements
1. **Professional**: Business-appropriate language
2. **Urgent**: Appropriate severity for risk level
3. **Objective**: Focused on facts, not opinions
4. **Constructive**: Solution-focused recommendations

### Formatting Requirements
1. **Markdown**: Use headers, bullet points, bold
2. **Numbers**: Always show actual values, not just ranges
3. **Dates**: Use DD.MM.YYYY format consistently
4. **Currency**: Always show TRY unit

---

## Validation Checklist

### Pre-LLM Data Validation
- [ ] All probability weights sum to 1.0
- [ ] Risk score = Probability × Impact
- [ ] Impact thresholds correctly applied
- [ ] All required data fields populated

### Post-LLM Output Validation
- [ ] Explanation matches calculated scores
- [ ] Justification references actual data
- [ ] Options are feasible and cost-verified
- [ ] Recommendation aligns with risk level

---

## Error Handling

### Low Confidence Signals
```
"For signals with reliability below 3/5, the LLM generates:
1. Clear caveats about uncertainty
2. Alternative scenarios with probability weights
3. Recommended verification steps
4. Caution in recommendation strength"
```

### Incomplete Data
```
"When data is missing, the LLM should:
1. Explicitly state missing information
2. Provide range estimates
3. Suggest data collection priorities
4. Avoid making up numbers"
```

---

## Testing Strategy

### Test Case 1: High-Risk Signal (R-01)
- **Input**: SG-2611-001 (Red Sea, Cidde delay)
- **Expected**: Comprehensive analysis, multiple options
- **Output**: 3+ mitigation strategies with cost comparison

### Test Case 2: Medium-Risk Signal (R-04)
- **Input**: SG-2611-003 (Quality OOS)
- **Expected**: Warning with options prepared
- **Output**: 1-2 practical options with minimal action

### Test Case 3: Low-Risk Signal (R-08)
- **Input**: SG-2611-012 (Social media rumor)
- **Expected**: Monitor-only, minimal output
- **Output**: Brief status update, no recommendations

---

## Examples

### Example 1: High-Risk Recommendation
```
### Agent Recommendation: Switch to Alternative Supplier

**Recommended Action**: Switch to T-BN-01 supplier in Hong Kong

**Rationale**: 
This option provides the optimal balance of cost, speed, and risk. 
The alternative source is already approved for MT100054, eliminating 
regulatory delays. With 2,000 pcs in immediate inventory, we can 
fulfill critical orders while the main shipment is delayed.

**Cost Analysis**:
- Alternative sourcing: 25,000 TRY (testing/re-certification)
- Current stock depletion: ~9.9 days remaining
- Production stop cost avoided: ~5 days × 45,000 TRY/day = 225,000 TRY

**Timeline**:
- Release from HK warehouse: Immediate
- Shipping to T-SG-01: 5 days
- Total availability: D0 + 5 (29.11.2026)

**Risk Assessment**: Medium risk (15/25)
- Source reliability: High (pre-approved)
- Quality: Verified (existing supplier)
- Logistics: Standard ocean freight
- Financial: Limited exposure (25,000 TRY)

**Next Steps**:
1. Approve alternative source (QA review: 2 hours)
2. Release 2,000 pcs from HK warehouse (immediate)
3. Expedite shipping to Istanbul facility (5 days)
4. Monitor alternative production quality (daily)
```

### Example 2: Low-Risk Status Update
```
### Agent Status: Low Risk Signal

**Signal**: SG-2611-012 - US Gulf Port Strike Rumor

**Assessment**: Low Risk (1.5/25)

**Analysis**:
This signal originates from social media sources without official 
verification. Current confirmed shipments (MV AEGEAN STAR) are on 
schedule, indicating no immediate impact. The rumors may be baseless 
or refer to future discussions rather than planned action.

**Recommendation**: Monitor Only

**Monitoring Criteria**:
1. Official union announcement
2. Port authority advisory
3. Carrier official communication
4. Real-time shipment tracking anomalies

**Review Schedule**:
- Daily status check
- Escalate if verified by official sources
- No immediate action required

**Confidence Level**: 30% (Unconfirmed source)
```
