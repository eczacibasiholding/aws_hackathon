"""
DataLoader for NEXUS Supply Chain Risk Agent.

Loads data/NEXUS_Agent_Veri_Seti_TEKNIK.xlsx once at startup and provides
typed accessor methods for all required sheets.

Usage:
    loader = DataLoader()
    signal = loader.get_signal("SG-2611-001")
    shipment = loader.get_shipment("AKH-MUN-26-1184")
    params = loader.get_parameters()
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from nexus.models import (
    CarrierRow,
    CustomerOrderRow,
    FacilityRow,
    MaterialRow,
    OpenOrderRow,
    ParametersRow,
    ProductionLineRow,
    RouteOptionRow,
    ShipmentRow,
    SignalRow,
    StockRow,
    SupplierRow,
    SupplySourceRow,
)

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Loads and provides typed access to NEXUS Excel data.
    
    All data is loaded once at initialization. Accessor methods return
    Pydantic models with proper type validation.
    
    Raises:
        FileNotFoundError: If Excel file is missing
        KeyError: If required sheet is missing
        KeyError: If lookup fails (e.g., signal_id not found)
    """
    
    REQUIRED_SHEETS = [
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
    
    def __init__(self, excel_path: Optional[str] = None):
        """
        Initialize DataLoader and load all sheets.
        
        Args:
            excel_path: Path to Excel file. Defaults to data/NEXUS_Agent_Veri_Seti_TEKNIK.xlsx
            
        Raises:
            FileNotFoundError: If Excel file doesn't exist
            KeyError: If required sheet is missing
        """
        if excel_path is None:
            # Default path relative to project root
            excel_path = Path(__file__).parent.parent.parent / "data" / "NEXUS_Agent_Veri_Seti_TEKNIK.xlsx"
        
        self.excel_path = Path(excel_path)
        
        if not self.excel_path.exists():
            raise FileNotFoundError(f"Excel file not found: {self.excel_path}")
        
        logger.info(f"Loading data from {self.excel_path}")
        
        # Load all sheets into DataFrames
        self._sheets: Dict[str, pd.DataFrame] = {}
        self._load_all_sheets()
        
        # Build indexes for fast lookup
        self._build_indexes()
        
        logger.info("DataLoader initialized successfully")
    
    def _load_all_sheets(self) -> None:
        """Load all required sheets from Excel."""
        excel_file = pd.ExcelFile(self.excel_path)
        
        for sheet_name in self.REQUIRED_SHEETS:
            if sheet_name not in excel_file.sheet_names:
                raise KeyError(f"Required sheet '{sheet_name}' not found in Excel file")
            
            # Load sheet with header in row 0
            df = pd.read_excel(excel_file, sheet_name=sheet_name, header=0)
            self._sheets[sheet_name] = df
            logger.debug(f"Loaded sheet '{sheet_name}' with {len(df)} rows")
    
    def _build_indexes(self) -> None:
        """Build indexes for fast lookup by primary keys."""
        # Index signals by Sinyal No
        self._signals_by_id: Dict[str, int] = {}
        if "Risk_Sinyalleri" in self._sheets:
            df = self._sheets["Risk_Sinyalleri"]
            for idx, row in df.iterrows():
                signal_id = row["Sinyal No"]
                self._signals_by_id[signal_id] = idx
        
        # Index shipments by Sevkiyat No
        self._shipments_by_id: Dict[str, int] = {}
        if "Sevkiyatlar" in self._sheets:
            df = self._sheets["Sevkiyatlar"]
            for idx, row in df.iterrows():
                shipment_id = row["Sevkiyat No"]
                self._shipments_by_id[shipment_id] = idx
        
        # Index materials by Malzeme No
        self._materials_by_no: Dict[str, int] = {}
        if "Malzemeler" in self._sheets:
            df = self._sheets["Malzemeler"]
            for idx, row in df.iterrows():
                material_no = row["Malzeme No"]
                self._materials_by_no[material_no] = idx
        
        # Index suppliers by Tedarikçi Kodu
        self._suppliers_by_code: Dict[str, int] = {}
        if "Tedarikciler" in self._sheets:
            df = self._sheets["Tedarikciler"]
            for idx, row in df.iterrows():
                supplier_code = row["Tedarikçi Kodu"]
                self._suppliers_by_code[supplier_code] = idx
        
        # Index carriers by Taşıyıcı No
        self._carriers_by_no: Dict[str, int] = {}
        if "Tasiyicilar" in self._sheets:
            df = self._sheets["Tasiyicilar"]
            for idx, row in df.iterrows():
                carrier_no = row["Taşıyıcı No"]
                self._carriers_by_no[carrier_no] = idx
        
        # Index facilities by Tesis Kodu
        self._facilities_by_code: Dict[str, int] = {}
        if "Tesisler" in self._sheets:
            df = self._sheets["Tesisler"]
            for idx, row in df.iterrows():
                facility_code = row["Tesis Kodu"]
                self._facilities_by_code[facility_code] = idx
        
        # Index stock by composite key (Tesis Kodu|Malzeme No)
        self._stock_by_key: Dict[str, int] = {}
        if "Stok_Durumu" in self._sheets:
            df = self._sheets["Stok_Durumu"]
            for idx, row in df.iterrows():
                # Build composite key
                facility_code = row["Tesis Kodu"]
                material_no = row["Malzeme No"]
                key = f"{facility_code}|{material_no}"
                self._stock_by_key[key] = idx
        
        # Index production lines by composite key (Tesis Kodu|Malzeme No)
        self._production_lines_by_key: Dict[str, int] = {}
        if "Uretim_Hatlari" in self._sheets:
            df = self._sheets["Uretim_Hatlari"]
            for idx, row in df.iterrows():
                facility_code = row["Tesis Kodu"]
                material_no = row["Malzeme No"]
                key = f"{facility_code}|{material_no}"
                self._production_lines_by_key[key] = idx
        
        logger.debug("Built indexes for all primary keys")
    
    # =========================================================================
    # Signal Accessors
    # =========================================================================
    
    def get_signal(self, signal_id: str) -> SignalRow:
        """
        Get signal by ID.
        
        Args:
            signal_id: Signal identifier (e.g., "SG-2611-001")
            
        Returns:
            SignalRow with parsed data
            
        Raises:
            KeyError: If signal_id not found
        """
        if signal_id not in self._signals_by_id:
            raise KeyError(f"Signal ID '{signal_id}' not found")
        
        idx = self._signals_by_id[signal_id]
        row = self._sheets["Risk_Sinyalleri"].iloc[idx]
        
        return SignalRow(
            **{
                "Sinyal No": row["Sinyal No"],
                "Yayın Zamanı": row["Yayın Zamanı"],
                "Tespit Zamanı": row["Tespit Zamanı"],
                "Kaynak Kodu": row["Kaynak Kodu"],
                "Kaynak Adı": row["Kaynak Adı"],
                "Kategori": row["Kategori"],
                "Dil": row["Dil"],
                "Ham Metin (LLM Girdisi)": row["Ham Metin (LLM Girdisi)"],
                "Kaynak Taban Güvenilirlik": int(row["Kaynak Taban Güvenilirlik"]),
                "Doğrulandı mı?": row["Doğrulandı mı?"],
                "Durum": row["Durum"],
            }
        )
    
    def get_all_signal_ids(self) -> List[str]:
        """
        Get list of all signal IDs.
        
        Returns:
            List of signal IDs
        """
        return list(self._signals_by_id.keys())
    
    def list_signals(self) -> List[SignalRow]:
        """
        Get all signals.
        
        Returns:
            List of all SignalRow objects
        """
        return [self.get_signal(signal_id) for signal_id in self._signals_by_id.keys()]
    
    # =========================================================================
    # Shipment Accessors
    # =========================================================================
    
    def get_shipment(self, shipment_id: str) -> ShipmentRow:
        """
        Get shipment by ID.
        
        Args:
            shipment_id: Shipment identifier (e.g., "AKH-MUN-26-1184")
            
        Returns:
            ShipmentRow with parsed data
            
        Raises:
            KeyError: If shipment_id not found
        """
        if shipment_id not in self._shipments_by_id:
            raise KeyError(f"Shipment ID '{shipment_id}' not found")
        
        idx = self._shipments_by_id[shipment_id]
        row = self._sheets["Sevkiyatlar"].iloc[idx]
        
        return ShipmentRow(
            **{
                "Sevkiyat No": row["Sevkiyat No"],
                "Takip No": row.get("Takip No"),
                "PO No": row["PO No"],
                "Malzeme No": row["Malzeme No"],
                "Miktar": float(row["Miktar"]),
                "Sevkiyat Tarihi": pd.to_datetime(row["Sevkiyat Tarihi"]).date(),
                "ETA": pd.to_datetime(row["ETA"]).date(),
                "Gemi Adı": row.get("Gemi Adı"),
                "Rotakod": row.get("Rotakod"),
                "Taşıyıcı No": row["Taşıyıcı No"],
                "Açıklama": row.get("Açıklama"),
            }
        )
    
    # =========================================================================
    # Material Accessors
    # =========================================================================
    
    def get_material(self, material_no: str) -> MaterialRow:
        """
        Get material by number.
        
        Args:
            material_no: Material code (e.g., "MT100054")
            
        Returns:
            MaterialRow with parsed data
            
        Raises:
            KeyError: If material_no not found
        """
        if material_no not in self._materials_by_no:
            raise KeyError(f"Material number '{material_no}' not found")
        
        idx = self._materials_by_no[material_no]
        row = self._sheets["Malzemeler"].iloc[idx]
        
        return MaterialRow(
            **{
                "Malzeme No": row["Malzeme No"],
                "Malzeme Adı": row["Malzeme Adı"],
                "Kategori": row["Kategori"],
                "Birim": row["Birim"],
                "Birim Maliyet": float(row["Birim Maliyet"]),
                "Kritiklik": row["Kritiklik"],
                "MOQ": float(row["MOQ"]) if pd.notna(row.get("MOQ")) else None,
            }
        )
    
    # =========================================================================
    # Supplier Accessors
    # =========================================================================
    
    def get_supplier(self, supplier_code: str) -> SupplierRow:
        """
        Get supplier by code.
        
        Args:
            supplier_code: Supplier code (e.g., "TD5011")
            
        Returns:
            SupplierRow with parsed data
            
        Raises:
            KeyError: If supplier_code not found
        """
        if supplier_code not in self._suppliers_by_code:
            raise KeyError(f"Supplier code '{supplier_code}' not found")
        
        idx = self._suppliers_by_code[supplier_code]
        row = self._sheets["Tedarikciler"].iloc[idx]
        
        return SupplierRow(
            **{
                "Tedarikçi Kodu": row["Tedarikçi Kodu"],
                "Tedarikçi Adı": row["Tedarikçi Adı"],
                "Ülke": row["Ülke"],
                "OTIF Performansı": float(row["OTIF Performansı"]),
                "Finansal Sağlık": int(row["Finansal Sağlık"]),
                "Kapasite (kg/ay)": float(row["Kapasite (kg/ay)"]) if pd.notna(row.get("Kapasite (kg/ay)")) else None,
            }
        )
    
    def get_supply_source(self, material_no: str, supplier_code: str) -> SupplySourceRow:
        """
        Get supply source for material-supplier combination.
        
        Args:
            material_no: Material code
            supplier_code: Supplier code
            
        Returns:
            SupplySourceRow with parsed data
            
        Raises:
            KeyError: If combination not found
        """
        df = self._sheets["Tedarik_Kaynaklari"]
        
        # Filter by material and supplier
        mask = (df["Malzeme No"] == material_no) & (df["Tedarikçi Kodu"] == supplier_code)
        matches = df[mask]
        
        if len(matches) == 0:
            raise KeyError(f"Supply source not found for material '{material_no}' and supplier '{supplier_code}'")
        
        # Return first match (there should only be one)
        row = matches.iloc[0]
        
        return SupplySourceRow(
            **{
                "Kaynak No": row["Kaynak No"],
                "Malzeme No": row["Malzeme No"],
                "Tedarikçi Kodu": row["Tedarikçi Kodu"],
                "Tesis Kodu": row["Tesis Kodu"],
                "Tedarik Süresi (gün)": int(row["Tedarik Süresi (gün)"]),
                "Birim Maliyet": float(row["Birim Maliyet"]),
                "MOQ": float(row["MOQ"]) if pd.notna(row.get("MOQ")) else None,
                "Kalifikasyon": row["Kalifikasyon"],
                "Mevcut Stok (kg)": float(row["Mevcut Stok (kg)"]) if pd.notna(row.get("Mevcut Stok (kg)")) else None,
            }
        )
    
    # =========================================================================
    # Carrier & Facility Accessors
    # =========================================================================
    
    def get_carrier(self, carrier_code: str) -> CarrierRow:
        """
        Get carrier by code.
        
        Args:
            carrier_code: Carrier code (e.g., "TS01")
            
        Returns:
            CarrierRow with parsed data
            
        Raises:
            KeyError: If carrier_code not found
        """
        if carrier_code not in self._carriers_by_no:
            raise KeyError(f"Carrier code '{carrier_code}' not found")
        
        idx = self._carriers_by_no[carrier_code]
        row = self._sheets["Tasiyicilar"].iloc[idx]
        
        return CarrierRow(
            **{
                "Taşıyıcı No": row["Taşıyıcı No"],
                "Taşıyıcı Adı": row["Taşıyıcı Adı"],
                "Taşıma Türü": row["Taşıma Türü"],
                "Zamanında Ulaşım Oranı": float(row["Zamanında Ulaşım Oranı"]),
                "Finansal Sağlık": int(row["Finansal Sağlık"]),
            }
        )
    
    def get_facility(self, facility_code: str) -> FacilityRow:
        """
        Get facility by code.
        
        Args:
            facility_code: Facility code (e.g., "T-SG-01")
            
        Returns:
            FacilityRow with parsed data
            
        Raises:
            KeyError: If facility_code not found
        """
        if facility_code not in self._facilities_by_code:
            raise KeyError(f"Facility code '{facility_code}' not found")
        
        idx = self._facilities_by_code[facility_code]
        row = self._sheets["Tesisler"].iloc[idx]
        
        return FacilityRow(
            **{
                "Tesis Kodu": row["Tesis Kodu"],
                "Tesis Adı": row["Tesis Adı"],
                "Şehir": row["Şehir"],
                "Ülke": row["Ülke"],
                "Tesis Tipi": row["Tesis Tipi"],
            }
        )
    
    # =========================================================================
    # Stock & Production Accessors
    # =========================================================================
    
    def get_stock_status(self, material_no: str, facility_code: str) -> StockRow:
        """
        Get stock status for material at facility.
        
        Args:
            material_no: Material code
            facility_code: Facility code
            
        Returns:
            StockRow with parsed data
            
        Raises:
            KeyError: If combination not found
        """
        key = f"{facility_code}|{material_no}"
        
        if key not in self._stock_by_key:
            raise KeyError(f"Stock not found for material '{material_no}' at facility '{facility_code}'")
        
        idx = self._stock_by_key[key]
        row = self._sheets["Stok_Durumu"].iloc[idx]
        
        return StockRow(
            **{
                "Stok Anahtarı": row["Stok Anahtarı"],
                "Malzeme No": row["Malzeme No"],
                "Tesis Kodu": row["Tesis Kodu"],
                "Mevcut Stok": float(row["Mevcut Stok"]),
                "Günlük Tüketim": float(row["Günlük Tüketim"]),
                "Emniyet Stoku": float(row["Emniyet Stoku"]),
                "Mevcut Stoğun Günlük Tüketim Üzerinden Süresi": float(row["Mevcut Stoğun Günlük Tüketim Üzerinden Süresi"]) if pd.notna(row.get("Mevcut Stoğun Günlük Tüketim Üzerinden Süresi")) else None,
            }
        )
    
    def get_production_line(self, facility_code: str, material_no: str) -> ProductionLineRow:
        """
        Get production line for facility-material combination.
        
        Args:
            facility_code: Facility code
            material_no: Material code
            
        Returns:
            ProductionLineRow with parsed data
            
        Raises:
            KeyError: If combination not found
        """
        key = f"{facility_code}|{material_no}"
        
        if key not in self._production_lines_by_key:
            raise KeyError(f"Production line not found for material '{material_no}' at facility '{facility_code}'")
        
        idx = self._production_lines_by_key[key]
        row = self._sheets["Uretim_Hatlari"].iloc[idx]
        
        return ProductionLineRow(
            **{
                "Tesis Kodu": row["Tesis Kodu"],
                "Tesis Adı": row["Tesis Adı"],
                "Malzeme No": row["Malzeme No"],
                "Üretim Hattı": row["Üretim Hattı"],
                "Günlük Üretim Kapasitesi": float(row["Günlük Üretim Kapasitesi"]),
                "Duruş Riski": row["Duruş Riski"],
                "Günlük Duruşma Maliyeti": float(row["Günlük Duruşma Maliyeti"]) if pd.notna(row.get("Günlük Duruşma Maliyeti")) else None,
                "Yeniden Başlama Maliyeti": float(row["Yeniden Başlama Maliyeti"]) if pd.notna(row.get("Yeniden Başlama Maliyeti")) else None,
            }
        )
    
    # =========================================================================
    # Order Accessors
    # =========================================================================
    
    def get_customer_orders(self, material_no: str) -> List[CustomerOrderRow]:
        """
        Get all customer orders for a material.
        
        Args:
            material_no: Material code
            
        Returns:
            List of CustomerOrderRow objects (may be empty)
        """
        df = self._sheets["Musteri_Siparisleri"]
        
        # Filter by material
        mask = df["Malzeme No"] == material_no
        matches = df[mask]
        
        result = []
        for _, row in matches.iterrows():
            result.append(
                CustomerOrderRow(
                    **{
                        "Sipariş No": row["Sipariş No"],
                        "Müşteri Kodu": row["Müşteri Kodu"],
                        "Malzeme No": row["Malzeme No"],
                        "Miktar": float(row["Miktar"]),
                        "Teslimat Tarihi": pd.to_datetime(row["Teslimat Tarihi"]).date(),
                        "Öncelik": row["Öncelik"],
                        "Gecikme Ceza Oranı": float(row["Gecikme Ceza Oranı"]) if pd.notna(row.get("Gecikme Ceza Oranı")) else None,
                    }
                )
            )
        
        return result
    
    def get_open_orders(self, material_no: str) -> List[OpenOrderRow]:
        """
        Get all open purchase orders for a material.
        
        Args:
            material_no: Material code
            
        Returns:
            List of OpenOrderRow objects (may be empty)
        """
        df = self._sheets["Acik_Siparisler"]
        
        # Filter by material
        mask = df["Malzeme No"] == material_no
        matches = df[mask]
        
        result = []
        for _, row in matches.iterrows():
            result.append(
                OpenOrderRow(
                    **{
                        "PO No": row["PO No"],
                        "Malzeme No": row["Malzeme No"],
                        "Tedarikçi Kodu": row["Tedarikçi Kodu"],
                        "Tesis Kodu": row["Tesis Kodu"],
                        "Sipariş Tarihi": pd.to_datetime(row["Sipariş Tarihi"]).date(),
                        "Miktar": float(row["Miktar"]),
                        "Teyit Tarihi": pd.to_datetime(row["Teyit Tarihi"]).date(),
                        "Birim Fiyat": float(row["Birim Fiyat"]),
                        "Toplam Tutar": float(row["Toplam Tutar"]),
                    }
                )
            )
        
        return result
    
    # =========================================================================
    # Route Accessors
    # =========================================================================
    
    def get_route_options(self, origin: str, destination: str) -> List[RouteOptionRow]:
        """
        Get all route options between origin and destination.
        
        Args:
            origin: Origin location
            destination: Destination location
            
        Returns:
            List of RouteOptionRow objects (may be empty)
        """
        df = self._sheets["Rota_Secenekleri"]
        
        # Filter by origin and destination
        mask = (df["Başlangıç"] == origin) & (df["Varış"] == destination)
        matches = df[mask]
        
        result = []
        for _, row in matches.iterrows():
            result.append(
                RouteOptionRow(
                    **{
                        "Rota Kodu": row["Rota Kodu"],
                        "Başlangıç": row["Başlangıç"],
                        "Varış": row["Varış"],
                        "Taşıma Türü": row["Taşıma Türü"],
                        "Süre (gün)": int(row["Süre (gün)"]),
                        "Maliyet ($/kg)": float(row["Maliyet ($/kg)"]),
                        "CO2 (kg/kg)": float(row["CO2 (kg/kg)"]),
                        "Kapasite Durum": row.get("Kapasite Durum"),
                    }
                )
            )
        
        return result
    
    # =========================================================================
    # Parameters Accessor
    # =========================================================================
    
    def get_parameters(self) -> Dict[str, float]:
        """
        Get all parameters as a dictionary.
        
        Returns:
            Dictionary mapping parameter name to value
            
        Note:
            AnalizTarihi is converted to datetime, all others are float
        """
        df = self._sheets["Parametreler"]
        
        params = {}
        for _, row in df.iterrows():
            param_name = row["Parametre"]
            param_value = row["Değer"]
            
            # Special handling for AnalizTarihi
            if param_name == "AnalizTarihi":
                params[param_name] = pd.to_datetime(param_value)
            else:
                params[param_name] = float(param_value)
        
        return params
