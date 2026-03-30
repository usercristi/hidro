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
            except Exception as e:
                _LOGGER.exception("Eroare neașteptată: %s", e)
                errors["base"] = "unknown"
        
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_select_account(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Selectează contul (UAN) de monitorizat."""
        if user_input is not None:
            self._selected_uan = user_input["uan"]
            return await self.async_step_options()
        
        account_options = {
            acc["uan"]: f"{acc['uan']} - {acc.get('name', 'Necunoscut')}"
            for acc in self._accounts
        }
        
        return self.async_show_form(
            step_id="select_account",
            data_schema=vol.Schema(
                {
                    vol.Required("uan"): vol.In(account_options),
                }
            ),
        )

    async def async_step_options(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Configurare opțiuni: interval de actualizare."""
        if user_input is not None:
            return self.async_create_entry(
                title=f"Hidroelectrica {self._selected_uan}",
                data={
                    "username": self._username,
                    "uan": self._selected_uan,
                    "scan_interval": user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL),
                },
            )
        
        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema(
                {
                    vol.Optional("scan_interval", default=DEFAULT_SCAN_INTERVAL): vol.All(
                        vol.Coerce(int),
                        vol.Clamp(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
                    ),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Returnează opțiunile flow-ului."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Opțiuni pentru integrare."""

    def __init__(self, config_entry):
        """Inițializează opțiunile."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Gestionează opțiunile."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "scan_interval",
                        default=self.config_entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Clamp(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
                    ),
                }
            ),
        )


class InvalidAuth(HomeAssistantError):
    """Eroare la autentificare."""