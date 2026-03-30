"""Buton pentru trimitere autocitire."""

import logging
from typing import Optional

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HidroelectricaCoordinator
from .api import HidroelectricaApiClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Configurează butonul pentru o intrare de configurare."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    client = hass.data[DOMAIN][entry.entry_id]["client"]
    uan = entry.data["uan"]
    
    if not coordinator.is_prosumer:
        async_add_entities([HidroelectricaSubmitReadingButton(coordinator, client, uan)])


class HidroelectricaSubmitReadingButton(CoordinatorEntity, ButtonEntity):
    """Buton pentru trimiterea autocitririi."""

    def __init__(
        self,
        coordinator: HidroelectricaCoordinator,
        client: HidroelectricaApiClient,
        uan: str,
    ):
        """Inițializează butonul."""
        super().__init__(coordinator)
        self._client = client
        self._uan = uan
        self._attr_name = f"Hidroelectrica {uan} Trimite Index"
        self._attr_unique_id = f"{DOMAIN}_{uan}_submit_reading"
        self._attr_icon = "mdi:counter"

    @property
    def available(self) -> bool:
        """Butonul este disponibil doar când fereastra de citire este activă."""
        if not super().available:
            return False
        
        window = self.coordinator.data.get("window_dates", {})
        start_date = window.get("start_date")
        end_date = window.get("end_date")
        
        if not start_date or not end_date:
            return False
        
        from datetime import datetime
        today = datetime.now().date()
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        return start <= today <= end

    async def async_press(self) -> None:
        """Trimite autocitirea."""
        prev_read = self.coordinator.data.get("previous_meter_read", {})
        current_index = prev_read.get("index")
        
        if current_index is None:
            _LOGGER.error("Nu s-a putut obține indexul curent pentru autocitire")
            return
        
        result = await self.hass.async_add_executor_job(
            self._client.submit_self_read,
            self._uan,
            current_index
        )
        
        if result:
            _LOGGER.info("Autocitire trimisă cu succes pentru %s: %s kWh", self._uan, current_index)
        else:
            _LOGGER.error("Eroare la trimiterea autocitririi pentru %s", self._uan)