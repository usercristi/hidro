"""Inițializarea integrării Hidroelectrica."""

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .api import HidroelectricaApiClient
from .coordinator import HidroelectricaCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BUTTON]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configurează integrarea dintr-o intrare de configurare."""
    
    # Inițializează clientul API
    client = HidroelectricaApiClient(
        entry.data["username"],
        entry.data["password"],
    )
    
    # Verifică autentificarea
    try:
        await hass.async_add_executor_job(client.get_accounts)
    except Exception as e:
        _LOGGER.error("Eroare la conectare: %s", e)
        raise ConfigEntryNotReady from e
    
    # Creează coordinatorul
    coordinator = HidroelectricaCoordinator(
        hass,
        client,
        entry.data["uan"],
        entry.data["scan_interval"],
    )
    
    # Rulează prima actualizare
    await coordinator.async_config_entry_first_refresh()
    
    # Salvează datele în hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }
    
    # Configurează platformele
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descarcă integrarea."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok