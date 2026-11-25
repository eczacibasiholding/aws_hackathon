# Calculation Rules and Formulas - NEXUS Risk Agent

## Overview
This document specifies all deterministic calculations for the risk agent.

## Time Reference
- **D0 (Analysis Date)**: 25.11.2026 (00:00)
- **Time Unit**: Days from D0
- **Example**: 27.11.2026 = D0 + 2

---

## 1. Signal Processing

### Signal Age Calculation
```
Gün Sayısı = (Signal_Tespt_Zamanı - D0).days
```

### Signal Delay Calculation
```
Gecikme_Günü = (ETA_Yeni - ETA_Eski).days
```

**Example**: 
- Original ETA: 27.11.2026 (D0 + 2)
- New ETA: 05.12.2026 (D0 + 10)
- Delay: 8 days

---

## 2. Probability Calculation

### Weighted Probability Formula
```
Olasılık = w_Sinyal × Sinyal_Güvenilirliği + 
           w_Performans × Taraf_Performans_Puanı + 
           w_DisKosul × Dış_Koşul_Puanı + 
           w_Finansal × Finansal_Puan
```

### Weights
| Weight | Value | Description |
|--------|-------|-------------|
| w_Sinyal | 0.4 | Signal reliability weight |
| w_Performans | 0.3 | Party performance weight |
| w_DisKosul | 0.2 | External condition weight |
| w_Finansal | 0.1 | Financial health weight |

### Score Mapping
| Rating | Description | Score |
|--------|-------------|-------|
| 5 | Excellent | 5 |
| 4 | Good | 4 |
| 3 | Fair | 3 |
| 2 | Poor | 2 |
| 1 | Very Poor | 1 |
| 0 | Not Applicable | 0 |

---

## 3. Impact Calculation

### Financial Impact Thresholds
```
if Aksiyonsuz_Maliyet >= 2,000,000 TRY:
    Etki = 5 (Yüksek)
elif Aksiyonsuz_Maliyet >= 500,000 TRY:
    Etki = 4 (Orta)
else:
    Etki = 3 (Düşük)
```

### Operational Impact Factors

#### Stock Coverage
```
Stok_Günü = Mevcut_Stok / Günlük_Tüketim
```

#### Impact based on Stock Coverage
| Coverage | Impact |
|----------|--------|
| <3 gün | 5 (Critical) |
| 3-7 gün | 4 (High) |
| 7-14 gün | 3 (Medium) |
| 14-30 gün | 2 (Low) |
| >30 gün | 1 (Very Low) |

#### Production Line Downtime Risk
```
if Stok_Günü < 3:
    Düşüş_Riski = Evet (High)
elif Stok_Günü < 7:
    Düşüş_Riski = Orta
else:
    Düşüş_Riski = Hayır (Low)
```

---

## 4. Risk Score

### Calculation
```
Risk_Puanı = Olasılık × Etki
```

### Risk Categories
| Score | Category | Agent Action |
|-------|----------|--------------|
| <7.0 | Düşük (Low) | İzlemeye al |
| 7.0-15.0 | Orta (Medium) | Uyarı + seçenekleri hazırda tut |
| ≥15.0 | Yüksek (High) | Tam analiz + onaya öneri |

---

## 5. Impact Cost Estimation

### Cost Components

#### 1. Stock Holding Cost
```
Stok_Tasima_Maliyeti = Stok_Miktarı × StokTasimaOrani × Günlük_Kullanım_Oranı
```

#### 2. Production Downtime Cost
```
Durmuş_Fırın_Maliyeti = Günlük_Üretim_Kapasitesi × Birim_Maliyet × Duruş_Günü
```

#### 3. expedited Shipping Cost
```
Acil_Sevkiyat_Maliyeti = Mesafe × Navlun_Oranı × Zaman_Faktörü
```

#### 4. Quality Rejection Cost
```
Kalite_Red_Maliyeti = Red_Parti_Miktarı × Birim_Maliyet + Test_Maliyeti
```

### Total Cost
```
Toplam_Aksiyonsuz_Maliyet = 
    Stok_Tasima_Maliyeti + 
    Durmuş_Fırın_Maliyeti + 
    Acil_Sevkiyat_Maliyeti +
    Kalite_Red_Maliyeti
```

---

## 6. Strategy Evaluation

