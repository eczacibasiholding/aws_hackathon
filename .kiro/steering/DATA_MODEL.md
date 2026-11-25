# Data Model Specification - NEXUS Risk Agent

## Overview
This document defines the data structures, relationships, and business logic for the NEXUS Supply Chain Risk Agent.

## Analysis Context
- **Analysis Reference Date (D0)**: 25.11.2026
- **Planning Horizon**: 30 days forward from D0
- **Time Units**: Days (integer), Hours (for detection time KPIs)

## Input Data Sheets

### 1. Risk_Sinyalleri (Risk Signals)
**Purpose**: Raw risk signals from various sources

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| Sinyal No | string | Unique signal ID | SG-2611-001 |
| Yayın Zamanı | datetime | Signal publication time | 2026-11-24 09:12:00 |
| Tespit Zamanı | datetime | Agent detection time | 2026-11-24 09:20:00 |
| Kaynak Kodu | string | Source identifier | KY02 |
| Kaynak Adı | string | Source name | Taşıyıcı müşteri bildirimi |
| Kategori | string | Signal category | Lojistik & Liman |
| Dil | string | Language code | EN, TR |
| Ham Metin (LLM Girdisi) | string | Raw signal text | Customer advisory text... |
| Kaynak Taban Güvenilirlik | int (1-5) | Source credibility | 4 |
| Doğrulandı mı? | boolean | Signal verification status | Evet/Hayır |
| Durum | string | Signal status | Açık – Analizde |

**Relationships**:
- `Kaynak Kodu` → `Risk_Kaynaklari(Kaynak Kodu)`
- Links to: `Sevkiyatlar`, `Acik_Siparisler`, `Malzemeler`

---

### 2. Risk_Kaynaklari (Risk Sources)
**Purpose**: Source metadata and reliability weights

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| Kaynak Kodu | string | Source identifier | KY02 |
| Kaynak Adı | string | Source name | Taşıyıcı müşteri bildirimi |
| Kategori | string | Source category | Lojistik & Liman |
| Anahtar / Bağlantılar | string | Key relationships | Sinyal No → Sevkiyatlar |
| Güvenilirlik | int (1-5) | Source reliability | 4 |

**Weights**:
- Signal reliability: w=0.4
- Party performance: w=0.3
- External condition: w=0.2
- Financial health: w=0.1

---

### 3. Sevkiyatlar (Shipments)
**Purpose**: Shipment records and tracking

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| Sevkiyat No | string | Shipment identifier | AKH-MUN-26-1184 |
| Takip No | string | Tracking number | - |
| PO No | string | Purchase order | 4500201377 |
| Malzeme No | string | Material code | MT100054 |
| Sevkiyat Tarihi | datetime | Scheduled shipment date | 2026-11-27 |
| ETA | datetime | Estimated time of arrival | 2026-12-05 |
| Gemi Adı | string | Vessel name | MV AEGEAN STAR |
| Rotakod | string | Route code | - |
| Taşıyıcı No | string | Carrier code | TS01 |
| Açıklama | string | Notes | Conjunction at Jeddah |

**Key Relationships**:
- `PO No` → `Acik_Siparisler(PO No)`
- `Sevkiyat No` → `Risk_Sinyalleri(Anahtar Bağlantı)`

---

### 4. Acik_Siparisler (Open Orders)
**Purpose**: Active purchase orders

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| PO No | string | Purchase order number | 4500201377 |
| Malzeme No | string | Material code | MT100054 |
| Tedarikçi Kodu | string | Supplier code | TD5011 |
| Tesis Kodu | string | Facility code | T-SG-01 |
| Sipariş Tarihi | datetime | Order date | 2026-11-15 |
| Miktar | float | Quantity (kg) | 2000 |
| Teyit Tarihi | datetime | Confirmation date | 2026-11-29 |
| Birim Fiyat | float | Unit price | 15.50 |
| Toplam Tutar | float | Total amount | 31000 |

---

### 5. Stok_Durumu (Inventory Status)
**Purpose**: Current inventory levels

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| Stok Anahtarı | string | Composite key | T-SG-01|MT100054 |
| Malzeme No | string | Material code | MT100054 |
| Tesis Kodu | string | Facility code | T-SG-01 |
| Mevcut Stok | float | Current stock | 9900 |
| Günlük Tüketim | float | Daily consumption | 1100 |
| Günlük Tüketim (kg) | float | Daily consumption | 1100 |
| Emniyet Stoku | float | Safety stock | 5500 |
| Mevcut Stoğun Günlük Tüketim Üzerinden Süresi | float | Coverage (days) | 9 |

