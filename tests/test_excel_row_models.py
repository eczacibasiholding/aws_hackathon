"""
Test Excel row models with sample data.
Validates that Pydantic models correctly map Turkish column headers.
"""

from datetime import date, datetime

import pytest

from src.nexus.models import (
    SignalRow,
    ShipmentRow,
    MaterialRow,
    SupplierRow,
    SupplySourceRow,
    StockRow,
    ProductionLineRow,
    ParametersRow,
    CustomerOrderRow,
    OpenOrderRow,
    RouteOptionRow,
    CarrierRow,
    FacilityRow,
)


class TestSignalRow:
    """Test SignalRow model"""

    def test_signal_row_with_turkish_headers(self):
        """Test that Turkish column headers are correctly mapped"""
        data = {
            "Sinyal No": "SG-2611-001",
            "Yayın Zamanı": datetime(2026, 11, 24, 9, 12, 0),
            "Tespit Zamanı": datetime(2026, 11, 24, 9, 20, 0),
            "Kaynak Kodu": "KY02",
            "Kaynak Adı": "Taşıyıcı müşteri bildirimi",
            "Kategori": "Lojistik & Liman",
            "Dil": "EN",
            "Ham Metin (LLM Girdisi)": "Customer advisory text...",
            "Kaynak Taban Güvenilirlik": 4,
            "Doğrulandı mı?": "Evet",
            "Durum": "Açık – Analizde",
        }
        
        signal = SignalRow(**data)
        
        assert signal.sinyal_no == "SG-2611-001"
        assert signal.kaynak_kodu == "KY02"
        assert signal.kaynak_taban_guvenilirlik == 4
        assert signal.ham_metin == "Customer advisory text..."


class TestShipmentRow:
    """Test ShipmentRow model"""

    def test_shipment_row_with_turkish_headers(self):
        """Test that Turkish column headers are correctly mapped"""
        data = {
            "Sevkiyat No": "AKH-MUN-26-1184",
            "Takip No": None,
            "PO No": "4500201377",
            "Malzeme No": "MT100054",
            "Miktar": 2000.0,
            "Sevkiyat Tarihi": date(2026, 11, 27),
            "ETA": date(2026, 12, 5),
            "Gemi Adı": "MV AEGEAN STAR",
            "Rotakod": None,
            "Taşıyıcı No": "TS01",
            "Açıklama": "Conjunction at Jeddah",
        }
        
        shipment = ShipmentRow(**data)
        
        assert shipment.sevkiyat_no == "AKH-MUN-26-1184"
        assert shipment.po_no == "4500201377"
        assert shipment.miktar == 2000.0
        assert shipment.gemi_adi == "MV AEGEAN STAR"


class TestMaterialRow:
    """Test MaterialRow model"""

    def test_material_row_with_turkish_headers(self):
        """Test that Turkish column headers are correctly mapped"""
        data = {
            "Malzeme No": "MT100054",
            "Malzeme Adı": "Clarithromycin API",
            "Kategori": "API",
            "Birim": "kg",
            "Birim Maliyet": 15.50,
            "Kritiklik": "Kritik",
            "MOQ": 500.0,
        }
        
        material = MaterialRow(**data)
        
        assert material.malzeme_no == "MT100054"
        assert material.kategori == "API"
        assert material.birim_maliyet == 15.50


class TestSupplierRow:
    """Test SupplierRow model"""

    def test_supplier_row_with_turkish_headers(self):
        """Test that Turkish column headers are correctly mapped"""
        data = {
            "Tedarikçi Kodu": "TD5011",
            "Tedarikçi Adı": "PharmaTech Industries",
            "Ülke": "India",
            "OTIF Performansı": 0.92,
            "Finansal Sağlık": 4,
            "Kapasite (kg/ay)": 50000.0,
        }
        
        supplier = SupplierRow(**data)
        
        assert supplier.tedarikci_kodu == "TD5011"
        assert supplier.otif_performansi == 0.92
        assert supplier.finansal_saglik == 4


class TestSupplySourceRow:
    """Test SupplySourceRow model - CRITICAL: contains Kalifikasyon"""

    def test_supply_source_row_with_qualification(self):
        """Test that Kalifikasyon field is correctly mapped"""
        data = {
            "Kaynak No": "K001",
            "Malzeme No": "MT100054",
            "Tedarikçi Kodu": "TD5011",
            "Tesis Kodu": "T-SG-01",
            "Tedarik Süresi (gün)": 15,
            "Birim Maliyet": 15.50,
            "MOQ": 500.0,
            "Kalifikasyon": "Ruhsatta Kayıtlı",
            "Mevcut Stok (kg)": 2000.0,
        }
        
        source = SupplySourceRow(**data)
        
        assert source.kalifikasyon == "Ruhsatta Kayıtlı"
        assert source.tedarik_suresi_gun == 15
        assert source.mevcut_stok_kg == 2000.0


class TestStockRow:
    """Test StockRow model"""

    def test_stock_row_with_turkish_headers(self):
        """Test that Turkish column headers are correctly mapped"""
        data = {
            "Stok Anahtarı": "T-SG-01|MT100054",
            "Malzeme No": "MT100054",
            "Tesis Kodu": "T-SG-01",
            "Mevcut Stok": 9900.0,
            "Günlük Tüketim": 1100.0,
            "Emniyet Stoku": 5500.0,
            "Mevcut Stoğun Günlük Tüketim Üzerinden Süresi": 9.0,
        }
        
        stock = StockRow(**data)
        
        assert stock.stok_anahtari == "T-SG-01|MT100054"
        assert stock.mevcut_stok == 9900.0
        assert stock.gunluk_tuketim == 1100.0