### Criteria Weights (ÇKKV)
| Criterion | Weight |
|-----------|--------|
| Total Cost | 0.45 |
| Downtime Days | 0.30 |
| CO2 Emissions | 0.10 |
| Implementation Risk | 0.15 |

### Multi-Criteria Score
```
ÇKKV_Puanı = w_Maliyet × P_Maliyet + 
             w_Durus × P_Durus + 
             w_CO2 × P_CO2 + 
             w_Risk × P_Risk
```

### Strategy Options
1. **Source Switch**: Alternative supplier
2. **Route Change**: Alternate shipping route
3. **Expedited Shipping**: Air freight or premium service
4. **Inventory Transfer**: Cross-facility reallocation
5. **Local Production**: Local manufacturing or sourcing

---

## 7. Time Metrics

### Detection Time
```
Manuel_Tespit_Saat = 52 saat (current baseline)
Hedef_Tespit_Saat = 4 saat (target)
```

### Decision Time
```
Manuel_Karar_Saat = 30 saat (current baseline)
Hedef_Karar_Dk = 30 dakika (target)
```

### Key Performance Indicators
| KPI | Current | Target | Measurement |
|-----|---------|--------|-------------|
| Detection Time | 52h | ≤4h | Signal to assessment |
| Decision Time | 30h | ≤30min | Assessment to recommendation |
| False Alarm Rate | - | ≤15% | Incorrect signals |
| Acceptance Rate | - | ≥75% | Stakeholder approval |
| Preventive Action | - | ≥80% | Actions before event |
| OTIF (Critical) | - | ≥92% | On-time in-full |
| On-Time Arrival | - | ≥90% | Carrier performance |

---

## 8. Example Calculations

### Example 1: Signal SG-2611-001 (High Risk)

**Input Data**:
- Sinyal Güvenilirliği: 5
- Taraf Performans Puanı: 4
- Dış Koşul Puanı: 5
- Finansal Puan: 2

**Probability**:
```
Olasılık = 0.4×5 + 0.3×4 + 0.2×5 + 0.1×2
Olasılık = 2.0 + 1.2 + 1.0 + 0.2 = 4.4
```

**Impact**: 5 (Production line stop risk)

**Risk Score**:
```
Risk_Puanı = 4.4 × 5 = 22.0
```

**Category**: Yüksek (≥15)

---

### Example 2: Signal SG-2611-003 (Medium Risk)

**Input Data**:
- Sinyal Güvenilirliği: 5
- Taraf Performans Puanı: 3
- Dış Koşul Puanı: 2
- Finansal Puan: 2

**Probability**:
```
Olasılık = 0.4×5 + 0.3×3 + 0.2×2 + 0.1×2
Olasılık = 2.0 + 0.9 + 0.4 + 0.2 = 3.5
```

**Impact**: 2 (Minor disruption)

**Risk Score**:
```
Risk_Puanı = 3.5 × 2 = 7.0
```

**Category**: Orta (7-15)

---

### Example 3: Signal SG-2611-012 (Low Risk)

**Input Data**:
- Sinyal Güvenilirliği: 1 (unconfirmed rumor)
- Taraf Performans Puanı: 2
- Dış Koşul Puanı: 2
- Finansal Puan: 1

**Probability**:
```
Olasılık = 0.4×1 + 0.3×2 + 0.2×2 + 0.1×1
Olasılık = 0.4 + 0.6 + 0.4 + 0.1 = 1.5
```

**Impact**: 1 (Negligible)

**Risk Score**:
```
Risk_Puanı = 1.5 × 1 = 1.5
```

**Category**: Düşük (<7)

---

## 9. Validation Rules

### Rule 1: Weight Sum
```
w_Sinyal + w_Performans + w_DisKosul + w_Finansal = 1.0 ✓
```

### Rule 2: Score Range
```
0 ≤ Olasılık ≤ 5
0 ≤ Etki ≤ 5
0 ≤ Risk_Puanı ≤ 25
```

### Rule 3: Threshold Consistency
```
EsikYuksek > EsikOrta > 0
```

### Rule 4: Impact Scaling
```
Etki 5: Critical (line stop, <3 days stock)
Etki 4: High (7 days stock)
Etki 3: Medium (14 days stock)
Etki 2: Low (30 days stock)
Etki 1: Very Low (>30 days stock)
```
