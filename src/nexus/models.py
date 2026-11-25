"""
Pydantic models for NEXUS Pipeline agent inputs and outputs.

This module defines the data structures for all four agents:
- Agent 1: Signal Agent (extraction from raw text)
- Agent 2: Risk & Impact Agent (deterministic risk calculation)
- Agent 3: Options Agent (mitigation option generation)
- Agent 4: Decision Agent (multi-criteria evaluation)
"""

from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Agent 1: Signal Agent Models
# =============================================================================


class SignalInput(BaseModel):
    """Input for Signal Agent"""
    signal_id: str = Field(..., description="Unique signal identifier (e.g., SG-2611-001)")
    signal_text: str = Field(..., description="Raw signal text to extract from")
    signal_date: date = Field(..., description="Signal publication date")
    signal_source: str = Field(..., description="Signal source code (e.g., KY02)")


class SignalExtraction(BaseModel):
    """Output from Signal Agent"""
    signal_id: str = Field(..., description="Signal identifier")
    event_type: str = Field(..., description="Event type (port closure, strike, weather, quality)")
    country_region: str = Field(..., description="Country or region affected")
    party_code: Optional[str] = Field(None, description="Supplier or carrier code")
    shipment_id: Optional[str] = Field(None, description="Affected shipment ID")
    material_no: Optional[str] = Field(None, description="Material number")
    estimated_delay_days: int = Field(..., description="Estimated delay in days")
    alternative_hints: List[str] = Field(default_factory=list, description="Alternative suggestions from signal text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence (0.0 to 1.0)")
    extraction_method: Literal["llm", "pattern_match", "not_found"] = Field(
        ..., description="Method used for extraction"
    )


# =============================================================================
# Agent 2: Risk & Impact Agent Models
# =============================================================================


class RiskInput(BaseModel):
    """Input for Risk & Impact Agent"""
    signal_id: str = Field(..., description="Signal identifier")
    extraction: SignalExtraction = Field(..., description="Extraction result from Agent 1")


class RiskAssessment(BaseModel):
    """Output from Risk & Impact Agent"""
    signal_id: str = Field(..., description="Signal identifier")
    probability_score: float = Field(..., ge=0.0, le=5.0, description="Weighted probability score (0-5)")
    impact_score: int = Field(..., ge=1, le=5, description="Impact score (1-5)")
    risk_score: float = Field(..., ge=0.0, le=25.0, description="Risk score = probability × impact")
    risk_category: Literal["Low", "Medium", "High"] = Field(..., description="Risk category")
    available_date: date = Field(..., description="Date when material becomes available (ETA + delays)")
    stock_coverage_days: float = Field(..., description="Days of stock coverage remaining")
    depletion_date: date = Field(..., description="Date when stock will be depleted")
    downtime_days: float = Field(..., ge=0.0, description="Production downtime days")
    remaining_buffer: float = Field(..., ge=0.0, description="Remaining safety buffer days")
    downtime_cost: float = Field(..., ge=0.0, description="Cost of production downtime (TRY)")
    customer_penalty: float = Field(..., ge=0.0, description="Customer penalty cost (TRY)")
    total_inaction_cost: float = Field(..., ge=0.0, description="Total cost if no action taken (TRY)")
    at_risk_orders: List[str] = Field(default_factory=list, description="Customer order numbers at risk")
    justification: str = Field(..., description="LLM-generated risk justification")


# =============================================================================
# Agent 3: Options Agent Models
# =============================================================================


class OptionsInput(BaseModel):
    """Input for Options Agent"""
    signal_id: str = Field(..., description="Signal identifier")
    extraction: SignalExtraction = Field(..., description="Extraction from Agent 1")
    assessment: RiskAssessment = Field(..., description="Risk assessment from Agent 2")


class Arrival(BaseModel):
    """Shipment arrival schedule (day and quantity)"""
    day: int = Field(..., description="Day from D0 when shipment arrives")
    quantity: float = Field(..., gt=0, description="Quantity arriving (kg or units)")