**Key Calculation**:
```
Stok Günlük Tüketim Üzerinden Süresi = Mevcut Stok / Günlük Tüketim
```

---

### 6. Uretim_Hatlari (Production Lines)
**Purpose**: Production facility information

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| Tesis Kodu | string | Facility code | T-SG-01 |
| Tesis Adı | string | Facility name | Sancaktepe Fabrikası |
| Malzeme No | string | Material code | MT100054 |
| Üretim Hattı | string | Production line | HAT-SG-03 |
| Günlük Üretim Kapasitesi | float | Daily capacity | 1200 |
| Duruş Riski | string | Downtime risk | Evet |

---

### 7. Parametreler (Parameters)
**Purpose**: Configuration parameters

| Parameter | Type | Value | Unit | Description |
|-----------|------|-------|------|-------------|
| AnalizTarihi | date | 2026-11-25 | - | Analysis reference date |
| USDTRY | float | 45.9 | TRY | USD/TRY exchange rate |
| EURTRY | float | 47.4 | TRY | EUR/TRY exchange rate |
| EURUSD | float | 1.03268 | USD | Cross rate EUR/USD |
| StokTasimaOrani | float | 0.3 | %/year | Inventory holding cost |
| PlanlamaTambonu | int | 2 | days | Planning uncertainty buffer |
| KorumaUfku | int | 7 | days | Transfer protection window |
| EsikYuksek | int | 15 | score | High risk threshold |
| EsikOrta | int | 7 | score | Medium risk threshold |

---

## Risk Scoring

### Probability Calculation
```
Olasılık = w_Sinyal × P_Sinyal + w_Performans × P_Performans + 
           w_DisKosul × P_DisKosul + w_Finansal × P_Finansal

where:
  w_Sinyal = 0.4
  w_Performans = 0.3
  w_DisKosul = 0.2
  w_Finansal = 0.1
```

### Risk Score
```
Risk_Puanı = Olasılık × Etki
```

### Risk Categories
| Score | Category | Action |
|-------|----------|--------|
| <7 | Düşük | İzlemeye al |
| 7-15 | Orta | Uyarı + seçenekleri hazırda tut |
| ≥15 | Yüksek | Tam analiz + onaya öneri |

---

## Impact Estimation

### Financial Impact
Based on threshold analysis:
- **High Impact (5)**: Cost ≥ 2,000,000 TRY
- **Medium Impact (4)**: Cost ≥ 500,000 TRY
- **Low Impact (3)**: Cost < 500,000 TRY

### Operational Impact
- **Etki 5**: Production line stop risk, critical shortage
- **Etki 4**: Significant disruption, stock below safety
- **Etki 3**: Moderate disruption, adequate buffer
- **Etki 2**: Minor impact, stock sufficient
- **Etki 1**: Negligible impact, ample buffer

### Customer Impact
- Stock availability
- Delivery date commitments
- Customer satisfaction risk

---

## Key Relationships Diagram

```
Risk_Sinyalleri
     ↓ (Kaynak Kodu)
Risk_Kaynaklari
     ↓
     ↓→ Probability calculation (weighted sum)
     
Risk_Sinyalleri
     ↓ (Anahtar Bağlantı → Sevkiyat No)
Sevkiyatlar
     ↓ (PO No)
Acik_Siparisler
     ↓ (Malzeme No, Tesis Kodu)
Stok_Durumu
     ↓
     ↓→ Impact estimation (stock coverage, disruption days)
     
Risk_Sinyalleri
     ↓ (Risk No)
Risk_Skorlama (reference)
     ↓
     ↓→ Validation and testing
```

---

## Validation Strategy

### Test Cases
1. **Signal SG-2611-001** (High Risk):
   - Red Sea diversion → Cidde delay
   - Expected: High probability, high impact
   - Validation: Compare with Risk_Skorlama R-01

2. **Signal SG-2611-003** (Medium Risk):
   - OOS quality issue
   - Expected: Medium probability, low impact
   - Validation: Compare with Risk_Skorlama R-04

3. **Signal SG-2611-012** (Low Risk):
   - Unconfirmed social media rumor
   - Expected: Low probability, low impact
   - Validation: Compare with Risk_Skorlama R-08

### Verification Steps
1. Signal parsing matches input format
2. Probability weights sum to 1.0
3. Impact thresholds correctly applied
4. Risk scores match reference values
5. Strategy options valid and cost-comparable
