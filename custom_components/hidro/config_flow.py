"""Config flow pentru integrarea Hidroelectrica."""

import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, MIN_SCAN_INTERVAL, MAX_SCAN_INTERVAL
from .api import HidroelectricaApiClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict) -> dict:
    """Validează datele de intrare."""
    client = HidroelectricaApiClient(data["username"], data["password"])
    
    accounts = await hass.async_add_executor_job(client.get_accounts)
    
    if not accounts:
        raise InvalidAuth
    
    return {"title": data["username"], "accounts": accounts}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow pentru Hidroelectrica."""

    VERSION = 1

    def __init__(self) -> None:
        """Inițializează config flow-ul."""
        self._username = None
        self._accounts = None
        self._selected_uan = None

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Primul pas: autentificare."""
        errors = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                self._username = user_input["username"]
                self._accounts = info["accounts"]
                
                if len(self._accounts) == 1:
                    self._selected_uan = self._accounts[0]["uan"]
                    return await self.async_step_options()
                
                return await self.async_step_select_account()
                
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Eroare neașteptată")
                errors["base"] = "unknown"
        
        return self.async_show_form(
            step_id="user",
            data_schema=STEP