class MitigationOption(BaseModel):
    """Mitigation option with cost, time, and feasibility"""
    option_id: str = Field(..., description="Unique option identifier")
    option_type: Literal[
        "transfer", 
        "alternative_supplier", 
        "route_change", 
        "expedited", 
        "hybrid", 
        "no_action"
    ] = Field(..., description="Type of mitigation option")
    details: str = Field(..., description="Human-readable description")
    arrivals: List[Arrival] = Field(..., description="List of arrival schedules (day, quantity)")
    action_cost: float = Field(..., ge=0.0, description="Direct cost of mitigation action (TRY)")
    co2_kg: float = Field(..., ge=0.0, description="CO2 emissions (kg)")
    risk_score: float = Field(..., ge=0.0, le=25.0, description="Residual risk score after mitigation")
    downtime_days: float = Field(..., ge=0.0, description="Production downtime days (simulated)")
    total_cost: float = Field(..., ge=0.0, description="Total cost including downtime and penalties (TRY)")
    constraints_satisfied: List[str] = Field(default_factory=list, description="Satisfied constraints")
    constraints_violated: List[str] = Field(default_factory=list, description="Violated constraints")
    feasibility: Literal["Feasible", "Conditional", "NotFeasible"] = Field(
        ..., description="Feasibility classification"
    )
    llm_suggestion: str = Field(default="", description="LLM-generated suggestion")


# =============================================================================
# Agent 4: Decision Agent Models
# =============================================================================


class DecisionInput(BaseModel):
    """Input for Decision Agent"""
    signal_id: str = Field(..., description="Signal identifier")
    extraction: SignalExtraction = Field(..., description="Extraction from Agent 1")
    assessment: RiskAssessment = Field(..., description="Assessment from Agent 2")
    options: List[MitigationOption] = Field(..., description="Mitigation options from Agent 3")


class RankedOption(BaseModel):
    """Mitigation option with normalized scores and CKKV ranking"""
    option: MitigationOption = Field(..., description="Mitigation option")
    normalized_cost: float = Field(..., ge=0.0, le=1.0, description="Normalized cost score (0-1)")
    normalized_downtime: float = Field(..., ge=0.0, le=1.0, description="Normalized downtime score (0-1)")
    normalized_co2: float = Field(..., ge=0.0, le=1.0, description="Normalized CO2 score (0-1)")
    normalized_risk: float = Field(..., ge=0.0, le=1.0, description="Normalized risk score (0-1)")
    ckkv_score: float = Field(..., ge=0.0, le=1.0, description="Weighted CKKV score (0-1)")
    rank: int = Field(..., ge=1, description="Rank (1=best)")


class DecisionResult(BaseModel):
    """Output from Decision Agent"""
    signal_id: str = Field(..., description="Signal identifier")
    all_options_ranked: List[RankedOption] = Field(..., description="All options ranked by CKKV score")
    recommended_option: RankedOption = Field(..., description="Top-ranked recommended option")
    justification: str = Field(..., description="LLM-generated recommendation justification")


# =============================================================================
# Excel Data Row Models (Turkish Column Headers)
# =============================================================================


class SignalRow(BaseModel):
    """
    Maps to Risk_Sinyalleri sheet.
    Uses REAL Turkish column headers from Excel.
    """
    model_config = ConfigDict(populate_by_name=True)

    sinyal_no: str = Field(..., alias="Sinyal No", description="Unique signal ID")
    yayin_zamani: datetime = Field(..., alias="Yayın Zamanı", description="Signal publication time")
    tespit_zamani: datetime = Field(..., alias="Tespit Zamanı", description="Agent detection time")
    kaynak_kodu: str = Field(..., alias="Kaynak Kodu", description="Source identifier")
    kaynak_adi: str = Field(..., alias="Kaynak Adı", description="Source name")
    kategori: str = Field(..., alias="Kategori", description="Signal category")
    dil: str = Field(..., alias="Dil", description="Language code (EN, TR)")
    ham_metin: str = Field(..., alias="Ham Metin (LLM Girdisi)", description="Raw signal text for LLM")
    kaynak_taban_guvenilirlik: int = Field(..., alias="Kaynak Taban Güvenilirlik", ge=1, le=5, description="Source base reliability (1-5)")
    dogrulandi_mi: str = Field(..., alias="Doğrulandı mı?", description="Verification status (Evet/Hayır)")
    durum: str = Field(..., alias="Durum", description="Signal status")


