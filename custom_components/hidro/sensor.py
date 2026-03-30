"""Senzori pentru integrarea Hidroelectrica."""

from datetime import datetime
import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import (
    UnitOfEnergy,
    CURRENCY_EURO,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN
from .coordinator import HidroelectricaCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Configurează senzorii pentru o intrare de configurare."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    uan = entry.data["uan"]
    is_prosumer = coordinator.is_prosumer
    
    sensors = [
        HidroelectricaContractDataSensor(coordinator, uan),
        HidroelectricaCurrentBalanceSensor(coordinator, uan),
        HidroelectricaOutstandingBillSensor(coordinator, uan),
        HidroelectricaCurrentIndexSensor(coordinator, uan, is_prosumer),
    ]
    
    if is_prosumer:
        sensors.append(HidroelectricaProductionIndexSensor(coordinator, uan))
    else:
        sensors.append(HidroelectricaAllowedReadingSensor(coordinator, uan))
    
    current_year = datetime.now().year
    sensors.append(HidroelectricaConsumptionArchiveSensor(coordinator, uan, current_year))
    sensors.append(HidroelectricaIndexArchiveSensor(coordinator, uan, current_year))
    sensors.append(HidroelectricaPaymentsArchiveSensor(coordinator, uan, current_year))
    
    if is_prosumer:
        sensors.append(HidroelectricaProductionIndexArchiveSensor(coordinator, uan, current_year))
        sensors.append(HidroelectricaProsumerPaymentsArchiveSensor(coordinator, uan, current_year))
    
    async_add_entities(sensors)


class HidroelectricaBaseSensor(CoordinatorEntity, SensorEntity):
    """Clasă de bază pentru toți senzorii."""

    def __init__(self, coordinator: HidroelectricaCoordinator, uan: str, name: str, icon: str):
        """Inițializează senzorul de bază."""
        super().__init__(coordinator)
        self._uan = uan
        self._attr_name = f"Hidroelectrica {uan} {name}"
        self._attr_unique_id = f"{DOMAIN}_{uan}_{name.lower().replace(' ', '_')}"
        self._attr_icon = icon

    @property
    def available(self):
        """Senzorul este disponibil dacă coordinatorul are date."""
        return self.coordinator.data is not None


class HidroelectricaContractDataSensor(HidroelectricaBaseSensor):
    """Senzor pentru datele contractului."""

    def __init__(self, coordinator: HidroelectricaCoordinator, uan: str):
        super().__init__(coordinator, uan, "Date Contract", "mdi:file-document")
        self._attr_extra_state_attributes = {}

    @property
    def native_value(self):
        if not self.coordinator.data:
            return "Necunoscut"
        
        multi_meter = self.coordinator.data.get("multi_meter", {})
        contract_info = multi_meter.get("contract_info", {})
        
        name = contract_info.get("name", "")
        if name:
            return name
        
        return "Contract activ"

    @callback
    def _handle_coordinator_update(self):
        if not self.coordinator.data:
            return
        
        multi_meter = self.coordinator.data.get("multi_meter", {})
        contract_info = multi_meter.get("contract_info", {})
        
        self._attr_extra_state_attributes = {
            "uan": self._uan,
            "nume": contract_info.get("first_name", ""),
            "prenume": contract_info.get("last_name", ""),
            "telefon": contract_info.get("phone", ""),
            "nlc": contract_info.get("nlc", ""),
            "tip_client": contract_info.get("client_type", ""),
            "adresa": contract_info.get("address", ""),
            "localitate": contract_info.get("city", ""),
            "serie_contor": contract_info.get("meter_serial", ""),
        }
        
        super()._handle_coordinator_update()


class HidroelectricaCurrentBalanceSensor(HidroelectricaBaseSensor):
    """Senzor pentru soldul curent."""

    def __init__(self, coordinator: HidroelectricaCoordinator, uan: str):
        super().__init__(coordinator, uan, "Sold Factură", "mdi:currency-eur")
        self._attr_native_unit_of_measurement = CURRENCY_EURO
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        bill = self.coordinator.data.get("bill", {})
        return float(bill.get("amount_due", 0))

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        
        bill = self.coordinator.data.get("bill", {})
        return {
            "due_date": bill.get("due_date"),
            "bill_number": bill.get("bill_number"),
            "bill_date": bill.get("bill_date"),
        }


class HidroelectricaOutstandingBillSensor(HidroelectricaBaseSensor):
    """Senzor pentru facturi restante."""

    def __init__(self, coordinator: HidroelectricaCoordinator, uan: str):
        super().__init__(coordinator, uan, "Factură Restantă", "mdi:alert-circle")
        self._attr_extra_state_attributes = {}

    @property
    def native_value(self):
        if not self.coordinator.data:
            return "Necunoscut"
        
        bill = self.coordinator.data.get("bill", {})
        amount = float(bill.get("amount_due", 0))
        due_date = bill.get("due_date")
        
        if amount <= 0:
            return "Nu"
        
        if due_date:
            due = datetime.strptime(due_date, "%Y-%m-%d").date()
            if due < datetime.now().date():
                return "Da"
        
        return "Nu"

    @callback
    def _handle_coordinator_update(self):
        if not self.coordinator.data:
            return
        
        bill = self.coordinator.data.get("bill", {})
        amount = float(bill.get("amount_due", 0))
        due_date = bill.get("due_date")
        
        days_overdue = 0
        if due_date and amount > 0:
            due = datetime.strptime(due_date, "%Y-%m-%d").date()
            if due < datetime.now().date():
                days_overdue = (datetime.now().date() - due).days
        
        self._attr_extra_state_attributes = {
            "suma_restanta": amount,
            "zile_intarziere": days_overdue,
            "data_scadenta": due_date,
        }
        
        super()._handle_coordinator_update()


class HidroelectricaCurrentIndexSensor(HidroelectricaBaseSensor):
    """Senzor pentru indexul curent."""

    def __init__(self, coordinator: HidroelectricaCoordinator, uan: str, is_prosumer: bool = False):
        super().__init__(coordinator, uan, "Index Energie", "mdi:counter")
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._is_prosumer = is_prosumer

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        prev_read = self.coordinator.data.get("previous_meter_read", {})
        if self._is_prosumer:
            return prev_read.get("consumption_index")
        else:
            return prev_read.get("index")


class HidroelectricaProductionIndexSensor(HidroelectricaBaseSensor):
    """Senzor pentru indexul de producție (prosumator)."""

    def __init__(self, coordinator: HidroelectricaCoordinator, uan: str):
        super().__init__(coordinator, uan, "Index Energie Produsă", "mdi:solar-panel")
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        prev_read = self.coordinator.data.get("previous_meter_read", {})
        return prev_read.get("production_index")


class HidroelectricaAllowedReadingSensor(HidroelectricaBaseSensor):
    """Senzor pentru fereastra de autocitire."""

    def __init__(self, coordinator: HidroelectricaCoordinator, uan: str):
        super().__init__(coordinator, uan, "Citire Permisă", "mdi:calendar-check")
        self._attr_extra_state_attributes = {}

    @property
    def native_value(self):
        if not self.coordinator.data:
            return "Necunoscut"
        
        window = self.coordinator.data.get("window_dates", {})
        start_date = window.get("start_date")
        end_date = window.get("end_date")
        
        if not start_date or not end_date:
            return "Nu"
        
        today = datetime.now().date()
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        if start <= today <= end:
            return "Da"
        return "Nu"

    @callback
    def _handle_coordinator_update(self):
        if not self.coordinator.data:
            return
        
        window = self.coordinator.data.get("window_dates", {})
        self._attr_extra_state_attributes = {
            "data_inceput": window.get("start_date"),
            "data_sfarsit": window.get("end_date"),
        }
        
        super()._handle_coordinator_update()


class HidroelectricaConsumptionArchiveSensor(HidroelectricaBaseSensor):
    """Senzor pentru arhiva de consum lunar."""

    def __init__(self, coordinator: HidroelectricaCoordinator, uan: str, year: int):
        super().__init__(coordinator, uan, f"Arhivă Consum {year}", "mdi:chart-line")
        self._year = year
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_extra_state_attributes = {}

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        usage = self.coordinator.data.get("usage_generation", {})
        monthly = usage.get("monthly_usage", {})
        
        total = sum(monthly.values())
        return total

    @callback
    def _handle_coordinator_update(self):
        if not self.coordinator.data:
            return
        
        usage = self.coordinator.data.get("usage_generation", {})
        monthly = usage.get("monthly_usage", {})
        
        self._attr_extra_state_attributes = {
            "consum_lunar": monthly,
            "an": self._year,
        }
        
        super()._handle_coordinator_update()


class HidroelectricaIndexArchiveSensor(HidroelectricaBaseSensor):
    """Senzor pentru arhiva de citiri index."""

    def __init__(self, coordinator: HidroelectricaCoordinator, uan: str, year: int):
        super().__init__(coordinator, uan, f"Arhivă Index {year}", "mdi:history")
        self._year = year
        self._attr_extra_state_attributes = {}

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        history = self.coordinator.data.get("meter_read_history", {})
        reads = history.get("reads", [])
        
        consumption_reads = [r for r in reads if r.get("register") == "1.8.0"]
        
        return len(consumption_reads)

    @callback
    def _handle_coordinator_update(self):
        if not self.coordinator.data:
            return
        
        history = self.coordinator.data.get("meter_read_history", {})
        reads = history.get("reads", [])
        
        consumption_reads = [r for r in reads if r.get("register") == "1.8.0"]
        
        self._attr_extra_state_attributes = {
            "citiri": consumption_reads,
            "an": self._year,
        }
        
        super()._handle_coordinator_update()


class HidroelectricaPaymentsArchiveSensor(HidroelectricaBaseSensor):
    """Senzor pentru arhiva de plăți."""

    def __init__(self, coordinator: HidroelectricaCoordinator, uan: str, year: int):
        super().__init__(coordinator, uan, f"Arhivă Plăți {year}", "mdi:credit-card")
        self._year = year
        self._attr_native_unit_of_measurement = CURRENCY_EURO
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_extra_state_attributes = {}

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        history = self.coordinator.data.get("billing_history", {})
        payments = history.get("payments", [])
        
        normal_payments = [p for p in payments if not p.get("type", "").startswith("Comp ANRE")]
        
        total = sum(float(p.get("amount", 0)) for p in normal_payments)
        return total

    @callback
    def _handle_coordinator_update(self):
        if not self.coordinator.data:
            return
        
        history = self.coordinator.data.get("billing_history", {})
        payments = history.get("payments", [])
        
        normal_payments = [p for p in payments if not p.get("type", "").startswith("Comp ANRE")]
        
        self._attr_extra_state_attributes = {
            "plati": normal_payments,
            "numar_plati": len(normal_payments),
            "an": self._year,
        }
        
        super()._handle_coordinator_update()


class HidroelectricaProductionIndexArchiveSensor(HidroelectricaBaseSensor):
    """Senzor pentru arhiva de index producție (prosumator)."""

    def __init__(self, coordinator: HidroelectricaCoordinator, uan: str, year: int):
        super().__init__(coordinator, uan, f"Arhivă Index Producție {year}", "mdi:solar-panel")
        self._year = year
        self._attr_extra_state_attributes = {}

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        history = self.coordinator.data.get("meter_read_history", {})
        reads = history.get("reads", [])
        
        production_reads = [r for r in reads if r.get("register") == "1.8.0_P"]
        
        return len(production_reads)

    @callback
    def _handle_coordinator_update(self):
        if not self.coordinator.data:
            return
        
        history = self.coordinator.data.get("meter_read_history", {})
        reads = history.get("reads", [])
        
        production_reads = [r for r in reads if r.get("register") == "1.8.0_P"]
        
        self._attr_extra_state_attributes = {
            "citiri_productie": production_reads,
            "an": self._year,
        }
        
        super()._handle_coordinator_update()


class HidroelectricaProsumerPaymentsArchiveSensor(HidroelectricaBaseSensor):
    """Senzor pentru arhiva de compensații ANRE (prosumator)."""

    def __init__(self, coordinator: HidroelectricaCoordinator, uan: str, year: int):
        super().__init__(coordinator, uan, f"Compensații ANRE {year}", "mdi:currency-eur")
        self._year = year
        self._attr_native_unit_of_measurement = CURRENCY_EURO
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_extra_state_attributes = {}

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        history = self.coordinator.data.get("billing_history", {})
        payments = history.get("payments", [])
        
        compensations = [p for p in payments if p.get("type", "").startswith("Comp ANRE")]
        
        total = sum(float(p.get("amount", 0)) for p in compensations)
        return total

    @callback
    def _handle_coordinator_update(self):
        if not self.coordinator.data:
            return
        
        history = self.coordinator.data.get("billing_history", {})
        payments = history.get("payments", [])
        
        compensations = [p for p in payments if p.get("type", "").startswith("Comp ANRE")]
        
        self._attr_extra_state_attributes = {
            "compensatii": compensations,
            "numar_compensatii": len(compensations),
            "an": self._year,
        }
        
        super()._handle_coordinator_update()