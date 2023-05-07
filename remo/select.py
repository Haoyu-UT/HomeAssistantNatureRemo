"""File for selecting signal"""

import logging

import voluptuous as vol

from homeassistant.components.select import (
    ATTR_OPTION,
    SERVICE_SELECT_OPTION,
    SelectEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform

from .api import RemoAPI
from .const import DOMAIN, Appliances, GeneralAppliance, NoSignalError, Signal

_LOGGER = logging.getLogger(__name__)


def extract_general_appliances(properties: dict) -> GeneralAppliance:
    """Build GeneralAppliance from given properties"""
    app_id, app_name = properties["id"], properties["nickname"]
    signals = []
    for signal in properties["signals"]:
        signal_id, signal_name = signal["id"], signal["name"]
        signals.append(Signal(signal_id, signal_name))
    if signals:
        return GeneralAppliance(app_id, app_name, signals)
    else:
        raise NoSignalError


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: entity_platform.AddEntitiesCallback,
) -> None:
    """Set up nature remo appliances from a config entry."""
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SELECT_OPTION,
        {vol.Required(ATTR_OPTION): cv.string},
        SignalEntity.async_select_option.__name__,
    )
    entities = []
    api: RemoAPI = hass.data[DOMAIN][entry.entry_id]["api"]
    appliances: Appliances = await api.fetch_appliance()
    hass.data[DOMAIN][entry.entry_id]["appliances"] = appliances
    hass.data[DOMAIN][entry.entry_id]["gerenal_appliances"] = []
    hass.data[DOMAIN][entry.entry_id]["signal_entities"] = []
    for properties in appliances.others:
        try:
            appliance: GeneralAppliance = extract_general_appliances(properties)
        except NoSignalError:
            logging.exception(
                "appliance %s has no signal binded", properties["nickname"]
            )
        else:
            signal_entity = SignalEntity(appliance)
            hass.data[DOMAIN][entry.entry_id]["signal_entities"].append(signal_entity)
            hass.data[DOMAIN][entry.entry_id]["gerenal_appliances"].append(appliance)
            entities.append(signal_entity)
    async_add_entities(entities)


class SignalEntity(SelectEntity):
    """Class for containing signals"""

    _attr_has_entity_name = True

    def __init__(self, appliance: GeneralAppliance) -> None:
        self._attr_name = f"Signals @ {appliance.name}"
        self._attr_unique_id = f"Signals @ {appliance.id}"
        self.signals: list[Signal] = appliance.signals
        self._attr_options = [
            f"{i+1}. {signal.name}" for i, signal in enumerate(self.signals)
        ]
        self._attr_current_option = self._attr_options[0]
        self.option_idx_map = {option: i for i, option in enumerate(self._attr_options)}
        self.current_option_idx = 0

    def select_option(self, option: str) -> None:
        """Change the selected option."""
        self._attr_current_option = option
        self.current_option_idx = self.option_idx_map[option]

    def get_signal_id(self):
        """Return the signal id of current option"""
        return self.signals[self.current_option_idx].id
