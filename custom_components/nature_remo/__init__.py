"""The nature_remo integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import RemoAPI
from .config_flow import ConfigFlow
from .const import (
    CONF_POLLING_INTERVAL_POWER_METER,
    CONF_POLLING_INTERVAL_SENSOR,
    CONF_TOKEN,
    DOMAIN,
    NetworkError,
)

_LOGGER = logging.getLogger(__name__)
# List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.LIGHT, Platform.SELECT, Platform.SENSOR]
SUBPLATFORMS: list[Platform] = [Platform.BUTTON, Platform.CLIMATE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up nature_remo from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    api = RemoAPI(entry.data[CONF_TOKEN])
    try:
        hass.data[DOMAIN][entry.entry_id] = {
            "api": api,
            "appliances": await api.fetch_grouped_appliances(),
            "polling_interval_sensor": entry.data[CONF_POLLING_INTERVAL_SENSOR],
            "polling_interval_power_meter": entry.data[
                CONF_POLLING_INTERVAL_POWER_METER
            ],
        }
    except NetworkError as e:
        _LOGGER.exception("Setup failed due to network error")
        raise ConfigEntryNotReady from e
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


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.info(
        "Current config entry version is %s.%s",
        config_entry.version,
        config_entry.minor_version,
    )
    _LOGGER.info("Current config entry contains data %s", config_entry.data)

    if (
        ConfigFlow.VERSION > config_entry.version
        or ConfigFlow.MINOR_VERSION > config_entry.minor_version
    ):
        # Migration required
        new_data = config_entry.data.copy()
        if config_entry.version == 1:
            #
            new_data.update(
                {
                    CONF_POLLING_INTERVAL_SENSOR: 60,
                    CONF_POLLING_INTERVAL_POWER_METER: 60,
                }
            )
        hass.config_entries.async_update_entry(
            config_entry,
            data=new_data,
            minor_version=ConfigFlow.MINOR_VERSION,
            version=ConfigFlow.VERSION,
        )

    _LOGGER.info(
        "Migrated config entry to version %s.%s",
        config_entry.version,
        config_entry.minor_version,
    )

    return True
