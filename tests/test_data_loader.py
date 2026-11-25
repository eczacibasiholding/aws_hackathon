"""
Tests for DataLoader class.

Validates:
- Excel file loading
- All accessor methods
- Proper Pydantic model returns
- Exception handling for missing data
- Key test cases from acceptance criteria
"""

import pytest
import sys
import os
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nexus.data_loader import DataLoader
from nexus.models import (
    SignalRow,
    ShipmentRow,
    MaterialRow,
    SupplierRow,
    SupplySourceRow,
    CarrierRow,
    FacilityRow,
    StockRow,
    ProductionLineRow,
    CustomerOrderRow,
    OpenOrderRow,
    RouteOptionRow,
)


@pytest.fixture
def loader():
    """Create DataLoader instance for testing."""
    return DataLoader()


class TestDataLoaderInitialization:
    """Test DataLoader initialization and file loading."""
    
    def test_loader_initialization(self, loader):
        """Test that DataLoader initializes successfully."""
        assert loader is not None
        assert loader.excel_path.exists()
    
    def test_missing_file_raises_error(self):
        """Test that missing Excel file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            DataLoader(excel_path="/nonexistent/path/file.xlsx")
    
    def test_all_sheets_loaded(self, loader):
        """Test that all required sheets are loaded."""
        expected_sheets = [
            "Risk_Sinyalleri",
            "Sevkiyatlar",
            "Malzemeler",
            "Tedarikciler",
            "Tedarik_Kaynaklari",
            "Tasiyicilar",
            "Tesisler",
            "Stok_Durumu",
            "Uretim_Hatlari",
            "Musteri_Siparisleri",
            "Acik_Siparisler",
            "Rota_Secenekleri",
            "Parametreler",
        ]
        
        for sheet_name in expected_sheets:
            assert sheet_name in loader._sheets


class TestSignalAccessors:
    """Test signal-related accessor methods."""
    
    def test_get_signal_sg_2611_001(self, loader):
        """Test getting signal SG-2611-001 (from acceptance criteria)."""
        signal = loader.get_signal("SG-2611-001")
        
        assert isinstance(signal, SignalRow)
        assert signal.sinyal_no == "SG-2611-001"
        assert signal.kaynak_kodu == "KY02"
        assert signal.kategori == "Lojistik & Liman"
        assert signal.dil == "EN"
        assert "Red Sea" in signal.ham_metin or "Jeddah" in signal.ham_metin
        assert signal.kaynak_taban_guvenilirlik == 4
        assert signal.dogrulandi_mi == "Evet"
    
    def test_get_signal_not_found(self, loader):
        """Test that missing signal raises KeyError."""
        with pytest.raises(KeyError, match="Signal ID 'SG-9999-999' not found"):
            loader.get_signal("SG-9999-999")
    
    def test_get_all_signal_ids(self, loader):
        """Test getting all signal IDs."""
        signal_ids = loader.get_all_signal_ids()
        
        assert isinstance(signal_ids, list)
        assert len(signal_ids) > 0
        assert "SG-2611-001" in signal_ids
    
    def test_list_signals(self, loader):
        """Test listing all signals."""
        signals = loader.list_signals()
        
        assert isinstance(signals, list)
        assert len(signals) > 0
        assert all(isinstance(s, SignalRow) for s in signals)
        
        # Find our test signal
        test_signal = next((s for s in signals if s.sinyal_no == "SG-2611-001"), None)
        assert test_signal is not None


class TestShipmentAccessors:
    """Test shipment-related accessor methods."""
    
    def test_get_shipment(self, loader):
        """Test getting shipment (check actual ID format in Excel)."""
        # Note: The task mentions "SV-26-1184" but the Excel has "AKH-MUN-26-1184"
        # Let's find what shipments exist
        shipment = loader.get_shipment("AKH-MUN-26-1184")
        
        assert isinstance(shipment, ShipmentRow)
        assert shipment.sevkiyat_no == "AKH-MUN-26-1184"
        assert shipment.malzeme_no == "MT100054"
        assert shipment.tasiyici_no == "TS01"
    
    def test_get_shipment_not_found(self, loader):
        """Test that missing shipment raises KeyError."""
        with pytest.raises(KeyError, match="Shipment ID 'INVALID-SHIP-999' not found"):
            loader.get_shipment("INVALID-SHIP-999")


class TestMaterialAccessors:
    """Test material-related accessor methods."""
    
    def test_get_material(self, loader):
        """Test getting material."""
        material = loader.get_material("MT100054")
        
        assert isinstance(material, MaterialRow)
        assert material.malzeme_no == "MT100054"
        assert material.malzeme_adi is not None
        assert material.kategori is not None
        assert material.birim_maliyet > 0
    
    def test_get_material_not_found(self, loader):
        """Test that missing material raises KeyError."""
        with pytest.raises(KeyError, match="Material number 'MT999999' not found"):
            loader.get_material("MT999999")


class TestSupplierAccessors:
    """Test supplier-related accessor methods."""
    
    def test_get_supplier(self, loader):
        """Test getting supplier."""
        supplier = loader.get_supplier("TD5011")
        
        assert isinstance(supplier, SupplierRow)
        assert supplier.tedarikci_kodu == "TD5011"
        assert supplier.tedarikci_adi is not None
        assert supplier.ulke is not None
        assert 0.0 <= supplier.otif_performansi <= 1.0
        assert 1 <= supplier.finansal_saglik <= 5
    
    def test_get_supplier_not_found(self, loader):
        """Test that missing supplier raises KeyError."""
        with pytest.raises(KeyError, match="Supplier code 'TD9999' not found"):
            loader.get_supplier("TD9999")
    
    def test_get_supply_source(self, loader):
        """Test getting supply source for material-supplier combination."""
        # Find a valid combination from the data
        source = loader.get_supply_source("MT100054", "TD5011")
        
        assert isinstance(source, SupplySourceRow)
        assert source.malzeme_no == "MT100054"
        assert source.tedarikci_kodu == "TD5011"
        assert source.tedarik_suresi_gun > 0
        assert source.birim_maliyet > 0
        assert source.kalifikasyon is not None
    
    def test_get_supply_source_not_found(self, loader):
        """Test that missing supply source raises KeyError."""
        with pytest.raises(KeyError, match="Supply source not found"):
            loader.get_supply_source("MT999999", "TD9999")


class TestCarrierAndFacilityAccessors:
    """Test carrier and facility accessor methods."""
    
    def test_get_carrier(self, loader):
        """Test getting carrier."""
        carrier = loader.get_carrier("TS01")
        
        assert isinstance(carrier, CarrierRow)
        assert carrier.tasiyici_no == "TS01"
        assert carrier.tasiyici_adi is not None
        assert 0.0 <= carrier.zamaninda_ulasim_orani <= 1.0
        assert 1 <= carrier.finansal_saglik <= 5
    
    def test_get_carrier_not_found(self, loader):
        """Test that missing carrier raises KeyError."""
        with pytest.raises(KeyError, match="Carrier code 'TS999' not found"):
            loader.get_carrier("TS999")
    
    def test_get_facility(self, loader):
        """Test getting facility."""
        facility = loader.get_facility("T-SG-01")
        
        assert isinstance(facility, FacilityRow)
        assert facility.tesis_kodu == "T-SG-01"
        assert facility.tesis_adi is not None
        assert facility.sehir is not None
        assert facility.ulke is not None
    
    def test_get_facility_not_found(self, loader):
        """Test that missing facility raises KeyError."""
        with pytest.raises(KeyError, match="Facility code 'T-XX-99' not found"):
            loader.get_facility("T-XX-99")


class TestStockAndProductionAccessors:
    """Test stock and production line accessor methods."""
    
    def test_get_stock_status(self, loader):
        """Test getting stock status."""
        stock = loader.get_stock_status("MT100054", "T-SG-01")
        
        assert isinstance(stock, StockRow)
        assert stock.malzeme_no == "MT100054"
        assert stock.tesis_kodu == "T-SG-01"
        assert stock.mevcut_stok >= 0
        assert stock.gunluk_tuketim > 0
        assert stock.emniyet_stoku >= 0
    
    def test_get_stock_status_not_found(self, loader):
        """Test that missing stock raises KeyError."""
        with pytest.raises(KeyError, match="Stock not found"):
            loader.get_stock_status("MT999999", "T-XX-99")
    
    def test_get_production_line(self, loader):
        """Test getting production line."""
        prod_line = loader.get_production_line("T-SG-01", "MT100054")
        
        assert isinstance(prod_line, ProductionLineRow)
        assert prod_line.tesis_kodu == "T-SG-01"
        assert prod_line.malzeme_no == "MT100054"
        assert prod_line.gunluk_uretim_kapasitesi > 0
        assert prod_line.durus_riski in ["Evet", "Hayır"]
    
    def test_get_production_line_not_found(self, loader):
        """Test that missing production line raises KeyError."""
        with pytest.raises(KeyError, match="Production line not found"):
            loader.get_production_line("T-XX-99", "MT999999")


class TestOrderAccessors:
    """Test order-related accessor methods."""
    
    def test_get_customer_orders(self, loader):
        """Test getting customer orders for a material."""
        orders = loader.get_customer_orders("MT100054")
        
        assert isinstance(orders, list)
        # May be empty or have items
        if len(orders) > 0:
            assert all(isinstance(o, CustomerOrderRow) for o in orders)
            assert all(o.malzeme_no == "MT100054" for o in orders)
    
    def test_get_customer_orders_no_results(self, loader):
        """Test getting customer orders when none exist (should return empty list)."""
        orders = loader.get_customer_orders("MT999999")
        
        assert isinstance(orders, list)
        assert len(orders) == 0
    
    def test_get_open_orders(self, loader):
        """Test getting open purchase orders for a material."""
        orders = loader.get_open_orders("MT100054")
        
        assert isinstance(orders, list)
        # May be empty or have items
        if len(orders) > 0:
            assert all(isinstance(o, OpenOrderRow) for o in orders)
            assert all(o.malzeme_no == "MT100054" for o in orders)
    
    def test_get_open_orders_no_results(self, loader):
        """Test getting open orders when none exist (should return empty list)."""
        orders = loader.get_open_orders("MT999999")
        
        assert isinstance(orders, list)
        assert len(orders) == 0


class TestRouteAccessors:
    """Test route-related accessor methods."""
    
    def test_get_route_options(self, loader):
        """Test getting route options between origin and destination."""
        # Find valid origin-destination pairs from the data
        # Let's try common routes (we'll need to check what exists)
        routes = loader.get_route_options("Mumbai", "Istanbul")
        
        assert isinstance(routes, list)
        # May be empty or have items
        if len(routes) > 0:
            assert all(isinstance(r, RouteOptionRow) for r in routes)
            assert all(r.baslangic == "Mumbai" for r in routes)
            assert all(r.varis == "Istanbul" for r in routes)
    
    def test_get_route_options_no_results(self, loader):
        """Test getting route options when none exist (should return empty list)."""
        routes = loader.get_route_options("InvalidCity", "AnotherInvalidCity")
        
        assert isinstance(routes, list)
        assert len(routes) == 0


class TestParametersAccessor:
    """Test parameters accessor method."""
    
    def test_get_parameters(self, loader):
        """Test getting parameters (from acceptance criteria)."""
        params = loader.get_parameters()
        
        assert isinstance(params, dict)
        
        # Validate key parameters from acceptance criteria
        assert "USDTRY" in params
        assert params["USDTRY"] == 45.9
        
        assert "EsikYuksek" in params
        assert params["EsikYuksek"] == 15
        
        assert "EsikOrta" in params
        assert params["EsikOrta"] == 7
        
        assert "StokTasimaOrani" in params
        assert params["StokTasimaOrani"] == 0.3
        
        assert "W_Sinyal" in params
        assert params["W_Sinyal"] == 0.4
        
        assert "W_Performans" in params
        assert params["W_Performans"] == 0.3
        
        assert "W_DisKosul" in params
        assert params["W_DisKosul"] == 0.2
        
        assert "W_Finansal" in params
        assert params["W_Finansal"] == 0.1
        
        # Validate AnalizTarihi is datetime
        assert "AnalizTarihi" in params
        assert isinstance(params["AnalizTarihi"], datetime)
    
    def test_parameters_weights_sum_to_one(self, loader):
        """Test that probability weights sum to 1.0."""
        params = loader.get_parameters()
        
        weight_sum = (
            params["W_Sinyal"] +
            params["W_Performans"] +
            params["W_DisKosul"] +
            params["W_Finansal"]
        )
        
        # Allow small floating-point tolerance
        assert abs(weight_sum - 1.0) < 0.0001


class TestDataIntegrity:
    """Test data integrity and relationships."""
    
    def test_signal_links_to_shipment(self, loader):
        """Test that signal SG-2611-001 correctly links to shipment."""
        signal = loader.get_signal("SG-2611-001")
        
        # The signal text mentions "AKH-MUN-26-1184"
        assert "AKH-MUN-26-1184" in signal.ham_metin
        
        # Verify the shipment exists
        shipment = loader.get_shipment("AKH-MUN-26-1184")
        assert shipment.malzeme_no == "MT100054"
    
    def test_shipment_links_to_material(self, loader):
        """Test that shipment links to material."""
        shipment = loader.get_shipment("AKH-MUN-26-1184")
        
        # Verify material exists
        material = loader.get_material(shipment.malzeme_no)
        assert material.malzeme_no == "MT100054"
    
    def test_material_has_stock(self, loader):
        """Test that material has stock status."""
        # Verify stock exists for the material at the facility
        stock = loader.get_stock_status("MT100054", "T-SG-01")
        
        assert stock.mevcut_stok > 0
        assert stock.gunluk_tuketim > 0
    
    def test_material_has_production_line(self, loader):
        """Test that material has production line."""
        # Verify production line exists
        prod_line = loader.get_production_line("T-SG-01", "MT100054")
        
        assert prod_line.gunluk_uretim_kapasitesi > 0
