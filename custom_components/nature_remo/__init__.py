"""The nature_remo integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import RemoAPI
from .const import DOMAIN

# List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SELECT, Platform.LIGHT]
SUBPLATFORMS: list[Platform] = [Platform.BUTTON, Platform.CLIMATE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up nature_remo from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    api = RemoAPI(entry.data["token"])
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "appliances": await api.fetch_appliance(),
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await hass.config_entries.async_forward_entry_setups(entry, SUBPLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        entry, SUBPLATFORMS
    ) and await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