class ShipmentRow(BaseModel):
    """
    Maps to Sevkiyatlar sheet.
    Uses REAL Turkish column headers from Excel.
    """
    model_config = ConfigDict(populate_by_name=True)

    sevkiyat_no: str = Field(..., alias="Sevkiyat No", description="Shipment identifier")
    takip_no: Optional[str] = Field(None, alias="Takip No", description="Tracking number")
    po_no: str = Field(..., alias="PO No", description="Purchase order number")
    malzeme_no: str = Field(..., alias="Malzeme No", description="Material code")
    miktar: float = Field(..., alias="Miktar", description="Quantity")
    sevkiyat_tarihi: date = Field(..., alias="Sevkiyat Tarihi", description="Scheduled shipment date")
    eta: date = Field(..., alias="ETA", description="Estimated time of arrival")
    gemi_adi: Optional[str] = Field(None, alias="Gemi Adı", description="Vessel name")
    rotakod: Optional[str] = Field(None, alias="Rotakod", description="Route code")
    tasiyici_no: str = Field(..., alias="Taşıyıcı No", description="Carrier code")
    aciklama: Optional[str] = Field(None, alias="Açıklama", description="Notes")


class MaterialRow(BaseModel):
    """
    Maps to Malzemeler sheet.
    Uses REAL Turkish column headers from Excel.
    """
    model_config = ConfigDict(populate_by_name=True)

    malzeme_no: str = Field(..., alias="Malzeme No", description="Material code")
    malzeme_adi: str = Field(..., alias="Malzeme Adı", description="Material name")
    kategori: str = Field(..., alias="Kategori", description="Material category (API, Excipient, etc.)")
    birim: str = Field(..., alias="Birim", description="Unit of measure (kg, pcs, etc.)")
    birim_maliyet: float = Field(..., alias="Birim Maliyet", description="Unit cost")
    kritiklik: str = Field(..., alias="Kritiklik", description="Criticality level")
    moq: Optional[float] = Field(None, alias="MOQ", description="Minimum order quantity")


class SupplierRow(BaseModel):
    """
    Maps to Tedarikciler sheet.
    Uses REAL Turkish column headers from Excel.
    Note: Qualification status is in Tedarik_Kaynaklari, NOT here.
    """
    model_config = ConfigDict(populate_by_name=True)

    tedarikci_kodu: str = Field(..., alias="Tedarikçi Kodu", description="Supplier code")
    tedarikci_adi: str = Field(..., alias="Tedarikçi Adı", description="Supplier name")
    ulke: str = Field(..., alias="Ülke", description="Country")
    otif_performansi: float = Field(..., alias="OTIF Performansı", ge=0.0, le=1.0, description="On-time in-full performance (0-1)")
    finansal_saglik: int = Field(..., alias="Finansal Sağlık", ge=1, le=5, description="Financial health score (1-5)")
    kapasite_kg_ay: Optional[float] = Field(None, alias="Kapasite (kg/ay)", description="Monthly capacity in kg")


class SupplySourceRow(BaseModel):
    """
    Maps to Tedarik_Kaynaklari sheet.
    CRITICAL: Contains 'Kalifikasyon' field (qualification status per material×supplier).
    Uses REAL Turkish column headers from Excel.
    """
    model_config = ConfigDict(populate_by_name=True)

    kaynak_no: str = Field(..., alias="Kaynak No", description="Source identifier")
    malzeme_no: str = Field(..., alias="Malzeme No", description="Material code")
    tedarikci_kodu: str = Field(..., alias="Tedarikçi Kodu", description="Supplier code")
    tesis_kodu: str = Field(..., alias="Tesis Kodu", description="Facility code")
    tedarik_suresi_gun: int = Field(..., alias="Tedarik Süresi (gün)", description="Lead time in days")
    birim_maliyet: float = Field(..., alias="Birim Maliyet", description="Unit cost")
    moq: Optional[float] = Field(None, alias="MOQ", description="Minimum order quantity")
    kalifikasyon: str = Field(..., alias="Kalifikasyon", description="Qualification status (e.g., 'Ruhsatta Kayıtlı')")
    mevcut_stok_kg: Optional[float] = Field(None, alias="Mevcut Stok (kg)", description="Current stock in kg")


