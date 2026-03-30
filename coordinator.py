"""Coordonator pentru actualizarea datelor."""

import asyncio
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .api import HidroelectricaApiClient

_LOGGER = logging.getLogger(__name__)


class HidroelectricaCoordinator(DataUpdateCoordinator):
    """Coordonator pentru gestionarea datelor API."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: HidroelectricaApiClient,
        uan: str,
        update_interval: int,
    ):
        """Inițializează coordinatorul."""
        self.client = client
        self.uan = uan
        self.is_prosumer = False
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{uan}",
            update_interval=timedelta(seconds=update_interval),
        )
        
        self._refresh_counter = 0

    async def _async_update_data(self):
        """Actualizează datele de la API."""
        self._refresh_counter += 1
        
        try:
            tasks = [
                self.hass.async_add_executor_job(self.client.get_multi_meter, self.uan),
                self.hass.async_add_executor_job(self.client.get_bill, self.uan),
                self.hass.async_add_executor_job(self.client.get_previous_meter_read, self.uan),
            ]
            
            heavy_tasks = []
            if self._refresh_counter % 4 == 1 or self._refresh_counter == 1:
                heavy_tasks = [
                    self.hass.async_add_executor_job(self.client.get_meter_read_history, self.uan, None),
                    self.hass.async_add_executor_job(self.client.get_usage_generation, self.uan, None),
                    self.hass.async_add_executor_job(self.client.get_billing_history, self.uan, None),
                ]
            
            if not self.is_prosumer:
                tasks.append(
                    self.hass.async_add_executor_job(self.client.get_window_dates, self.uan)
                )
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            data = {
                "multi_meter": results[0] if not isinstance(results[0], Exception) else {},
                "bill": results[1] if not isinstance(results[1], Exception) else {},
                "previous_meter_read": results[2] if not isinstance(results[2], Exception) else {},
            }
            
            if len(results) > 3 and not self.is_prosumer:
                data["window_dates"] = results[3] if not isinstance(results[3], Exception) else {}
            
            if heavy_tasks:
                heavy_results = await asyncio.gather(*heavy_tasks, return_exceptions=True)
                
                data["meter_read_history"] = heavy_results[0] if not isinstance(heavy_results[0], Exception) else {}
                data["usage_generation"] = heavy_results[1] if not isinstance(heavy_results[1], Exception) else {}
                data["billing_history"] = heavy_results[2] if not isinstance(heavy_results[2], Exception) else {}
                
                if "meter_read_history" in data and data["meter_read_history"]:
                    reads = data["meter_read_history"].get("reads", [])
                    self.is_prosumer = any(read.get("register") == "1.8.0_P" for read in reads)
            
            return data
            
        except Exception as e:
            _LOGGER.error("Eroare la actualizarea datelor: %s", e)
            raise UpdateFailed(f"Eroare la actualizare: {e}") from e