class TestProductionLineRow:
    """Test ProductionLineRow model"""

    def test_production_line_row_with_turkish_headers(self):
        """Test that Turkish column headers are correctly mapped"""
        data = {
            "Tesis Kodu": "T-SG-01",
            "Tesis Adı": "Sancaktepe Fabrikası",
            "Malzeme No": "MT100054",
            "Üretim Hattı": "HAT-SG-03",
            "Günlük Üretim Kapasitesi": 1200.0,
            "Duruş Riski": "Evet",
            "Günlük Duruşma Maliyeti": 45000.0,
            "Yeniden Başlama Maliyeti": 25000.0,
        }
        
        prod_line = ProductionLineRow(**data)
        
        assert prod_line.uretim_hatti == "HAT-SG-03"
        assert prod_line.gunluk_uretim_kapasitesi == 1200.0
        assert prod_line.durus_riski == "Evet"
        assert prod_line.gunluk_durusma_maliyeti == 45000.0


class TestParametersRow:
    """Test ParametersRow model"""

    def test_parameters_row_with_turkish_headers(self):
        """Test that Turkish column headers are correctly mapped"""
        data = {
            "Parametre": "USDTRY",
            "Değer": 45.9,
            "Birim": "TRY",
            "Açıklama": "USD/TRY exchange rate",
        }
        
        param = ParametersRow(**data)
        
        assert param.parametre == "USDTRY"
        assert param.deger == 45.9
        assert param.birim == "TRY"


class TestCustomerOrderRow:
    """Test CustomerOrderRow model"""

    def test_customer_order_row_with_turkish_headers(self):
        """Test that Turkish column headers are correctly mapped"""
        data = {
            "Sipariş No": "SO-2026-001",
            "Müşteri Kodu": "C001",
            "Malzeme No": "MT100054",
            "Miktar": 500.0,
            "Teslimat Tarihi": date(2026, 12, 10),
            "Öncelik": "Yüksek",
            "Gecikme Ceza Oranı": 0.05,
        }
        
        order = CustomerOrderRow(**data)
        
        assert order.siparis_no == "SO-2026-001"
        assert order.oncelik == "Yüksek"
        assert order.gecikme_ceza_orani == 0.05


class TestOpenOrderRow:
    """Test OpenOrderRow model"""

    def test_open_order_row_with_turkish_headers(self):
        """Test that Turkish column headers are correctly mapped"""
        data = {
            "PO No": "4500201377",
            "Malzeme No": "MT100054",
            "Tedarikçi Kodu": "TD5011",
            "Tesis Kodu": "T-SG-01",
            "Sipariş Tarihi": date(2026, 11, 15),
            "Miktar": 2000.0,
            "Teyit Tarihi": date(2026, 11, 29),
            "Birim Fiyat": 15.50,
            "Toplam Tutar": 31000.0,
        }
        
        open_order = OpenOrderRow(**data)
        
        assert open_order.po_no == "4500201377"
        assert open_order.miktar == 2000.0
        assert open_order.toplam_tutar == 31000.0


class TestRouteOptionRow:
    """Test RouteOptionRow model"""

    def test_route_option_row_with_turkish_headers(self):
        """Test that Turkish column headers are correctly mapped"""
        data = {
            "Rota Kodu": "RT-SEA-001",
            "Başlangıç": "Mumbai",
            "Varış": "Istanbul",
            "Taşıma Türü": "Sea",
            "Süre (gün)": 18,
            "Maliyet ($/kg)": 2.50,
            "CO2 (kg/kg)": 0.015,
            "Kapasite Durum": "Available",
        }
        
        route = RouteOptionRow(**data)
        
        assert route.rota_kodu == "RT-SEA-001"
        assert route.sure_gun == 18
        assert route.maliyet_kg == 2.50


class TestCarrierRow:
    """Test CarrierRow model"""

    def test_carrier_row_with_turkish_headers(self):
        """Test that Turkish column headers are correctly mapped"""
        data = {
            "Taşıyıcı No": "TS01",
            "Taşıyıcı Adı": "Mediterranean Shipping Co",
            "Taşıma Türü": "Sea",
            "Zamanında Ulaşım Oranı": 0.90,
            "Finansal Sağlık": 4,
        }
        
        carrier = CarrierRow(**data)
        
        assert carrier.tasiyici_no == "TS01"
        assert carrier.zamaninda_ulasim_orani == 0.90


class TestFacilityRow:
    """Test FacilityRow model"""

    def test_facility_row_with_turkish_headers(self):
        """Test that Turkish column headers are correctly mapped"""
        data = {
            "Tesis Kodu": "T-SG-01",
            "Tesis Adı": "Sancaktepe Fabrikası",
            "Şehir": "Istanbul",
            "Ülke": "Turkey",
            "Tesis Tipi": "Production",
        }
        
        facility = FacilityRow(**data)
        
        assert facility.tesis_kodu == "T-SG-01"
        assert facility.sehir == "Istanbul"
        assert facility.tesis_tipi == "Production"
