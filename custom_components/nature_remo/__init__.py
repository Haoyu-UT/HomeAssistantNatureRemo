"""The nature_remo integration."""
from __future__ import annotations

from functools import partial
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er

from .api import RemoAPI
from .config_flow import ConfigFlow
from .const import (
    CONF_LIGHTS,
    CONF_POLLING_INTERVAL_POWER_METER,
    CONF_POLLING_INTERVAL_SENSOR,
    CONF_TOKEN,
    DOMAIN,
    Appliances,
    NetworkError,
)
from .coordinator import ApplianceCoordinator, SensorCoordinator

_LOGGER = logging.getLogger(__name__)
# List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.LIGHT, Platform.SELECT, Platform.SENSOR]
SUBPLATFORMS: list[Platform] = [Platform.BUTTON, Platform.CLIMATE]
# Platforms whose unique_id used to start with the appliance's nickname.
NICKNAMED_UNIQUE_ID_PLATFORMS = {Platform.LIGHT, Platform.CLIMATE}


def migrated_unique_id(domain: str, unique_id: str) -> str | None:
    """The unique_id an entity should have now, or None if it needs no change.

    Lights ("<nickname> @ <id>") and air conditioners ("<nickname> @ <Remo
    name> @ <id>") once had names in their unique_id, so renaming the appliance
    in the Nature Remo app turned it into a new entity. They are now identified
    by the appliance id alone.
    """
    if domain not in NICKNAMED_UNIQUE_ID_PLATFORMS or " @ " not in unique_id:
        return None
    # The names are free text and may themselves contain " @ "; the id cannot.
    return unique_id.rpartition(" @ ")[2]


def current_old_unique_ids(appliances: Appliances) -> set[str]:
    """The old-style unique_ids the appliances would have been given today."""
    return {f"{light.nickname} @ {light.id}" for light in appliances.light} | {
        f"{ac.nickname} @ {ac.device.name} @ {ac.id}"
        for ac in appliances.ac
        if ac.device is not None
    }


async def async_migrate_unique_ids(
    hass: HomeAssistant, entry: ConfigEntry, appliances: Appliances
) -> None:
    """Rewrite old unique_ids in the entity registry so entities keep their history."""
    registry = er.async_get(hass)
    current = current_old_unique_ids(appliances)

    def update_unique_id(
        entity_entry: er.RegistryEntry, *, current_only: bool
    ) -> dict[str, str] | None:
        new_unique_id = migrated_unique_id(entity_entry.domain, entity_entry.unique_id)
        if new_unique_id is None:
            return None
        if current_only and entity_entry.unique_id not in current:
            return None
        if existing := registry.async_get_entity_id(
            entity_entry.domain, DOMAIN, new_unique_id
        ):
            # Renaming an appliance before this fix left an orphaned entity
            # behind. The one matching the appliance's name today is migrated
            # first and keeps the id; the orphan is left for the user to delete.
            _LOGGER.warning(
                "Not migrating %s to unique_id %s, already used by %s",
                entity_entry.entity_id,
                new_unique_id,
                existing,
            )
            return None
        _LOGGER.info(
            "Migrating %s from unique_id %s to %s",
            entity_entry.entity_id,
            entity_entry.unique_id,
            new_unique_id,
        )
        return {"new_unique_id": new_unique_id}

    for current_only in (True, False):
        await er.async_migrate_entries(
            hass,
            entry.entry_id,
            callback(partial(update_unique_id, current_only=current_only)),
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up nature_remo from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    api = RemoAPI(entry.data[CONF_TOKEN])
    try:
        appliances = await api.fetch_grouped_appliances()
    except NetworkError as e:
        _LOGGER.exception("Setup failed due to network error")
        raise ConfigEntryNotReady from e
    await async_migrate_unique_ids(hass, entry, appliances)
    polling_interval_sensor = entry.data[CONF_POLLING_INTERVAL_SENSOR]
    polling_interval_power_meter = entry.data[CONF_POLLING_INTERVAL_POWER_METER]
    # Built here, not in a platform: the platforms are set up concurrently, so
    # one cannot rely on a coordinator another has built.
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "appliances": appliances,
        "polling_interval_sensor": polling_interval_sensor,
        "polling_interval_power_meter": polling_interval_power_meter,
        "sensor_coordinator": SensorCoordinator(hass, api, polling_interval_sensor),
        "appliance_coordinator": ApplianceCoordinator(
            hass, api, polling_interval_power_meter
        ),
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
            new_data.update(
                {
                    CONF_POLLING_INTERVAL_SENSOR: 60,
                    CONF_POLLING_INTERVAL_POWER_METER: 60,
                }
            )
        # Entries made before the setup flow asked about light buttons carry no
        # choice; the light platform falls back to detecting the buttons.
        new_data.setdefault(CONF_LIGHTS, {})
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