class StockRow(BaseModel):
    """
    Maps to Stok_Durumu sheet.
    Uses REAL Turkish column headers from Excel.
    """
    model_config = ConfigDict(populate_by_name=True)

    stok_anahtari: str = Field(..., alias="Stok Anahtarı", description="Composite key (Facility|Material)")
    malzeme_no: str = Field(..., alias="Malzeme No", description="Material code")
    tesis_kodu: str = Field(..., alias="Tesis Kodu", description="Facility code")
    mevcut_stok: float = Field(..., alias="Mevcut Stok", description="Current stock quantity")
    gunluk_tuketim: float = Field(..., alias="Günlük Tüketim", description="Daily consumption rate")
    emniyet_stoku: float = Field(..., alias="Emniyet Stoku", description="Safety stock level")
    mevcut_stok_gun: Optional[float] = Field(None, alias="Mevcut Stoğun Günlük Tüketim Üzerinden Süresi", description="Stock coverage in days")


class ProductionLineRow(BaseModel):
    """
    Maps to Uretim_Hatlari sheet.
    Uses REAL Turkish column headers from Excel.
    """
    model_config = ConfigDict(populate_by_name=True)

    tesis_kodu: str = Field(..., alias="Tesis Kodu", description="Facility code")
    tesis_adi: str = Field(..., alias="Tesis Adı", description="Facility name")
    malzeme_no: str = Field(..., alias="Malzeme No", description="Material code")
    uretim_hatti: str = Field(..., alias="Üretim Hattı", description="Production line identifier")
    gunluk_uretim_kapasitesi: float = Field(..., alias="Günlük Üretim Kapasitesi", description="Daily production capacity")
    durus_riski: str = Field(..., alias="Duruş Riski", description="Downtime risk (Evet/Hayır)")
    gunluk_durusma_maliyeti: Optional[float] = Field(None, alias="Günlük Duruşma Maliyeti", description="Daily downtime cost")
    yeniden_baslama_maliyeti: Optional[float] = Field(None, alias="Yeniden Başlama Maliyeti", description="Restart cost")


class ParametersRow(BaseModel):
    """
    Maps to Parametreler sheet.
    Uses REAL Turkish column headers from Excel.
    CRITICAL: Contains exchange rates, thresholds, weights.
    """
    model_config = ConfigDict(populate_by_name=True)

    parametre: str = Field(..., alias="Parametre", description="Parameter name")
    deger: float = Field(..., alias="Değer", description="Parameter value")
    birim: Optional[str] = Field(None, alias="Birim", description="Unit of measure")
    aciklama: Optional[str] = Field(None, alias="Açıklama", description="Description")


class CustomerOrderRow(BaseModel):
    """
    Maps to Musteri_Siparisleri sheet.
    Uses REAL Turkish column headers from Excel.
    """
    model_config = ConfigDict(populate_by_name=True)

    siparis_no: str = Field(..., alias="Sipariş No", description="Customer order number")
    musteri_kodu: str = Field(..., alias="Müşteri Kodu", description="Customer code")
    malzeme_no: str = Field(..., alias="Malzeme No", description="Material code")
    miktar: float = Field(..., alias="Miktar", description="Quantity")
    teslimat_tarihi: date = Field(..., alias="Teslimat Tarihi", description="Delivery date")
    oncelik: str = Field(..., alias="Öncelik", description="Priority level")
    gecikme_ceza_orani: Optional[float] = Field(None, alias="Gecikme Ceza Oranı", description="Penalty rate for delay")


class OpenOrderRow(BaseModel):
    """
    Maps to Acik_Siparisler sheet.
    Uses REAL Turkish column headers from Excel.
    """
    model_config = ConfigDict(populate_by_name=True)

    po_no: str = Field(..., alias="PO No", description="Purchase order number")
    malzeme_no: str = Field(..., alias="Malzeme No", description="Material code")
    tedarikci_kodu: str = Field(..., alias="Tedarikçi Kodu", description="Supplier code")
    tesis_kodu: str = Field(..., alias="Tesis Kodu", description="Facility code")
    siparis_tarihi: date = Field(..., alias="Sipariş Tarihi", description="Order date")
    miktar: float = Field(..., alias="Miktar", description="Quantity")
    teyit_tarihi: date = Field(..., alias="Teyit Tarihi", description="Confirmation date")
    birim_fiyat: float = Field(..., alias="Birim Fiyat", description="Unit price")
    toplam_tutar: float = Field(..., alias="Toplam Tutar", description="Total amount")


class RouteOptionRow(BaseModel):
    """
    Maps to Rota_Secenekleri sheet.
    Uses REAL Turkish column headers from Excel.
    """
    model_config = ConfigDict(populate_by_name=True)

    rota_kodu: str = Field(..., alias="Rota Kodu", description="Route code")
    baslangic: str = Field(..., alias="Başlangıç", description="Origin")
    varis: str = Field(..., alias="Varış", description="Destination")
    tasima_turu: str = Field(..., alias="Taşıma Türü", description="Transport mode (Sea, Air, Ground)")
    sure_gun: int = Field(..., alias="Süre (gün)", description="Transit time in days")
    maliyet_kg: float = Field(..., alias="Maliyet ($/kg)", description="Cost per kg in USD")
    co2_kg: float = Field(..., alias="CO2 (kg/kg)", description="CO2 emissions per kg")
    kapasite_durum: Optional[str] = Field(None, alias="Kapasite Durum", description="Capacity status")


class CarrierRow(BaseModel):
    """
    Maps to Tasiyicilar sheet.
    Uses REAL Turkish column headers from Excel.
    """
    model_config = ConfigDict(populate_by_name=True)

    tasiyici_no: str = Field(..., alias="Taşıyıcı No", description="Carrier code")
    tasiyici_adi: str = Field(..., alias="Taşıyıcı Adı", description="Carrier name")
    tasima_turu: str = Field(..., alias="Taşıma Türü", description="Transport mode")
    zamaninda_ulasim_orani: float = Field(..., alias="Zamanında Ulaşım Oranı", ge=0.0, le=1.0, description="On-time arrival rate (0-1)")
    finansal_saglik: int = Field(..., alias="Finansal Sağlık", ge=1, le=5, description="Financial health score (1-5)")


class FacilityRow(BaseModel):
    """
    Maps to Tesisler sheet.
    Uses REAL Turkish column headers from Excel.
    """
    model_config = ConfigDict(populate_by_name=True)

    tesis_kodu: str = Field(..., alias="Tesis Kodu", description="Facility code")
    tesis_adi: str = Field(..., alias="Tesis Adı", description="Facility name")
    sehir: str = Field(..., alias="Şehir", description="City")
    ulke: str = Field(..., alias="Ülke", description="Country")
    tesis_tipi: str = Field(..., alias="Tesis Tipi", description="Facility type (Production, Warehouse, etc.)")


# =============================================================================
# Orchestrator: Pipeline State Model
# =============================================================================


class PipelineState(BaseModel):
    """
    State persistence model for orchestrator pipeline.
    
    Tracks the complete execution state of the 4-agent pipeline:
    - Agent 1: Signal extraction
    - Agent 2: Risk assessment
    - Agent 3: Mitigation options
    - Agent 4: Decision recommendation
    
    Supports human approval workflow and audit trail.
    """
    signal_id: str = Field(..., description="Signal identifier")
    timestamp: datetime = Field(..., description="Pipeline execution timestamp")
    status: Literal["completed", "low_risk", "error", "in_progress"] = Field(
        ..., description="Pipeline execution status"
    )
    agent_1_output: Optional[SignalExtraction] = Field(
        None, description="Output from Agent 1 (Signal Agent)"
    )
    agent_2_output: Optional[RiskAssessment] = Field(
        None, description="Output from Agent 2 (Risk & Impact Agent)"
    )
    agent_3_output: Optional[List[MitigationOption]] = Field(
        None, description="Output from Agent 3 (Options Agent)"
    )
    agent_4_output: Optional[DecisionResult] = Field(
        None, description="Output from Agent 4 (Decision Agent)"
    )
    approval_decision: Optional[Literal["approved", "rejected"]] = Field(
        None, description="Human approval decision"
    )
    approver_identity: Optional[str] = Field(
        None, description="Identity of approver (username/email)"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if status is 'error'"
    )
